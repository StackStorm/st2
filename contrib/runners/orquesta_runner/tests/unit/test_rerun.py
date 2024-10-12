# Copyright 2020 The StackStorm Authors.
# Copyright 2019 Extreme Networks, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import absolute_import

import mock

import st2tests

import st2tests.config as tests_config

tests_config.parse_args()

from local_runner import local_shell_command_runner
from orquesta import statuses as wf_statuses
from st2common.bootstrap import actionsregistrar
from st2common.bootstrap import runnersregistrar
from st2common.constants import action as action_constants
from st2common.models.db import liveaction as lv_db_models
from st2common.persistence import execution as ex_db_access
from st2common.persistence import liveaction as lv_db_access
from st2common.persistence import workflow as wf_db_access
from st2common.services import action as action_service
from st2common.services import workflows as workflow_service
from st2common.transport import liveaction as lv_ac_xport
from st2common.transport import workflow as wf_ex_xport
from st2common.transport import publishers
from st2tests.fixtures.packs.core.fixture import PACK_PATH as CORE_PACK_PATH
from st2tests.fixtures.packs.orquesta_tests.fixture import PACK_PATH as TEST_PACK_PATH
from st2tests.mocks import liveaction as mock_lv_ac_xport
from st2tests.mocks import workflow as mock_wf_ex_xport


PACKS = [TEST_PACK_PATH, CORE_PACK_PATH]

RUNNER_RESULT_FAILED = (
    action_constants.LIVEACTION_STATUS_FAILED,
    {"stderror": "..."},
    {},
)
RUNNER_RESULT_RUNNING = (
    action_constants.LIVEACTION_STATUS_RUNNING,
    {"stdout": "..."},
    {},
)
RUNNER_RESULT_SUCCEEDED = (
    action_constants.LIVEACTION_STATUS_SUCCEEDED,
    {"stdout": "foobar", "succeeded": True, "failed": False, "stderr": ""},
    {},
)


@mock.patch.object(
    publishers.CUDPublisher, "publish_update", mock.MagicMock(return_value=None)
)
@mock.patch.object(
    lv_ac_xport.LiveActionPublisher,
    "publish_create",
    mock.MagicMock(side_effect=mock_lv_ac_xport.MockLiveActionPublisher.publish_create),
)
@mock.patch.object(
    lv_ac_xport.LiveActionPublisher,
    "publish_state",
    mock.MagicMock(side_effect=mock_lv_ac_xport.MockLiveActionPublisher.publish_state),
)
@mock.patch.object(
    wf_ex_xport.WorkflowExecutionPublisher,
    "publish_create",
    mock.MagicMock(
        side_effect=mock_wf_ex_xport.MockWorkflowExecutionPublisher.publish_create
    ),
)
@mock.patch.object(
    wf_ex_xport.WorkflowExecutionPublisher,
    "publish_state",
    mock.MagicMock(
        side_effect=mock_wf_ex_xport.MockWorkflowExecutionPublisher.publish_state
    ),
)
class OrquestRunnerTest(st2tests.WorkflowTestCase):
    @classmethod
    def setUpClass(cls):
        super(OrquestRunnerTest, cls).setUpClass()

        # Register runners.
        runnersregistrar.register_runners()

        # Register test pack(s).
        actions_registrar = actionsregistrar.ActionsRegistrar(
            use_pack_cache=False, fail_on_failure=True
        )

        for pack in PACKS:
            actions_registrar.register_from_pack(pack)

    @mock.patch.object(
        local_shell_command_runner.LocalShellCommandRunner,
        "run",
        mock.MagicMock(side_effect=[RUNNER_RESULT_FAILED, RUNNER_RESULT_SUCCEEDED]),
    )
    def test_rerun_workflow(self):
        wf_meta = self.get_wf_fixture_meta_data(TEST_PACK_PATH, "sequential.yaml")
        wf_input = {"who": "Thanos"}
        lv_ac_db1 = lv_db_models.LiveActionDB(
            action=wf_meta["name"], parameters=wf_input
        )
        lv_ac_db1, ac_ex_db1 = action_service.request(lv_ac_db1)
        wf_ex_db = wf_db_access.WorkflowExecution.query(
            action_execution=str(ac_ex_db1.id)
        )[0]

        # Process task1.
        query_filters = {"workflow_execution": str(wf_ex_db.id), "task_id": "task1"}
        tk1_ex_db = wf_db_access.TaskExecution.query(**query_filters)[0]
        tk1_ac_ex_db = ex_db_access.ActionExecution.query(
            task_execution=str(tk1_ex_db.id)
        )[0]
        tk1_lv_ac_db = lv_db_access.LiveAction.get_by_id(tk1_ac_ex_db.liveaction["id"])
        self.assertEqual(tk1_lv_ac_db.status, action_constants.LIVEACTION_STATUS_FAILED)
        workflow_service.handle_action_execution_completion(tk1_ac_ex_db)
        tk1_ex_db = wf_db_access.TaskExecution.get_by_id(tk1_ex_db.id)
        self.assertEqual(tk1_ex_db.status, wf_statuses.FAILED)

        # Assert workflow is completed.
        wf_ex_db = wf_db_access.WorkflowExecution.get_by_id(wf_ex_db.id)
        self.assertEqual(wf_ex_db.status, wf_statuses.FAILED)
        lv_ac_db1 = lv_db_access.LiveAction.get_by_id(str(lv_ac_db1.id))
        self.assertEqual(lv_ac_db1.status, action_constants.LIVEACTION_STATUS_FAILED)
        ac_ex_db1 = ex_db_access.ActionExecution.get_by_id(str(ac_ex_db1.id))
        self.assertEqual(ac_ex_db1.status, action_constants.LIVEACTION_STATUS_FAILED)

        # Rerun the execution.
        context = {"re-run": {"ref": str(ac_ex_db1.id), "tasks": ["task1"]}}

        lv_ac_db2 = lv_db_models.LiveActionDB(action=wf_meta["name"], context=context)
        lv_ac_db2, ac_ex_db2 = action_service.request(lv_ac_db2)

        # Assert the workflow reran ok and is running.
        wf_ex_db = wf_db_access.WorkflowExecution.query(
            action_execution=str(ac_ex_db2.id)
        )[0]
        self.assertEqual(wf_ex_db.status, wf_statuses.RUNNING)
        lv_ac_db2 = lv_db_access.LiveAction.get_by_id(str(lv_ac_db2.id))
        self.assertEqual(lv_ac_db2.status, action_constants.LIVEACTION_STATUS_RUNNING)
        ac_ex_db2 = ex_db_access.ActionExecution.get_by_id(str(ac_ex_db2.id))
        self.assertEqual(ac_ex_db2.status, action_constants.LIVEACTION_STATUS_RUNNING)

        # Process task1 and make sure it succeeds.
        query_filters = {"workflow_execution": str(wf_ex_db.id), "task_id": "task1"}
        tk1_ex_dbs = wf_db_access.TaskExecution.query(**query_filters)
        self.assertEqual(len(tk1_ex_dbs), 2)
        tk1_ex_dbs = sorted(tk1_ex_dbs, key=lambda x: x.start_timestamp)
        tk1_ex_db = tk1_ex_dbs[-1]
        tk1_ac_ex_db = ex_db_access.ActionExecution.query(
            task_execution=str(tk1_ex_db.id)
        )[0]
        tk1_lv_ac_db = lv_db_access.LiveAction.get_by_id(tk1_ac_ex_db.liveaction["id"])
        self.assertEqual(
            tk1_lv_ac_db.status, action_constants.LIVEACTION_STATUS_SUCCEEDED
        )
        workflow_service.handle_action_execution_completion(tk1_ac_ex_db)
        tk1_ex_db = wf_db_access.TaskExecution.get_by_id(tk1_ex_db.id)
        self.assertEqual(tk1_ex_db.status, wf_statuses.SUCCEEDED)

    @mock.patch.object(
        local_shell_command_runner.LocalShellCommandRunner,
        "run",
        mock.MagicMock(side_effect=[RUNNER_RESULT_FAILED]),
    )
    def test_rerun_with_missing_workflow_execution_id(self):
        wf_meta = self.get_wf_fixture_meta_data(TEST_PACK_PATH, "sequential.yaml")
        wf_input = {"who": "Thanos"}
        lv_ac_db1 = lv_db_models.LiveActionDB(
            action=wf_meta["name"], parameters=wf_input
        )
        lv_ac_db1, ac_ex_db1 = action_service.request(lv_ac_db1)
        wf_ex_db = wf_db_access.WorkflowExecution.query(
            action_execution=str(ac_ex_db1.id)
        )[0]

        # Process task1.
        query_filters = {"workflow_execution": str(wf_ex_db.id), "task_id": "task1"}
        tk1_ex_db = wf_db_access.TaskExecution.query(**query_filters)[0]
        tk1_ac_ex_db = ex_db_access.ActionExecution.query(
            task_execution=str(tk1_ex_db.id)
        )[0]
        tk1_lv_ac_db = lv_db_access.LiveAction.get_by_id(tk1_ac_ex_db.liveaction["id"])
        self.assertEqual(tk1_lv_ac_db.status, action_constants.LIVEACTION_STATUS_FAILED)
        workflow_service.handle_action_execution_completion(tk1_ac_ex_db)
        tk1_ex_db = wf_db_access.TaskExecution.get_by_id(tk1_ex_db.id)
        self.assertEqual(tk1_ex_db.status, wf_statuses.FAILED)

        # Assert workflow is completed.
        wf_ex_db = wf_db_access.WorkflowExecution.get_by_id(wf_ex_db.id)
        self.assertEqual(wf_ex_db.status, wf_statuses.FAILED)
        lv_ac_db1 = lv_db_access.LiveAction.get_by_id(str(lv_ac_db1.id))
        self.assertEqual(lv_ac_db1.status, action_constants.LIVEACTION_STATUS_FAILED)
        ac_ex_db1 = ex_db_access.ActionExecution.get_by_id(str(ac_ex_db1.id))
        self.assertEqual(ac_ex_db1.status, action_constants.LIVEACTION_STATUS_FAILED)

        # Delete the workflow execution.
        wf_db_access.WorkflowExecution.delete(wf_ex_db, publish=False)

        # Manually delete the workflow_execution_id from context of the liveaction.
        lv_ac_db1.context.pop("workflow_execution")
        lv_ac_db1 = lv_db_access.LiveAction.add_or_update(lv_ac_db1, publish=False)
        # Manually delete the workflow_execution_id from context of the action execution.
        # We cannot use execution_service.update_execution here because by the time we reach
        # execution_service.update_execution, action is already in completed state.
        # Popping of workflow id and and updating the execution object will not work.
        ac_ex_db1.context.pop("workflow_execution")
        ac_ex_db1 = ex_db_access.ActionExecution.add_or_update(ac_ex_db1, publish=False)

        # Rerun the execution.
        context = {"re-run": {"ref": str(ac_ex_db1.id), "tasks": ["task1"]}}

        lv_ac_db2 = lv_db_models.LiveActionDB(action=wf_meta["name"], context=context)
        lv_ac_db2, ac_ex_db2 = action_service.request(lv_ac_db2)

        expected_error = (
            "Unable to rerun workflow execution because "
            "workflow_execution_id is not provided."
        )

        # Assert the workflow rerrun fails.
        lv_ac_db2 = lv_db_access.LiveAction.get_by_id(str(lv_ac_db2.id))
        self.assertEqual(lv_ac_db2.status, action_constants.LIVEACTION_STATUS_FAILED)
        self.assertEqual(expected_error, lv_ac_db2.result["errors"][0]["message"])
        ac_ex_db2 = ex_db_access.ActionExecution.get_by_id(str(ac_ex_db2.id))
        self.assertEqual(ac_ex_db2.status, action_constants.LIVEACTION_STATUS_FAILED)
        self.assertEqual(expected_error, ac_ex_db2.result["errors"][0]["message"])

    @mock.patch.object(
        local_shell_command_runner.LocalShellCommandRunner,
        "run",
        mock.MagicMock(side_effect=[RUNNER_RESULT_FAILED]),
    )
    def test_rerun_with_invalid_workflow_execution(self):
        wf_meta = self.get_wf_fixture_meta_data(TEST_PACK_PATH, "sequential.yaml")
        wf_input = {"who": "Thanos"}
        lv_ac_db1 = lv_db_models.LiveActionDB(
            action=wf_meta["name"], parameters=wf_input
        )
        lv_ac_db1, ac_ex_db1 = action_service.request(lv_ac_db1)
        wf_ex_db = wf_db_access.WorkflowExecution.query(
            action_execution=str(ac_ex_db1.id)
        )[0]

        # Process task1.
        query_filters = {"workflow_execution": str(wf_ex_db.id), "task_id": "task1"}
        tk1_ex_db = wf_db_access.TaskExecution.query(**query_filters)[0]
        tk1_ac_ex_db = ex_db_access.ActionExecution.query(
            task_execution=str(tk1_ex_db.id)
        )[0]
        tk1_lv_ac_db = lv_db_access.LiveAction.get_by_id(tk1_ac_ex_db.liveaction["id"])
        self.assertEqual(tk1_lv_ac_db.status, action_constants.LIVEACTION_STATUS_FAILED)
        workflow_service.handle_action_execution_completion(tk1_ac_ex_db)
        tk1_ex_db = wf_db_access.TaskExecution.get_by_id(tk1_ex_db.id)
        self.assertEqual(tk1_ex_db.status, wf_statuses.FAILED)

        # Assert workflow is completed.
        wf_ex_db = wf_db_access.WorkflowExecution.get_by_id(wf_ex_db.id)
        self.assertEqual(wf_ex_db.status, wf_statuses.FAILED)
        lv_ac_db1 = lv_db_access.LiveAction.get_by_id(str(lv_ac_db1.id))
        self.assertEqual(lv_ac_db1.status, action_constants.LIVEACTION_STATUS_FAILED)
        ac_ex_db1 = ex_db_access.ActionExecution.get_by_id(str(ac_ex_db1.id))
        self.assertEqual(ac_ex_db1.status, action_constants.LIVEACTION_STATUS_FAILED)

        # Delete the workflow execution.
        wf_db_access.WorkflowExecution.delete(wf_ex_db, publish=False)

        # Rerun the execution.
        context = {"re-run": {"ref": str(ac_ex_db1.id), "tasks": ["task1"]}}

        lv_ac_db2 = lv_db_models.LiveActionDB(action=wf_meta["name"], context=context)
        lv_ac_db2, ac_ex_db2 = action_service.request(lv_ac_db2)

        expected_error = (
            'Unable to rerun workflow execution "%s" because '
            "it does not exist." % str(wf_ex_db.id)
        )

        # Assert the workflow rerrun fails.
        lv_ac_db2 = lv_db_access.LiveAction.get_by_id(str(lv_ac_db2.id))
        self.assertEqual(lv_ac_db2.status, action_constants.LIVEACTION_STATUS_FAILED)
        self.assertEqual(expected_error, lv_ac_db2.result["errors"][0]["message"])
        ac_ex_db2 = ex_db_access.ActionExecution.get_by_id(str(ac_ex_db2.id))
        self.assertEqual(ac_ex_db2.status, action_constants.LIVEACTION_STATUS_FAILED)
        self.assertEqual(expected_error, ac_ex_db2.result["errors"][0]["message"])

    @mock.patch.object(
        local_shell_command_runner.LocalShellCommandRunner,
        "run",
        mock.MagicMock(side_effect=[RUNNER_RESULT_RUNNING]),
    )
    def test_rerun_workflow_still_running(self):
        wf_meta = self.get_wf_fixture_meta_data(TEST_PACK_PATH, "sequential.yaml")
        wf_input = {"who": "Thanos"}
        lv_ac_db1 = lv_db_models.LiveActionDB(
            action=wf_meta["name"], parameters=wf_input
        )
        lv_ac_db1, ac_ex_db1 = action_service.request(lv_ac_db1)
        wf_ex_db = wf_db_access.WorkflowExecution.query(
            action_execution=str(ac_ex_db1.id)
        )[0]

        # Process task1.
        query_filters = {"workflow_execution": str(wf_ex_db.id), "task_id": "task1"}
        tk1_ex_db = wf_db_access.TaskExecution.query(**query_filters)[0]
        tk1_ac_ex_db = ex_db_access.ActionExecution.query(
            task_execution=str(tk1_ex_db.id)
        )[0]
        tk1_lv_ac_db = lv_db_access.LiveAction.get_by_id(tk1_ac_ex_db.liveaction["id"])
        self.assertEqual(
            tk1_lv_ac_db.status, action_constants.LIVEACTION_STATUS_RUNNING
        )

        # Assert workflow is still running.
        wf_ex_db = wf_db_access.WorkflowExecution.get_by_id(wf_ex_db.id)
        self.assertEqual(wf_ex_db.status, wf_statuses.RUNNING)
        lv_ac_db1 = lv_db_access.LiveAction.get_by_id(str(lv_ac_db1.id))
        self.assertEqual(lv_ac_db1.status, action_constants.LIVEACTION_STATUS_RUNNING)
        ac_ex_db1 = ex_db_access.ActionExecution.get_by_id(str(ac_ex_db1.id))
        self.assertEqual(ac_ex_db1.status, action_constants.LIVEACTION_STATUS_RUNNING)

        # Rerun the execution.
        context = {"re-run": {"ref": str(ac_ex_db1.id), "tasks": ["task1"]}}

        lv_ac_db2 = lv_db_models.LiveActionDB(action=wf_meta["name"], context=context)
        lv_ac_db2, ac_ex_db2 = action_service.request(lv_ac_db2)

        expected_error = (
            'Unable to rerun workflow execution "%s" because '
            "it is not in a completed state." % str(wf_ex_db.id)
        )

        # Assert the workflow rerrun fails.
        lv_ac_db2 = lv_db_access.LiveAction.get_by_id(str(lv_ac_db2.id))
        self.assertEqual(lv_ac_db2.status, action_constants.LIVEACTION_STATUS_FAILED)
        self.assertEqual(expected_error, lv_ac_db2.result["errors"][0]["message"])
        ac_ex_db2 = ex_db_access.ActionExecution.get_by_id(str(ac_ex_db2.id))
        self.assertEqual(ac_ex_db2.status, action_constants.LIVEACTION_STATUS_FAILED)
        self.assertEqual(expected_error, ac_ex_db2.result["errors"][0]["message"])

    @mock.patch.object(
        workflow_service,
        "request_rerun",
        mock.MagicMock(side_effect=Exception("Unexpected.")),
    )
    @mock.patch.object(
        local_shell_command_runner.LocalShellCommandRunner,
        "run",
        mock.MagicMock(side_effect=[RUNNER_RESULT_FAILED]),
    )
    def test_rerun_with_unexpected_error(self):
        wf_meta = self.get_wf_fixture_meta_data(TEST_PACK_PATH, "sequential.yaml")
        wf_input = {"who": "Thanos"}
        lv_ac_db1 = lv_db_models.LiveActionDB(
            action=wf_meta["name"], parameters=wf_input
        )
        lv_ac_db1, ac_ex_db1 = action_service.request(lv_ac_db1)
        wf_ex_db = wf_db_access.WorkflowExecution.query(
            action_execution=str(ac_ex_db1.id)
        )[0]

        # Process task1.
        query_filters = {"workflow_execution": str(wf_ex_db.id), "task_id": "task1"}
        tk1_ex_db = wf_db_access.TaskExecution.query(**query_filters)[0]
        tk1_ac_ex_db = ex_db_access.ActionExecution.query(
            task_execution=str(tk1_ex_db.id)
        )[0]
        tk1_lv_ac_db = lv_db_access.LiveAction.get_by_id(tk1_ac_ex_db.liveaction["id"])
        self.assertEqual(tk1_lv_ac_db.status, action_constants.LIVEACTION_STATUS_FAILED)
        workflow_service.handle_action_execution_completion(tk1_ac_ex_db)
        tk1_ex_db = wf_db_access.TaskExecution.get_by_id(tk1_ex_db.id)
        self.assertEqual(tk1_ex_db.status, wf_statuses.FAILED)

        # Assert workflow is completed.
        wf_ex_db = wf_db_access.WorkflowExecution.get_by_id(wf_ex_db.id)
        self.assertEqual(wf_ex_db.status, wf_statuses.FAILED)
        lv_ac_db1 = lv_db_access.LiveAction.get_by_id(str(lv_ac_db1.id))
        self.assertEqual(lv_ac_db1.status, action_constants.LIVEACTION_STATUS_FAILED)
        ac_ex_db1 = ex_db_access.ActionExecution.get_by_id(str(ac_ex_db1.id))
        self.assertEqual(ac_ex_db1.status, action_constants.LIVEACTION_STATUS_FAILED)

        # Delete the workflow execution.
        wf_db_access.WorkflowExecution.delete(wf_ex_db, publish=False)

        # Rerun the execution.
        context = {"re-run": {"ref": str(ac_ex_db1.id), "tasks": ["task1"]}}

        lv_ac_db2 = lv_db_models.LiveActionDB(action=wf_meta["name"], context=context)
        lv_ac_db2, ac_ex_db2 = action_service.request(lv_ac_db2)

        expected_error = "Unexpected."

        # Assert the workflow rerrun fails.
        lv_ac_db2 = lv_db_access.LiveAction.get_by_id(str(lv_ac_db2.id))
        self.assertEqual(lv_ac_db2.status, action_constants.LIVEACTION_STATUS_FAILED)
        self.assertEqual(expected_error, lv_ac_db2.result["errors"][0]["message"])
        ac_ex_db2 = ex_db_access.ActionExecution.get_by_id(str(ac_ex_db2.id))
        self.assertEqual(ac_ex_db2.status, action_constants.LIVEACTION_STATUS_FAILED)
        self.assertEqual(expected_error, ac_ex_db2.result["errors"][0]["message"])

    @mock.patch.object(
        local_shell_command_runner.LocalShellCommandRunner,
        "run",
        mock.MagicMock(return_value=RUNNER_RESULT_SUCCEEDED),
    )
    def test_rerun_workflow_already_succeeded(self):
        wf_meta = self.get_wf_fixture_meta_data(TEST_PACK_PATH, "sequential.yaml")
        wf_input = {"who": "Thanos"}
        lv_ac_db1 = lv_db_models.LiveActionDB(
            action=wf_meta["name"], parameters=wf_input
        )
        lv_ac_db1, ac_ex_db1 = action_service.request(lv_ac_db1)
        wf_ex_db = wf_db_access.WorkflowExecution.query(
            action_execution=str(ac_ex_db1.id)
        )[0]

        # Process task1.
        query_filters = {"workflow_execution": str(wf_ex_db.id), "task_id": "task1"}
        tk1_ex_db = wf_db_access.TaskExecution.query(**query_filters)[0]
        tk1_ac_ex_db = ex_db_access.ActionExecution.query(
            task_execution=str(tk1_ex_db.id)
        )[0]
        tk1_lv_ac_db = lv_db_access.LiveAction.get_by_id(tk1_ac_ex_db.liveaction["id"])
        self.assertEqual(
            tk1_lv_ac_db.status, action_constants.LIVEACTION_STATUS_SUCCEEDED
        )
        workflow_service.handle_action_execution_completion(tk1_ac_ex_db)
        tk1_ex_db = wf_db_access.TaskExecution.get_by_id(tk1_ex_db.id)
        self.assertEqual(tk1_ex_db.status, wf_statuses.SUCCEEDED)

        # Process task2.
        query_filters = {"workflow_execution": str(wf_ex_db.id), "task_id": "task2"}
        tk2_ex_db = wf_db_access.TaskExecution.query(**query_filters)[0]
        tk2_ac_ex_db = ex_db_access.ActionExecution.query(
            task_execution=str(tk2_ex_db.id)
        )[0]
        tk2_lv_ac_db = lv_db_access.LiveAction.get_by_id(tk2_ac_ex_db.liveaction["id"])
        self.assertEqual(
            tk2_lv_ac_db.status, action_constants.LIVEACTION_STATUS_SUCCEEDED
        )
        workflow_service.handle_action_execution_completion(tk2_ac_ex_db)
        tk2_ex_db = wf_db_access.TaskExecution.get_by_id(tk2_ex_db.id)
        self.assertEqual(tk2_ex_db.status, wf_statuses.SUCCEEDED)

        # Process task3.
        query_filters = {"workflow_execution": str(wf_ex_db.id), "task_id": "task3"}
        tk3_ex_db = wf_db_access.TaskExecution.query(**query_filters)[0]
        tk3_ac_ex_db = ex_db_access.ActionExecution.query(
            task_execution=str(tk3_ex_db.id)
        )[0]
        tk3_lv_ac_db = lv_db_access.LiveAction.get_by_id(tk3_ac_ex_db.liveaction["id"])
        self.assertEqual(
            tk3_lv_ac_db.status, action_constants.LIVEACTION_STATUS_SUCCEEDED
        )
        workflow_service.handle_action_execution_completion(tk3_ac_ex_db)
        tk3_ex_db = wf_db_access.TaskExecution.get_by_id(tk3_ex_db.id)
        self.assertEqual(tk3_ex_db.status, wf_statuses.SUCCEEDED)

        # Assert workflow is completed.
        wf_ex_db = wf_db_access.WorkflowExecution.get_by_id(wf_ex_db.id)
        self.assertEqual(wf_ex_db.status, wf_statuses.SUCCEEDED)
        lv_ac_db1 = lv_db_access.LiveAction.get_by_id(str(lv_ac_db1.id))
        self.assertEqual(lv_ac_db1.status, action_constants.LIVEACTION_STATUS_SUCCEEDED)
        ac_ex_db1 = ex_db_access.ActionExecution.get_by_id(str(ac_ex_db1.id))
        self.assertEqual(ac_ex_db1.status, action_constants.LIVEACTION_STATUS_SUCCEEDED)

        # Rerun the execution.
        context = {"re-run": {"ref": str(ac_ex_db1.id), "tasks": ["task1"]}}

        lv_ac_db2 = lv_db_models.LiveActionDB(action=wf_meta["name"], context=context)
        lv_ac_db2, ac_ex_db2 = action_service.request(lv_ac_db2)

        # Assert the workflow reran ok and is running.
        wf_ex_db = wf_db_access.WorkflowExecution.query(
            action_execution=str(ac_ex_db2.id)
        )[0]
        self.assertEqual(wf_ex_db.status, wf_statuses.RUNNING)
        lv_ac_db2 = lv_db_access.LiveAction.get_by_id(str(lv_ac_db2.id))
        self.assertEqual(lv_ac_db2.status, action_constants.LIVEACTION_STATUS_RUNNING)
        ac_ex_db2 = ex_db_access.ActionExecution.get_by_id(str(ac_ex_db2.id))
        self.assertEqual(ac_ex_db2.status, action_constants.LIVEACTION_STATUS_RUNNING)

        # Assert there are two task1 and the last entry succeeded.
        query_filters = {"workflow_execution": str(wf_ex_db.id), "task_id": "task1"}
        tk1_ex_dbs = wf_db_access.TaskExecution.query(**query_filters)
        self.assertEqual(len(tk1_ex_dbs), 2)
        tk1_ex_dbs = sorted(tk1_ex_dbs, key=lambda x: x.start_timestamp)
        tk1_ex_db = tk1_ex_dbs[-1]
        tk1_ac_ex_db = ex_db_access.ActionExecution.query(
            task_execution=str(tk1_ex_db.id)
        )[0]
        tk1_lv_ac_db = lv_db_access.LiveAction.get_by_id(tk1_ac_ex_db.liveaction["id"])
        self.assertEqual(
            tk1_lv_ac_db.status, action_constants.LIVEACTION_STATUS_SUCCEEDED
        )
        workflow_service.handle_action_execution_completion(tk1_ac_ex_db)
        tk1_ex_db = wf_db_access.TaskExecution.get_by_id(tk1_ex_db.id)
        self.assertEqual(tk1_ex_db.status, wf_statuses.SUCCEEDED)

        # Assert there are two task2 and the last entry succeeded.
        query_filters = {"workflow_execution": str(wf_ex_db.id), "task_id": "task2"}
        tk2_ex_dbs = wf_db_access.TaskExecution.query(**query_filters)
        self.assertEqual(len(tk2_ex_dbs), 2)
        tk2_ex_dbs = sorted(tk2_ex_dbs, key=lambda x: x.start_timestamp)
        tk2_ex_db = tk2_ex_dbs[-1]
        tk2_ac_ex_db = ex_db_access.ActionExecution.query(
            task_execution=str(tk2_ex_db.id)
        )[0]
        tk2_lv_ac_db = lv_db_access.LiveAction.get_by_id(tk2_ac_ex_db.liveaction["id"])
        self.assertEqual(
            tk2_lv_ac_db.status, action_constants.LIVEACTION_STATUS_SUCCEEDED
        )
        workflow_service.handle_action_execution_completion(tk2_ac_ex_db)
        tk2_ex_db = wf_db_access.TaskExecution.get_by_id(tk2_ex_db.id)
        self.assertEqual(tk2_ex_db.status, wf_statuses.SUCCEEDED)

        # Assert there are two task3 and the last entry succeeded.
        query_filters = {"workflow_execution": str(wf_ex_db.id), "task_id": "task3"}
        tk3_ex_dbs = wf_db_access.TaskExecution.query(**query_filters)
        self.assertEqual(len(tk3_ex_dbs), 2)
        tk3_ex_dbs = sorted(tk3_ex_dbs, key=lambda x: x.start_timestamp)
        tk3_ex_db = tk3_ex_dbs[-1]
        tk3_ac_ex_db = ex_db_access.ActionExecution.query(
            task_execution=str(tk3_ex_db.id)
        )[0]
        tk3_lv_ac_db = lv_db_access.LiveAction.get_by_id(tk3_ac_ex_db.liveaction["id"])
        self.assertEqual(
            tk3_lv_ac_db.status, action_constants.LIVEACTION_STATUS_SUCCEEDED
        )
        workflow_service.handle_action_execution_completion(tk3_ac_ex_db)
        tk3_ex_db = wf_db_access.TaskExecution.get_by_id(tk3_ex_db.id)
        self.assertEqual(tk3_ex_db.status, wf_statuses.SUCCEEDED)

        # Assert workflow is completed.
        wf_ex_db = wf_db_access.WorkflowExecution.get_by_id(wf_ex_db.id)
        self.assertEqual(wf_ex_db.status, wf_statuses.SUCCEEDED)
        lv_ac_db1 = lv_db_access.LiveAction.get_by_id(str(lv_ac_db1.id))
        self.assertEqual(lv_ac_db1.status, action_constants.LIVEACTION_STATUS_SUCCEEDED)
        ac_ex_db1 = ex_db_access.ActionExecution.get_by_id(str(ac_ex_db1.id))
        self.assertEqual(ac_ex_db1.status, action_constants.LIVEACTION_STATUS_SUCCEEDED)

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

from orquesta import statuses as wf_statuses

import st2tests

from oslo_config import cfg

# XXX: actionsensor import depends on config being setup.
import st2tests.config as tests_config

tests_config.parse_args()

from tests.unit import base

from local_runner import local_shell_command_runner
from st2actions.workflows import workflows
from st2common.bootstrap import actionsregistrar
from st2common.bootstrap import runnersregistrar
from st2common.constants import action as action_constants
from st2common.models.db import liveaction as lv_db_models
from st2common.persistence import execution as ex_db_access
from st2common.persistence import liveaction as lv_db_access
from st2common.persistence import workflow as wf_db_access
from st2common.runners import base as runners
from st2common.services import action as action_service
from st2common.services import executions as execution_service
from st2common.transport import liveaction as lv_ac_xport
from st2common.transport import workflow as wf_ex_xport
from st2common.transport import publishers
from st2common.util import action_db as action_utils
from st2tests.fixtures.packs.core.fixture import PACK_PATH as CORE_PACK_PATH
from st2tests.fixtures.packs.orquesta_tests.fixture import PACK_PATH as TEST_PACK_PATH
from st2tests.mocks import liveaction as mock_lv_ac_xport
from st2tests.mocks import workflow as mock_wf_ex_xport


PACKS = [TEST_PACK_PATH, CORE_PACK_PATH]

RUNNER_RESULT_RUNNING = (
    action_constants.LIVEACTION_STATUS_RUNNING,
    {"stdout": "...", "stderr": ""},
    {},
)

RUNNER_RESULT_SUCCEEDED = (
    action_constants.LIVEACTION_STATUS_SUCCEEDED,
    {"stdout": "...", "stderr": "", "succeeded": True, "failed": False},
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
class OrquestaWithItemsTest(st2tests.ExecutionDbTestCase):
    @classmethod
    def setUpClass(cls):
        super(OrquestaWithItemsTest, cls).setUpClass()

        # Register runners.
        runnersregistrar.register_runners()

        # Register test pack(s).
        actions_registrar = actionsregistrar.ActionsRegistrar(
            use_pack_cache=False, fail_on_failure=True
        )

        for pack in PACKS:
            actions_registrar.register_from_pack(pack)

    @classmethod
    def get_runner_class(cls, runner_name):
        return runners.get_runner(runner_name, runner_name).__class__

    def set_execution_status(self, lv_ac_db_id, status):
        lv_ac_db = action_utils.update_liveaction_status(
            status=status, liveaction_id=lv_ac_db_id, publish=False
        )

        ac_ex_db = execution_service.update_execution(lv_ac_db, publish=False)

        return lv_ac_db, ac_ex_db

    def test_with_items(self):
        num_items = 3

        wf_meta = base.get_wf_fixture_meta_data(TEST_PACK_PATH, "with-items.yaml")
        lv_ac_db = lv_db_models.LiveActionDB(action=wf_meta["name"])
        lv_ac_db, ac_ex_db = action_service.request(lv_ac_db)

        # Assert action execution is running.
        lv_ac_db = lv_db_access.LiveAction.get_by_id(str(lv_ac_db.id))
        self.assertEqual(lv_ac_db.status, action_constants.LIVEACTION_STATUS_RUNNING)
        wf_ex_db = wf_db_access.WorkflowExecution.query(
            action_execution=str(ac_ex_db.id)
        )[0]
        self.assertEqual(wf_ex_db.status, action_constants.LIVEACTION_STATUS_RUNNING)

        # Process the with items task.
        query_filters = {"workflow_execution": str(wf_ex_db.id), "task_id": "task1"}
        t1_ex_db = wf_db_access.TaskExecution.query(**query_filters)[0]
        t1_ac_ex_dbs = ex_db_access.ActionExecution.query(
            task_execution=str(t1_ex_db.id)
        )

        self.assertEqual(len(t1_ac_ex_dbs), num_items)

        status = [
            ac_ex.status == action_constants.LIVEACTION_STATUS_SUCCEEDED
            for ac_ex in t1_ac_ex_dbs
        ]

        self.assertTrue(all(status))

        for t1_ac_ex_db in t1_ac_ex_dbs:
            workflows.get_engine().process(t1_ac_ex_db)

        t1_ex_db = wf_db_access.TaskExecution.get_by_id(t1_ex_db.id)
        self.assertEqual(t1_ex_db.status, wf_statuses.SUCCEEDED)

        # Assert the main workflow is completed.
        wf_ex_db = wf_db_access.WorkflowExecution.get_by_id(wf_ex_db.id)
        self.assertEqual(wf_ex_db.status, wf_statuses.SUCCEEDED)
        lv_ac_db = lv_db_access.LiveAction.get_by_id(str(lv_ac_db.id))
        self.assertEqual(lv_ac_db.status, action_constants.LIVEACTION_STATUS_SUCCEEDED)

    def test_with_items_failure(self):
        num_items = 10

        wf_meta = base.get_wf_fixture_meta_data(
            TEST_PACK_PATH, "with-items-failure.yaml"
        )
        lv_ac_db = lv_db_models.LiveActionDB(action=wf_meta["name"])
        lv_ac_db, ac_ex_db = action_service.request(lv_ac_db)

        # Assert action execution is running.
        lv_ac_db = lv_db_access.LiveAction.get_by_id(str(lv_ac_db.id))
        self.assertEqual(lv_ac_db.status, action_constants.LIVEACTION_STATUS_RUNNING)
        wf_ex_db = wf_db_access.WorkflowExecution.query(
            action_execution=str(ac_ex_db.id)
        )[0]
        self.assertEqual(wf_ex_db.status, action_constants.LIVEACTION_STATUS_RUNNING)

        # Process the with items task.
        query_filters = {"workflow_execution": str(wf_ex_db.id), "task_id": "task1"}
        t1_ex_db = wf_db_access.TaskExecution.query(**query_filters)[0]
        t1_ac_ex_dbs = ex_db_access.ActionExecution.query(
            task_execution=str(t1_ex_db.id)
        )

        self.assertEqual(len(t1_ac_ex_dbs), num_items)

        for i in range(0, num_items):
            if not i % 2:
                expected_status = action_constants.LIVEACTION_STATUS_SUCCEEDED
            else:
                expected_status = action_constants.LIVEACTION_STATUS_FAILED

            self.assertEqual(t1_ac_ex_dbs[i].status, expected_status)

        for t1_ac_ex_db in t1_ac_ex_dbs:
            workflows.get_engine().process(t1_ac_ex_db)

        t1_ex_db = wf_db_access.TaskExecution.get_by_id(t1_ex_db.id)
        self.assertEqual(t1_ex_db.status, wf_statuses.FAILED)

        # Assert the main workflow is completed.
        wf_ex_db = wf_db_access.WorkflowExecution.get_by_id(wf_ex_db.id)
        self.assertEqual(wf_ex_db.status, wf_statuses.FAILED)
        lv_ac_db = lv_db_access.LiveAction.get_by_id(str(lv_ac_db.id))
        self.assertEqual(lv_ac_db.status, action_constants.LIVEACTION_STATUS_FAILED)

    def test_with_items_empty_list(self):
        items = []
        num_items = len(items)
        wf_input = {"members": items}

        wf_meta = base.get_wf_fixture_meta_data(TEST_PACK_PATH, "with-items.yaml")
        lv_ac_db = lv_db_models.LiveActionDB(
            action=wf_meta["name"], parameters=wf_input
        )
        lv_ac_db, ac_ex_db = action_service.request(lv_ac_db)

        # Wait for the liveaction to complete.
        lv_ac_db = self._wait_on_status(
            lv_ac_db, action_constants.LIVEACTION_STATUS_SUCCEEDED
        )

        # Retrieve records from database.
        wf_ex_db = wf_db_access.WorkflowExecution.query(
            action_execution=str(ac_ex_db.id)
        )[0]
        query_filters = {"workflow_execution": str(wf_ex_db.id), "task_id": "task1"}
        t1_ex_db = wf_db_access.TaskExecution.query(**query_filters)[0]
        t1_ac_ex_dbs = ex_db_access.ActionExecution.query(
            task_execution=str(t1_ex_db.id)
        )

        # Ensure there is no action executions for the task and the task is already completed.
        self.assertEqual(len(t1_ac_ex_dbs), num_items)
        self.assertEqual(t1_ex_db.status, wf_statuses.SUCCEEDED)
        self.assertDictEqual(t1_ex_db.result, {"items": []})

        # Assert the main workflow is completed.
        wf_ex_db = wf_db_access.WorkflowExecution.get_by_id(wf_ex_db.id)
        self.assertEqual(wf_ex_db.status, wf_statuses.SUCCEEDED)
        lv_ac_db = lv_db_access.LiveAction.get_by_id(str(lv_ac_db.id))
        self.assertEqual(lv_ac_db.status, action_constants.LIVEACTION_STATUS_SUCCEEDED)
        self.assertDictEqual(lv_ac_db.result, {"output": {"items": []}})

    def test_with_items_concurrency(self):
        num_items = 3
        concurrency = 2

        wf_input = {"concurrency": concurrency}
        wf_meta = base.get_wf_fixture_meta_data(
            TEST_PACK_PATH, "with-items-concurrency.yaml"
        )
        lv_ac_db = lv_db_models.LiveActionDB(
            action=wf_meta["name"], parameters=wf_input
        )
        lv_ac_db, ac_ex_db = action_service.request(lv_ac_db)

        # Assert action execution is running.
        lv_ac_db = lv_db_access.LiveAction.get_by_id(str(lv_ac_db.id))
        self.assertEqual(lv_ac_db.status, action_constants.LIVEACTION_STATUS_RUNNING)
        wf_ex_db = wf_db_access.WorkflowExecution.query(
            action_execution=str(ac_ex_db.id)
        )[0]
        self.assertEqual(wf_ex_db.status, action_constants.LIVEACTION_STATUS_RUNNING)

        # Process the first set of action executions from with items concurrency.
        query_filters = {"workflow_execution": str(wf_ex_db.id), "task_id": "task1"}
        t1_ex_db = wf_db_access.TaskExecution.query(**query_filters)[0]
        t1_ac_ex_dbs = ex_db_access.ActionExecution.query(
            task_execution=str(t1_ex_db.id)
        )

        self.assertEqual(len(t1_ac_ex_dbs), concurrency)

        status = [
            ac_ex.status == action_constants.LIVEACTION_STATUS_SUCCEEDED
            for ac_ex in t1_ac_ex_dbs
        ]

        self.assertTrue(all(status))

        for t1_ac_ex_db in t1_ac_ex_dbs:
            workflows.get_engine().process(t1_ac_ex_db)

        t1_ex_db = wf_db_access.TaskExecution.get_by_id(t1_ex_db.id)
        self.assertEqual(t1_ex_db.status, wf_statuses.RUNNING)

        wf_ex_db = wf_db_access.WorkflowExecution.get_by_id(wf_ex_db.id)
        self.assertEqual(wf_ex_db.status, wf_statuses.RUNNING)

        # Process the second set of action executions from with items concurrency.
        t1_ac_ex_dbs = ex_db_access.ActionExecution.query(
            task_execution=str(t1_ex_db.id)
        )

        self.assertEqual(len(t1_ac_ex_dbs), num_items)

        status = [
            ac_ex.status == action_constants.LIVEACTION_STATUS_SUCCEEDED
            for ac_ex in t1_ac_ex_dbs
        ]

        self.assertTrue(all(status))

        for t1_ac_ex_db in t1_ac_ex_dbs[concurrency:]:
            workflows.get_engine().process(t1_ac_ex_db)

        t1_ex_db = wf_db_access.TaskExecution.get_by_id(t1_ex_db.id)
        self.assertEqual(t1_ex_db.status, wf_statuses.SUCCEEDED)

        # Assert the main workflow is completed.
        wf_ex_db = wf_db_access.WorkflowExecution.get_by_id(wf_ex_db.id)
        self.assertEqual(wf_ex_db.status, wf_statuses.SUCCEEDED)
        lv_ac_db = lv_db_access.LiveAction.get_by_id(str(lv_ac_db.id))
        self.assertEqual(lv_ac_db.status, action_constants.LIVEACTION_STATUS_SUCCEEDED)

    @mock.patch.object(
        local_shell_command_runner.LocalShellCommandRunner,
        "run",
        mock.MagicMock(return_value=RUNNER_RESULT_RUNNING),
    )
    def test_with_items_cancellation(self):
        num_items = 3

        wf_meta = base.get_wf_fixture_meta_data(
            TEST_PACK_PATH, "with-items-concurrency.yaml"
        )
        lv_ac_db = lv_db_models.LiveActionDB(action=wf_meta["name"])
        lv_ac_db, ac_ex_db = action_service.request(lv_ac_db)

        # Assert the workflow execution is running.
        lv_ac_db = lv_db_access.LiveAction.get_by_id(str(lv_ac_db.id))
        self.assertEqual(lv_ac_db.status, action_constants.LIVEACTION_STATUS_RUNNING)
        wf_ex_db = wf_db_access.WorkflowExecution.query(
            action_execution=str(ac_ex_db.id)
        )[0]
        self.assertEqual(wf_ex_db.status, action_constants.LIVEACTION_STATUS_RUNNING)

        query_filters = {"workflow_execution": str(wf_ex_db.id), "task_id": "task1"}
        t1_ex_db = wf_db_access.TaskExecution.query(**query_filters)[0]
        t1_ac_ex_dbs = ex_db_access.ActionExecution.query(
            task_execution=str(t1_ex_db.id)
        )
        self.assertEqual(t1_ex_db.status, wf_statuses.RUNNING)
        self.assertEqual(len(t1_ac_ex_dbs), num_items)

        status = [
            ac_ex.status == action_constants.LIVEACTION_STATUS_RUNNING
            for ac_ex in t1_ac_ex_dbs
        ]

        self.assertTrue(all(status))

        # Cancels the workflow execution.
        requester = cfg.CONF.system_user.user
        lv_ac_db, ac_ex_db = action_service.request_cancellation(lv_ac_db, requester)
        lv_ac_db = lv_db_access.LiveAction.get_by_id(str(lv_ac_db.id))
        self.assertEqual(lv_ac_db.status, action_constants.LIVEACTION_STATUS_CANCELING)

        # Manually succeed the action executions and process completion.
        for ac_ex in t1_ac_ex_dbs:
            self.set_execution_status(
                ac_ex.liveaction["id"], action_constants.LIVEACTION_STATUS_SUCCEEDED
            )

        t1_ac_ex_dbs = ex_db_access.ActionExecution.query(
            task_execution=str(t1_ex_db.id)
        )

        status = [
            ac_ex.status == action_constants.LIVEACTION_STATUS_SUCCEEDED
            for ac_ex in t1_ac_ex_dbs
        ]

        self.assertTrue(all(status))

        for t1_ac_ex_db in t1_ac_ex_dbs:
            workflows.get_engine().process(t1_ac_ex_db)

        # Check that the workflow execution is canceled.
        wf_ex_db = wf_db_access.WorkflowExecution.get_by_id(wf_ex_db.id)
        self.assertEqual(wf_ex_db.status, wf_statuses.CANCELED)
        lv_ac_db = lv_db_access.LiveAction.get_by_id(str(lv_ac_db.id))
        self.assertEqual(lv_ac_db.status, action_constants.LIVEACTION_STATUS_CANCELED)

    @mock.patch.object(
        local_shell_command_runner.LocalShellCommandRunner,
        "run",
        mock.MagicMock(return_value=RUNNER_RESULT_RUNNING),
    )
    def test_with_items_concurrency_cancellation(self):
        concurrency = 2

        wf_input = {"concurrency": concurrency}
        wf_meta = base.get_wf_fixture_meta_data(
            TEST_PACK_PATH, "with-items-concurrency.yaml"
        )
        lv_ac_db = lv_db_models.LiveActionDB(
            action=wf_meta["name"], parameters=wf_input
        )
        lv_ac_db, ac_ex_db = action_service.request(lv_ac_db)

        # Assert the workflow execution is running.
        lv_ac_db = lv_db_access.LiveAction.get_by_id(str(lv_ac_db.id))
        self.assertEqual(lv_ac_db.status, action_constants.LIVEACTION_STATUS_RUNNING)
        wf_ex_db = wf_db_access.WorkflowExecution.query(
            action_execution=str(ac_ex_db.id)
        )[0]
        self.assertEqual(wf_ex_db.status, action_constants.LIVEACTION_STATUS_RUNNING)

        query_filters = {"workflow_execution": str(wf_ex_db.id), "task_id": "task1"}
        t1_ex_db = wf_db_access.TaskExecution.query(**query_filters)[0]
        t1_ac_ex_dbs = ex_db_access.ActionExecution.query(
            task_execution=str(t1_ex_db.id)
        )
        self.assertEqual(t1_ex_db.status, wf_statuses.RUNNING)
        self.assertEqual(len(t1_ac_ex_dbs), concurrency)

        status = [
            ac_ex.status == action_constants.LIVEACTION_STATUS_RUNNING
            for ac_ex in t1_ac_ex_dbs
        ]

        self.assertTrue(all(status))

        # Cancel the workflow execution.
        requester = cfg.CONF.system_user.user
        lv_ac_db, ac_ex_db = action_service.request_cancellation(lv_ac_db, requester)
        lv_ac_db = lv_db_access.LiveAction.get_by_id(str(lv_ac_db.id))
        self.assertEqual(lv_ac_db.status, action_constants.LIVEACTION_STATUS_CANCELING)

        # Manually succeed the action executions and process completion.
        for ac_ex in t1_ac_ex_dbs:
            self.set_execution_status(
                ac_ex.liveaction["id"], action_constants.LIVEACTION_STATUS_SUCCEEDED
            )

        t1_ac_ex_dbs = ex_db_access.ActionExecution.query(
            task_execution=str(t1_ex_db.id)
        )

        status = [
            ac_ex.status == action_constants.LIVEACTION_STATUS_SUCCEEDED
            for ac_ex in t1_ac_ex_dbs
        ]

        self.assertTrue(all(status))

        for t1_ac_ex_db in t1_ac_ex_dbs:
            workflows.get_engine().process(t1_ac_ex_db)

        # Check that the workflow execution is canceled.
        wf_ex_db = wf_db_access.WorkflowExecution.get_by_id(wf_ex_db.id)
        self.assertEqual(wf_ex_db.status, wf_statuses.CANCELED)
        lv_ac_db = lv_db_access.LiveAction.get_by_id(str(lv_ac_db.id))
        self.assertEqual(lv_ac_db.status, action_constants.LIVEACTION_STATUS_CANCELED)

    @mock.patch.object(
        local_shell_command_runner.LocalShellCommandRunner,
        "run",
        mock.MagicMock(return_value=RUNNER_RESULT_RUNNING),
    )
    def test_with_items_pause_and_resume(self):
        num_items = 3

        wf_meta = base.get_wf_fixture_meta_data(
            TEST_PACK_PATH, "with-items-concurrency.yaml"
        )
        lv_ac_db = lv_db_models.LiveActionDB(action=wf_meta["name"])
        lv_ac_db, ac_ex_db = action_service.request(lv_ac_db)

        # Assert the workflow execution is running.
        lv_ac_db = lv_db_access.LiveAction.get_by_id(str(lv_ac_db.id))
        self.assertEqual(lv_ac_db.status, action_constants.LIVEACTION_STATUS_RUNNING)
        wf_ex_db = wf_db_access.WorkflowExecution.query(
            action_execution=str(ac_ex_db.id)
        )[0]
        self.assertEqual(wf_ex_db.status, action_constants.LIVEACTION_STATUS_RUNNING)

        query_filters = {"workflow_execution": str(wf_ex_db.id), "task_id": "task1"}
        t1_ex_db = wf_db_access.TaskExecution.query(**query_filters)[0]
        t1_ac_ex_dbs = ex_db_access.ActionExecution.query(
            task_execution=str(t1_ex_db.id)
        )
        self.assertEqual(t1_ex_db.status, wf_statuses.RUNNING)
        self.assertEqual(len(t1_ac_ex_dbs), num_items)

        status = [
            ac_ex.status == action_constants.LIVEACTION_STATUS_RUNNING
            for ac_ex in t1_ac_ex_dbs
        ]

        self.assertTrue(all(status))

        # Pause the workflow execution.
        requester = cfg.CONF.system_user.user
        lv_ac_db, ac_ex_db = action_service.request_pause(lv_ac_db, requester)
        lv_ac_db = lv_db_access.LiveAction.get_by_id(str(lv_ac_db.id))
        self.assertEqual(lv_ac_db.status, action_constants.LIVEACTION_STATUS_PAUSING)

        # Manually succeed the action executions and process completion.
        for ac_ex in t1_ac_ex_dbs:
            self.set_execution_status(
                ac_ex.liveaction["id"], action_constants.LIVEACTION_STATUS_SUCCEEDED
            )

        t1_ac_ex_dbs = ex_db_access.ActionExecution.query(
            task_execution=str(t1_ex_db.id)
        )

        status = [
            ac_ex.status == action_constants.LIVEACTION_STATUS_SUCCEEDED
            for ac_ex in t1_ac_ex_dbs
        ]

        self.assertTrue(all(status))

        for t1_ac_ex_db in t1_ac_ex_dbs:
            workflows.get_engine().process(t1_ac_ex_db)

        # Check that the workflow execution is paused.
        wf_ex_db = wf_db_access.WorkflowExecution.get_by_id(wf_ex_db.id)
        self.assertEqual(wf_ex_db.status, wf_statuses.PAUSED)
        lv_ac_db = lv_db_access.LiveAction.get_by_id(str(lv_ac_db.id))
        self.assertEqual(lv_ac_db.status, action_constants.LIVEACTION_STATUS_PAUSED)

        # Resume the workflow execution.
        requester = cfg.CONF.system_user.user
        lv_ac_db, ac_ex_db = action_service.request_resume(lv_ac_db, requester)
        self.assertEqual(lv_ac_db.status, action_constants.LIVEACTION_STATUS_RESUMING)

        # Check that the workflow execution is completed.
        wf_ex_db = wf_db_access.WorkflowExecution.get_by_id(wf_ex_db.id)
        self.assertEqual(wf_ex_db.status, wf_statuses.SUCCEEDED)
        lv_ac_db = lv_db_access.LiveAction.get_by_id(str(lv_ac_db.id))
        self.assertEqual(lv_ac_db.status, action_constants.LIVEACTION_STATUS_SUCCEEDED)

    @mock.patch.object(
        local_shell_command_runner.LocalShellCommandRunner,
        "run",
        mock.MagicMock(
            side_effect=[
                RUNNER_RESULT_RUNNING,
                RUNNER_RESULT_RUNNING,
                RUNNER_RESULT_SUCCEEDED,
            ]
        ),
    )
    def test_with_items_concurrency_pause_and_resume(self):
        num_items = 3
        concurrency = 2

        wf_input = {"concurrency": concurrency}
        wf_meta = base.get_wf_fixture_meta_data(
            TEST_PACK_PATH, "with-items-concurrency.yaml"
        )
        lv_ac_db = lv_db_models.LiveActionDB(
            action=wf_meta["name"], parameters=wf_input
        )
        lv_ac_db, ac_ex_db = action_service.request(lv_ac_db)

        # Assert the workflow execution is running.
        lv_ac_db = lv_db_access.LiveAction.get_by_id(str(lv_ac_db.id))
        self.assertEqual(lv_ac_db.status, action_constants.LIVEACTION_STATUS_RUNNING)
        wf_ex_db = wf_db_access.WorkflowExecution.query(
            action_execution=str(ac_ex_db.id)
        )[0]
        self.assertEqual(wf_ex_db.status, action_constants.LIVEACTION_STATUS_RUNNING)

        query_filters = {"workflow_execution": str(wf_ex_db.id), "task_id": "task1"}
        t1_ex_db = wf_db_access.TaskExecution.query(**query_filters)[0]
        t1_ac_ex_dbs = ex_db_access.ActionExecution.query(
            task_execution=str(t1_ex_db.id)
        )
        self.assertEqual(t1_ex_db.status, wf_statuses.RUNNING)
        self.assertEqual(len(t1_ac_ex_dbs), concurrency)

        status = [
            ac_ex.status == action_constants.LIVEACTION_STATUS_RUNNING
            for ac_ex in t1_ac_ex_dbs
        ]

        self.assertTrue(all(status))

        # Pause the workflow execution.
        requester = cfg.CONF.system_user.user
        lv_ac_db, ac_ex_db = action_service.request_pause(lv_ac_db, requester)
        lv_ac_db = lv_db_access.LiveAction.get_by_id(str(lv_ac_db.id))
        self.assertEqual(lv_ac_db.status, action_constants.LIVEACTION_STATUS_PAUSING)

        # Manually succeed the action executions and process completion.
        for ac_ex in t1_ac_ex_dbs:
            self.set_execution_status(
                ac_ex.liveaction["id"], action_constants.LIVEACTION_STATUS_SUCCEEDED
            )

        t1_ac_ex_dbs = ex_db_access.ActionExecution.query(
            task_execution=str(t1_ex_db.id)
        )

        status = [
            ac_ex.status == action_constants.LIVEACTION_STATUS_SUCCEEDED
            for ac_ex in t1_ac_ex_dbs
        ]

        self.assertTrue(all(status))

        for t1_ac_ex_db in t1_ac_ex_dbs:
            workflows.get_engine().process(t1_ac_ex_db)

        # Check that the workflow execution is paused.
        wf_ex_db = wf_db_access.WorkflowExecution.get_by_id(wf_ex_db.id)
        self.assertEqual(wf_ex_db.status, wf_statuses.PAUSED)
        lv_ac_db = lv_db_access.LiveAction.get_by_id(str(lv_ac_db.id))
        self.assertEqual(lv_ac_db.status, action_constants.LIVEACTION_STATUS_PAUSED)

        # Resume the workflow execution.
        requester = cfg.CONF.system_user.user
        lv_ac_db, ac_ex_db = action_service.request_resume(lv_ac_db, requester)
        self.assertEqual(lv_ac_db.status, action_constants.LIVEACTION_STATUS_RESUMING)

        # Check that the workflow execution is running.
        lv_ac_db = lv_db_access.LiveAction.get_by_id(str(lv_ac_db.id))
        self.assertEqual(lv_ac_db.status, action_constants.LIVEACTION_STATUS_RUNNING)

        # Check new set of action execution is scheduled.
        t1_ac_ex_dbs = ex_db_access.ActionExecution.query(
            task_execution=str(t1_ex_db.id)
        )
        self.assertEqual(len(t1_ac_ex_dbs), num_items)

        # Manually process the last action execution.
        workflows.get_engine().process(t1_ac_ex_dbs[2])

        # Check that the workflow execution is completed.
        wf_ex_db = wf_db_access.WorkflowExecution.get_by_id(wf_ex_db.id)
        self.assertEqual(wf_ex_db.status, wf_statuses.SUCCEEDED)
        lv_ac_db = lv_db_access.LiveAction.get_by_id(str(lv_ac_db.id))
        self.assertEqual(lv_ac_db.status, action_constants.LIVEACTION_STATUS_SUCCEEDED)

    def test_subworkflow_with_items_empty_list(self):
        wf_input = {"members": []}
        wf_meta = base.get_wf_fixture_meta_data(
            TEST_PACK_PATH, "with-items-empty-parent.yaml"
        )
        lv_ac_db = lv_db_models.LiveActionDB(
            action=wf_meta["name"], parameters=wf_input
        )
        lv_ac_db, ac_ex_db = action_service.request(lv_ac_db)

        # Identify the records for the main workflow.
        wf_ex_db = wf_db_access.WorkflowExecution.query(
            action_execution=str(ac_ex_db.id)
        )[0]
        tk_ex_dbs = wf_db_access.TaskExecution.query(
            workflow_execution=str(wf_ex_db.id)
        )
        self.assertEqual(len(tk_ex_dbs), 1)

        # Identify the records for the tasks.
        t1_ac_ex_db = ex_db_access.ActionExecution.query(
            task_execution=str(tk_ex_dbs[0].id)
        )[0]
        t1_wf_ex_db = wf_db_access.WorkflowExecution.query(
            action_execution=str(t1_ac_ex_db.id)
        )[0]
        self.assertEqual(
            t1_ac_ex_db.status, action_constants.LIVEACTION_STATUS_SUCCEEDED
        )
        self.assertEqual(t1_wf_ex_db.status, wf_statuses.SUCCEEDED)

        # Manually processing completion of the subworkflow in task1.
        workflows.get_engine().process(t1_ac_ex_db)
        t1_ex_db = wf_db_access.TaskExecution.get_by_id(tk_ex_dbs[0].id)
        self.assertEqual(t1_ex_db.status, wf_statuses.SUCCEEDED)

        # Check that the workflow execution is completed.
        wf_ex_db = wf_db_access.WorkflowExecution.get_by_id(wf_ex_db.id)
        self.assertEqual(wf_ex_db.status, wf_statuses.SUCCEEDED)
        lv_ac_db = lv_db_access.LiveAction.get_by_id(str(lv_ac_db.id))
        self.assertEqual(lv_ac_db.status, action_constants.LIVEACTION_STATUS_SUCCEEDED)

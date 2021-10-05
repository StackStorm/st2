# -*- coding: utf-8 -*-

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
import six

from orquesta import statuses as wf_statuses

import st2tests

# XXX: actionsensor import depends on config being setup.
import st2tests.config as tests_config

tests_config.parse_args()

from tests.unit import base

from st2actions.notifier import notifier
from st2actions.workflows import workflows
from st2common.bootstrap import actionsregistrar
from st2common.bootstrap import runnersregistrar
from st2common.constants import action as ac_const
from st2common.models.db import liveaction as lv_db_models
from st2common.persistence import execution as ex_db_access
from st2common.persistence import liveaction as lv_db_access
from st2common.persistence import workflow as wf_db_access
from st2common.runners import base as runners
from st2common.runners import utils as runners_utils
from st2common.services import action as ac_svc
from st2common.services import policies as pc_svc
from st2common.services import workflows as wf_svc
from st2common.transport import liveaction as lv_ac_xport
from st2common.transport import workflow as wf_ex_xport
from st2common.transport import publishers
from st2tests.mocks import liveaction as mock_lv_ac_xport
from st2tests.mocks import workflow as mock_wf_ex_xport


TEST_PACK = "orquesta_tests"
TEST_PACK_PATH = (
    st2tests.fixturesloader.get_fixtures_packs_base_path() + "/" + TEST_PACK
)

PACKS = [
    TEST_PACK_PATH,
    st2tests.fixturesloader.get_fixtures_packs_base_path() + "/core",
]


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
class OrquestaRunnerTest(st2tests.ExecutionDbTestCase):
    @classmethod
    def setUpClass(cls):
        super(OrquestaRunnerTest, cls).setUpClass()

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

    @mock.patch.object(
        runners_utils, "invoke_post_run", mock.MagicMock(return_value=None)
    )
    def test_run_workflow(self):
        username = "stanley"
        wf_meta = base.get_wf_fixture_meta_data(TEST_PACK_PATH, "sequential.yaml")
        wf_input = {"who": "Thanos"}
        lv_ac_db = lv_db_models.LiveActionDB(
            action=wf_meta["name"], parameters=wf_input
        )
        lv_ac_db, ac_ex_db = ac_svc.request(lv_ac_db)

        # The main action execution for this workflow is not under the context of another workflow.
        self.assertFalse(wf_svc.is_action_execution_under_workflow_context(ac_ex_db))

        # Assert action execution is running.
        lv_ac_db = lv_db_access.LiveAction.get_by_id(str(lv_ac_db.id))

        self.assertTrue(lv_ac_db.action_is_workflow)
        self.assertEqual(
            lv_ac_db.status, ac_const.LIVEACTION_STATUS_RUNNING, lv_ac_db.result
        )

        wf_ex_dbs = wf_db_access.WorkflowExecution.query(
            action_execution=str(ac_ex_db.id)
        )
        wf_ex_db = wf_ex_dbs[0]

        # Check required attributes.
        self.assertEqual(len(wf_ex_dbs), 1)
        self.assertIsNotNone(wf_ex_db.id)
        self.assertGreater(wf_ex_db.rev, 0)
        self.assertEqual(wf_ex_db.action_execution, str(ac_ex_db.id))
        self.assertEqual(wf_ex_db.status, ac_const.LIVEACTION_STATUS_RUNNING)

        # Check context in the workflow execution.
        expected_wf_ex_ctx = {
            "st2": {
                "workflow_execution_id": str(wf_ex_db.id),
                "action_execution_id": str(ac_ex_db.id),
                "api_url": "http://127.0.0.1/v1",
                "user": username,
                "pack": "orquesta_tests",
                "action": "orquesta_tests.sequential",
                "runner": "orquesta",
            },
            "parent": {"pack": "orquesta_tests"},
        }

        self.assertDictEqual(wf_ex_db.context, expected_wf_ex_ctx)

        # Check context in the liveaction.
        expected_lv_ac_ctx = {
            "workflow_execution": str(wf_ex_db.id),
            "pack": "orquesta_tests",
        }

        self.assertDictEqual(lv_ac_db.context, expected_lv_ac_ctx)

        # Check graph.
        self.assertIsNotNone(wf_ex_db.graph)
        self.assertIsInstance(wf_ex_db.graph, dict)
        self.assertIn("nodes", wf_ex_db.graph)
        self.assertIn("adjacency", wf_ex_db.graph)

        # Check task states.
        self.assertIsNotNone(wf_ex_db.state)
        self.assertIsInstance(wf_ex_db.state, dict)
        self.assertIn("tasks", wf_ex_db.state)
        self.assertIn("sequence", wf_ex_db.state)

        # Check input.
        self.assertDictEqual(wf_ex_db.input, wf_input)

        # Assert task1 is already completed.
        query_filters = {"workflow_execution": str(wf_ex_db.id), "task_id": "task1"}
        tk1_ex_db = wf_db_access.TaskExecution.query(**query_filters)[0]
        tk1_ac_ex_db = ex_db_access.ActionExecution.query(
            task_execution=str(tk1_ex_db.id)
        )[0]
        tk1_lv_ac_db = lv_db_access.LiveAction.get_by_id(tk1_ac_ex_db.liveaction["id"])
        self.assertEqual(tk1_lv_ac_db.context.get("user"), username)
        self.assertEqual(tk1_lv_ac_db.status, ac_const.LIVEACTION_STATUS_SUCCEEDED)
        self.assertTrue(wf_svc.is_action_execution_under_workflow_context(tk1_ac_ex_db))

        # Manually handle action execution completion.
        wf_svc.handle_action_execution_completion(tk1_ac_ex_db)

        # Assert task1 succeeded and workflow is still running.
        tk1_ex_db = wf_db_access.TaskExecution.get_by_id(tk1_ex_db.id)
        self.assertEqual(tk1_ex_db.status, wf_statuses.SUCCEEDED)
        wf_ex_db = wf_db_access.WorkflowExecution.get_by_id(wf_ex_db.id)
        self.assertEqual(wf_ex_db.status, wf_statuses.RUNNING)

        # Assert task2 is already completed.
        query_filters = {"workflow_execution": str(wf_ex_db.id), "task_id": "task2"}
        tk2_ex_db = wf_db_access.TaskExecution.query(**query_filters)[0]
        tk2_ac_ex_db = ex_db_access.ActionExecution.query(
            task_execution=str(tk2_ex_db.id)
        )[0]
        tk2_lv_ac_db = lv_db_access.LiveAction.get_by_id(tk2_ac_ex_db.liveaction["id"])
        self.assertEqual(tk2_lv_ac_db.context.get("user"), username)
        self.assertEqual(tk2_lv_ac_db.status, ac_const.LIVEACTION_STATUS_SUCCEEDED)
        self.assertTrue(wf_svc.is_action_execution_under_workflow_context(tk2_ac_ex_db))

        # Manually handle action execution completion.
        wf_svc.handle_action_execution_completion(tk2_ac_ex_db)

        # Assert task2 succeeded and workflow is still running.
        tk2_ex_db = wf_db_access.TaskExecution.get_by_id(tk2_ex_db.id)
        self.assertEqual(tk2_ex_db.status, wf_statuses.SUCCEEDED)
        wf_ex_db = wf_db_access.WorkflowExecution.get_by_id(wf_ex_db.id)
        self.assertEqual(wf_ex_db.status, wf_statuses.RUNNING)

        # Assert task3 is already completed.
        query_filters = {"workflow_execution": str(wf_ex_db.id), "task_id": "task3"}
        tk3_ex_db = wf_db_access.TaskExecution.query(**query_filters)[0]
        tk3_ac_ex_db = ex_db_access.ActionExecution.query(
            task_execution=str(tk3_ex_db.id)
        )[0]
        tk3_lv_ac_db = lv_db_access.LiveAction.get_by_id(tk3_ac_ex_db.liveaction["id"])
        self.assertEqual(tk3_lv_ac_db.context.get("user"), username)
        self.assertEqual(tk3_lv_ac_db.status, ac_const.LIVEACTION_STATUS_SUCCEEDED)
        self.assertTrue(wf_svc.is_action_execution_under_workflow_context(tk3_ac_ex_db))

        # Manually handle action execution completion.
        wf_svc.handle_action_execution_completion(tk3_ac_ex_db)

        # Assert workflow is completed.
        wf_ex_db = wf_db_access.WorkflowExecution.get_by_id(wf_ex_db.id)
        self.assertEqual(wf_ex_db.status, wf_statuses.SUCCEEDED)
        lv_ac_db = lv_db_access.LiveAction.get_by_id(str(lv_ac_db.id))
        self.assertEqual(lv_ac_db.status, ac_const.LIVEACTION_STATUS_SUCCEEDED)
        ac_ex_db = ex_db_access.ActionExecution.get_by_id(str(ac_ex_db.id))
        self.assertEqual(ac_ex_db.status, ac_const.LIVEACTION_STATUS_SUCCEEDED)

        # Check post run is invoked for the liveaction.
        self.assertTrue(runners_utils.invoke_post_run.called)
        self.assertEqual(runners_utils.invoke_post_run.call_count, 1)

        # Check workflow output.
        expected_output = {
            "msg": "%s, All your base are belong to us!" % wf_input["who"]
        }

        self.assertDictEqual(wf_ex_db.output, expected_output)

        # Check liveaction and action execution result.
        expected_result = {"output": expected_output}

        self.assertDictEqual(lv_ac_db.result, expected_result)
        self.assertDictEqual(ac_ex_db.result, expected_result)

    def test_run_workflow_with_unicode_input(self):
        wf_meta = base.get_wf_fixture_meta_data(TEST_PACK_PATH, "sequential.yaml")
        wf_input = {"who": "薩諾斯"}
        lv_ac_db = lv_db_models.LiveActionDB(
            action=wf_meta["name"], parameters=wf_input
        )
        lv_ac_db, ac_ex_db = ac_svc.request(lv_ac_db)
        wf_ex_db = wf_db_access.WorkflowExecution.query(
            action_execution=str(ac_ex_db.id)
        )[0]

        # Process task1.
        query_filters = {"workflow_execution": str(wf_ex_db.id), "task_id": "task1"}
        tk1_ex_db = wf_db_access.TaskExecution.query(**query_filters)[0]
        tk1_ac_ex_db = ex_db_access.ActionExecution.query(
            task_execution=str(tk1_ex_db.id)
        )[0]
        tk1_lv_ac_db = lv_db_access.LiveAction.get_by_id(tk1_ac_ex_db.liveaction["id"])
        self.assertEqual(tk1_lv_ac_db.status, ac_const.LIVEACTION_STATUS_SUCCEEDED)
        wf_svc.handle_action_execution_completion(tk1_ac_ex_db)
        tk1_ex_db = wf_db_access.TaskExecution.get_by_id(tk1_ex_db.id)
        self.assertEqual(tk1_ex_db.status, wf_statuses.SUCCEEDED)

        # Process task2.
        query_filters = {"workflow_execution": str(wf_ex_db.id), "task_id": "task2"}
        tk2_ex_db = wf_db_access.TaskExecution.query(**query_filters)[0]
        tk2_ac_ex_db = ex_db_access.ActionExecution.query(
            task_execution=str(tk2_ex_db.id)
        )[0]
        tk2_lv_ac_db = lv_db_access.LiveAction.get_by_id(tk2_ac_ex_db.liveaction["id"])
        self.assertEqual(tk2_lv_ac_db.status, ac_const.LIVEACTION_STATUS_SUCCEEDED)
        wf_svc.handle_action_execution_completion(tk2_ac_ex_db)
        tk2_ex_db = wf_db_access.TaskExecution.get_by_id(tk2_ex_db.id)
        self.assertEqual(tk2_ex_db.status, wf_statuses.SUCCEEDED)

        # Process task3.
        query_filters = {"workflow_execution": str(wf_ex_db.id), "task_id": "task3"}
        tk3_ex_db = wf_db_access.TaskExecution.query(**query_filters)[0]
        tk3_ac_ex_db = ex_db_access.ActionExecution.query(
            task_execution=str(tk3_ex_db.id)
        )[0]
        tk3_lv_ac_db = lv_db_access.LiveAction.get_by_id(tk3_ac_ex_db.liveaction["id"])
        self.assertEqual(tk3_lv_ac_db.status, ac_const.LIVEACTION_STATUS_SUCCEEDED)
        wf_svc.handle_action_execution_completion(tk3_ac_ex_db)
        tk3_ex_db = wf_db_access.TaskExecution.get_by_id(tk3_ex_db.id)
        self.assertEqual(tk3_ex_db.status, wf_statuses.SUCCEEDED)

        # Assert workflow is completed.
        wf_ex_db = wf_db_access.WorkflowExecution.get_by_id(wf_ex_db.id)
        self.assertEqual(wf_ex_db.status, wf_statuses.SUCCEEDED)
        lv_ac_db = lv_db_access.LiveAction.get_by_id(str(lv_ac_db.id))
        self.assertEqual(lv_ac_db.status, ac_const.LIVEACTION_STATUS_SUCCEEDED)
        ac_ex_db = ex_db_access.ActionExecution.get_by_id(str(ac_ex_db.id))
        self.assertEqual(ac_ex_db.status, ac_const.LIVEACTION_STATUS_SUCCEEDED)

        # Check workflow output.
        wf_input_val = wf_input["who"].decode("utf-8") if six.PY2 else wf_input["who"]
        expected_output = {"msg": "%s, All your base are belong to us!" % wf_input_val}
        self.assertDictEqual(wf_ex_db.output, expected_output)

        # Check liveaction and action execution result.
        expected_result = {"output": expected_output}

        self.assertDictEqual(lv_ac_db.result, expected_result)
        self.assertDictEqual(ac_ex_db.result, expected_result)

    def test_run_workflow_action_config_context(self):
        wf_meta = base.get_wf_fixture_meta_data(TEST_PACK_PATH, "config-context.yaml")
        wf_input = {}
        lv_ac_db = lv_db_models.LiveActionDB(
            action=wf_meta["name"], parameters=wf_input
        )
        lv_ac_db, ac_ex_db = ac_svc.request(lv_ac_db)

        # Assert action execution is running.
        lv_ac_db = lv_db_access.LiveAction.get_by_id(str(lv_ac_db.id))
        self.assertEqual(
            lv_ac_db.status, ac_const.LIVEACTION_STATUS_RUNNING, lv_ac_db.result
        )
        wf_ex_db = wf_db_access.WorkflowExecution.query(
            action_execution=str(ac_ex_db.id)
        )[0]
        self.assertEqual(wf_ex_db.status, ac_const.LIVEACTION_STATUS_RUNNING)

        # Assert task1 is already completed.
        query_filters = {"workflow_execution": str(wf_ex_db.id), "task_id": "task1"}
        tk1_ex_db = wf_db_access.TaskExecution.query(**query_filters)[0]
        tk1_ac_ex_db = ex_db_access.ActionExecution.query(
            task_execution=str(tk1_ex_db.id)
        )[0]
        tk1_lv_ac_db = lv_db_access.LiveAction.get_by_id(tk1_ac_ex_db.liveaction["id"])
        self.assertEqual(tk1_lv_ac_db.status, ac_const.LIVEACTION_STATUS_SUCCEEDED)
        self.assertTrue(wf_svc.is_action_execution_under_workflow_context(tk1_ac_ex_db))

        # Manually handle action execution completion.
        wf_svc.handle_action_execution_completion(tk1_ac_ex_db)

        # Assert workflow is completed.
        wf_ex_db = wf_db_access.WorkflowExecution.get_by_id(wf_ex_db.id)
        self.assertEqual(wf_ex_db.status, wf_statuses.SUCCEEDED)
        lv_ac_db = lv_db_access.LiveAction.get_by_id(str(lv_ac_db.id))
        self.assertEqual(lv_ac_db.status, ac_const.LIVEACTION_STATUS_SUCCEEDED)
        ac_ex_db = ex_db_access.ActionExecution.get_by_id(str(ac_ex_db.id))
        self.assertEqual(ac_ex_db.status, ac_const.LIVEACTION_STATUS_SUCCEEDED)

        # Verify config_context works
        self.assertEqual(wf_ex_db.output, {"msg": "value of config key a"})

    def test_run_workflow_with_action_less_tasks(self):
        wf_meta = base.get_wf_fixture_meta_data(
            TEST_PACK_PATH, "action-less-tasks.yaml"
        )
        wf_input = {"name": "Thanos"}
        lv_ac_db = lv_db_models.LiveActionDB(
            action=wf_meta["name"], parameters=wf_input
        )
        lv_ac_db, ac_ex_db = ac_svc.request(lv_ac_db)

        # Assert action execution is running.
        lv_ac_db = lv_db_access.LiveAction.get_by_id(str(lv_ac_db.id))
        self.assertEqual(
            lv_ac_db.status, ac_const.LIVEACTION_STATUS_RUNNING, lv_ac_db.result
        )
        wf_ex_db = wf_db_access.WorkflowExecution.query(
            action_execution=str(ac_ex_db.id)
        )[0]
        self.assertEqual(wf_ex_db.status, ac_const.LIVEACTION_STATUS_RUNNING)

        # Assert task1 is already completed.
        query_filters = {"workflow_execution": str(wf_ex_db.id), "task_id": "task1"}
        tk1_ex_db = wf_db_access.TaskExecution.query(**query_filters)[0]
        tk1_ac_ex_dbs = ex_db_access.ActionExecution.query(
            task_execution=str(tk1_ex_db.id)
        )
        self.assertEqual(len(tk1_ac_ex_dbs), 0)
        self.assertEqual(tk1_ex_db.status, wf_statuses.SUCCEEDED)

        # Assert task2 is already completed.
        query_filters = {"workflow_execution": str(wf_ex_db.id), "task_id": "task2"}
        tk2_ex_db = wf_db_access.TaskExecution.query(**query_filters)[0]
        tk2_ac_ex_db = ex_db_access.ActionExecution.query(
            task_execution=str(tk2_ex_db.id)
        )[0]
        tk2_lv_ac_db = lv_db_access.LiveAction.get_by_id(tk2_ac_ex_db.liveaction["id"])
        self.assertEqual(tk2_lv_ac_db.status, ac_const.LIVEACTION_STATUS_SUCCEEDED)

        # Manually handle action execution completion.
        wf_svc.handle_action_execution_completion(tk2_ac_ex_db)

        # Assert task3 is already completed.
        query_filters = {"workflow_execution": str(wf_ex_db.id), "task_id": "task3"}
        tk3_ex_db = wf_db_access.TaskExecution.query(**query_filters)[0]
        tk3_ac_ex_db = ex_db_access.ActionExecution.query(
            task_execution=str(tk3_ex_db.id)
        )[0]
        tk3_lv_ac_db = lv_db_access.LiveAction.get_by_id(tk3_ac_ex_db.liveaction["id"])
        self.assertEqual(tk3_lv_ac_db.status, ac_const.LIVEACTION_STATUS_SUCCEEDED)

        # Manually handle action execution completion.
        wf_svc.handle_action_execution_completion(tk3_ac_ex_db)

        # Assert task4 is already completed.
        query_filters = {"workflow_execution": str(wf_ex_db.id), "task_id": "task4"}
        tk4_ex_db = wf_db_access.TaskExecution.query(**query_filters)[0]
        tk4_ac_ex_dbs = ex_db_access.ActionExecution.query(
            task_execution=str(tk4_ex_db.id)
        )
        self.assertEqual(len(tk4_ac_ex_dbs), 0)
        self.assertEqual(tk4_ex_db.status, wf_statuses.SUCCEEDED)

        # Assert task5 is already completed.
        query_filters = {"workflow_execution": str(wf_ex_db.id), "task_id": "task5"}
        tk5_ex_db = wf_db_access.TaskExecution.query(**query_filters)[0]
        tk5_ac_ex_db = ex_db_access.ActionExecution.query(
            task_execution=str(tk5_ex_db.id)
        )[0]
        tk5_lv_ac_db = lv_db_access.LiveAction.get_by_id(tk5_ac_ex_db.liveaction["id"])
        self.assertEqual(tk5_lv_ac_db.status, ac_const.LIVEACTION_STATUS_SUCCEEDED)

        # Manually handle action execution completion.
        wf_svc.handle_action_execution_completion(tk5_ac_ex_db)

        # Assert workflow is completed.
        wf_ex_db = wf_db_access.WorkflowExecution.get_by_id(wf_ex_db.id)
        self.assertEqual(wf_ex_db.status, wf_statuses.SUCCEEDED)
        lv_ac_db = lv_db_access.LiveAction.get_by_id(str(lv_ac_db.id))
        self.assertEqual(lv_ac_db.status, ac_const.LIVEACTION_STATUS_SUCCEEDED)
        ac_ex_db = ex_db_access.ActionExecution.get_by_id(str(ac_ex_db.id))
        self.assertEqual(ac_ex_db.status, ac_const.LIVEACTION_STATUS_SUCCEEDED)

        # Check workflow output.
        expected_output = {
            "greeting": "%s, All your base are belong to us!" % wf_input["name"]
        }
        expected_output["greeting"] = expected_output["greeting"].upper()

        self.assertDictEqual(wf_ex_db.output, expected_output)

        # Check liveaction and action execution result.
        expected_result = {"output": expected_output}

        self.assertDictEqual(lv_ac_db.result, expected_result)
        self.assertDictEqual(ac_ex_db.result, expected_result)

    @mock.patch.object(
        pc_svc, "apply_post_run_policies", mock.MagicMock(return_value=None)
    )
    def test_handle_action_execution_completion(self):
        wf_meta = base.get_wf_fixture_meta_data(TEST_PACK_PATH, "subworkflow.yaml")
        lv_ac_db = lv_db_models.LiveActionDB(action=wf_meta["name"])
        lv_ac_db, ac_ex_db = ac_svc.request(lv_ac_db)
        lv_ac_db = lv_db_access.LiveAction.get_by_id(str(lv_ac_db.id))
        self.assertEqual(
            lv_ac_db.status, ac_const.LIVEACTION_STATUS_RUNNING, lv_ac_db.result
        )

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
        self.assertEqual(t1_ac_ex_db.status, ac_const.LIVEACTION_STATUS_RUNNING)
        self.assertEqual(t1_wf_ex_db.status, wf_statuses.RUNNING)

        # Manually notify action execution completion for the tasks.
        # Assert policies are not applied in the notifier.
        t1_t1_ex_db = wf_db_access.TaskExecution.query(
            workflow_execution=str(t1_wf_ex_db.id)
        )[0]
        t1_t1_ac_ex_db = ex_db_access.ActionExecution.query(
            task_execution=str(t1_t1_ex_db.id)
        )[0]
        notifier.get_notifier().process(t1_t1_ac_ex_db)
        self.assertFalse(pc_svc.apply_post_run_policies.called)
        t1_tk_ex_dbs = wf_db_access.TaskExecution.query(
            workflow_execution=str(t1_wf_ex_db.id)
        )
        self.assertEqual(len(t1_tk_ex_dbs), 1)
        workflows.get_engine().process(t1_t1_ac_ex_db)
        self.assertTrue(pc_svc.apply_post_run_policies.called)
        pc_svc.apply_post_run_policies.reset_mock()

        t1_t2_ex_db = wf_db_access.TaskExecution.query(
            workflow_execution=str(t1_wf_ex_db.id)
        )[1]
        t1_t2_ac_ex_db = ex_db_access.ActionExecution.query(
            task_execution=str(t1_t2_ex_db.id)
        )[0]
        notifier.get_notifier().process(t1_t2_ac_ex_db)
        self.assertFalse(pc_svc.apply_post_run_policies.called)
        t1_tk_ex_dbs = wf_db_access.TaskExecution.query(
            workflow_execution=str(t1_wf_ex_db.id)
        )
        self.assertEqual(len(t1_tk_ex_dbs), 2)
        workflows.get_engine().process(t1_t2_ac_ex_db)
        self.assertTrue(pc_svc.apply_post_run_policies.called)
        pc_svc.apply_post_run_policies.reset_mock()

        t1_t3_ex_db = wf_db_access.TaskExecution.query(
            workflow_execution=str(t1_wf_ex_db.id)
        )[2]
        t1_t3_ac_ex_db = ex_db_access.ActionExecution.query(
            task_execution=str(t1_t3_ex_db.id)
        )[0]
        notifier.get_notifier().process(t1_t3_ac_ex_db)
        self.assertFalse(pc_svc.apply_post_run_policies.called)
        t1_tk_ex_dbs = wf_db_access.TaskExecution.query(
            workflow_execution=str(t1_wf_ex_db.id)
        )
        self.assertEqual(len(t1_tk_ex_dbs), 3)
        workflows.get_engine().process(t1_t3_ac_ex_db)
        self.assertTrue(pc_svc.apply_post_run_policies.called)
        pc_svc.apply_post_run_policies.reset_mock()

        t1_ac_ex_db = ex_db_access.ActionExecution.get_by_id(t1_ac_ex_db.id)
        notifier.get_notifier().process(t1_ac_ex_db)
        self.assertFalse(pc_svc.apply_post_run_policies.called)
        tk_ex_dbs = wf_db_access.TaskExecution.query(
            workflow_execution=str(wf_ex_db.id)
        )
        self.assertEqual(len(tk_ex_dbs), 1)
        workflows.get_engine().process(t1_ac_ex_db)
        self.assertTrue(pc_svc.apply_post_run_policies.called)
        pc_svc.apply_post_run_policies.reset_mock()

        t2_ex_db_qry = {"workflow_execution": str(wf_ex_db.id), "task_id": "task2"}
        t2_ex_db = wf_db_access.TaskExecution.query(**t2_ex_db_qry)[0]
        t2_ac_ex_db = ex_db_access.ActionExecution.query(
            task_execution=str(t2_ex_db.id)
        )[0]
        self.assertEqual(t2_ac_ex_db.status, ac_const.LIVEACTION_STATUS_SUCCEEDED)
        notifier.get_notifier().process(t2_ac_ex_db)
        self.assertFalse(pc_svc.apply_post_run_policies.called)
        tk_ex_dbs = wf_db_access.TaskExecution.query(
            workflow_execution=str(wf_ex_db.id)
        )
        self.assertEqual(len(tk_ex_dbs), 2)
        workflows.get_engine().process(t2_ac_ex_db)
        self.assertTrue(pc_svc.apply_post_run_policies.called)
        pc_svc.apply_post_run_policies.reset_mock()

        # Assert the main workflow is completed.
        lv_ac_db = lv_db_access.LiveAction.get_by_id(str(lv_ac_db.id))
        self.assertEqual(lv_ac_db.status, ac_const.LIVEACTION_STATUS_SUCCEEDED)

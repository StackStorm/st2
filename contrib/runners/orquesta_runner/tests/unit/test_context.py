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

import copy
import mock

from orquesta import statuses as wf_statuses
from oslo_config import cfg

import st2tests

# XXX: actionsensor import depends on config being setup.
import st2tests.config as tests_config

tests_config.parse_args()

from tests.unit import base

from st2common.bootstrap import actionsregistrar
from st2common.bootstrap import runnersregistrar
from st2common.constants import action as ac_const
from st2common.models.db import liveaction as lv_db_models
from st2common.persistence import execution as ex_db_access
from st2common.persistence import liveaction as lv_db_access
from st2common.persistence import workflow as wf_db_access
from st2common.services import action as ac_svc
from st2common.services import workflows as wf_svc
from st2common.transport import liveaction as lv_ac_xport
from st2common.transport import workflow as wf_ex_xport
from st2common.transport import publishers
from st2tests.fixtures.packs.core.fixture import PACK_PATH as CORE_PACK_PATH
from st2tests.fixtures.packs.orquesta_tests.fixture import PACK_PATH as TEST_PACK_PATH
from st2tests.mocks import liveaction as mock_lv_ac_xport
from st2tests.mocks import workflow as mock_wf_ex_xport

PACKS = [TEST_PACK_PATH, CORE_PACK_PATH]


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
class OrquestaContextTest(st2tests.ExecutionDbTestCase):
    @classmethod
    def setUpClass(cls):
        super(OrquestaContextTest, cls).setUpClass()

        # Register runners.
        runnersregistrar.register_runners()

        # Register test pack(s).
        actions_registrar = actionsregistrar.ActionsRegistrar(
            use_pack_cache=False, fail_on_failure=True
        )

        for pack in PACKS:
            actions_registrar.register_from_pack(pack)

    def test_runtime_context(self):
        wf_meta = base.get_wf_fixture_meta_data(TEST_PACK_PATH, "runtime-context.yaml")
        lv_ac_db = lv_db_models.LiveActionDB(action=wf_meta["name"])
        lv_ac_db, ac_ex_db = ac_svc.request(lv_ac_db)
        lv_ac_db = lv_db_access.LiveAction.get_by_id(str(lv_ac_db.id))
        self.assertEqual(
            lv_ac_db.status, ac_const.LIVEACTION_STATUS_RUNNING, lv_ac_db.result
        )

        # Identify the records for the workflow.
        wf_ex_db = wf_db_access.WorkflowExecution.query(
            action_execution=str(ac_ex_db.id)
        )[0]
        t1_ex_db = wf_db_access.TaskExecution.query(
            workflow_execution=str(wf_ex_db.id)
        )[0]
        t1_ac_ex_db = ex_db_access.ActionExecution.query(
            task_execution=str(t1_ex_db.id)
        )[0]

        # Complete the worklfow.
        wf_svc.handle_action_execution_completion(t1_ac_ex_db)
        t1_ex_db = wf_db_access.TaskExecution.get_by_id(str(t1_ex_db.id))
        wf_ex_db = wf_db_access.WorkflowExecution.get_by_id(str(wf_ex_db.id))
        lv_ac_db = lv_db_access.LiveAction.get_by_id(str(lv_ac_db.id))
        self.assertEqual(t1_ex_db.status, wf_statuses.SUCCEEDED)
        self.assertEqual(wf_ex_db.status, wf_statuses.SUCCEEDED)
        self.assertEqual(lv_ac_db.status, ac_const.LIVEACTION_STATUS_SUCCEEDED)

        # Check result.
        expected_st2_ctx = {
            "action_execution_id": str(ac_ex_db.id),
            "api_url": "http://127.0.0.1/v1",
            "user": cfg.CONF.system_user.user,
            "pack": "orquesta_tests",
            "action": "orquesta_tests.runtime-context",
            "runner": "orquesta",
        }

        expected_st2_ctx_with_wf_ex_id = copy.deepcopy(expected_st2_ctx)
        expected_st2_ctx_with_wf_ex_id["workflow_execution_id"] = str(wf_ex_db.id)

        expected_output = {
            "st2_ctx_at_input": expected_st2_ctx,
            "st2_ctx_at_vars": expected_st2_ctx,
            "st2_ctx_at_publish": expected_st2_ctx_with_wf_ex_id,
            "st2_ctx_at_output": expected_st2_ctx_with_wf_ex_id,
        }

        expected_result = {"output": expected_output}

        self.assertDictEqual(lv_ac_db.result, expected_result)

    def test_action_context_sys_user(self):
        wf_name = "subworkflow-default-value-from-action-context"
        wf_meta = base.get_wf_fixture_meta_data(TEST_PACK_PATH, wf_name + ".yaml")
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
        t1_ex_db = wf_db_access.TaskExecution.query(
            workflow_execution=str(wf_ex_db.id)
        )[0]
        t1_ac_ex_db = ex_db_access.ActionExecution.query(
            task_execution=str(t1_ex_db.id)
        )[0]
        t1_wf_ex_db = wf_db_access.WorkflowExecution.query(
            action_execution=str(t1_ac_ex_db.id)
        )[0]
        self.assertEqual(t1_ex_db.status, wf_statuses.RUNNING)
        self.assertEqual(t1_ac_ex_db.status, ac_const.LIVEACTION_STATUS_RUNNING)
        self.assertEqual(t1_wf_ex_db.status, wf_statuses.RUNNING)

        # Complete subworkflow under task1.
        query_filters = {"workflow_execution": str(t1_wf_ex_db.id), "task_id": "task1"}
        t1_t1_ex_db = wf_db_access.TaskExecution.query(**query_filters)[0]
        t1_t1_ac_ex_db = ex_db_access.ActionExecution.query(
            task_execution=str(t1_t1_ex_db.id)
        )[0]
        wf_svc.handle_action_execution_completion(t1_t1_ac_ex_db)

        query_filters = {"workflow_execution": str(t1_wf_ex_db.id), "task_id": "task2"}
        t1_t2_ex_db = wf_db_access.TaskExecution.query(**query_filters)[0]
        t1_t2_ac_ex_db = ex_db_access.ActionExecution.query(
            task_execution=str(t1_t2_ex_db.id)
        )[0]
        wf_svc.handle_action_execution_completion(t1_t2_ac_ex_db)

        query_filters = {"workflow_execution": str(t1_wf_ex_db.id), "task_id": "task3"}
        t1_t3_ex_db = wf_db_access.TaskExecution.query(**query_filters)[0]
        t1_t3_ac_ex_db = ex_db_access.ActionExecution.query(
            task_execution=str(t1_t3_ex_db.id)
        )[0]
        wf_svc.handle_action_execution_completion(t1_t3_ac_ex_db)

        t1_wf_ex_db = wf_db_access.WorkflowExecution.get_by_id(str(t1_wf_ex_db.id))
        t1_ac_ex_db = ex_db_access.ActionExecution.get_by_id(str(t1_ac_ex_db.id))
        self.assertEqual(t1_wf_ex_db.status, wf_statuses.SUCCEEDED)
        self.assertEqual(t1_ac_ex_db.status, ac_const.LIVEACTION_STATUS_SUCCEEDED)

        # Complete task1 and main workflow.
        wf_svc.handle_action_execution_completion(t1_ac_ex_db)
        t1_ex_db = wf_db_access.TaskExecution.get_by_id(str(t1_ex_db.id))
        wf_ex_db = wf_db_access.WorkflowExecution.get_by_id(str(wf_ex_db.id))
        lv_ac_db = lv_db_access.LiveAction.get_by_id(str(lv_ac_db.id))
        self.assertEqual(t1_ex_db.status, wf_statuses.SUCCEEDED)
        self.assertEqual(wf_ex_db.status, wf_statuses.SUCCEEDED)
        self.assertEqual(lv_ac_db.status, ac_const.LIVEACTION_STATUS_SUCCEEDED)

        user = cfg.CONF.system_user.user
        # Check result.
        expected_result = {
            "output": {"msg": f"{user}, All your base are belong to us!"}
        }

        self.assertDictEqual(lv_ac_db.result, expected_result)

    def test_action_context_api_user(self):
        wf_name = "subworkflow-default-value-from-action-context"
        wf_meta = base.get_wf_fixture_meta_data(TEST_PACK_PATH, wf_name + ".yaml")
        lv_ac_db = lv_db_models.LiveActionDB(
            action=wf_meta["name"], context={"api_user": "Thanos"}
        )
        lv_ac_db, ac_ex_db = ac_svc.request(lv_ac_db)
        lv_ac_db = lv_db_access.LiveAction.get_by_id(str(lv_ac_db.id))
        self.assertEqual(
            lv_ac_db.status, ac_const.LIVEACTION_STATUS_RUNNING, lv_ac_db.result
        )

        # Identify the records for the main workflow.
        wf_ex_db = wf_db_access.WorkflowExecution.query(
            action_execution=str(ac_ex_db.id)
        )[0]
        t1_ex_db = wf_db_access.TaskExecution.query(
            workflow_execution=str(wf_ex_db.id)
        )[0]
        t1_ac_ex_db = ex_db_access.ActionExecution.query(
            task_execution=str(t1_ex_db.id)
        )[0]
        t1_wf_ex_db = wf_db_access.WorkflowExecution.query(
            action_execution=str(t1_ac_ex_db.id)
        )[0]
        self.assertEqual(t1_ex_db.status, wf_statuses.RUNNING)
        self.assertEqual(t1_ac_ex_db.status, ac_const.LIVEACTION_STATUS_RUNNING)
        self.assertEqual(t1_wf_ex_db.status, wf_statuses.RUNNING)

        # Complete subworkflow under task1.
        query_filters = {"workflow_execution": str(t1_wf_ex_db.id), "task_id": "task1"}
        t1_t1_ex_db = wf_db_access.TaskExecution.query(**query_filters)[0]
        t1_t1_ac_ex_db = ex_db_access.ActionExecution.query(
            task_execution=str(t1_t1_ex_db.id)
        )[0]
        wf_svc.handle_action_execution_completion(t1_t1_ac_ex_db)

        query_filters = {"workflow_execution": str(t1_wf_ex_db.id), "task_id": "task2"}
        t1_t2_ex_db = wf_db_access.TaskExecution.query(**query_filters)[0]
        t1_t2_ac_ex_db = ex_db_access.ActionExecution.query(
            task_execution=str(t1_t2_ex_db.id)
        )[0]
        wf_svc.handle_action_execution_completion(t1_t2_ac_ex_db)

        query_filters = {"workflow_execution": str(t1_wf_ex_db.id), "task_id": "task3"}
        t1_t3_ex_db = wf_db_access.TaskExecution.query(**query_filters)[0]
        t1_t3_ac_ex_db = ex_db_access.ActionExecution.query(
            task_execution=str(t1_t3_ex_db.id)
        )[0]
        wf_svc.handle_action_execution_completion(t1_t3_ac_ex_db)

        t1_wf_ex_db = wf_db_access.WorkflowExecution.get_by_id(str(t1_wf_ex_db.id))
        t1_ac_ex_db = ex_db_access.ActionExecution.get_by_id(str(t1_ac_ex_db.id))
        self.assertEqual(t1_wf_ex_db.status, wf_statuses.SUCCEEDED)
        self.assertEqual(t1_ac_ex_db.status, ac_const.LIVEACTION_STATUS_SUCCEEDED)

        # Complete task1 and main workflow.
        wf_svc.handle_action_execution_completion(t1_ac_ex_db)
        t1_ex_db = wf_db_access.TaskExecution.get_by_id(str(t1_ex_db.id))
        wf_ex_db = wf_db_access.WorkflowExecution.get_by_id(str(wf_ex_db.id))
        lv_ac_db = lv_db_access.LiveAction.get_by_id(str(lv_ac_db.id))
        self.assertEqual(t1_ex_db.status, wf_statuses.SUCCEEDED)
        self.assertEqual(wf_ex_db.status, wf_statuses.SUCCEEDED)
        self.assertEqual(lv_ac_db.status, ac_const.LIVEACTION_STATUS_SUCCEEDED)

        # Check result.
        expected_result = {"output": {"msg": "Thanos, All your base are belong to us!"}}

        self.assertDictEqual(lv_ac_db.result, expected_result)

    def test_action_context_no_channel(self):
        wf_name = "subworkflow-source-channel-from-action-context"
        wf_meta = base.get_wf_fixture_meta_data(TEST_PACK_PATH, wf_name + ".yaml")
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
        t1_ex_db = wf_db_access.TaskExecution.query(
            workflow_execution=str(wf_ex_db.id)
        )[0]
        t1_ac_ex_db = ex_db_access.ActionExecution.query(
            task_execution=str(t1_ex_db.id)
        )[0]
        t1_wf_ex_db = wf_db_access.WorkflowExecution.query(
            action_execution=str(t1_ac_ex_db.id)
        )[0]
        self.assertEqual(t1_ex_db.status, wf_statuses.RUNNING)
        self.assertEqual(t1_ac_ex_db.status, ac_const.LIVEACTION_STATUS_RUNNING)
        self.assertEqual(t1_wf_ex_db.status, wf_statuses.RUNNING)

        # Complete subworkflow under task1.
        query_filters = {"workflow_execution": str(t1_wf_ex_db.id), "task_id": "task1"}
        t1_t1_ex_db = wf_db_access.TaskExecution.query(**query_filters)[0]
        t1_t1_ac_ex_db = ex_db_access.ActionExecution.query(
            task_execution=str(t1_t1_ex_db.id)
        )[0]
        wf_svc.handle_action_execution_completion(t1_t1_ac_ex_db)

        query_filters = {"workflow_execution": str(t1_wf_ex_db.id), "task_id": "task2"}
        t1_t2_ex_db = wf_db_access.TaskExecution.query(**query_filters)[0]
        t1_t2_ac_ex_db = ex_db_access.ActionExecution.query(
            task_execution=str(t1_t2_ex_db.id)
        )[0]
        wf_svc.handle_action_execution_completion(t1_t2_ac_ex_db)

        query_filters = {"workflow_execution": str(t1_wf_ex_db.id), "task_id": "task3"}
        t1_t3_ex_db = wf_db_access.TaskExecution.query(**query_filters)[0]
        t1_t3_ac_ex_db = ex_db_access.ActionExecution.query(
            task_execution=str(t1_t3_ex_db.id)
        )[0]
        wf_svc.handle_action_execution_completion(t1_t3_ac_ex_db)

        t1_wf_ex_db = wf_db_access.WorkflowExecution.get_by_id(str(t1_wf_ex_db.id))
        t1_ac_ex_db = ex_db_access.ActionExecution.get_by_id(str(t1_ac_ex_db.id))
        self.assertEqual(t1_wf_ex_db.status, wf_statuses.SUCCEEDED)
        self.assertEqual(t1_ac_ex_db.status, ac_const.LIVEACTION_STATUS_SUCCEEDED)

        # Complete task1 and main workflow.
        wf_svc.handle_action_execution_completion(t1_ac_ex_db)
        t1_ex_db = wf_db_access.TaskExecution.get_by_id(str(t1_ex_db.id))
        wf_ex_db = wf_db_access.WorkflowExecution.get_by_id(str(wf_ex_db.id))
        lv_ac_db = lv_db_access.LiveAction.get_by_id(str(lv_ac_db.id))
        self.assertEqual(t1_ex_db.status, wf_statuses.SUCCEEDED)
        self.assertEqual(wf_ex_db.status, wf_statuses.SUCCEEDED)
        self.assertEqual(lv_ac_db.status, ac_const.LIVEACTION_STATUS_SUCCEEDED)

        # Check result.
        expected_result = {
            "output": {"msg": "no_channel, All your base are belong to us!"}
        }

        self.assertDictEqual(lv_ac_db.result, expected_result)

    def test_action_context_source_channel(self):
        wf_name = "subworkflow-source-channel-from-action-context"
        wf_meta = base.get_wf_fixture_meta_data(TEST_PACK_PATH, wf_name + ".yaml")
        lv_ac_db = lv_db_models.LiveActionDB(
            action=wf_meta["name"], context={"source_channel": "general"}
        )
        lv_ac_db, ac_ex_db = ac_svc.request(lv_ac_db)
        lv_ac_db = lv_db_access.LiveAction.get_by_id(str(lv_ac_db.id))
        self.assertEqual(
            lv_ac_db.status, ac_const.LIVEACTION_STATUS_RUNNING, lv_ac_db.result
        )

        # Identify the records for the main workflow.
        wf_ex_db = wf_db_access.WorkflowExecution.query(
            action_execution=str(ac_ex_db.id)
        )[0]
        t1_ex_db = wf_db_access.TaskExecution.query(
            workflow_execution=str(wf_ex_db.id)
        )[0]
        t1_ac_ex_db = ex_db_access.ActionExecution.query(
            task_execution=str(t1_ex_db.id)
        )[0]
        t1_wf_ex_db = wf_db_access.WorkflowExecution.query(
            action_execution=str(t1_ac_ex_db.id)
        )[0]
        self.assertEqual(t1_ex_db.status, wf_statuses.RUNNING)
        self.assertEqual(t1_ac_ex_db.status, ac_const.LIVEACTION_STATUS_RUNNING)
        self.assertEqual(t1_wf_ex_db.status, wf_statuses.RUNNING)

        # Complete subworkflow under task1.
        query_filters = {"workflow_execution": str(t1_wf_ex_db.id), "task_id": "task1"}
        t1_t1_ex_db = wf_db_access.TaskExecution.query(**query_filters)[0]
        t1_t1_ac_ex_db = ex_db_access.ActionExecution.query(
            task_execution=str(t1_t1_ex_db.id)
        )[0]
        wf_svc.handle_action_execution_completion(t1_t1_ac_ex_db)

        query_filters = {"workflow_execution": str(t1_wf_ex_db.id), "task_id": "task2"}
        t1_t2_ex_db = wf_db_access.TaskExecution.query(**query_filters)[0]
        t1_t2_ac_ex_db = ex_db_access.ActionExecution.query(
            task_execution=str(t1_t2_ex_db.id)
        )[0]
        wf_svc.handle_action_execution_completion(t1_t2_ac_ex_db)

        query_filters = {"workflow_execution": str(t1_wf_ex_db.id), "task_id": "task3"}
        t1_t3_ex_db = wf_db_access.TaskExecution.query(**query_filters)[0]
        t1_t3_ac_ex_db = ex_db_access.ActionExecution.query(
            task_execution=str(t1_t3_ex_db.id)
        )[0]
        wf_svc.handle_action_execution_completion(t1_t3_ac_ex_db)

        t1_wf_ex_db = wf_db_access.WorkflowExecution.get_by_id(str(t1_wf_ex_db.id))
        t1_ac_ex_db = ex_db_access.ActionExecution.get_by_id(str(t1_ac_ex_db.id))
        self.assertEqual(t1_wf_ex_db.status, wf_statuses.SUCCEEDED)
        self.assertEqual(t1_ac_ex_db.status, ac_const.LIVEACTION_STATUS_SUCCEEDED)

        # Complete task1 and main workflow.
        wf_svc.handle_action_execution_completion(t1_ac_ex_db)
        t1_ex_db = wf_db_access.TaskExecution.get_by_id(str(t1_ex_db.id))
        wf_ex_db = wf_db_access.WorkflowExecution.get_by_id(str(wf_ex_db.id))
        lv_ac_db = lv_db_access.LiveAction.get_by_id(str(lv_ac_db.id))
        self.assertEqual(t1_ex_db.status, wf_statuses.SUCCEEDED)
        self.assertEqual(wf_ex_db.status, wf_statuses.SUCCEEDED)
        self.assertEqual(lv_ac_db.status, ac_const.LIVEACTION_STATUS_SUCCEEDED)

        # Check result.
        expected_result = {
            "output": {"msg": "general, All your base are belong to us!"}
        }

        self.assertDictEqual(lv_ac_db.result, expected_result)

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

# XXX: actionsensor import depends on config being setup.
import st2tests.config as tests_config

tests_config.parse_args()

from tests.unit import base

from st2actions.workflows import workflows
from st2common.bootstrap import actionsregistrar
from st2common.bootstrap import runnersregistrar
from st2common.constants import action as action_constants
from st2common.models.api import inquiry as inqy_api_models
from st2common.models.db import liveaction as lv_db_models
from st2common.persistence import execution as ex_db_access
from st2common.persistence import liveaction as lv_db_access
from st2common.persistence import workflow as wf_db_access
from st2common.services import action as action_service
from st2common.services import inquiry as inquiry_service
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

    def test_inquiry(self):
        wf_meta = base.get_wf_fixture_meta_data(TEST_PACK_PATH, "ask-approval.yaml")
        lv_ac_db = lv_db_models.LiveActionDB(action=wf_meta["name"])
        lv_ac_db, ac_ex_db = action_service.request(lv_ac_db)

        # Assert action execution is running.
        lv_ac_db = lv_db_access.LiveAction.get_by_id(str(lv_ac_db.id))
        self.assertEqual(lv_ac_db.status, action_constants.LIVEACTION_STATUS_RUNNING)
        wf_ex_db = wf_db_access.WorkflowExecution.query(
            action_execution=str(ac_ex_db.id)
        )[0]
        self.assertEqual(wf_ex_db.status, action_constants.LIVEACTION_STATUS_RUNNING)

        # Assert start task is already completed.
        query_filters = {"workflow_execution": str(wf_ex_db.id), "task_id": "start"}
        t1_ex_db = wf_db_access.TaskExecution.query(**query_filters)[0]
        t1_ac_ex_db = ex_db_access.ActionExecution.query(
            task_execution=str(t1_ex_db.id)
        )[0]
        t1_lv_ac_db = lv_db_access.LiveAction.get_by_id(t1_ac_ex_db.liveaction["id"])
        self.assertEqual(
            t1_lv_ac_db.status, action_constants.LIVEACTION_STATUS_SUCCEEDED
        )
        workflows.get_engine().process(t1_ac_ex_db)
        t1_ex_db = wf_db_access.TaskExecution.get_by_id(t1_ex_db.id)
        self.assertEqual(t1_ex_db.status, wf_statuses.SUCCEEDED)

        # Assert the main workflow is still running.
        wf_ex_db = wf_db_access.WorkflowExecution.get_by_id(wf_ex_db.id)
        self.assertEqual(wf_ex_db.status, wf_statuses.RUNNING)

        # Assert get approval task is already pending.
        query_filters = {
            "workflow_execution": str(wf_ex_db.id),
            "task_id": "get_approval",
        }
        t2_ex_db = wf_db_access.TaskExecution.query(**query_filters)[0]
        t2_ac_ex_db = ex_db_access.ActionExecution.query(
            task_execution=str(t2_ex_db.id)
        )[0]
        t2_lv_ac_db = lv_db_access.LiveAction.get_by_id(t2_ac_ex_db.liveaction["id"])
        self.assertEqual(t2_lv_ac_db.status, action_constants.LIVEACTION_STATUS_PENDING)
        workflows.get_engine().process(t2_ac_ex_db)
        t2_ex_db = wf_db_access.TaskExecution.get_by_id(t2_ex_db.id)
        self.assertEqual(t2_ex_db.status, wf_statuses.PENDING)

        # Assert the main workflow is paused since it has no other active tasks.
        wf_ex_db = wf_db_access.WorkflowExecution.get_by_id(wf_ex_db.id)
        self.assertEqual(wf_ex_db.status, wf_statuses.PAUSED)

        # Respond to the inquiry and check status.
        inquiry_api = inqy_api_models.InquiryAPI.from_model(t2_ac_ex_db)
        inquiry_response = {"approved": True}
        inquiry_service.respond(inquiry_api, inquiry_response)
        t2_lv_ac_db = lv_db_access.LiveAction.get_by_id(str(t2_lv_ac_db.id))
        self.assertEqual(
            t2_lv_ac_db.status, action_constants.LIVEACTION_STATUS_SUCCEEDED
        )
        t2_ac_ex_db = ex_db_access.ActionExecution.get_by_id(str(t2_ac_ex_db.id))
        self.assertEqual(
            t2_ac_ex_db.status, action_constants.LIVEACTION_STATUS_SUCCEEDED
        )
        workflows.get_engine().process(t2_ac_ex_db)
        t2_ex_db = wf_db_access.TaskExecution.get_by_id(str(t2_ex_db.id))
        self.assertEqual(t2_ex_db.status, action_constants.LIVEACTION_STATUS_SUCCEEDED)

        # Assert the main workflow is paused since it has no other active tasks.
        wf_ex_db = wf_db_access.WorkflowExecution.get_by_id(wf_ex_db.id)
        self.assertEqual(wf_ex_db.status, wf_statuses.RUNNING)

        # Assert the final task is completed.
        query_filters = {"workflow_execution": str(wf_ex_db.id), "task_id": "finish"}
        t3_ex_db = wf_db_access.TaskExecution.query(**query_filters)[0]
        t3_ac_ex_db = ex_db_access.ActionExecution.query(
            task_execution=str(t3_ex_db.id)
        )[0]
        t3_lv_ac_db = lv_db_access.LiveAction.get_by_id(t3_ac_ex_db.liveaction["id"])
        self.assertEqual(
            t3_lv_ac_db.status, action_constants.LIVEACTION_STATUS_SUCCEEDED
        )
        workflows.get_engine().process(t3_ac_ex_db)
        t3_ex_db = wf_db_access.TaskExecution.get_by_id(t3_ex_db.id)
        self.assertEqual(t3_ex_db.status, wf_statuses.SUCCEEDED)

        # Assert the main workflow is completed
        wf_ex_db = wf_db_access.WorkflowExecution.get_by_id(wf_ex_db.id)
        self.assertEqual(wf_ex_db.status, wf_statuses.SUCCEEDED)

    def test_consecutive_inquiries(self):
        wf_meta = base.get_wf_fixture_meta_data(
            TEST_PACK_PATH, "ask-consecutive-approvals.yaml"
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

        # Assert start task is already completed.
        query_filters = {"workflow_execution": str(wf_ex_db.id), "task_id": "start"}
        t1_ex_db = wf_db_access.TaskExecution.query(**query_filters)[0]
        t1_ac_ex_db = ex_db_access.ActionExecution.query(
            task_execution=str(t1_ex_db.id)
        )[0]
        t1_lv_ac_db = lv_db_access.LiveAction.get_by_id(t1_ac_ex_db.liveaction["id"])
        self.assertEqual(
            t1_lv_ac_db.status, action_constants.LIVEACTION_STATUS_SUCCEEDED
        )
        workflows.get_engine().process(t1_ac_ex_db)
        t1_ex_db = wf_db_access.TaskExecution.get_by_id(t1_ex_db.id)
        self.assertEqual(t1_ex_db.status, wf_statuses.SUCCEEDED)

        # Assert the main workflow is still running.
        wf_ex_db = wf_db_access.WorkflowExecution.get_by_id(wf_ex_db.id)
        self.assertEqual(wf_ex_db.status, wf_statuses.RUNNING)

        # Assert get approval task is already pending.
        query_filters = {
            "workflow_execution": str(wf_ex_db.id),
            "task_id": "get_approval",
        }
        t2_ex_db = wf_db_access.TaskExecution.query(**query_filters)[0]
        t2_ac_ex_db = ex_db_access.ActionExecution.query(
            task_execution=str(t2_ex_db.id)
        )[0]
        t2_lv_ac_db = lv_db_access.LiveAction.get_by_id(t2_ac_ex_db.liveaction["id"])
        self.assertEqual(t2_lv_ac_db.status, action_constants.LIVEACTION_STATUS_PENDING)
        workflows.get_engine().process(t2_ac_ex_db)
        t2_ex_db = wf_db_access.TaskExecution.get_by_id(t2_ex_db.id)
        self.assertEqual(t2_ex_db.status, wf_statuses.PENDING)

        # Assert the main workflow is paused since it has no other active tasks.
        wf_ex_db = wf_db_access.WorkflowExecution.get_by_id(wf_ex_db.id)
        self.assertEqual(wf_ex_db.status, wf_statuses.PAUSED)

        # Respond to the inquiry and check status.
        inquiry_api = inqy_api_models.InquiryAPI.from_model(t2_ac_ex_db)
        inquiry_response = {"approved": True}
        inquiry_service.respond(inquiry_api, inquiry_response)
        t2_lv_ac_db = lv_db_access.LiveAction.get_by_id(str(t2_lv_ac_db.id))
        self.assertEqual(
            t2_lv_ac_db.status, action_constants.LIVEACTION_STATUS_SUCCEEDED
        )
        t2_ac_ex_db = ex_db_access.ActionExecution.get_by_id(str(t2_ac_ex_db.id))
        self.assertEqual(
            t2_ac_ex_db.status, action_constants.LIVEACTION_STATUS_SUCCEEDED
        )
        workflows.get_engine().process(t2_ac_ex_db)
        t2_ex_db = wf_db_access.TaskExecution.get_by_id(str(t2_ex_db.id))
        self.assertEqual(t2_ex_db.status, action_constants.LIVEACTION_STATUS_SUCCEEDED)

        # Assert the main workflow is paused since it has no other active tasks.
        wf_ex_db = wf_db_access.WorkflowExecution.get_by_id(wf_ex_db.id)
        self.assertEqual(wf_ex_db.status, wf_statuses.RUNNING)

        # Assert the final task is completed.
        query_filters = {
            "workflow_execution": str(wf_ex_db.id),
            "task_id": "get_confirmation",
        }
        t3_ex_db = wf_db_access.TaskExecution.query(**query_filters)[0]
        t3_ac_ex_db = ex_db_access.ActionExecution.query(
            task_execution=str(t3_ex_db.id)
        )[0]
        t3_lv_ac_db = lv_db_access.LiveAction.get_by_id(t3_ac_ex_db.liveaction["id"])
        self.assertEqual(t3_lv_ac_db.status, action_constants.LIVEACTION_STATUS_PENDING)
        workflows.get_engine().process(t3_ac_ex_db)
        t3_ex_db = wf_db_access.TaskExecution.get_by_id(t3_ex_db.id)
        self.assertEqual(t3_ex_db.status, wf_statuses.PENDING)

        # Assert the main workflow is completed
        wf_ex_db = wf_db_access.WorkflowExecution.get_by_id(wf_ex_db.id)
        self.assertEqual(wf_ex_db.status, wf_statuses.PAUSED)

        # Respond to the inquiry and check status.
        inquiry_api = inqy_api_models.InquiryAPI.from_model(t3_ac_ex_db)
        inquiry_response = {"approved": True}
        inquiry_service.respond(inquiry_api, inquiry_response)
        t3_lv_ac_db = lv_db_access.LiveAction.get_by_id(str(t3_lv_ac_db.id))
        self.assertEqual(
            t3_lv_ac_db.status, action_constants.LIVEACTION_STATUS_SUCCEEDED
        )
        t3_ac_ex_db = ex_db_access.ActionExecution.get_by_id(str(t3_ac_ex_db.id))
        self.assertEqual(
            t3_ac_ex_db.status, action_constants.LIVEACTION_STATUS_SUCCEEDED
        )
        workflows.get_engine().process(t3_ac_ex_db)
        t3_ex_db = wf_db_access.TaskExecution.get_by_id(str(t3_ex_db.id))
        self.assertEqual(t3_ex_db.status, action_constants.LIVEACTION_STATUS_SUCCEEDED)

        # Assert the main workflow is completed
        wf_ex_db = wf_db_access.WorkflowExecution.get_by_id(wf_ex_db.id)
        self.assertEqual(wf_ex_db.status, wf_statuses.RUNNING)

        # Assert the final task is completed.
        query_filters = {"workflow_execution": str(wf_ex_db.id), "task_id": "finish"}
        t4_ex_db = wf_db_access.TaskExecution.query(**query_filters)[0]
        t4_ac_ex_db = ex_db_access.ActionExecution.query(
            task_execution=str(t4_ex_db.id)
        )[0]
        t4_lv_ac_db = lv_db_access.LiveAction.get_by_id(t4_ac_ex_db.liveaction["id"])
        self.assertEqual(
            t4_lv_ac_db.status, action_constants.LIVEACTION_STATUS_SUCCEEDED
        )
        workflows.get_engine().process(t4_ac_ex_db)
        t4_ex_db = wf_db_access.TaskExecution.get_by_id(t4_ex_db.id)
        self.assertEqual(t4_ex_db.status, wf_statuses.SUCCEEDED)

        # Assert the main workflow is completed
        wf_ex_db = wf_db_access.WorkflowExecution.get_by_id(wf_ex_db.id)
        self.assertEqual(wf_ex_db.status, wf_statuses.SUCCEEDED)

    def test_parallel_inquiries(self):
        wf_meta = base.get_wf_fixture_meta_data(
            TEST_PACK_PATH, "ask-parallel-approvals.yaml"
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

        # Assert start task is already completed.
        query_filters = {"workflow_execution": str(wf_ex_db.id), "task_id": "start"}
        t1_ex_db = wf_db_access.TaskExecution.query(**query_filters)[0]
        t1_ac_ex_db = ex_db_access.ActionExecution.query(
            task_execution=str(t1_ex_db.id)
        )[0]
        t1_lv_ac_db = lv_db_access.LiveAction.get_by_id(t1_ac_ex_db.liveaction["id"])
        self.assertEqual(
            t1_lv_ac_db.status, action_constants.LIVEACTION_STATUS_SUCCEEDED
        )
        workflows.get_engine().process(t1_ac_ex_db)
        t1_ex_db = wf_db_access.TaskExecution.get_by_id(t1_ex_db.id)
        self.assertEqual(t1_ex_db.status, wf_statuses.SUCCEEDED)

        # Assert the main workflow is still running.
        wf_ex_db = wf_db_access.WorkflowExecution.get_by_id(wf_ex_db.id)
        self.assertEqual(wf_ex_db.status, wf_statuses.RUNNING)

        # Assert get approval task is already pending.
        query_filters = {"workflow_execution": str(wf_ex_db.id), "task_id": "ask_jack"}
        t2_ex_db = wf_db_access.TaskExecution.query(**query_filters)[0]
        t2_ac_ex_db = ex_db_access.ActionExecution.query(
            task_execution=str(t2_ex_db.id)
        )[0]
        t2_lv_ac_db = lv_db_access.LiveAction.get_by_id(t2_ac_ex_db.liveaction["id"])
        self.assertEqual(t2_lv_ac_db.status, action_constants.LIVEACTION_STATUS_PENDING)
        workflows.get_engine().process(t2_ac_ex_db)
        t2_ex_db = wf_db_access.TaskExecution.get_by_id(t2_ex_db.id)
        self.assertEqual(t2_ex_db.status, wf_statuses.PENDING)

        # Assert the main workflow is paused since it has no other active tasks.
        wf_ex_db = wf_db_access.WorkflowExecution.get_by_id(wf_ex_db.id)
        self.assertEqual(wf_ex_db.status, wf_statuses.PAUSING)

        # Assert get approval task is already pending.
        query_filters = {"workflow_execution": str(wf_ex_db.id), "task_id": "ask_jill"}
        t3_ex_db = wf_db_access.TaskExecution.query(**query_filters)[0]
        t3_ac_ex_db = ex_db_access.ActionExecution.query(
            task_execution=str(t3_ex_db.id)
        )[0]
        t3_lv_ac_db = lv_db_access.LiveAction.get_by_id(t3_ac_ex_db.liveaction["id"])
        self.assertEqual(t3_lv_ac_db.status, action_constants.LIVEACTION_STATUS_PENDING)
        workflows.get_engine().process(t3_ac_ex_db)
        t3_ex_db = wf_db_access.TaskExecution.get_by_id(t3_ex_db.id)
        self.assertEqual(t3_ex_db.status, wf_statuses.PENDING)

        # Assert the main workflow is paused since it has no other active tasks.
        wf_ex_db = wf_db_access.WorkflowExecution.get_by_id(wf_ex_db.id)
        self.assertEqual(wf_ex_db.status, wf_statuses.PAUSED)

        # Respond to the inquiry and check status.
        inquiry_api = inqy_api_models.InquiryAPI.from_model(t2_ac_ex_db)
        inquiry_response = {"approved": True}
        inquiry_service.respond(inquiry_api, inquiry_response)
        t2_lv_ac_db = lv_db_access.LiveAction.get_by_id(str(t2_lv_ac_db.id))
        self.assertEqual(
            t2_lv_ac_db.status, action_constants.LIVEACTION_STATUS_SUCCEEDED
        )
        t2_ac_ex_db = ex_db_access.ActionExecution.get_by_id(str(t2_ac_ex_db.id))
        self.assertEqual(
            t2_ac_ex_db.status, action_constants.LIVEACTION_STATUS_SUCCEEDED
        )
        workflows.get_engine().process(t2_ac_ex_db)
        t2_ex_db = wf_db_access.TaskExecution.get_by_id(str(t2_ex_db.id))
        self.assertEqual(t2_ex_db.status, action_constants.LIVEACTION_STATUS_SUCCEEDED)

        # Assert the main workflow is paused because we are still waiting for
        # the other pending task and there are no other active tasks.
        wf_ex_db = wf_db_access.WorkflowExecution.get_by_id(wf_ex_db.id)
        self.assertEqual(wf_ex_db.status, wf_statuses.PAUSED)

        # Respond to the inquiry and check status.
        inquiry_api = inqy_api_models.InquiryAPI.from_model(t3_ac_ex_db)
        inquiry_response = {"approved": True}
        inquiry_service.respond(inquiry_api, inquiry_response)
        t3_lv_ac_db = lv_db_access.LiveAction.get_by_id(str(t3_lv_ac_db.id))
        self.assertEqual(
            t3_lv_ac_db.status, action_constants.LIVEACTION_STATUS_SUCCEEDED
        )
        t3_ac_ex_db = ex_db_access.ActionExecution.get_by_id(str(t3_ac_ex_db.id))
        self.assertEqual(
            t3_ac_ex_db.status, action_constants.LIVEACTION_STATUS_SUCCEEDED
        )
        workflows.get_engine().process(t3_ac_ex_db)
        t3_ex_db = wf_db_access.TaskExecution.get_by_id(str(t3_ex_db.id))
        self.assertEqual(t3_ex_db.status, action_constants.LIVEACTION_STATUS_SUCCEEDED)

        # Assert the main workflow resumed running.
        wf_ex_db = wf_db_access.WorkflowExecution.get_by_id(wf_ex_db.id)
        self.assertEqual(wf_ex_db.status, wf_statuses.RUNNING)

        # Assert the final task is completed.
        query_filters = {"workflow_execution": str(wf_ex_db.id), "task_id": "finish"}
        t4_ex_db = wf_db_access.TaskExecution.query(**query_filters)[0]
        t4_ac_ex_db = ex_db_access.ActionExecution.query(
            task_execution=str(t4_ex_db.id)
        )[0]
        t4_lv_ac_db = lv_db_access.LiveAction.get_by_id(t4_ac_ex_db.liveaction["id"])
        self.assertEqual(
            t4_lv_ac_db.status, action_constants.LIVEACTION_STATUS_SUCCEEDED
        )
        workflows.get_engine().process(t4_ac_ex_db)
        t4_ex_db = wf_db_access.TaskExecution.get_by_id(t4_ex_db.id)
        self.assertEqual(t4_ex_db.status, wf_statuses.SUCCEEDED)

        # Assert the main workflow is completed
        wf_ex_db = wf_db_access.WorkflowExecution.get_by_id(wf_ex_db.id)
        self.assertEqual(wf_ex_db.status, wf_statuses.SUCCEEDED)

    def test_nested_inquiry(self):
        wf_meta = base.get_wf_fixture_meta_data(
            TEST_PACK_PATH, "ask-nested-approval.yaml"
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

        # Assert start task is already completed.
        query_filters = {"workflow_execution": str(wf_ex_db.id), "task_id": "start"}
        t1_ex_db = wf_db_access.TaskExecution.query(**query_filters)[0]
        t1_ac_ex_db = ex_db_access.ActionExecution.query(
            task_execution=str(t1_ex_db.id)
        )[0]
        t1_lv_ac_db = lv_db_access.LiveAction.get_by_id(t1_ac_ex_db.liveaction["id"])
        self.assertEqual(
            t1_lv_ac_db.status, action_constants.LIVEACTION_STATUS_SUCCEEDED
        )
        workflows.get_engine().process(t1_ac_ex_db)
        t1_ex_db = wf_db_access.TaskExecution.get_by_id(t1_ex_db.id)
        self.assertEqual(t1_ex_db.status, wf_statuses.SUCCEEDED)

        # Assert the main workflow is still running.
        wf_ex_db = wf_db_access.WorkflowExecution.get_by_id(wf_ex_db.id)
        self.assertEqual(wf_ex_db.status, wf_statuses.RUNNING)

        # Assert the subworkflow is already started.
        query_filters = {
            "workflow_execution": str(wf_ex_db.id),
            "task_id": "get_approval",
        }
        t2_ex_db = wf_db_access.TaskExecution.query(**query_filters)[0]
        t2_ac_ex_db = ex_db_access.ActionExecution.query(
            task_execution=str(t2_ex_db.id)
        )[0]
        t2_lv_ac_db = lv_db_access.LiveAction.get_by_id(t2_ac_ex_db.liveaction["id"])
        self.assertEqual(t2_lv_ac_db.status, action_constants.LIVEACTION_STATUS_RUNNING)
        workflows.get_engine().process(t2_ac_ex_db)
        t2_ex_db = wf_db_access.TaskExecution.get_by_id(t2_ex_db.id)
        self.assertEqual(t2_ex_db.status, wf_statuses.RUNNING)
        t2_wf_ex_db = wf_db_access.WorkflowExecution.query(
            action_execution=str(t2_ac_ex_db.id)
        )[0]
        self.assertEqual(t2_wf_ex_db.status, wf_statuses.RUNNING)

        # Process task1 of subworkflow.
        query_filters = {"workflow_execution": str(t2_wf_ex_db.id), "task_id": "start"}
        t2_t1_ex_db = wf_db_access.TaskExecution.query(**query_filters)[0]
        t2_t1_ac_ex_db = ex_db_access.ActionExecution.query(
            task_execution=str(t2_t1_ex_db.id)
        )[0]
        t2_t1_lv_ac_db = lv_db_access.LiveAction.get_by_id(
            t2_t1_ac_ex_db.liveaction["id"]
        )
        self.assertEqual(
            t2_t1_lv_ac_db.status, action_constants.LIVEACTION_STATUS_SUCCEEDED
        )
        workflows.get_engine().process(t2_t1_ac_ex_db)
        t2_t1_ex_db = wf_db_access.TaskExecution.get_by_id(t2_t1_ex_db.id)
        self.assertEqual(t2_t1_ex_db.status, wf_statuses.SUCCEEDED)
        t2_wf_ex_db = wf_db_access.WorkflowExecution.get_by_id(str(t2_wf_ex_db.id))
        self.assertEqual(t2_wf_ex_db.status, wf_statuses.RUNNING)

        # Process inquiry task of subworkflow and assert the subworkflow is paused.
        query_filters = {
            "workflow_execution": str(t2_wf_ex_db.id),
            "task_id": "get_approval",
        }
        t2_t2_ex_db = wf_db_access.TaskExecution.query(**query_filters)[0]
        t2_t2_ac_ex_db = ex_db_access.ActionExecution.query(
            task_execution=str(t2_t2_ex_db.id)
        )[0]
        t2_t2_lv_ac_db = lv_db_access.LiveAction.get_by_id(
            t2_t2_ac_ex_db.liveaction["id"]
        )
        self.assertEqual(
            t2_t2_lv_ac_db.status, action_constants.LIVEACTION_STATUS_PENDING
        )
        workflows.get_engine().process(t2_t2_ac_ex_db)
        t2_t2_ex_db = wf_db_access.TaskExecution.get_by_id(t2_t2_ex_db.id)
        self.assertEqual(t2_t2_ex_db.status, wf_statuses.PENDING)
        t2_wf_ex_db = wf_db_access.WorkflowExecution.get_by_id(str(t2_wf_ex_db.id))
        self.assertEqual(t2_wf_ex_db.status, wf_statuses.PAUSED)

        # Process the corresponding task in parent workflow and assert the task is paused.
        t2_ac_ex_db = ex_db_access.ActionExecution.query(
            task_execution=str(t2_ex_db.id)
        )[0]
        t2_lv_ac_db = lv_db_access.LiveAction.get_by_id(t2_ac_ex_db.liveaction["id"])
        self.assertEqual(t2_lv_ac_db.status, action_constants.LIVEACTION_STATUS_PAUSED)
        workflows.get_engine().process(t2_ac_ex_db)
        t2_ex_db = wf_db_access.TaskExecution.get_by_id(t2_ex_db.id)
        self.assertEqual(t2_ex_db.status, wf_statuses.PAUSED)

        # Assert the main workflow is paused.
        wf_ex_db = wf_db_access.WorkflowExecution.get_by_id(wf_ex_db.id)
        self.assertEqual(wf_ex_db.status, wf_statuses.PAUSED)

        # Respond to the inquiry and check status.
        inquiry_api = inqy_api_models.InquiryAPI.from_model(t2_t2_ac_ex_db)
        inquiry_response = {"approved": True}
        inquiry_service.respond(inquiry_api, inquiry_response)
        t2_t2_lv_ac_db = lv_db_access.LiveAction.get_by_id(str(t2_t2_lv_ac_db.id))
        self.assertEqual(
            t2_t2_lv_ac_db.status, action_constants.LIVEACTION_STATUS_SUCCEEDED
        )
        t2_t2_ac_ex_db = ex_db_access.ActionExecution.get_by_id(str(t2_t2_ac_ex_db.id))
        self.assertEqual(
            t2_t2_ac_ex_db.status, action_constants.LIVEACTION_STATUS_SUCCEEDED
        )
        workflows.get_engine().process(t2_t2_ac_ex_db)
        t2_t2_ex_db = wf_db_access.TaskExecution.get_by_id(str(t2_t2_ex_db.id))
        self.assertEqual(
            t2_t2_ex_db.status, action_constants.LIVEACTION_STATUS_SUCCEEDED
        )

        # Assert the main workflow is running again.
        wf_ex_db = wf_db_access.WorkflowExecution.get_by_id(wf_ex_db.id)
        self.assertEqual(wf_ex_db.status, wf_statuses.RUNNING)

        # Complete the rest of the subworkflow
        query_filters = {"workflow_execution": str(t2_wf_ex_db.id), "task_id": "finish"}
        t2_t3_ex_db = wf_db_access.TaskExecution.query(**query_filters)[0]
        t2_t3_ac_ex_db = ex_db_access.ActionExecution.query(
            task_execution=str(t2_t3_ex_db.id)
        )[0]
        t2_t3_lv_ac_db = lv_db_access.LiveAction.get_by_id(
            t2_t3_ac_ex_db.liveaction["id"]
        )
        self.assertEqual(
            t2_t3_lv_ac_db.status, action_constants.LIVEACTION_STATUS_SUCCEEDED
        )
        workflows.get_engine().process(t2_t3_ac_ex_db)
        t2_t3_ex_db = wf_db_access.TaskExecution.get_by_id(t2_t3_ex_db.id)
        self.assertEqual(t2_t3_ex_db.status, wf_statuses.SUCCEEDED)
        t2_wf_ex_db = wf_db_access.WorkflowExecution.get_by_id(str(t2_wf_ex_db.id))
        self.assertEqual(t2_wf_ex_db.status, wf_statuses.SUCCEEDED)
        t2_ac_ex_db = ex_db_access.ActionExecution.query(
            task_execution=str(t2_ex_db.id)
        )[0]
        t2_lv_ac_db = lv_db_access.LiveAction.get_by_id(t2_ac_ex_db.liveaction["id"])
        self.assertEqual(
            t2_lv_ac_db.status, action_constants.LIVEACTION_STATUS_SUCCEEDED
        )
        workflows.get_engine().process(t2_ac_ex_db)
        t2_ex_db = wf_db_access.TaskExecution.get_by_id(t2_ex_db.id)
        self.assertEqual(t2_ex_db.status, wf_statuses.SUCCEEDED)
        wf_ex_db = wf_db_access.WorkflowExecution.get_by_id(wf_ex_db.id)
        self.assertEqual(wf_ex_db.status, wf_statuses.RUNNING)

        # Complete the rest of the main workflow
        query_filters = {"workflow_execution": str(wf_ex_db.id), "task_id": "finish"}
        t3_ex_db = wf_db_access.TaskExecution.query(**query_filters)[0]
        t3_ac_ex_db = ex_db_access.ActionExecution.query(
            task_execution=str(t3_ex_db.id)
        )[0]
        t3_lv_ac_db = lv_db_access.LiveAction.get_by_id(t3_ac_ex_db.liveaction["id"])
        self.assertEqual(
            t3_lv_ac_db.status, action_constants.LIVEACTION_STATUS_SUCCEEDED
        )
        workflows.get_engine().process(t3_ac_ex_db)
        t3_ex_db = wf_db_access.TaskExecution.get_by_id(t3_ex_db.id)
        self.assertEqual(t3_ex_db.status, wf_statuses.SUCCEEDED)
        wf_ex_db = wf_db_access.WorkflowExecution.get_by_id(wf_ex_db.id)
        self.assertEqual(wf_ex_db.status, wf_statuses.SUCCEEDED)

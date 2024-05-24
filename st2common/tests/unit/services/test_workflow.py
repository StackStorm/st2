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

from orquesta import exceptions as orquesta_exc
from orquesta.specs import loader as specs_loader
from orquesta import statuses as wf_statuses

import st2tests

from st2common.bootstrap import actionsregistrar
from st2common.bootstrap import runnersregistrar
from st2common.exceptions import action as action_exc
from st2common.models.db import liveaction as lv_db_models
from st2common.models.db import execution as ex_db_models
from st2common.models.db import pack as pk_db_models
from st2common.persistence import execution as ex_db_access
from st2common.persistence import pack as pk_db_access
from st2common.persistence import workflow as wf_db_access
from st2common.services import action as action_service
from st2common.services import workflows as workflow_service
from st2common.transport import liveaction as lv_ac_xport
from st2common.transport import publishers
from st2tests.fixtures.packs.core.fixture import PACK_PATH as CORE_PACK_PATH
from st2tests.fixtures.packs.dummy_pack_7.fixture import (
    PACK_DIR_NAME as PACK_7,
    PACK_PATH as PACK_7_PATH,
)
from st2tests.fixtures.packs.orquesta_tests.fixture import PACK_PATH as TEST_PACK_PATH
from st2tests.mocks import liveaction as mock_lv_ac_xport


PACKS = [TEST_PACK_PATH, PACK_7_PATH, CORE_PACK_PATH]


@mock.patch.object(
    publishers.CUDPublisher, "publish_update", mock.MagicMock(return_value=None)
)
@mock.patch.object(
    publishers.CUDPublisher,
    "publish_create",
    mock.MagicMock(side_effect=mock_lv_ac_xport.MockLiveActionPublisher.publish_create),
)
@mock.patch.object(
    lv_ac_xport.LiveActionPublisher,
    "publish_state",
    mock.MagicMock(side_effect=mock_lv_ac_xport.MockLiveActionPublisher.publish_state),
)
class WorkflowExecutionServiceTest(st2tests.WorkflowTestCase):
    @classmethod
    def setUpClass(cls):
        super(WorkflowExecutionServiceTest, cls).setUpClass()

        # Register runners.
        runnersregistrar.register_runners()

        # Register test pack(s).
        actions_registrar = actionsregistrar.ActionsRegistrar(
            use_pack_cache=False, fail_on_failure=True
        )

        for pack in PACKS:
            actions_registrar.register_from_pack(pack)

    def test_request(self):
        wf_meta = self.get_wf_fixture_meta_data(TEST_PACK_PATH, "sequential.yaml")

        # Manually create the liveaction and action execution objects without publishing.
        lv_ac_db = lv_db_models.LiveActionDB(action=wf_meta["name"])
        lv_ac_db, ac_ex_db = action_service.create_request(lv_ac_db)

        # Request the workflow execution.
        wf_def = self.get_wf_def(TEST_PACK_PATH, wf_meta)
        st2_ctx = self.mock_st2_context(ac_ex_db)
        wf_ex_db = workflow_service.request(wf_def, ac_ex_db, st2_ctx)

        # Check workflow execution is saved to the database.
        wf_ex_dbs = wf_db_access.WorkflowExecution.query(
            action_execution=str(ac_ex_db.id)
        )
        self.assertEqual(len(wf_ex_dbs), 1)

        # Check required attributes.
        wf_ex_db = wf_ex_dbs[0]
        self.assertIsNotNone(wf_ex_db.id)
        self.assertGreater(wf_ex_db.rev, 0)
        self.assertEqual(wf_ex_db.action_execution, str(ac_ex_db.id))
        self.assertEqual(wf_ex_db.status, wf_statuses.REQUESTED)

    def test_request_with_input(self):
        wf_meta = self.get_wf_fixture_meta_data(TEST_PACK_PATH, "sequential.yaml")

        # Manually create the liveaction and action execution objects without publishing.
        lv_ac_db = lv_db_models.LiveActionDB(
            action=wf_meta["name"], parameters={"who": "stan"}
        )
        lv_ac_db, ac_ex_db = action_service.create_request(lv_ac_db)

        # Request the workflow execution.
        wf_def = self.get_wf_def(TEST_PACK_PATH, wf_meta)
        st2_ctx = self.mock_st2_context(ac_ex_db)
        wf_ex_db = workflow_service.request(wf_def, ac_ex_db, st2_ctx)

        # Check workflow execution is saved to the database.
        wf_ex_dbs = wf_db_access.WorkflowExecution.query(
            action_execution=str(ac_ex_db.id)
        )
        self.assertEqual(len(wf_ex_dbs), 1)

        # Check required attributes.
        wf_ex_db = wf_ex_dbs[0]
        self.assertIsNotNone(wf_ex_db.id)
        self.assertGreater(wf_ex_db.rev, 0)
        self.assertEqual(wf_ex_db.action_execution, str(ac_ex_db.id))
        self.assertEqual(wf_ex_db.status, wf_statuses.REQUESTED)

        # Check input and context.
        expected_input = {"who": "stan"}

        self.assertDictEqual(wf_ex_db.input, expected_input)

    def test_request_bad_action(self):
        wf_meta = self.get_wf_fixture_meta_data(TEST_PACK_PATH, "sequential.yaml")

        # Manually create the action execution object with the bad action.
        ac_ex_db = ex_db_models.ActionExecutionDB(
            action={"ref": "mock.foobar"}, runner={"name": "foobar"}
        )

        # Request the workflow execution.
        self.assertRaises(
            action_exc.InvalidActionReferencedException,
            workflow_service.request,
            self.get_wf_def(TEST_PACK_PATH, wf_meta),
            ac_ex_db,
            self.mock_st2_context(ac_ex_db),
        )

    def test_request_wf_def_with_bad_action_ref(self):
        wf_meta = self.get_wf_fixture_meta_data(
            TEST_PACK_PATH, "fail-inspection-action-ref.yaml"
        )

        # Manually create the liveaction and action execution objects without publishing.
        lv_ac_db = lv_db_models.LiveActionDB(action=wf_meta["name"])
        lv_ac_db, ac_ex_db = action_service.create_request(lv_ac_db)

        # Exception is expected on request of workflow execution.
        self.assertRaises(
            orquesta_exc.WorkflowInspectionError,
            workflow_service.request,
            self.get_wf_def(TEST_PACK_PATH, wf_meta),
            ac_ex_db,
            self.mock_st2_context(ac_ex_db),
        )

    def test_request_wf_def_with_unregistered_action(self):
        wf_meta = self.get_wf_fixture_meta_data(
            TEST_PACK_PATH, "fail-inspection-action-db.yaml"
        )

        # Manually create the liveaction and action execution objects without publishing.
        lv_ac_db = lv_db_models.LiveActionDB(action=wf_meta["name"])
        lv_ac_db, ac_ex_db = action_service.create_request(lv_ac_db)

        # Exception is expected on request of workflow execution.
        self.assertRaises(
            orquesta_exc.WorkflowInspectionError,
            workflow_service.request,
            self.get_wf_def(TEST_PACK_PATH, wf_meta),
            ac_ex_db,
            self.mock_st2_context(ac_ex_db),
        )

    def test_request_wf_def_with_missing_required_action_param(self):
        wf_name = "fail-inspection-missing-required-action-param"
        wf_meta = self.get_wf_fixture_meta_data(TEST_PACK_PATH, wf_name + ".yaml")

        # Manually create the liveaction and action execution objects without publishing.
        lv_ac_db = lv_db_models.LiveActionDB(action=wf_meta["name"])
        lv_ac_db, ac_ex_db = action_service.create_request(lv_ac_db)

        # Exception is expected on request of workflow execution.
        self.assertRaises(
            orquesta_exc.WorkflowInspectionError,
            workflow_service.request,
            self.get_wf_def(TEST_PACK_PATH, wf_meta),
            ac_ex_db,
            self.mock_st2_context(ac_ex_db),
        )

    def test_request_wf_def_with_unexpected_action_param(self):
        wf_name = "fail-inspection-unexpected-action-param"
        wf_meta = self.get_wf_fixture_meta_data(TEST_PACK_PATH, wf_name + ".yaml")

        # Manually create the liveaction and action execution objects without publishing.
        lv_ac_db = lv_db_models.LiveActionDB(action=wf_meta["name"])
        lv_ac_db, ac_ex_db = action_service.create_request(lv_ac_db)

        # Exception is expected on request of workflow execution.
        self.assertRaises(
            orquesta_exc.WorkflowInspectionError,
            workflow_service.request,
            self.get_wf_def(TEST_PACK_PATH, wf_meta),
            ac_ex_db,
            self.mock_st2_context(ac_ex_db),
        )

    def test_request_task_execution(self):
        wf_meta = self.get_wf_fixture_meta_data(TEST_PACK_PATH, "sequential.yaml")

        # Manually create the liveaction and action execution objects without publishing.
        lv_ac_db = lv_db_models.LiveActionDB(action=wf_meta["name"])
        lv_ac_db, ac_ex_db = action_service.create_request(lv_ac_db)

        # Request the workflow execution.
        wf_def = self.get_wf_def(TEST_PACK_PATH, wf_meta)
        st2_ctx = self.mock_st2_context(ac_ex_db)
        wf_ex_db = workflow_service.request(wf_def, ac_ex_db, st2_ctx)
        spec_module = specs_loader.get_spec_module(wf_ex_db.spec["catalog"])
        wf_spec = spec_module.WorkflowSpec.deserialize(wf_ex_db.spec)

        # Manually request task execution.
        task_route = 0
        task_id = "task1"
        task_spec = wf_spec.tasks.get_task(task_id)
        task_ctx = {"foo": "bar"}
        st2_ctx = {"execution_id": wf_ex_db.action_execution}

        task_ex_req = {
            "id": task_id,
            "route": task_route,
            "spec": task_spec,
            "ctx": task_ctx,
            "actions": [
                {"action": "core.echo", "input": {"message": "Veni, vidi, vici."}}
            ],
        }

        workflow_service.request_task_execution(wf_ex_db, st2_ctx, task_ex_req)

        # Check task execution is saved to the database.
        task_ex_dbs = wf_db_access.TaskExecution.query(
            workflow_execution=str(wf_ex_db.id)
        )
        self.assertEqual(len(task_ex_dbs), 1)

        # Check required attributes.
        task_ex_db = task_ex_dbs[0]
        self.assertIsNotNone(task_ex_db.id)
        self.assertGreater(task_ex_db.rev, 0)
        self.assertEqual(task_ex_db.workflow_execution, str(wf_ex_db.id))
        self.assertEqual(task_ex_db.status, wf_statuses.RUNNING)

        # Check action execution for the task query with task execution ID.
        ac_ex_dbs = ex_db_access.ActionExecution.query(
            task_execution=str(task_ex_db.id)
        )
        self.assertEqual(len(ac_ex_dbs), 1)

        # Check action execution for the task query with workflow execution ID.
        ac_ex_dbs = ex_db_access.ActionExecution.query(
            workflow_execution=str(wf_ex_db.id)
        )
        self.assertEqual(len(ac_ex_dbs), 1)

    def test_request_task_execution_bad_action(self):
        wf_meta = self.get_wf_fixture_meta_data(TEST_PACK_PATH, "sequential.yaml")

        # Manually create the liveaction and action execution objects without publishing.
        lv_ac_db = lv_db_models.LiveActionDB(action=wf_meta["name"])
        lv_ac_db, ac_ex_db = action_service.create_request(lv_ac_db)

        # Request the workflow execution.
        wf_def = self.get_wf_def(TEST_PACK_PATH, wf_meta)
        st2_ctx = self.mock_st2_context(ac_ex_db)
        wf_ex_db = workflow_service.request(wf_def, ac_ex_db, st2_ctx)
        spec_module = specs_loader.get_spec_module(wf_ex_db.spec["catalog"])
        wf_spec = spec_module.WorkflowSpec.deserialize(wf_ex_db.spec)

        # Manually request task execution.
        task_route = 0
        task_id = "task1"
        task_spec = wf_spec.tasks.get_task(task_id)
        task_ctx = {"foo": "bar"}
        st2_ctx = {"execution_id": wf_ex_db.action_execution}

        task_ex_req = {
            "id": task_id,
            "route": task_route,
            "spec": task_spec,
            "ctx": task_ctx,
            "actions": [
                {"action": "mock.echo", "input": {"message": "Veni, vidi, vici."}}
            ],
        }

        self.assertRaises(
            action_exc.InvalidActionReferencedException,
            workflow_service.request_task_execution,
            wf_ex_db,
            st2_ctx,
            task_ex_req,
        )

    def test_handle_action_execution_completion(self):
        wf_meta = self.get_wf_fixture_meta_data(TEST_PACK_PATH, "sequential.yaml")

        # Manually create the liveaction and action execution objects without publishing.
        lv_ac_db = lv_db_models.LiveActionDB(action=wf_meta["name"])
        lv_ac_db, ac_ex_db = action_service.create_request(lv_ac_db)

        # Request and pre-process the workflow execution.
        wf_def = self.get_wf_def(TEST_PACK_PATH, wf_meta)
        st2_ctx = self.mock_st2_context(ac_ex_db)
        wf_ex_db = workflow_service.request(wf_def, ac_ex_db, st2_ctx)
        wf_ex_db = self.prep_wf_ex(wf_ex_db)

        # Manually request task execution.
        self.run_workflow_step(wf_ex_db, "task1", 0, ctx={"foo": "bar"})

        # Check that a new task is executed.
        self.assert_task_running("task2", 0)

    def test_evaluate_action_execution_delay(self):
        base_task_ex_req = {"task_id": "task1", "task_name": "task1", "route": 0}

        # No task delay.
        task_ex_req = copy.deepcopy(base_task_ex_req)
        ac_ex_req = {"action": "core.noop", "input": None}
        actual_delay = workflow_service.eval_action_execution_delay(
            task_ex_req, ac_ex_req
        )
        self.assertIsNone(actual_delay)

        # Simple task delay.
        task_ex_req = copy.deepcopy(base_task_ex_req)
        task_ex_req["delay"] = 180
        ac_ex_req = {"action": "core.noop", "input": None}
        actual_delay = workflow_service.eval_action_execution_delay(
            task_ex_req, ac_ex_req
        )
        self.assertEqual(actual_delay, 180)

        # Task delay for with items task and with no concurrency.
        task_ex_req = copy.deepcopy(base_task_ex_req)
        task_ex_req["delay"] = 180
        task_ex_req["concurrency"] = None
        ac_ex_req = {"action": "core.noop", "input": None, "items_id": 0}
        actual_delay = workflow_service.eval_action_execution_delay(
            task_ex_req, ac_ex_req, True
        )
        self.assertEqual(actual_delay, 180)

        # Task delay for with items task, with concurrency, and evaluate first item.
        task_ex_req = copy.deepcopy(base_task_ex_req)
        task_ex_req["delay"] = 180
        task_ex_req["concurrency"] = 1
        ac_ex_req = {"action": "core.noop", "input": None, "item_id": 0}
        actual_delay = workflow_service.eval_action_execution_delay(
            task_ex_req, ac_ex_req, True
        )
        self.assertEqual(actual_delay, 180)

        # Task delay for with items task, with concurrency, and evaluate later items.
        task_ex_req = copy.deepcopy(base_task_ex_req)
        task_ex_req["delay"] = 180
        task_ex_req["concurrency"] = 1
        ac_ex_req = {"action": "core.noop", "input": None, "item_id": 1}
        actual_delay = workflow_service.eval_action_execution_delay(
            task_ex_req, ac_ex_req, True
        )
        self.assertIsNone(actual_delay)

    def test_request_action_execution_render(self):
        # Manually create ConfigDB
        output = "Testing"
        value = {"config_item_one": output}
        config_db = pk_db_models.ConfigDB(pack=PACK_7, values=value)
        config = pk_db_access.Config.add_or_update(config_db)
        self.assertEqual(len(config), 3)

        wf_meta = self.get_wf_fixture_meta_data(
            TEST_PACK_PATH, "render_config_context.yaml"
        )

        # Manually create the liveaction and action execution objects without publishing.
        lv_ac_db = lv_db_models.LiveActionDB(action=wf_meta["name"])
        lv_ac_db, ac_ex_db = action_service.create_request(lv_ac_db)

        # Request the workflow execution.
        wf_def = self.get_wf_def(TEST_PACK_PATH, wf_meta)
        st2_ctx = self.mock_st2_context(ac_ex_db)
        wf_ex_db = workflow_service.request(wf_def, ac_ex_db, st2_ctx)
        spec_module = specs_loader.get_spec_module(wf_ex_db.spec["catalog"])
        wf_spec = spec_module.WorkflowSpec.deserialize(wf_ex_db.spec)

        # Pass down appropriate st2 context to the task and action execution(s).
        root_st2_ctx = wf_ex_db.context.get("st2", {})
        st2_ctx = {
            "execution_id": wf_ex_db.action_execution,
            "user": root_st2_ctx.get("user"),
            "pack": root_st2_ctx.get("pack"),
        }

        # Manually request task execution.
        task_route = 0
        task_id = "task1"
        task_spec = wf_spec.tasks.get_task(task_id)
        task_ctx = {"foo": "bar"}

        task_ex_req = {
            "id": task_id,
            "route": task_route,
            "spec": task_spec,
            "ctx": task_ctx,
            "actions": [
                {"action": "dummy_pack_7.render_config_context", "input": None}
            ],
        }
        workflow_service.request_task_execution(wf_ex_db, st2_ctx, task_ex_req)

        # Check task execution is saved to the database.
        task_ex_dbs = wf_db_access.TaskExecution.query(
            workflow_execution=str(wf_ex_db.id)
        )
        self.assertEqual(len(task_ex_dbs), 1)
        workflow_service.request_task_execution(wf_ex_db, st2_ctx, task_ex_req)

        # Manually request action execution
        task_ex_db = task_ex_dbs[0]
        action_ex_db = workflow_service.request_action_execution(
            wf_ex_db, task_ex_db, st2_ctx, task_ex_req["actions"][0]
        )

        # Check required attributes.
        self.assertIsNotNone(str(action_ex_db.id))
        self.assertEqual(task_ex_db.workflow_execution, str(wf_ex_db.id))
        expected_parameters = {"value1": output}
        self.assertEqual(expected_parameters, action_ex_db.parameters)

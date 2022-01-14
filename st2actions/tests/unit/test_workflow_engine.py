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

import eventlet
import mock

import st2tests

from orquesta import statuses as wf_statuses
from oslo_config import cfg
from tooz import coordination

# XXX: actionsensor import depends on config being setup.
import st2tests.config as tests_config

tests_config.parse_args()

from st2actions.workflows import workflows
from st2common.bootstrap import actionsregistrar
from st2common.bootstrap import runnersregistrar
from st2common.constants import action as action_constants
from st2common.models.db import liveaction as lv_db_models
from st2common.persistence import execution as ex_db_access
from st2common.persistence import liveaction as lv_db_access
from st2common.persistence import workflow as wf_db_access
from st2common.services import action as action_service
from st2common.services import coordination as coordination_service
from st2common.transport import liveaction as lv_ac_xport
from st2common.transport import workflow as wf_ex_xport
from st2common.transport import publishers
from st2reactor.garbage_collector import base as garbage_collector
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
class WorkflowExecutionHandlerTest(st2tests.WorkflowTestCase):
    @classmethod
    def setUpClass(cls):
        super(WorkflowExecutionHandlerTest, cls).setUpClass()

        # Register runners.
        runnersregistrar.register_runners()

        # Register test pack(s).
        actions_registrar = actionsregistrar.ActionsRegistrar(
            use_pack_cache=False, fail_on_failure=True
        )

        for pack in PACKS:
            actions_registrar.register_from_pack(pack)

    def test_process(self):
        wf_meta = self.get_wf_fixture_meta_data(TEST_PACK_PATH, "sequential.yaml")
        lv_ac_db = lv_db_models.LiveActionDB(action=wf_meta["name"])
        lv_ac_db, ac_ex_db = action_service.request(lv_ac_db)

        # Assert action execution is running.
        lv_ac_db = lv_db_access.LiveAction.get_by_id(str(lv_ac_db.id))
        self.assertEqual(lv_ac_db.status, action_constants.LIVEACTION_STATUS_RUNNING)
        wf_ex_db = wf_db_access.WorkflowExecution.query(
            action_execution=str(ac_ex_db.id)
        )[0]
        self.assertEqual(wf_ex_db.status, action_constants.LIVEACTION_STATUS_RUNNING)

        # Process task1.
        query_filters = {"workflow_execution": str(wf_ex_db.id), "task_id": "task1"}
        t1_ex_db = wf_db_access.TaskExecution.query(**query_filters)[0]
        t1_ac_ex_db = ex_db_access.ActionExecution.query(
            task_execution=str(t1_ex_db.id)
        )[0]
        workflows.get_engine().process(t1_ac_ex_db)
        t1_ex_db = wf_db_access.TaskExecution.get_by_id(t1_ex_db.id)
        self.assertEqual(t1_ex_db.status, wf_statuses.SUCCEEDED)

        # Process task2.
        query_filters = {"workflow_execution": str(wf_ex_db.id), "task_id": "task2"}
        t2_ex_db = wf_db_access.TaskExecution.query(**query_filters)[0]
        t2_ac_ex_db = ex_db_access.ActionExecution.query(
            task_execution=str(t2_ex_db.id)
        )[0]
        workflows.get_engine().process(t2_ac_ex_db)
        t2_ex_db = wf_db_access.TaskExecution.get_by_id(t2_ex_db.id)
        self.assertEqual(t2_ex_db.status, wf_statuses.SUCCEEDED)

        # Process task3.
        query_filters = {"workflow_execution": str(wf_ex_db.id), "task_id": "task3"}
        t3_ex_db = wf_db_access.TaskExecution.query(**query_filters)[0]
        t3_ac_ex_db = ex_db_access.ActionExecution.query(
            task_execution=str(t3_ex_db.id)
        )[0]
        workflows.get_engine().process(t3_ac_ex_db)
        t3_ex_db = wf_db_access.TaskExecution.get_by_id(t3_ex_db.id)
        self.assertEqual(t3_ex_db.status, wf_statuses.SUCCEEDED)

        # Assert the workflow has completed successfully with expected output.
        expected_output = {"msg": "Stanley, All your base are belong to us!"}
        wf_ex_db = wf_db_access.WorkflowExecution.get_by_id(wf_ex_db.id)
        self.assertEqual(wf_ex_db.status, wf_statuses.SUCCEEDED)
        self.assertDictEqual(wf_ex_db.output, expected_output)
        lv_ac_db = lv_db_access.LiveAction.get_by_id(str(lv_ac_db.id))
        self.assertEqual(lv_ac_db.status, action_constants.LIVEACTION_STATUS_SUCCEEDED)

    @mock.patch.object(coordination_service.NoOpDriver, "get_lock")
    def test_process_error_handling(self, mock_get_lock):
        expected_errors = [
            {
                "message": "Execution failed. See result for details.",
                "type": "error",
                "task_id": "task1",
            },
            {
                "type": "error",
                "message": "ToozConnectionError: foobar",
                "task_id": "task1",
                "route": 0,
            },
        ]

        mock_get_lock.side_effect = coordination_service.NoOpLock(name="noop")
        wf_meta = self.get_wf_fixture_meta_data(TEST_PACK_PATH, "sequential.yaml")
        lv_ac_db = lv_db_models.LiveActionDB(action=wf_meta["name"])
        lv_ac_db, ac_ex_db = action_service.request(lv_ac_db)

        # Assert action execution is running.
        lv_ac_db = lv_db_access.LiveAction.get_by_id(str(lv_ac_db.id))
        self.assertEqual(lv_ac_db.status, action_constants.LIVEACTION_STATUS_RUNNING)
        wf_ex_db = wf_db_access.WorkflowExecution.query(
            action_execution=str(ac_ex_db.id)
        )[0]
        self.assertEqual(wf_ex_db.status, action_constants.LIVEACTION_STATUS_RUNNING)

        # Process task1.
        query_filters = {"workflow_execution": str(wf_ex_db.id), "task_id": "task1"}
        t1_ex_db = wf_db_access.TaskExecution.query(**query_filters)[0]
        t1_ac_ex_db = ex_db_access.ActionExecution.query(
            task_execution=str(t1_ex_db.id)
        )[0]
        mock_get_lock.side_effect = [
            coordination.ToozConnectionError("foobar"),
            coordination.ToozConnectionError("foobar"),
            coordination.ToozConnectionError("foobar"),
            coordination.ToozConnectionError("foobar"),
            coordination.ToozConnectionError("foobar"),
            coordination_service.NoOpLock(name="noop"),
            coordination_service.NoOpLock(name="noop"),
        ]
        workflows.get_engine().process(t1_ac_ex_db)

        # Assert the task is marked as failed.
        t1_ex_db = wf_db_access.TaskExecution.get_by_id(str(t1_ex_db.id))
        self.assertEqual(t1_ex_db.status, wf_statuses.FAILED)

        # Assert the workflow has failed with expected errors.
        wf_ex_db = wf_db_access.WorkflowExecution.get_by_id(wf_ex_db.id)
        self.assertEqual(wf_ex_db.status, wf_statuses.FAILED)
        self.assertListEqual(wf_ex_db.errors, expected_errors)
        lv_ac_db = lv_db_access.LiveAction.get_by_id(str(lv_ac_db.id))
        self.assertEqual(lv_ac_db.status, action_constants.LIVEACTION_STATUS_FAILED)

    @mock.patch.object(
        coordination_service.NoOpDriver,
        "get_lock",
    )
    @mock.patch.object(
        workflows.WorkflowExecutionHandler,
        "fail_workflow_execution",
        mock.MagicMock(side_effect=Exception("Unexpected error.")),
    )
    def test_process_error_handling_has_error(self, mock_get_lock):
        mock_get_lock.side_effect = coordination_service.NoOpLock(name="noop")
        wf_meta = self.get_wf_fixture_meta_data(TEST_PACK_PATH, "sequential.yaml")
        lv_ac_db = lv_db_models.LiveActionDB(action=wf_meta["name"])
        lv_ac_db, ac_ex_db = action_service.request(lv_ac_db)

        # Assert action execution is running.
        lv_ac_db = lv_db_access.LiveAction.get_by_id(str(lv_ac_db.id))
        self.assertEqual(lv_ac_db.status, action_constants.LIVEACTION_STATUS_RUNNING)
        wf_ex_db = wf_db_access.WorkflowExecution.query(
            action_execution=str(ac_ex_db.id)
        )[0]
        self.assertEqual(wf_ex_db.status, action_constants.LIVEACTION_STATUS_RUNNING)

        # Process task1.
        query_filters = {"workflow_execution": str(wf_ex_db.id), "task_id": "task1"}
        t1_ex_db = wf_db_access.TaskExecution.query(**query_filters)[0]
        t1_ac_ex_db = ex_db_access.ActionExecution.query(
            task_execution=str(t1_ex_db.id)
        )[0]

        mock_get_lock.side_effect = [
            coordination.ToozConnectionError("foobar"),
            coordination.ToozConnectionError("foobar"),
            coordination.ToozConnectionError("foobar"),
            coordination.ToozConnectionError("foobar"),
            coordination.ToozConnectionError("foobar"),
        ]
        self.assertRaisesRegexp(
            Exception, "Unexpected error.", workflows.get_engine().process, t1_ac_ex_db
        )

        self.assertTrue(
            workflows.WorkflowExecutionHandler.fail_workflow_execution.called
        )
        mock_get_lock.side_effect = coordination_service.NoOpLock(name="noop")

        # Since error handling failed, the workflow will have status of running.
        wf_ex_db = wf_db_access.WorkflowExecution.get_by_id(wf_ex_db.id)
        self.assertEqual(wf_ex_db.status, wf_statuses.RUNNING)
        lv_ac_db = lv_db_access.LiveAction.get_by_id(str(lv_ac_db.id))
        self.assertEqual(lv_ac_db.status, action_constants.LIVEACTION_STATUS_RUNNING)

        # Sleep up to the test config gc_max_idle_sec before running gc.
        eventlet.sleep(cfg.CONF.workflow_engine.gc_max_idle_sec)

        # Run garbage collection.
        gc = garbage_collector.GarbageCollectorService()
        gc._purge_orphaned_workflow_executions()

        # Assert workflow execution is cleaned up and canceled.
        lv_ac_db = lv_db_access.LiveAction.get_by_id(str(lv_ac_db.id))
        self.assertEqual(lv_ac_db.status, action_constants.LIVEACTION_STATUS_CANCELED)

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
import logging
import mock

# This import must be early for import-time side-effects.
import st2tests

LOG = logging.getLogger(__name__)

from orquesta import statuses as wf_statuses
from oslo_config import cfg
from tooz import coordination
from tooz.drivers.redis import RedisDriver

import st2tests.config as tests_config
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

    @staticmethod
    def reset_config(
        graceful_shutdown=None,  # default is True (st2common.config)
        exit_still_active_check=None,  # default is 300 (st2common.config)
        still_active_check_interval=None,  # default is 2 (st2common.config)
        service_registry=None,  # default is False (st2common.config)
        bootstrap_enabled=False,  # default off; opt-in per test
        bootstrap_interval=None,
        bootstrap_duration=None,
        bootstrap_lookback_days=None,
    ):
        tests_config.reset()
        tests_config.parse_args()
        if graceful_shutdown is not None:
            cfg.CONF.set_override(
                name="graceful_shutdown",
                override=graceful_shutdown,
                group="actionrunner",
            )
        if exit_still_active_check is not None:
            cfg.CONF.set_override(
                name="exit_still_active_check",
                override=exit_still_active_check,
                group="workflow_engine",
            )
        if still_active_check_interval is not None:
            cfg.CONF.set_override(
                name="still_active_check_interval",
                override=still_active_check_interval,
                group="workflow_engine",
            )
        if service_registry is not None:
            cfg.CONF.set_override(
                name="service_registry", override=service_registry, group="coordination"
            )
        cfg.CONF.set_override(
            name="bootstrap_enabled",
            override=bootstrap_enabled,
            group="workflow_engine",
        )
        if bootstrap_interval is not None:
            cfg.CONF.set_override(
                name="bootstrap_interval",
                override=bootstrap_interval,
                group="workflow_engine",
            )
        if bootstrap_duration is not None:
            cfg.CONF.set_override(
                name="bootstrap_duration",
                override=bootstrap_duration,
                group="workflow_engine",
            )
        if bootstrap_lookback_days is not None:
            cfg.CONF.set_override(
                name="bootstrap_lookback_days",
                override=bootstrap_lookback_days,
                group="workflow_engine",
            )

    def test_process(self):
        self.reset_config()

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

    @mock.patch.object(RedisDriver, "get_lock")
    def test_process_error_handling(self, mock_get_lock):
        self.reset_config(service_registry=True)

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
        RedisDriver,
        "get_lock",
    )
    @mock.patch.object(
        workflows.WorkflowExecutionHandler,
        "fail_workflow_execution",
        mock.MagicMock(side_effect=Exception("Unexpected error.")),
    )
    def test_process_error_handling_has_error(self, mock_get_lock):
        self.reset_config()

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
        self.assertRaisesRegex(
            Exception, "Unexpected error.", workflows.get_engine().process, t1_ac_ex_db
        )

        self.assertTrue(
            workflows.WorkflowExecutionHandler.fail_workflow_execution.called  # pylint: disable=no-member
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

    @mock.patch.object(
        coordination_service,
        "get_member_id",
        mock.MagicMock(return_value=b"test_host_12345"),
    )
    @mock.patch.object(
        RedisDriver,
        "get_members",
        mock.MagicMock(
            return_value=coordination_service.NoOpAsyncResult([b"test_host_12345"])
        ),
    )
    def test_workflow_engine_shutdown(self):
        self.reset_config(
            graceful_shutdown=True,
            exit_still_active_check=4,
            still_active_check_interval=1,
            service_registry=True,
        )

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
        workflow_engine = workflows.get_engine()
        eventlet.spawn(workflow_engine.shutdown)
        # Sleep for few seconds to ensure shutdown sequence completes.
        eventlet.sleep(5)

        # WFE pause the workflow with service registry is disabled.
        lv_ac_db = lv_db_access.LiveAction.get_by_id(str(lv_ac_db.id))
        self.assertEqual(lv_ac_db.status, action_constants.LIVEACTION_STATUS_PAUSED)

    @mock.patch.object(
        RedisDriver,
        "get_members",
        mock.MagicMock(
            return_value=coordination_service.NoOpAsyncResult(("member-1",))
        ),
    )
    def test_workflow_engine_shutdown_with_multiple_members(self):
        self.reset_config(service_registry=True)

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
        workflow_engine = workflows.get_engine()

        eventlet.spawn(workflow_engine.shutdown)

        # Sleep for few seconds to ensure shutdown sequence completes.
        eventlet.sleep(5)

        lv_ac_db = lv_db_access.LiveAction.get_by_id(str(lv_ac_db.id))
        self.assertEqual(lv_ac_db.status, action_constants.LIVEACTION_STATUS_PAUSED)

    def test_workflow_engine_shutdown_with_service_registry_disabled(self):
        self.reset_config(service_registry=False)

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
        workflow_engine = workflows.get_engine()

        eventlet.spawn(workflow_engine.shutdown)

        # Sleep for few seconds to ensure shutdown sequence completes.
        eventlet.sleep(5)

        # WFE pause the workflow with service registry is disabled.
        lv_ac_db = lv_db_access.LiveAction.get_by_id(str(lv_ac_db.id))
        self.assertEqual(lv_ac_db.status, action_constants.LIVEACTION_STATUS_PAUSED)

    @mock.patch.object(
        coordination_service,
        "get_member_id",
        mock.MagicMock(return_value=b"member-1"),
    )
    @mock.patch.object(
        RedisDriver,
        "get_members",
        mock.MagicMock(
            return_value=coordination_service.NoOpAsyncResult((b"member-1",))
        ),
    )
    @mock.patch.object(
        RedisDriver,
        "get_lock",
        mock.MagicMock(return_value=coordination_service.NoOpLock(name="noop")),
    )
    def test_workflow_engine_shutdown_first_then_start(self):
        import time

        self.reset_config(
            service_registry=True,
            exit_still_active_check=0,
            bootstrap_enabled=True,
            bootstrap_interval=5,
            bootstrap_duration=60,
            bootstrap_lookback_days=7,
        )

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
        workflow_engine = workflows.get_engine()

        LOG.info("=" * 80)
        LOG.info("TEST DEBUG: Initial State")
        LOG.info("LiveAction ID: %s", lv_ac_db.id)
        LOG.info("ActionExecution ID: %s", ac_ex_db.id)
        LOG.info("WorkflowExecution ID: %s", wf_ex_db.id)
        LOG.info("LiveAction status: %s", lv_ac_db.status)
        LOG.info("WorkflowExecution status: %s", wf_ex_db.status)
        LOG.info("Time: %s", time.time())

        workflow_engine._delay = 5
        # Initiate shutdown first
        LOG.info("-" * 80)
        LOG.info("TEST DEBUG: Initiating Shutdown")
        LOG.info(
            "Engine delay (unused, retained for log parity): %s", workflow_engine._delay
        )
        eventlet.spawn(workflow_engine.shutdown)

        # Sleep long enough for shutdown to complete
        LOG.info("TEST DEBUG: Sleeping 10 seconds for shutdown...")
        eventlet.sleep(10)

        lv_ac_db = lv_db_access.LiveAction.get_by_id(str(lv_ac_db.id))
        wf_ex_db = wf_db_access.WorkflowExecution.get_by_id(str(wf_ex_db.id))
        LOG.info("-" * 80)
        LOG.info("TEST DEBUG: After Shutdown")
        LOG.info("Time: %s", time.time())
        LOG.info("LiveAction status: %s", lv_ac_db.status)
        LOG.info("WorkflowExecution status: %s", wf_ex_db.status)

        # Shutdown routine acquires the lock first
        self.assertEqual(lv_ac_db.status, action_constants.LIVEACTION_STATUS_PAUSED)

        # Now get a fresh engine and start it
        # This simulates a real restart where a new engine is created
        # The engine start should automatically resume paused workflows

        LOG.info("-" * 80)
        LOG.info("TEST DEBUG: Preparing Engine Restart")
        LOG.info("Checking paused workflows in DB...")
        paused_workflows = lv_db_access.LiveAction.query(
            status=action_constants.LIVEACTION_STATUS_PAUSED, action_is_workflow=True
        )
        LOG.info("Found %d paused workflow(s)", len(paused_workflows))
        for pw in paused_workflows:
            LOG.info("  - LiveAction %s: %s, status=%s", pw.id, pw.action, pw.status)

        # Use context managers to mock the coordinator instance methods
        with mock.patch.object(
            coordination_service.get_coordinator(),
            "get_members",
            return_value=coordination_service.NoOpAsyncResult((b"member-1",)),
        ):
            with mock.patch.object(
                coordination_service, "get_member_id", return_value=b"member-1"
            ):
                LOG.info("TEST DEBUG: Creating new engine instance...")
                new_engine = workflows.get_engine()
                new_engine._delay = 5
                LOG.info("New engine delay: %s", new_engine._delay)
                LOG.info("TEST DEBUG: Starting new engine (resume_workflows=False)...")
                LOG.info("Time before start: %s", time.time())
                new_engine.start(False)

                # Wait for the engine's delay + additional time for resume to complete
                # Increased from 10 to 15 seconds to give more time in CI/CD
                wait_time = 5 + 15
                LOG.info(
                    "TEST DEBUG: Sleeping %d seconds for engine start and resume...",
                    wait_time,
                )
                eventlet.sleep(wait_time)

        LOG.info("-" * 80)
        LOG.info("TEST DEBUG: After Engine Start")
        LOG.info("Time: %s", time.time())
        lv_ac_db = lv_db_access.LiveAction.get_by_id(str(lv_ac_db.id))
        wf_ex_db = wf_db_access.WorkflowExecution.get_by_id(str(wf_ex_db.id))
        LOG.info("LiveAction status: %s", lv_ac_db.status)
        LOG.info("WorkflowExecution status: %s", wf_ex_db.status)

        # Check task executions
        task_execs = wf_db_access.TaskExecution.query(
            workflow_execution=str(wf_ex_db.id)
        )
        LOG.info("Task executions count: %d", len(task_execs))
        for te in task_execs:
            LOG.info("  - Task %s: status=%s", te.task_id, te.status)

        # Check all paused workflows
        all_paused = lv_db_access.LiveAction.query(
            status=action_constants.LIVEACTION_STATUS_PAUSED, action_is_workflow=True
        )
        LOG.info("Total paused workflows in DB: %d", len(all_paused))

        LOG.info("Expected statuses: RESUMING, RUNNING, or SUCCEEDED")
        LOG.info("Actual status: %s", lv_ac_db.status)
        expected_statuses = [
            action_constants.LIVEACTION_STATUS_RESUMING,
            action_constants.LIVEACTION_STATUS_RUNNING,
            action_constants.LIVEACTION_STATUS_SUCCEEDED,
        ]
        LOG.info("Status in expected list: %s", lv_ac_db.status)
        LOG.info("=" * 80)

        self.assertTrue(lv_ac_db.status in expected_statuses)

    @mock.patch.object(
        RedisDriver,
        "get_lock",
        mock.MagicMock(return_value=coordination_service.NoOpLock(name="noop")),
    )
    def test_workflow_engine_start_first_then_shutdown(self):
        self.reset_config(service_registry=True, exit_still_active_check=0)

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
        workflow_engine = workflows.get_engine()

        RedisDriver.get_members = mock.MagicMock(
            return_value=coordination_service.NoOpAsyncResult(("member-1",))
        )

        workflow_engine._delay = 0
        # Initiate start first
        eventlet.spawn(workflow_engine.start, True)
        eventlet.spawn_after(1, workflow_engine.shutdown)

        RedisDriver.get_members = mock.MagicMock(
            return_value=coordination_service.NoOpAsyncResult("member-1")
        )
        lv_ac_db = lv_db_access.LiveAction.get_by_id(str(lv_ac_db.id))

        # Startup routine acquires the lock first and shutdown routine sees a new member present in registry.
        eventlet.sleep(workflow_engine._delay + 5)
        lv_ac_db = lv_db_access.LiveAction.get_by_id(str(lv_ac_db.id))
        self.assertEqual(lv_ac_db.status, action_constants.LIVEACTION_STATUS_RUNNING)

    def test_bootstrap_disabled_by_default(self):
        self.reset_config(service_registry=True, exit_still_active_check=0)

        workflow_engine = workflows.get_engine()
        with mock.patch.object(
            workflow_engine,
            "_resume_workflows_paused_during_shutdown",
        ) as mock_resume:
            eventlet.spawn(workflow_engine.start, False)
            eventlet.sleep(1.0)
            workflow_engine.shutdown()

            self.assertEqual(mock_resume.call_count, 0)

        self.assertIsNone(workflow_engine._bootstrap_thread)

    def test_bootstrap_runs_periodically_when_enabled(self):
        self.reset_config(
            service_registry=True,
            exit_still_active_check=0,
            bootstrap_enabled=True,
            bootstrap_interval=1,
            bootstrap_duration=60,
        )

        workflow_engine = workflows.get_engine()

        with mock.patch.object(
            workflow_engine,
            "_resume_workflows_paused_during_shutdown",
        ) as mock_resume:
            eventlet.spawn(workflow_engine.start, False)
            eventlet.sleep(3.5)
            workflow_engine.shutdown()

            self.assertGreaterEqual(mock_resume.call_count, 2)

        self.assertIsNone(workflow_engine._bootstrap_thread)

    def test_bootstrap_stops_after_duration(self):
        self.reset_config(
            service_registry=True,
            exit_still_active_check=0,
            bootstrap_enabled=True,
            bootstrap_interval=1,
            bootstrap_duration=2,
        )

        workflow_engine = workflows.get_engine()

        with mock.patch.object(
            workflow_engine,
            "_resume_workflows_paused_during_shutdown",
        ) as mock_resume:
            thread = eventlet.spawn(workflow_engine.start, False)
            # Sleep long past the 2s bootstrap window so the loop exits on its own.
            eventlet.sleep(5)
            # Loop should have exited on its own (deadline). No calls after ~2s.
            call_count_after_deadline = mock_resume.call_count
            eventlet.sleep(2)
            self.assertEqual(mock_resume.call_count, call_count_after_deadline)
            workflow_engine.shutdown()
            thread.wait()

    def test_bootstrap_survives_transient_errors(self):
        import pymongo

        self.reset_config(
            service_registry=True,
            exit_still_active_check=0,
            bootstrap_enabled=True,
            bootstrap_interval=1,
            bootstrap_duration=60,
        )

        workflow_engine = workflows.get_engine()

        with mock.patch.object(
            workflow_engine,
            "_resume_workflows_paused_during_shutdown",
            side_effect=[
                pymongo.errors.ConnectionFailure("boom"),
                None,
                None,
                None,
            ],
        ) as mock_resume:
            eventlet.spawn(workflow_engine.start, False)
            eventlet.sleep(3.5)
            workflow_engine.shutdown()

            self.assertGreaterEqual(mock_resume.call_count, 3)

    def test_bootstrap_lookback_filters_ancient(self):
        import datetime as _dt

        from st2common.services import workflows as wf_svc
        from st2common.util import date as date_utils

        self.reset_config(
            service_registry=True,
            exit_still_active_check=0,
            bootstrap_lookback_days=1,
        )

        # Two paused-by-shutdown LiveActions: one recent, one ancient.
        recent = lv_db_models.LiveActionDB(
            action="core.local",
            status=action_constants.LIVEACTION_STATUS_PAUSED,
            context={"paused_by": wf_svc.WORKFLOW_ENGINE_START_STOP_SEQ},
            start_timestamp=date_utils.get_datetime_utc_now(),
        )
        ancient = lv_db_models.LiveActionDB(
            action="core.local",
            status=action_constants.LIVEACTION_STATUS_PAUSED,
            context={"paused_by": wf_svc.WORKFLOW_ENGINE_START_STOP_SEQ},
            start_timestamp=date_utils.get_datetime_utc_now() - _dt.timedelta(days=5),
        )
        recent = lv_db_access.LiveAction.add_or_update(recent, publish=False)
        ancient = lv_db_access.LiveAction.add_or_update(ancient, publish=False)

        try:
            engine = workflows.get_engine()
            results = engine._get_workflows_paused_during_shutdown()
            result_ids = {str(x.id) for x in results}
            self.assertIn(str(recent.id), result_ids)
            self.assertNotIn(str(ancient.id), result_ids)
        finally:
            lv_db_access.LiveAction.delete(recent)
            lv_db_access.LiveAction.delete(ancient)

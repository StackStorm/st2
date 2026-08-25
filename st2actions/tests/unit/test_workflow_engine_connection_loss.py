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
# limitations under the License

"""
Unit tests for workflow engine RabbitMQ connection loss handling.
"""

from __future__ import absolute_import

import mock

import st2tests
import st2tests.config as tests_config
from oslo_config import cfg
from st2actions.workflows import workflows
from st2common.bootstrap import actionsregistrar
from st2common.bootstrap import runnersregistrar
from st2common.constants import action as action_constants
from st2common.models.db import liveaction as lv_db_models
from st2common.persistence import liveaction as lv_db_access
from st2common.services import action as action_service
from st2common.transport import liveaction as lv_ac_xport
from st2common.transport import workflow as wf_ex_xport
from st2common.transport import publishers
from st2tests.fixtures.packs.core.fixture import PACK_PATH as CORE_PACK_PATH
from st2tests.fixtures.packs.orquesta_tests.fixture import PACK_PATH as TEST_PACK_PATH
from st2tests.mocks import liveaction as mock_lv_ac_xport
from st2tests.mocks import workflow as mock_wf_ex_xport
from tooz.coordination import GroupNotCreated


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
class WorkflowEngineConnectionLossTest(st2tests.WorkflowTestCase):
    """Test workflow engine behavior when RabbitMQ connection is lost."""

    @classmethod
    def setUpClass(cls):
        super(WorkflowEngineConnectionLossTest, cls).setUpClass()

        # Register runners
        runnersregistrar.register_runners()

        # Register test packs
        actions_registrar = actionsregistrar.ActionsRegistrar(
            use_pack_cache=False, fail_on_failure=True
        )

        for pack in PACKS:
            actions_registrar.register_from_pack(pack)

    def setUp(self):
        super(WorkflowEngineConnectionLossTest, self).setUp()
        # Reset and parse config for tests
        tests_config.reset()
        tests_config.parse_args()

        # Enable coordination service for tests
        cfg.CONF.set_override(
            name="service_registry",
            override=True,
            group="coordination",
        )

    def test_on_connection_error_pauses_workflows_when_last_engine(self):
        """Test that workflows are paused when connection lost and this is the last engine."""
        # Create a running workflow
        wf_meta = self.get_wf_fixture_meta_data(TEST_PACK_PATH, "sequential.yaml")
        lv_ac_db = lv_db_models.LiveActionDB(action=wf_meta["name"])
        lv_ac_db, ac_ex_db = action_service.request(lv_ac_db)

        # Verify workflow is running
        lv_ac_db = lv_db_access.LiveAction.get_by_id(str(lv_ac_db.id))
        self.assertEqual(lv_ac_db.status, action_constants.LIVEACTION_STATUS_RUNNING)

        # Create workflow engine handler
        with mock.patch("st2common.transport.utils.get_connection"):
            handler = workflows.WorkflowExecutionHandler(None, [])

        # Mock coordination to simulate this is the last engine
        mock_coordinator = mock.MagicMock()
        mock_coordinator.get_members.return_value.get.return_value = (
            []
        )  # No other members
        mock_coordinator.get_lock.return_value.__enter__ = mock.MagicMock()
        mock_coordinator.get_lock.return_value.__exit__ = mock.MagicMock()

        with mock.patch(
            "st2common.services.coordination.get_coordinator",
            return_value=mock_coordinator,
        ):
            with mock.patch.object(
                handler, "_get_running_workflows", return_value=[ac_ex_db]
            ):
                # Call _pause_running_workflows_on_connection_loss directly
                handler._pause_running_workflows_on_connection_loss()

        # Verify workflow was directly set to "paused" state (not "pausing")
        lv_ac_db = lv_db_access.LiveAction.get_by_id(str(lv_ac_db.id))
        self.assertEqual(lv_ac_db.status, action_constants.LIVEACTION_STATUS_PAUSED)
        self.assertEqual(
            lv_ac_db.context.get("paused_by"),
            workflows.WORKFLOW_ENGINE_START_STOP_SEQ,
        )

    def test_on_connection_error_skips_pause_when_other_engines_present(self):
        """Test that workflows are NOT paused when other engines are still running."""
        # Create a running workflow
        wf_meta = self.get_wf_fixture_meta_data(TEST_PACK_PATH, "sequential.yaml")
        lv_ac_db = lv_db_models.LiveActionDB(action=wf_meta["name"])
        lv_ac_db, ac_ex_db = action_service.request(lv_ac_db)

        # Verify workflow is running
        lv_ac_db = lv_db_access.LiveAction.get_by_id(str(lv_ac_db.id))
        self.assertEqual(lv_ac_db.status, action_constants.LIVEACTION_STATUS_RUNNING)

        # Create workflow engine handler
        with mock.patch("st2common.transport.utils.get_connection"):
            handler = workflows.WorkflowExecutionHandler(None, [])

        # Mock coordination to simulate other engines are present
        mock_coordinator = mock.MagicMock()
        mock_coordinator.get_members.return_value.get.return_value = [
            "engine1",
            "engine2",
            "engine3",
        ]
        mock_coordinator.get_lock.return_value.__enter__ = mock.MagicMock()
        mock_coordinator.get_lock.return_value.__exit__ = mock.MagicMock()

        with mock.patch(
            "st2common.services.coordination.get_coordinator",
            return_value=mock_coordinator,
        ):
            with mock.patch.object(
                handler, "_get_running_workflows", return_value=[ac_ex_db]
            ):
                # Call _pause_running_workflows_on_connection_loss directly
                handler._pause_running_workflows_on_connection_loss()

        # Verify workflow was NOT paused (still running)
        lv_ac_db = lv_db_access.LiveAction.get_by_id(str(lv_ac_db.id))
        self.assertEqual(lv_ac_db.status, action_constants.LIVEACTION_STATUS_RUNNING)

    def test_on_connection_error_logs_warning_without_coordination(self):
        """Test that warning is logged when coordination service is not enabled."""
        # Create a running workflow
        wf_meta = self.get_wf_fixture_meta_data(TEST_PACK_PATH, "sequential.yaml")
        lv_ac_db = lv_db_models.LiveActionDB(action=wf_meta["name"])
        lv_ac_db, ac_ex_db = action_service.request(lv_ac_db)

        # Create workflow engine handler
        with mock.patch("st2common.transport.utils.get_connection"):
            handler = workflows.WorkflowExecutionHandler(None, [])

        # Mock coordination service as disabled
        cfg.CONF.set_override(
            name="service_registry",
            override=False,
            group="coordination",
        )

        with mock.patch("st2actions.workflows.workflows.LOG") as mock_log:
            # Call _pause_running_workflows_on_connection_loss directly
            handler._pause_running_workflows_on_connection_loss()

            # Verify warning was logged
            mock_log.warning.assert_called()
            warning_message = mock_log.warning.call_args[0][0]
            self.assertIn("Coordination service not enabled", warning_message)

    def test_pause_workflows_handles_individual_failures(self):
        """Test that if one workflow fails to pause, the engine logs error and continues."""
        # Create multiple running workflows
        workflows_to_create = 3
        ac_ex_dbs = []

        for i in range(workflows_to_create):
            wf_meta = self.get_wf_fixture_meta_data(TEST_PACK_PATH, "sequential.yaml")
            lv_ac_db = lv_db_models.LiveActionDB(action=wf_meta["name"])
            lv_ac_db, ac_ex_db = action_service.request(lv_ac_db)
            ac_ex_dbs.append(ac_ex_db)

        # Verify all workflows are running
        for ac_ex_db in ac_ex_dbs:
            lv_ac_db = lv_db_access.LiveAction.get_by_id(ac_ex_db.liveaction_id)
            self.assertEqual(
                lv_ac_db.status, action_constants.LIVEACTION_STATUS_RUNNING
            )

        # Create workflow engine handler
        with mock.patch("st2common.transport.utils.get_connection"):
            handler = workflows.WorkflowExecutionHandler(None, [])

        # Mock coordination to simulate this is the last engine
        mock_coordinator = mock.MagicMock()
        mock_coordinator.get_members.return_value.get.return_value = []
        mock_coordinator.get_lock.return_value.__enter__ = mock.MagicMock()
        mock_coordinator.get_lock.return_value.__exit__ = mock.MagicMock()

        # Mock get_liveaction_by_id to fail on the second workflow
        from st2common.util import action_db as action_utils

        original_get_liveaction = action_utils.get_liveaction_by_id
        call_count = [0]

        def mock_get_liveaction(liveaction_id):
            call_count[0] += 1
            if call_count[0] == 2:
                raise Exception("Failed to get workflow 2")
            return original_get_liveaction(liveaction_id)

        with mock.patch(
            "st2common.services.coordination.get_coordinator",
            return_value=mock_coordinator,
        ):
            with mock.patch(
                "st2actions.workflows.workflows.action_utils.get_liveaction_by_id",
                side_effect=mock_get_liveaction,
            ):
                with mock.patch.object(
                    handler, "_get_running_workflows", return_value=ac_ex_dbs
                ):
                    with mock.patch("st2actions.workflows.workflows.LOG") as mock_log:
                        # Call _pause_running_workflows_on_connection_loss directly
                        handler._pause_running_workflows_on_connection_loss()

                        # Verify error was logged for failed workflow
                        self.assertTrue(mock_log.error.called)
                        error_calls = [
                            str(call) for call in mock_log.error.call_args_list
                        ]
                        self.assertTrue(
                            any(
                                "Failed to get workflow 2" in str(call)
                                for call in error_calls
                            )
                        )

        # Verify workflows 1 and 3 were paused (workflow 2 failed before pause attempt)
        paused_count = 0
        for idx, ac_ex_db in enumerate(ac_ex_dbs):
            lv_ac_db = lv_db_access.LiveAction.get_by_id(ac_ex_db.liveaction_id)
            if lv_ac_db.status == action_constants.LIVEACTION_STATUS_PAUSED:
                paused_count += 1

        # Should have paused 2 out of 3 workflows (second one failed)
        self.assertEqual(paused_count, 2)

    def test_pause_workflows_handles_group_not_created(self):
        """Test graceful handling when coordination group doesn't exist."""
        # Create a running workflow
        wf_meta = self.get_wf_fixture_meta_data(TEST_PACK_PATH, "sequential.yaml")
        lv_ac_db = lv_db_models.LiveActionDB(action=wf_meta["name"])
        lv_ac_db, ac_ex_db = action_service.request(lv_ac_db)

        # Create workflow engine handler
        with mock.patch("st2common.transport.utils.get_connection"):
            handler = workflows.WorkflowExecutionHandler(None, [])

        # Mock coordination to raise GroupNotCreated
        mock_coordinator = mock.MagicMock()
        mock_coordinator.get_members.return_value.get.side_effect = GroupNotCreated(
            "group_id"
        )
        mock_coordinator.get_lock.return_value.__enter__ = mock.MagicMock()
        mock_coordinator.get_lock.return_value.__exit__ = mock.MagicMock()

        with mock.patch(
            "st2common.services.coordination.get_coordinator",
            return_value=mock_coordinator,
        ):
            with mock.patch.object(
                handler, "_get_running_workflows", return_value=[ac_ex_db]
            ):
                # Should handle GroupNotCreated gracefully and pause workflows
                handler._pause_running_workflows_on_connection_loss()

        # Verify workflow was directly set to "paused" (GroupNotCreated treated as no members)
        lv_ac_db = lv_db_access.LiveAction.get_by_id(str(lv_ac_db.id))
        self.assertEqual(lv_ac_db.status, action_constants.LIVEACTION_STATUS_PAUSED)

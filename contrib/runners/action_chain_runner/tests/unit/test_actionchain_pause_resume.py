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
import os
import tempfile

from st2tests import config as test_config

test_config.parse_args()

from st2common.bootstrap import actionsregistrar
from st2common.bootstrap import runnersregistrar

from st2common.constants import action as action_constants
from st2common.models.db.liveaction import LiveActionDB
from st2common.persistence.execution import ActionExecution
from st2common.persistence.liveaction import LiveAction
from st2common.services import action as action_service
from st2common.transport.liveaction import LiveActionPublisher
from st2common.transport.publishers import CUDPublisher
from st2common.util import action_db as action_utils
from st2common.util import date as date_utils

from st2tests import ExecutionDbTestCase
from st2tests.fixtures.packs.action_chain_tests.fixture import (
    PACK_NAME as TEST_PACK,
    PACK_PATH as TEST_PACK_PATH,
)
from st2tests.fixtures.packs.core.fixture import PACK_PATH as CORE_PACK_PATH
from st2tests.mocks.liveaction import MockLiveActionPublisherNonBlocking
from six.moves import range


TEST_FIXTURES = {
    "chains": [
        "test_pause_resume.yaml",
        "test_pause_resume_context_result",
        "test_pause_resume_with_published_vars.yaml",
        "test_pause_resume_with_error.yaml",
        "test_pause_resume_with_subworkflow.yaml",
        "test_pause_resume_with_context_access.yaml",
        "test_pause_resume_with_init_vars.yaml",
        "test_pause_resume_with_no_more_task.yaml",
        "test_pause_resume_last_task_failed_with_no_next_task.yaml",
    ],
    "actions": [
        "test_pause_resume.yaml",
        "test_pause_resume_context_result",
        "test_pause_resume_with_published_vars.yaml",
        "test_pause_resume_with_error.yaml",
        "test_pause_resume_with_subworkflow.yaml",
        "test_pause_resume_with_context_access.yaml",
        "test_pause_resume_with_init_vars.yaml",
        "test_pause_resume_with_no_more_task.yaml",
        "test_pause_resume_last_task_failed_with_no_next_task.yaml",
    ],
}

PACKS = [TEST_PACK_PATH, CORE_PACK_PATH]

USERNAME = "stanley"


@mock.patch.object(CUDPublisher, "publish_update", mock.MagicMock(return_value=None))
@mock.patch.object(CUDPublisher, "publish_create", mock.MagicMock(return_value=None))
@mock.patch.object(
    LiveActionPublisher,
    "publish_state",
    mock.MagicMock(side_effect=MockLiveActionPublisherNonBlocking.publish_state),
)
class ActionChainRunnerPauseResumeTest(ExecutionDbTestCase):

    temp_file_path = None

    @classmethod
    def setUpClass(cls):
        super(ActionChainRunnerPauseResumeTest, cls).setUpClass()

        # Register runners.
        runnersregistrar.register_runners()

        # Register test pack(s).
        actions_registrar = actionsregistrar.ActionsRegistrar(
            use_pack_cache=False, fail_on_failure=True
        )

        for pack in PACKS:
            actions_registrar.register_from_pack(pack)

    def setUp(self):
        super(ActionChainRunnerPauseResumeTest, self).setUp()

        # Create temporary directory used by the tests
        _, self.temp_file_path = tempfile.mkstemp()
        os.chmod(self.temp_file_path, 0o755)  # nosec

    def tearDown(self):
        if self.temp_file_path and os.path.exists(self.temp_file_path):
            os.remove(self.temp_file_path)

        super(ActionChainRunnerPauseResumeTest, self).tearDown()

    def _wait_for_status(self, liveaction, status, interval=0.1, retries=100):
        # Wait until the liveaction reaches status.
        for i in range(0, retries):
            liveaction = LiveAction.get_by_id(str(liveaction.id))
            if liveaction.status != status:
                eventlet.sleep(interval)
                continue
            else:
                break

        return liveaction

    def _wait_for_children(self, execution, interval=0.1, retries=100):
        # Wait until the execution has children.
        for i in range(0, retries):
            execution = ActionExecution.get_by_id(str(execution.id))
            if len(getattr(execution, "children", [])) <= 0:
                eventlet.sleep(interval)
                continue

        return execution

    def test_chain_pause_resume(self):
        # A temp file is created during test setup. Ensure the temp file exists.
        # The test action chain will stall until this file is deleted. This gives
        # the unit test a moment to run any test related logic.
        path = self.temp_file_path
        self.assertTrue(os.path.exists(path))

        action = TEST_PACK + "." + "test_pause_resume"
        params = {"tempfile": path, "message": "foobar"}
        liveaction = LiveActionDB(action=action, parameters=params)
        liveaction, execution = action_service.request(liveaction)
        liveaction = LiveAction.get_by_id(str(liveaction.id))

        # Wait until the liveaction is running.
        liveaction = self._wait_for_status(
            liveaction, action_constants.LIVEACTION_STATUS_RUNNING
        )
        self.assertEqual(liveaction.status, action_constants.LIVEACTION_STATUS_RUNNING)

        # Request action chain to pause.
        liveaction, execution = action_service.request_pause(liveaction, USERNAME)

        # Wait until the liveaction is pausing.
        liveaction = self._wait_for_status(
            liveaction, action_constants.LIVEACTION_STATUS_PAUSING
        )
        extra_info = str(liveaction)
        self.assertEqual(
            liveaction.status, action_constants.LIVEACTION_STATUS_PAUSING, extra_info
        )

        # Delete the temporary file that the action chain is waiting on.
        os.remove(path)
        self.assertFalse(os.path.exists(path))

        # Wait until the liveaction is paused.
        liveaction = self._wait_for_status(
            liveaction, action_constants.LIVEACTION_STATUS_PAUSED
        )
        extra_info = str(liveaction)
        self.assertEqual(
            liveaction.status, action_constants.LIVEACTION_STATUS_PAUSED, extra_info
        )

        # Wait for non-blocking threads to complete. Ensure runner is not running.
        MockLiveActionPublisherNonBlocking.wait_all()

        # Request action chain to resume.
        liveaction, execution = action_service.request_resume(liveaction, USERNAME)

        # Wait until the liveaction is completed.
        liveaction = self._wait_for_status(
            liveaction, action_constants.LIVEACTION_STATUS_SUCCEEDED
        )
        self.assertEqual(
            liveaction.status, action_constants.LIVEACTION_STATUS_SUCCEEDED
        )

        # Wait for non-blocking threads to complete.
        MockLiveActionPublisherNonBlocking.wait_all()

        # Check liveaction result.
        self.assertIn("tasks", liveaction.result)
        self.assertEqual(len(liveaction.result["tasks"]), 2)

    def test_chain_pause_resume_with_published_vars(self):
        # A temp file is created during test setup. Ensure the temp file exists.
        # The test action chain will stall until this file is deleted. This gives
        # the unit test a moment to run any test related logic.
        path = self.temp_file_path
        self.assertTrue(os.path.exists(path))

        action = TEST_PACK + "." + "test_pause_resume_with_published_vars"
        params = {"tempfile": path, "message": "foobar"}
        liveaction = LiveActionDB(action=action, parameters=params)
        liveaction, execution = action_service.request(liveaction)
        liveaction = LiveAction.get_by_id(str(liveaction.id))

        # Wait until the liveaction is running.
        liveaction = self._wait_for_status(
            liveaction, action_constants.LIVEACTION_STATUS_RUNNING
        )
        self.assertEqual(liveaction.status, action_constants.LIVEACTION_STATUS_RUNNING)

        # Request action chain to pause.
        liveaction, execution = action_service.request_pause(liveaction, USERNAME)

        # Wait until the liveaction is pausing.
        liveaction = self._wait_for_status(
            liveaction, action_constants.LIVEACTION_STATUS_PAUSING
        )
        extra_info = str(liveaction)
        self.assertEqual(
            liveaction.status, action_constants.LIVEACTION_STATUS_PAUSING, extra_info
        )

        # Delete the temporary file that the action chain is waiting on.
        os.remove(path)
        self.assertFalse(os.path.exists(path))

        # Wait until the liveaction is paused.
        liveaction = self._wait_for_status(
            liveaction, action_constants.LIVEACTION_STATUS_PAUSED
        )
        extra_info = str(liveaction)
        self.assertEqual(
            liveaction.status, action_constants.LIVEACTION_STATUS_PAUSED, extra_info
        )

        # Wait for non-blocking threads to complete. Ensure runner is not running.
        MockLiveActionPublisherNonBlocking.wait_all()

        # Request action chain to resume.
        liveaction, execution = action_service.request_resume(liveaction, USERNAME)

        # Wait until the liveaction is completed.
        liveaction = self._wait_for_status(
            liveaction, action_constants.LIVEACTION_STATUS_SUCCEEDED
        )
        self.assertEqual(
            liveaction.status, action_constants.LIVEACTION_STATUS_SUCCEEDED
        )

        # Wait for non-blocking threads to complete.
        MockLiveActionPublisherNonBlocking.wait_all()

        # Check liveaction result.
        self.assertIn("tasks", liveaction.result)
        self.assertEqual(len(liveaction.result["tasks"]), 2)
        self.assertIn("published", liveaction.result)
        self.assertDictEqual(
            {"var1": "foobar", "var2": "fubar"}, liveaction.result["published"]
        )

    def test_chain_pause_resume_with_published_vars_display_false(self):
        # A temp file is created during test setup. Ensure the temp file exists.
        # The test action chain will stall until this file is deleted. This gives
        # the unit test a moment to run any test related logic.
        path = self.temp_file_path
        self.assertTrue(os.path.exists(path))

        action = TEST_PACK + "." + "test_pause_resume_with_published_vars"
        params = {"tempfile": path, "message": "foobar", "display_published": False}
        liveaction = LiveActionDB(action=action, parameters=params)
        liveaction, execution = action_service.request(liveaction)
        liveaction = LiveAction.get_by_id(str(liveaction.id))

        # Wait until the liveaction is running.
        liveaction = self._wait_for_status(
            liveaction, action_constants.LIVEACTION_STATUS_RUNNING
        )
        self.assertEqual(liveaction.status, action_constants.LIVEACTION_STATUS_RUNNING)

        # Request action chain to pause.
        liveaction, execution = action_service.request_pause(liveaction, USERNAME)

        # Wait until the liveaction is pausing.
        liveaction = self._wait_for_status(
            liveaction, action_constants.LIVEACTION_STATUS_PAUSING
        )
        extra_info = str(liveaction)
        self.assertEqual(
            liveaction.status, action_constants.LIVEACTION_STATUS_PAUSING, extra_info
        )

        # Delete the temporary file that the action chain is waiting on.
        os.remove(path)
        self.assertFalse(os.path.exists(path))

        # Wait until the liveaction is paused.
        liveaction = self._wait_for_status(
            liveaction, action_constants.LIVEACTION_STATUS_PAUSED
        )
        extra_info = str(liveaction)
        self.assertEqual(
            liveaction.status, action_constants.LIVEACTION_STATUS_PAUSED, extra_info
        )

        # Wait for non-blocking threads to complete. Ensure runner is not running.
        MockLiveActionPublisherNonBlocking.wait_all()

        # Request action chain to resume.
        liveaction, execution = action_service.request_resume(liveaction, USERNAME)

        # Wait until the liveaction is completed.
        liveaction = self._wait_for_status(
            liveaction, action_constants.LIVEACTION_STATUS_SUCCEEDED
        )
        self.assertEqual(
            liveaction.status, action_constants.LIVEACTION_STATUS_SUCCEEDED
        )

        # Wait for non-blocking threads to complete.
        MockLiveActionPublisherNonBlocking.wait_all()

        # Check liveaction result.
        self.assertIn("tasks", liveaction.result)
        self.assertEqual(len(liveaction.result["tasks"]), 2)
        self.assertNotIn("published", liveaction.result)

    def test_chain_pause_resume_with_error(self):
        # A temp file is created during test setup. Ensure the temp file exists.
        # The test action chain will stall until this file is deleted. This gives
        # the unit test a moment to run any test related logic.
        path = self.temp_file_path
        self.assertTrue(os.path.exists(path))

        action = TEST_PACK + "." + "test_pause_resume_with_error"
        params = {"tempfile": path, "message": "foobar"}
        liveaction = LiveActionDB(action=action, parameters=params)
        liveaction, execution = action_service.request(liveaction)
        liveaction = LiveAction.get_by_id(str(liveaction.id))

        # Wait until the liveaction is running.
        liveaction = self._wait_for_status(
            liveaction, action_constants.LIVEACTION_STATUS_RUNNING
        )
        self.assertEqual(liveaction.status, action_constants.LIVEACTION_STATUS_RUNNING)

        # Request action chain to pause.
        liveaction, execution = action_service.request_pause(liveaction, USERNAME)

        # Wait until the liveaction is pausing.
        liveaction = self._wait_for_status(
            liveaction, action_constants.LIVEACTION_STATUS_PAUSING
        )
        extra_info = str(liveaction)
        self.assertEqual(
            liveaction.status, action_constants.LIVEACTION_STATUS_PAUSING, extra_info
        )

        # Delete the temporary file that the action chain is waiting on.
        os.remove(path)
        self.assertFalse(os.path.exists(path))

        # Wait until the liveaction is paused.
        liveaction = self._wait_for_status(
            liveaction, action_constants.LIVEACTION_STATUS_PAUSED
        )
        extra_info = str(liveaction)
        self.assertEqual(
            liveaction.status, action_constants.LIVEACTION_STATUS_PAUSED, extra_info
        )

        # Wait for non-blocking threads to complete. Ensure runner is not running.
        MockLiveActionPublisherNonBlocking.wait_all()

        # Request action chain to resume.
        liveaction, execution = action_service.request_resume(liveaction, USERNAME)

        # Wait until the liveaction is completed.
        liveaction = self._wait_for_status(
            liveaction, action_constants.LIVEACTION_STATUS_SUCCEEDED
        )
        self.assertEqual(
            liveaction.status, action_constants.LIVEACTION_STATUS_SUCCEEDED
        )

        # Wait for non-blocking threads to complete.
        MockLiveActionPublisherNonBlocking.wait_all()

        # Check liveaction result.
        self.assertIn("tasks", liveaction.result)
        self.assertEqual(len(liveaction.result["tasks"]), 2)
        self.assertTrue(liveaction.result["tasks"][0]["result"]["failed"])
        self.assertEqual(1, liveaction.result["tasks"][0]["result"]["return_code"])
        self.assertTrue(liveaction.result["tasks"][1]["result"]["succeeded"])
        self.assertEqual(0, liveaction.result["tasks"][1]["result"]["return_code"])

    def test_chain_pause_resume_cascade_to_subworkflow(self):
        # A temp file is created during test setup. Ensure the temp file exists.
        # The test action chain will stall until this file is deleted. This gives
        # the unit test a moment to run any test related logic.
        path = self.temp_file_path
        self.assertTrue(os.path.exists(path))

        action = TEST_PACK + "." + "test_pause_resume_with_subworkflow"
        params = {"tempfile": path, "message": "foobar"}
        liveaction = LiveActionDB(action=action, parameters=params)
        liveaction, execution = action_service.request(liveaction)
        liveaction = LiveAction.get_by_id(str(liveaction.id))

        # Wait until the liveaction is running.
        liveaction = self._wait_for_status(
            liveaction, action_constants.LIVEACTION_STATUS_RUNNING
        )
        self.assertEqual(liveaction.status, action_constants.LIVEACTION_STATUS_RUNNING)

        # Wait for subworkflow to register.
        execution = self._wait_for_children(execution)
        self.assertEqual(len(execution.children), 1)

        # Wait until the subworkflow is running.
        task1_exec = ActionExecution.get_by_id(execution.children[0])
        task1_live = LiveAction.get_by_id(task1_exec.liveaction["id"])
        task1_live = self._wait_for_status(
            task1_live, action_constants.LIVEACTION_STATUS_RUNNING
        )
        self.assertEqual(task1_live.status, action_constants.LIVEACTION_STATUS_RUNNING)

        # Request action chain to pause.
        liveaction, execution = action_service.request_pause(liveaction, USERNAME)

        # Wait until the liveaction is pausing.
        liveaction = self._wait_for_status(
            liveaction, action_constants.LIVEACTION_STATUS_PAUSING
        )
        extra_info = str(liveaction)
        self.assertEqual(
            liveaction.status, action_constants.LIVEACTION_STATUS_PAUSING, extra_info
        )
        self.assertEqual(len(execution.children), 1)

        # Wait until the subworkflow is pausing.
        task1_exec = ActionExecution.get_by_id(execution.children[0])
        task1_live = LiveAction.get_by_id(task1_exec.liveaction["id"])
        task1_live = self._wait_for_status(
            task1_live, action_constants.LIVEACTION_STATUS_PAUSING
        )
        extra_info = str(task1_live)
        self.assertEqual(
            task1_live.status, action_constants.LIVEACTION_STATUS_PAUSING, extra_info
        )

        # Delete the temporary file that the action chain is waiting on.
        os.remove(path)
        self.assertFalse(os.path.exists(path))

        # Wait until the liveaction is paused.
        liveaction = self._wait_for_status(
            liveaction, action_constants.LIVEACTION_STATUS_PAUSED
        )
        extra_info = str(liveaction)
        self.assertEqual(
            liveaction.status, action_constants.LIVEACTION_STATUS_PAUSED, extra_info
        )
        self.assertEqual(len(execution.children), 1)

        # Wait until the subworkflow is paused.
        task1_exec = ActionExecution.get_by_id(execution.children[0])
        task1_live = LiveAction.get_by_id(task1_exec.liveaction["id"])
        task1_live = self._wait_for_status(
            task1_live, action_constants.LIVEACTION_STATUS_PAUSED
        )
        extra_info = str(task1_live)
        self.assertEqual(
            task1_live.status, action_constants.LIVEACTION_STATUS_PAUSED, extra_info
        )

        # Wait for non-blocking threads to complete. Ensure runner is not running.
        MockLiveActionPublisherNonBlocking.wait_all()

        # Check liveaction result.
        self.assertIn("tasks", liveaction.result)
        self.assertEqual(len(liveaction.result["tasks"]), 1)

        subworkflow = liveaction.result["tasks"][0]
        self.assertEqual(len(subworkflow["result"]["tasks"]), 1)
        self.assertEqual(
            subworkflow["state"], action_constants.LIVEACTION_STATUS_PAUSED
        )

        # Request action chain to resume.
        liveaction, execution = action_service.request_resume(liveaction, USERNAME)

        # Wait until the liveaction is completed.
        liveaction = self._wait_for_status(
            liveaction, action_constants.LIVEACTION_STATUS_SUCCEEDED
        )
        self.assertEqual(
            liveaction.status, action_constants.LIVEACTION_STATUS_SUCCEEDED
        )

        # Wait for non-blocking threads to complete.
        MockLiveActionPublisherNonBlocking.wait_all()

        # Check liveaction result.
        self.assertIn("tasks", liveaction.result)
        self.assertEqual(len(liveaction.result["tasks"]), 2)

        subworkflow = liveaction.result["tasks"][0]
        self.assertEqual(len(subworkflow["result"]["tasks"]), 2)
        self.assertEqual(
            subworkflow["state"], action_constants.LIVEACTION_STATUS_SUCCEEDED
        )

    def test_chain_pause_resume_cascade_to_parent_workflow(self):
        # A temp file is created during test setup. Ensure the temp file exists.
        # The test action chain will stall until this file is deleted. This gives
        # the unit test a moment to run any test related logic.
        path = self.temp_file_path
        self.assertTrue(os.path.exists(path))

        action = TEST_PACK + "." + "test_pause_resume_with_subworkflow"
        params = {"tempfile": path, "message": "foobar"}
        liveaction = LiveActionDB(action=action, parameters=params)
        liveaction, execution = action_service.request(liveaction)
        liveaction = LiveAction.get_by_id(str(liveaction.id))

        # Wait until the liveaction is running.
        liveaction = self._wait_for_status(
            liveaction, action_constants.LIVEACTION_STATUS_RUNNING
        )
        self.assertEqual(liveaction.status, action_constants.LIVEACTION_STATUS_RUNNING)

        # Wait for subworkflow to register.
        execution = self._wait_for_children(execution)
        self.assertEqual(len(execution.children), 1)

        # Wait until the subworkflow is running.
        task1_exec = ActionExecution.get_by_id(execution.children[0])
        task1_live = LiveAction.get_by_id(task1_exec.liveaction["id"])
        task1_live = self._wait_for_status(
            task1_live, action_constants.LIVEACTION_STATUS_RUNNING
        )
        self.assertEqual(task1_live.status, action_constants.LIVEACTION_STATUS_RUNNING)

        # Request subworkflow to pause.
        task1_live, task1_exec = action_service.request_pause(task1_live, USERNAME)

        # Wait until the subworkflow is pausing.
        task1_exec = ActionExecution.get_by_id(execution.children[0])
        task1_live = LiveAction.get_by_id(task1_exec.liveaction["id"])
        task1_live = self._wait_for_status(
            task1_live, action_constants.LIVEACTION_STATUS_PAUSING
        )
        extra_info = str(task1_live)
        self.assertEqual(
            task1_live.status, action_constants.LIVEACTION_STATUS_PAUSING, extra_info
        )

        # Delete the temporary file that the action chain is waiting on.
        os.remove(path)
        self.assertFalse(os.path.exists(path))

        # Wait until the subworkflow is paused.
        task1_exec = ActionExecution.get_by_id(execution.children[0])
        task1_live = LiveAction.get_by_id(task1_exec.liveaction["id"])
        task1_live = self._wait_for_status(
            task1_live, action_constants.LIVEACTION_STATUS_PAUSED
        )
        extra_info = str(task1_live)
        self.assertEqual(
            task1_live.status, action_constants.LIVEACTION_STATUS_PAUSED, extra_info
        )

        # Wait until the parent liveaction is paused.
        liveaction = self._wait_for_status(
            liveaction, action_constants.LIVEACTION_STATUS_PAUSED
        )
        extra_info = str(liveaction)
        self.assertEqual(
            liveaction.status, action_constants.LIVEACTION_STATUS_PAUSED, extra_info
        )
        self.assertEqual(len(execution.children), 1)

        # Wait for non-blocking threads to complete. Ensure runner is not running.
        MockLiveActionPublisherNonBlocking.wait_all()

        # Check liveaction result.
        self.assertIn("tasks", liveaction.result)
        self.assertEqual(len(liveaction.result["tasks"]), 1)

        subworkflow = liveaction.result["tasks"][0]
        self.assertEqual(len(subworkflow["result"]["tasks"]), 1)
        self.assertEqual(
            subworkflow["state"], action_constants.LIVEACTION_STATUS_PAUSED
        )

        # Request subworkflow to resume.
        task1_live, task1_exec = action_service.request_resume(task1_live, USERNAME)

        # Wait until the subworkflow is paused.
        task1_exec = ActionExecution.get_by_id(execution.children[0])
        task1_live = LiveAction.get_by_id(task1_exec.liveaction["id"])
        task1_live = self._wait_for_status(
            task1_live, action_constants.LIVEACTION_STATUS_SUCCEEDED
        )
        self.assertEqual(
            task1_live.status, action_constants.LIVEACTION_STATUS_SUCCEEDED
        )

        # The parent workflow will stay paused.
        liveaction = self._wait_for_status(
            liveaction, action_constants.LIVEACTION_STATUS_PAUSED
        )
        self.assertEqual(liveaction.status, action_constants.LIVEACTION_STATUS_PAUSED)

        # Wait for non-blocking threads to complete.
        MockLiveActionPublisherNonBlocking.wait_all()

        # Check liveaction result of the parent, which should stay the same
        # because only the subworkflow was resumed.
        self.assertIn("tasks", liveaction.result)
        self.assertEqual(len(liveaction.result["tasks"]), 1)

        subworkflow = liveaction.result["tasks"][0]
        self.assertEqual(len(subworkflow["result"]["tasks"]), 1)
        self.assertEqual(
            subworkflow["state"], action_constants.LIVEACTION_STATUS_PAUSED
        )

        # Request parent workflow to resume.
        liveaction, execution = action_service.request_resume(liveaction, USERNAME)

        # Wait until the liveaction is completed.
        liveaction = self._wait_for_status(
            liveaction, action_constants.LIVEACTION_STATUS_SUCCEEDED
        )
        self.assertEqual(
            liveaction.status, action_constants.LIVEACTION_STATUS_SUCCEEDED
        )

        # Wait for non-blocking threads to complete.
        MockLiveActionPublisherNonBlocking.wait_all()

        # Check liveaction result.
        self.assertIn("tasks", liveaction.result)
        self.assertEqual(len(liveaction.result["tasks"]), 2)

        subworkflow = liveaction.result["tasks"][0]
        self.assertEqual(len(subworkflow["result"]["tasks"]), 2)
        self.assertEqual(
            subworkflow["state"], action_constants.LIVEACTION_STATUS_SUCCEEDED
        )

    def test_chain_pause_resume_with_context_access(self):
        # A temp file is created during test setup. Ensure the temp file exists.
        # The test action chain will stall until this file is deleted. This gives
        # the unit test a moment to run any test related logic.
        path = self.temp_file_path
        self.assertTrue(os.path.exists(path))

        action = TEST_PACK + "." + "test_pause_resume_with_context_access"
        params = {"tempfile": path, "message": "foobar"}
        liveaction = LiveActionDB(action=action, parameters=params)
        liveaction, execution = action_service.request(liveaction)
        liveaction = LiveAction.get_by_id(str(liveaction.id))

        # Wait until the liveaction is running.
        liveaction = self._wait_for_status(
            liveaction, action_constants.LIVEACTION_STATUS_RUNNING
        )
        self.assertEqual(liveaction.status, action_constants.LIVEACTION_STATUS_RUNNING)

        # Request action chain to pause.
        liveaction, execution = action_service.request_pause(liveaction, USERNAME)

        # Wait until the liveaction is pausing.
        liveaction = self._wait_for_status(
            liveaction, action_constants.LIVEACTION_STATUS_PAUSING
        )
        extra_info = str(liveaction)
        self.assertEqual(
            liveaction.status, action_constants.LIVEACTION_STATUS_PAUSING, extra_info
        )

        # Delete the temporary file that the action chain is waiting on.
        os.remove(path)
        self.assertFalse(os.path.exists(path))

        # Wait until the liveaction is paused.
        liveaction = self._wait_for_status(
            liveaction, action_constants.LIVEACTION_STATUS_PAUSED
        )
        extra_info = str(liveaction)
        self.assertEqual(
            liveaction.status, action_constants.LIVEACTION_STATUS_PAUSED, extra_info
        )

        # Wait for non-blocking threads to complete. Ensure runner is not running.
        MockLiveActionPublisherNonBlocking.wait_all()

        # Request action chain to resume.
        liveaction, execution = action_service.request_resume(liveaction, USERNAME)

        # Wait until the liveaction is completed.
        liveaction = self._wait_for_status(
            liveaction, action_constants.LIVEACTION_STATUS_SUCCEEDED
        )
        self.assertEqual(
            liveaction.status, action_constants.LIVEACTION_STATUS_SUCCEEDED
        )

        # Wait for non-blocking threads to complete.
        MockLiveActionPublisherNonBlocking.wait_all()

        # Check liveaction result.
        self.assertIn("tasks", liveaction.result)
        self.assertEqual(len(liveaction.result["tasks"]), 3)
        self.assertEqual(liveaction.result["tasks"][2]["result"]["stdout"], "foobar")

    def test_chain_pause_resume_with_init_vars(self):
        # A temp file is created during test setup. Ensure the temp file exists.
        # The test action chain will stall until this file is deleted. This gives
        # the unit test a moment to run any test related logic.
        path = self.temp_file_path
        self.assertTrue(os.path.exists(path))

        action = TEST_PACK + "." + "test_pause_resume_with_init_vars"
        params = {"tempfile": path, "message": "foobar"}
        liveaction = LiveActionDB(action=action, parameters=params)
        liveaction, execution = action_service.request(liveaction)
        liveaction = LiveAction.get_by_id(str(liveaction.id))

        # Wait until the liveaction is running.
        liveaction = self._wait_for_status(
            liveaction, action_constants.LIVEACTION_STATUS_RUNNING
        )
        self.assertEqual(liveaction.status, action_constants.LIVEACTION_STATUS_RUNNING)

        # Request action chain to pause.
        liveaction, execution = action_service.request_pause(liveaction, USERNAME)

        # Wait until the liveaction is pausing.
        liveaction = self._wait_for_status(
            liveaction, action_constants.LIVEACTION_STATUS_PAUSING
        )
        extra_info = str(liveaction)
        self.assertEqual(
            liveaction.status, action_constants.LIVEACTION_STATUS_PAUSING, extra_info
        )

        # Delete the temporary file that the action chain is waiting on.
        os.remove(path)
        self.assertFalse(os.path.exists(path))

        # Wait until the liveaction is paused.
        liveaction = self._wait_for_status(
            liveaction, action_constants.LIVEACTION_STATUS_PAUSED
        )
        extra_info = str(liveaction)
        self.assertEqual(
            liveaction.status, action_constants.LIVEACTION_STATUS_PAUSED, extra_info
        )

        # Wait for non-blocking threads to complete. Ensure runner is not running.
        MockLiveActionPublisherNonBlocking.wait_all()

        # Request action chain to resume.
        liveaction, execution = action_service.request_resume(liveaction, USERNAME)

        # Wait until the liveaction is completed.
        liveaction = self._wait_for_status(
            liveaction, action_constants.LIVEACTION_STATUS_SUCCEEDED
        )
        self.assertEqual(
            liveaction.status, action_constants.LIVEACTION_STATUS_SUCCEEDED
        )

        # Wait for non-blocking threads to complete.
        MockLiveActionPublisherNonBlocking.wait_all()

        # Check liveaction result.
        self.assertIn("tasks", liveaction.result)
        self.assertEqual(len(liveaction.result["tasks"]), 2)
        self.assertEqual(liveaction.result["tasks"][1]["result"]["stdout"], "FOOBAR")

    def test_chain_pause_resume_with_no_more_task(self):
        # A temp file is created during test setup. Ensure the temp file exists.
        # The test action chain will stall until this file is deleted. This gives
        # the unit test a moment to run any test related logic.
        path = self.temp_file_path
        self.assertTrue(os.path.exists(path))

        action = TEST_PACK + "." + "test_pause_resume_with_no_more_task"
        params = {"tempfile": path, "message": "foobar"}
        liveaction = LiveActionDB(action=action, parameters=params)
        liveaction, execution = action_service.request(liveaction)
        liveaction = LiveAction.get_by_id(str(liveaction.id))

        # Wait until the liveaction is running.
        liveaction = self._wait_for_status(
            liveaction, action_constants.LIVEACTION_STATUS_RUNNING
        )
        self.assertEqual(liveaction.status, action_constants.LIVEACTION_STATUS_RUNNING)

        # Request action chain to pause.
        liveaction, execution = action_service.request_pause(liveaction, USERNAME)

        # Wait until the liveaction is pausing.
        liveaction = self._wait_for_status(
            liveaction, action_constants.LIVEACTION_STATUS_PAUSING
        )
        extra_info = str(liveaction)
        self.assertEqual(
            liveaction.status, action_constants.LIVEACTION_STATUS_PAUSING, extra_info
        )

        # Delete the temporary file that the action chain is waiting on.
        os.remove(path)
        self.assertFalse(os.path.exists(path))

        # Wait until the liveaction is paused.
        liveaction = self._wait_for_status(
            liveaction, action_constants.LIVEACTION_STATUS_PAUSED
        )
        extra_info = str(liveaction)
        self.assertEqual(
            liveaction.status, action_constants.LIVEACTION_STATUS_PAUSED, extra_info
        )

        # Wait for non-blocking threads to complete. Ensure runner is not running.
        MockLiveActionPublisherNonBlocking.wait_all()

        # Request action chain to resume.
        liveaction, execution = action_service.request_resume(liveaction, USERNAME)

        # Wait until the liveaction is completed.
        liveaction = self._wait_for_status(
            liveaction, action_constants.LIVEACTION_STATUS_SUCCEEDED
        )
        self.assertEqual(
            liveaction.status, action_constants.LIVEACTION_STATUS_SUCCEEDED
        )

        # Wait for non-blocking threads to complete.
        MockLiveActionPublisherNonBlocking.wait_all()

        # Check liveaction result.
        self.assertIn("tasks", liveaction.result)
        self.assertEqual(len(liveaction.result["tasks"]), 1)

    def test_chain_pause_resume_last_task_failed_with_no_next_task(self):
        # A temp file is created during test setup. Ensure the temp file exists.
        # The test action chain will stall until this file is deleted. This gives
        # the unit test a moment to run any test related logic.
        path = self.temp_file_path
        self.assertTrue(os.path.exists(path))

        action = (
            TEST_PACK + "." + "test_pause_resume_last_task_failed_with_no_next_task"
        )
        params = {"tempfile": path, "message": "foobar"}
        liveaction = LiveActionDB(action=action, parameters=params)
        liveaction, execution = action_service.request(liveaction)
        liveaction = LiveAction.get_by_id(str(liveaction.id))

        # Wait until the liveaction is running.
        liveaction = self._wait_for_status(
            liveaction, action_constants.LIVEACTION_STATUS_RUNNING
        )
        self.assertEqual(liveaction.status, action_constants.LIVEACTION_STATUS_RUNNING)

        # Request action chain to pause.
        liveaction, execution = action_service.request_pause(liveaction, USERNAME)

        # Wait until the liveaction is pausing.
        liveaction = self._wait_for_status(
            liveaction, action_constants.LIVEACTION_STATUS_PAUSING
        )
        extra_info = str(liveaction)
        self.assertEqual(
            liveaction.status, action_constants.LIVEACTION_STATUS_PAUSING, extra_info
        )

        # Delete the temporary file that the action chain is waiting on.
        os.remove(path)
        self.assertFalse(os.path.exists(path))

        # Wait until the liveaction is paused.
        liveaction = self._wait_for_status(
            liveaction, action_constants.LIVEACTION_STATUS_PAUSED
        )
        extra_info = str(liveaction)
        self.assertEqual(
            liveaction.status, action_constants.LIVEACTION_STATUS_PAUSED, extra_info
        )

        # Wait for non-blocking threads to complete. Ensure runner is not running.
        MockLiveActionPublisherNonBlocking.wait_all()

        # Request action chain to resume.
        liveaction, execution = action_service.request_resume(liveaction, USERNAME)

        # Wait until the liveaction is completed.
        liveaction = self._wait_for_status(
            liveaction, action_constants.LIVEACTION_STATUS_FAILED
        )
        self.assertEqual(liveaction.status, action_constants.LIVEACTION_STATUS_FAILED)

        # Wait for non-blocking threads to complete.
        MockLiveActionPublisherNonBlocking.wait_all()

        # Check liveaction result.
        self.assertIn("tasks", liveaction.result)
        self.assertEqual(len(liveaction.result["tasks"]), 1)

        self.assertEqual(
            liveaction.result["tasks"][0]["state"],
            action_constants.LIVEACTION_STATUS_FAILED,
        )

    def test_chain_pause_resume_status_change(self):
        # Tests context_result is updated when last task's status changes between pause and resume

        action = TEST_PACK + "." + "test_pause_resume_context_result"
        liveaction = LiveActionDB(action=action)
        liveaction, execution = action_service.request(liveaction)
        liveaction = LiveAction.get_by_id(str(liveaction.id))

        # Wait until the liveaction is paused.
        liveaction = self._wait_for_status(
            liveaction, action_constants.LIVEACTION_STATUS_PAUSED
        )
        extra_info = str(liveaction)
        self.assertEqual(
            liveaction.status, action_constants.LIVEACTION_STATUS_PAUSED, extra_info
        )

        # Wait for non-blocking threads to complete. Ensure runner is not running.
        MockLiveActionPublisherNonBlocking.wait_all()

        last_task_liveaction_id = liveaction.result["tasks"][-1]["liveaction_id"]

        action_utils.update_liveaction_status(
            status=action_constants.LIVEACTION_STATUS_SUCCEEDED,
            end_timestamp=date_utils.get_datetime_utc_now(),
            result={"foo": "bar"},
            liveaction_id=last_task_liveaction_id,
        )

        # Request action chain to resume.
        liveaction, execution = action_service.request_resume(liveaction, USERNAME)

        # Wait until the liveaction is completed.
        liveaction = self._wait_for_status(
            liveaction, action_constants.LIVEACTION_STATUS_SUCCEEDED
        )

        self.assertEqual(
            liveaction.status,
            action_constants.LIVEACTION_STATUS_SUCCEEDED,
            str(liveaction),
        )

        # Wait for non-blocking threads to complete.
        MockLiveActionPublisherNonBlocking.wait_all()

        # Check liveaction result.
        self.assertIn("tasks", liveaction.result)
        self.assertEqual(len(liveaction.result["tasks"]), 2)
        self.assertEqual(liveaction.result["tasks"][0]["result"]["foo"], "bar")

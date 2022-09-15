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

from st2common.bootstrap import actionsregistrar
from st2common.bootstrap import runnersregistrar
from st2common.constants import action as action_constants
from st2common.models.api import notification as notify_api_models
from st2common.models.db.liveaction import LiveActionDB
from st2common.models.system.common import ResourceReference
from st2common.persistence.execution import ActionExecution
from st2common.persistence.liveaction import LiveAction
from st2common.services import action as action_service
from st2common.util import action_db as action_db_util
from st2tests import ExecutionDbTestCase
from st2tests import fixturesloader
from action_chain_runner import action_chain_runner as acr


from st2common.transport.liveaction import LiveActionPublisher
from st2common.transport.publishers import CUDPublisher

from st2tests.fixtures.generic.fixture import PACK_NAME as FIXTURES_PACK
from st2tests.fixtures.packs.action_chain_tests.fixture import (
    PACK_NAME as TEST_PACK,
    PACK_PATH as TEST_PACK_PATH,
)
from st2tests.fixtures.packs.core.fixture import PACK_PATH as CORE_PACK_PATH
from st2tests.mocks.liveaction import MockLiveActionPublisherNonBlocking


class DummyActionExecution(object):
    def __init__(self, status=action_constants.LIVEACTION_STATUS_SUCCEEDED, result=""):
        self.id = None
        self.status = status
        self.result = result


TEST_MODELS = {"actions": ["a1.yaml", "a2.yaml"], "runners": ["testrunner1.yaml"]}

MODELS = fixturesloader.FixturesLoader().load_models(
    fixtures_pack=FIXTURES_PACK, fixtures_dict=TEST_MODELS
)
ACTION_1 = MODELS["actions"]["a1.yaml"]
ACTION_2 = MODELS["actions"]["a2.yaml"]
RUNNER = MODELS["runners"]["testrunner1.yaml"]

CHAIN_1_PATH = fixturesloader.FixturesLoader().get_fixture_file_path_abs(
    FIXTURES_PACK, "actionchains", "chain_with_notifications.yaml"
)

PACKS = [TEST_PACK_PATH, CORE_PACK_PATH]

MOCK_NOTIFY = {
    "on-complete": {
        "routes": ["hubot"],
    }
}


@mock.patch.object(
    action_db_util, "get_runnertype_by_name", mock.MagicMock(return_value=RUNNER)
)
@mock.patch.object(
    action_service,
    "is_action_canceled_or_canceling",
    mock.MagicMock(return_value=False),
)
@mock.patch.object(
    action_service, "is_action_paused_or_pausing", mock.MagicMock(return_value=False)
)
@mock.patch.object(CUDPublisher, "publish_update", mock.MagicMock(return_value=None))
@mock.patch.object(CUDPublisher, "publish_create", mock.MagicMock(return_value=None))
@mock.patch.object(
    LiveActionPublisher,
    "publish_state",
    mock.MagicMock(side_effect=MockLiveActionPublisherNonBlocking.publish_state),
)
class TestActionChainNotifications(ExecutionDbTestCase):
    @classmethod
    def setUpClass(cls):
        super(TestActionChainNotifications, cls).setUpClass()

        # Register runners.
        runnersregistrar.register_runners()

        # Register test pack(s).
        actions_registrar = actionsregistrar.ActionsRegistrar(
            use_pack_cache=False, fail_on_failure=True
        )

        for pack in PACKS:
            actions_registrar.register_from_pack(pack)

    @mock.patch.object(
        action_db_util, "get_action_by_ref", mock.MagicMock(return_value=ACTION_1)
    )
    @mock.patch.object(
        action_service, "request", return_value=(DummyActionExecution(), None)
    )
    def test_chain_runner_success_path(self, request):
        chain_runner = acr.get_runner()
        chain_runner.entry_point = CHAIN_1_PATH
        chain_runner.action = ACTION_1
        action_ref = ResourceReference.to_string_reference(
            name=ACTION_1.name, pack=ACTION_1.pack
        )
        chain_runner.liveaction = LiveActionDB(action=action_ref)
        chain_runner.pre_run()
        chain_runner.run({})
        self.assertNotEqual(chain_runner.chain_holder.actionchain, None)
        self.assertEqual(request.call_count, 2)
        first_call_args = request.call_args_list[0][0]
        liveaction_db = first_call_args[0]
        self.assertTrue(liveaction_db.notify, "Notify property expected.")

        second_call_args = request.call_args_list[1][0]
        liveaction_db = second_call_args[0]
        self.assertFalse(liveaction_db.notify, "Notify property not expected.")

    def test_skip_notify_for_task_with_notify(self):
        action = TEST_PACK + "." + "test_subworkflow_default_with_notify_task"
        params = {"skip_notify": ["task1"]}
        liveaction = LiveActionDB(action=action, parameters=params)
        liveaction.notify = notify_api_models.NotificationsHelper.to_model(MOCK_NOTIFY)
        liveaction, execution = action_service.request(liveaction)
        liveaction = LiveAction.get_by_id(str(liveaction.id))

        # Wait until the liveaction is running.
        liveaction = self._wait_on_status(
            liveaction, action_constants.LIVEACTION_STATUS_RUNNING
        )

        execution = self._wait_for_children(execution)
        self.assertEqual(len(execution.children), 1)

        # Assert task1 notify is skipped
        task1_exec = ActionExecution.get_by_id(execution.children[0])
        task1_live = LiveAction.get_by_id(task1_exec.liveaction["id"])
        task1_live = self._wait_on_status(
            task1_live, action_constants.LIVEACTION_STATUS_SUCCEEDED
        )
        self.assertIsNone(task1_live.notify)

        execution = self._wait_for_children(execution, expected_children=2, retries=300)
        self.assertEqual(len(execution.children), 2)

        # Assert task2 notify is not skipped
        task2_exec = ActionExecution.get_by_id(execution.children[1])
        task2_live = LiveAction.get_by_id(task2_exec.liveaction["id"])
        notify = notify_api_models.NotificationsHelper.from_model(
            notify_model=task2_live.notify
        )
        self.assertEqual(notify, MOCK_NOTIFY)
        MockLiveActionPublisherNonBlocking.wait_all()

    def test_skip_notify_default_for_task_with_notify(self):
        action = TEST_PACK + "." + "test_subworkflow_default_with_notify_task"
        liveaction = LiveActionDB(action=action)
        liveaction.notify = notify_api_models.NotificationsHelper.to_model(MOCK_NOTIFY)
        liveaction, execution = action_service.request(liveaction)
        liveaction = LiveAction.get_by_id(str(liveaction.id))

        # Wait until the liveaction is running.
        liveaction = self._wait_on_status(
            liveaction, action_constants.LIVEACTION_STATUS_RUNNING
        )

        execution = self._wait_for_children(execution)
        self.assertEqual(len(execution.children), 1)

        # Assert task1 notify is set.
        task1_exec = ActionExecution.get_by_id(execution.children[0])
        task1_live = LiveAction.get_by_id(task1_exec.liveaction["id"])
        task1_live = self._wait_on_status(
            task1_live, action_constants.LIVEACTION_STATUS_SUCCEEDED
        )
        notify = notify_api_models.NotificationsHelper.from_model(
            notify_model=task1_live.notify
        )
        self.assertEqual(notify, MOCK_NOTIFY)

        execution = self._wait_for_children(execution, expected_children=2, retries=300)
        self.assertEqual(len(execution.children), 2)

        # Assert task2 notify is not skipped by default.
        task2_exec = ActionExecution.get_by_id(execution.children[1])
        task2_live = LiveAction.get_by_id(task2_exec.liveaction["id"])
        self.assertIsNone(task2_live.notify)
        MockLiveActionPublisherNonBlocking.wait_all()

    def _wait_for_children(
        self, execution, expected_children=1, interval=0.1, retries=100
    ):
        # Wait until the execution has children.
        for i in range(0, retries):
            execution = ActionExecution.get_by_id(str(execution.id))
            found_children = len(getattr(execution, "children", []))

            if found_children == expected_children:
                return execution

            if found_children > expected_children:
                raise AssertionError(
                    "Expected %s children, but got %s"
                    % (expected_children, found_children)
                )

            eventlet.sleep(interval)

        found_children = len(getattr(execution, "children", []))

        if found_children != expected_children:
            raise AssertionError(
                "Expected %s children, but got %s after %s retry attempts"
                % (expected_children, found_children, retries)
            )

        return execution

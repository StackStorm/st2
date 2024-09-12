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
from mock import call
from six.moves import range

# This import must be early for import-time side-effects.
# Importing st2actions.scheduler relies on config being parsed :/
from st2tests import DbTestCase, EventletTestCase, ExecutionDbTestCase

import st2common
from st2actions.scheduler import handler as scheduling_queue
from st2common.bootstrap.policiesregistrar import register_policy_types
from st2common.constants import action as action_constants
from st2common.models.db.action import LiveActionDB
from st2common.persistence.action import LiveAction
from st2common.persistence.execution import ActionExecution
from st2common.persistence.execution_queue import ActionExecutionSchedulingQueue
from st2common.persistence.policy import Policy
from st2common.services import action as action_service
from st2common.services import coordination
from st2common.transport.liveaction import LiveActionPublisher
from st2common.transport.publishers import CUDPublisher
from st2common.bootstrap import runnersregistrar as runners_registrar
import st2tests.config as tests_config
from st2tests.fixtures.generic.fixture import PACK_NAME as PACK
from st2tests.fixturesloader import FixturesLoader
from st2tests.mocks.execution import MockExecutionPublisher
from st2tests.mocks.liveaction import MockLiveActionPublisherSchedulingQueueOnly
from st2tests.mocks.runners import runner


__all__ = ["ConcurrencyPolicyTestCase"]

TEST_FIXTURES = {
    "actions": ["action1.yaml", "action2.yaml"],
    "policies": ["policy_1.yaml", "policy_5.yaml"],
}

NON_EMPTY_RESULT = {"data": "non-empty"}
MOCK_RUN_RETURN_VALUE = (
    action_constants.LIVEACTION_STATUS_RUNNING,
    NON_EMPTY_RESULT,
    None,
)

SCHEDULED_STATES = [
    action_constants.LIVEACTION_STATUS_SCHEDULED,
    action_constants.LIVEACTION_STATUS_RUNNING,
    action_constants.LIVEACTION_STATUS_SUCCEEDED,
]


@mock.patch(
    "st2common.runners.base.get_runner", mock.Mock(return_value=runner.get_runner())
)
@mock.patch(
    "st2actions.container.base.get_runner", mock.Mock(return_value=runner.get_runner())
)
@mock.patch.object(
    CUDPublisher,
    "publish_update",
    mock.MagicMock(side_effect=MockExecutionPublisher.publish_update),
)
@mock.patch.object(CUDPublisher, "publish_create", mock.MagicMock(return_value=None))
class ConcurrencyPolicyTestCase(EventletTestCase, ExecutionDbTestCase):
    @classmethod
    def setUpClass(cls):
        EventletTestCase.setUpClass()
        DbTestCase.setUpClass()

        # Override the coordinator to use the noop driver otherwise the tests will be blocked.
        tests_config.parse_args(coordinator_noop=True)
        coordination.COORDINATOR = None

        # Register runners
        runners_registrar.register_runners()

        # Register common policy types
        register_policy_types(st2common)

        loader = FixturesLoader()
        loader.save_fixtures_to_db(fixtures_pack=PACK, fixtures_dict=TEST_FIXTURES)

    @classmethod
    def tearDownClass(cls):
        # Reset the coordinator.
        coordination.coordinator_teardown(coordination.COORDINATOR)
        coordination.COORDINATOR = None

        super(ConcurrencyPolicyTestCase, cls).tearDownClass()

    # NOTE: This monkey patch needs to happen again here because during tests for some reason this
    # method gets unpatched (test doing reload() or similar)
    @mock.patch(
        "st2actions.container.base.get_runner",
        mock.Mock(return_value=runner.get_runner()),
    )
    def tearDown(self):
        for liveaction in LiveAction.get_all():
            action_service.update_status(
                liveaction, action_constants.LIVEACTION_STATUS_CANCELED
            )

    @staticmethod
    def _process_scheduling_queue():
        for queued_req in ActionExecutionSchedulingQueue.get_all():
            scheduling_queue.get_handler()._handle_execution(queued_req)

    @mock.patch.object(
        runner.MockActionRunner,
        "run",
        mock.MagicMock(return_value=MOCK_RUN_RETURN_VALUE),
    )
    @mock.patch.object(
        LiveActionPublisher,
        "publish_state",
        mock.MagicMock(
            side_effect=MockLiveActionPublisherSchedulingQueueOnly.publish_state
        ),
    )
    def test_over_threshold_delay_executions(self):
        # Ensure the concurrency policy is accurate.
        policy_db = Policy.get_by_ref("wolfpack.action-1.concurrency")
        self.assertGreater(policy_db.parameters["threshold"], 0)

        # Launch action executions until the expected threshold is reached.
        for i in range(0, policy_db.parameters["threshold"]):
            parameters = {"actionstr": "foo-" + str(i)}
            liveaction = LiveActionDB(action="wolfpack.action-1", parameters=parameters)
            action_service.request(liveaction)

        # Run the scheduler to schedule action executions.
        self._process_scheduling_queue()

        # Check the number of action executions in scheduled state.
        scheduled = [
            item for item in LiveAction.get_all() if item.status in SCHEDULED_STATES
        ]
        self.assertEqual(len(scheduled), policy_db.parameters["threshold"])

        # Assert the correct number of published states and action executions. This is to avoid
        # duplicate executions caused by accidental publishing of state in the concurrency policies.
        # num_state_changes = len(scheduled) * len(['requested', 'scheduled', 'running'])
        expected_num_exec = len(scheduled)
        expected_num_pubs = expected_num_exec * 3
        self.assertEqual(
            expected_num_pubs, LiveActionPublisher.publish_state.call_count
        )
        self.assertEqual(expected_num_exec, runner.MockActionRunner.run.call_count)

        # Execution is expected to be delayed since concurrency threshold is reached.
        liveaction = LiveActionDB(
            action="wolfpack.action-1", parameters={"actionstr": "foo-last"}
        )
        liveaction, _ = action_service.request(liveaction)

        expected_num_pubs += 1  # Tally requested state.
        self.assertEqual(
            expected_num_pubs, LiveActionPublisher.publish_state.call_count
        )

        # Run the scheduler to schedule action executions.
        self._process_scheduling_queue()

        # Since states are being processed async, wait for the liveaction to go into delayed state.
        liveaction = self._wait_on_status(
            liveaction, action_constants.LIVEACTION_STATUS_DELAYED
        )

        expected_num_exec += 0  # This request will not be scheduled for execution.
        expected_num_pubs += 0  # The delayed status change should not be published.
        self.assertEqual(
            expected_num_pubs, LiveActionPublisher.publish_state.call_count
        )
        self.assertEqual(expected_num_exec, runner.MockActionRunner.run.call_count)

        # Mark one of the scheduled/running execution as completed.
        action_service.update_status(
            scheduled[0], action_constants.LIVEACTION_STATUS_SUCCEEDED, publish=True
        )

        expected_num_pubs += 1  # Tally succeeded state.
        self.assertEqual(
            expected_num_pubs, LiveActionPublisher.publish_state.call_count
        )

        # Run the scheduler to schedule action executions.
        self._process_scheduling_queue()

        # Once capacity freed up, the delayed execution is published as scheduled.
        expected_num_exec += 1  # This request is expected to be executed.
        expected_num_pubs += 2  # Tally scheduled and running state.

        # Since states are being processed async, wait for the liveaction to be scheduled.
        liveaction = self._wait_on_statuses(liveaction, SCHEDULED_STATES)
        self.assertEqual(
            expected_num_pubs, LiveActionPublisher.publish_state.call_count
        )
        self.assertEqual(expected_num_exec, runner.MockActionRunner.run.call_count)

        # Check the status changes.
        execution = ActionExecution.get(liveaction__id=str(liveaction.id))
        expected_status_changes = [
            "requested",
            "delayed",
            "requested",
            "scheduled",
            "running",
        ]
        actual_status_changes = [entry["status"] for entry in execution.log]
        self.assertListEqual(actual_status_changes, expected_status_changes)

    @mock.patch.object(
        runner.MockActionRunner,
        "run",
        mock.MagicMock(return_value=MOCK_RUN_RETURN_VALUE),
    )
    @mock.patch.object(
        LiveActionPublisher,
        "publish_state",
        mock.MagicMock(
            side_effect=MockLiveActionPublisherSchedulingQueueOnly.publish_state
        ),
    )
    def test_over_threshold_cancel_executions(self):
        policy_db = Policy.get_by_ref("wolfpack.action-2.concurrency.cancel")
        self.assertEqual(policy_db.parameters["action"], "cancel")
        self.assertGreater(policy_db.parameters["threshold"], 0)

        # Launch action executions until the expected threshold is reached.
        for i in range(0, policy_db.parameters["threshold"]):
            parameters = {"actionstr": "foo-" + str(i)}
            liveaction = LiveActionDB(action="wolfpack.action-2", parameters=parameters)
            action_service.request(liveaction)

        # Run the scheduler to schedule action executions.
        self._process_scheduling_queue()

        # Check the number of action executions in scheduled state.
        scheduled = [
            item for item in LiveAction.get_all() if item.status in SCHEDULED_STATES
        ]
        self.assertEqual(len(scheduled), policy_db.parameters["threshold"])

        # duplicate executions caused by accidental publishing of state in the concurrency policies.
        # num_state_changes = len(scheduled) * len(['requested', 'scheduled', 'running'])
        expected_num_exec = len(scheduled)
        expected_num_pubs = expected_num_exec * 3
        self.assertEqual(
            expected_num_pubs, LiveActionPublisher.publish_state.call_count
        )
        self.assertEqual(expected_num_exec, runner.MockActionRunner.run.call_count)

        # Execution is expected to be canceled since concurrency threshold is reached.
        liveaction = LiveActionDB(
            action="wolfpack.action-2", parameters={"actionstr": "foo"}
        )
        liveaction, _ = action_service.request(liveaction)

        expected_num_pubs += 1  # Tally requested state.
        self.assertEqual(
            expected_num_pubs, LiveActionPublisher.publish_state.call_count
        )

        # Run the scheduler to schedule action executions.
        self._process_scheduling_queue()

        # Assert the canceling state is being published.
        calls = [call(liveaction, action_constants.LIVEACTION_STATUS_CANCELING)]
        LiveActionPublisher.publish_state.assert_has_calls(calls)
        expected_num_pubs += 2  # Tally canceling and canceled state changes.
        expected_num_exec += 0  # This request will not be scheduled for execution.
        self.assertEqual(
            expected_num_pubs, LiveActionPublisher.publish_state.call_count
        )
        self.assertEqual(expected_num_exec, runner.MockActionRunner.run.call_count)

        # Assert the action is canceled.
        liveaction = LiveAction.get_by_id(str(liveaction.id))
        self.assertEqual(liveaction.status, action_constants.LIVEACTION_STATUS_CANCELED)
        self.assertEqual(
            expected_num_pubs, LiveActionPublisher.publish_state.call_count
        )
        self.assertEqual(expected_num_exec, runner.MockActionRunner.run.call_count)

    @mock.patch.object(
        runner.MockActionRunner,
        "run",
        mock.MagicMock(return_value=MOCK_RUN_RETURN_VALUE),
    )
    @mock.patch.object(
        LiveActionPublisher,
        "publish_state",
        mock.MagicMock(
            side_effect=MockLiveActionPublisherSchedulingQueueOnly.publish_state
        ),
    )
    def test_on_cancellation(self):
        policy_db = Policy.get_by_ref("wolfpack.action-1.concurrency")
        self.assertGreater(policy_db.parameters["threshold"], 0)

        # Launch action executions until the expected threshold is reached.
        for i in range(0, policy_db.parameters["threshold"]):
            parameters = {"actionstr": "foo-" + str(i)}
            liveaction = LiveActionDB(action="wolfpack.action-1", parameters=parameters)
            action_service.request(liveaction)

        # Run the scheduler to schedule action executions.
        self._process_scheduling_queue()

        # Check the number of action executions in scheduled state.
        scheduled = [
            item for item in LiveAction.get_all() if item.status in SCHEDULED_STATES
        ]
        self.assertEqual(len(scheduled), policy_db.parameters["threshold"])

        # duplicate executions caused by accidental publishing of state in the concurrency policies.
        # num_state_changes = len(scheduled) * len(['requested', 'scheduled', 'running'])
        expected_num_exec = len(scheduled)
        expected_num_pubs = expected_num_exec * 3
        self.assertEqual(
            expected_num_pubs, LiveActionPublisher.publish_state.call_count
        )
        self.assertEqual(expected_num_exec, runner.MockActionRunner.run.call_count)

        # Execution is expected to be delayed since concurrency threshold is reached.
        liveaction = LiveActionDB(
            action="wolfpack.action-1", parameters={"actionstr": "foo"}
        )
        liveaction, _ = action_service.request(liveaction)

        expected_num_pubs += 1  # Tally requested state.
        self.assertEqual(
            expected_num_pubs, LiveActionPublisher.publish_state.call_count
        )

        # Run the scheduler to schedule action executions.
        self._process_scheduling_queue()

        # Since states are being processed async, wait for the liveaction to go into delayed state.
        liveaction = self._wait_on_status(
            liveaction, action_constants.LIVEACTION_STATUS_DELAYED
        )

        expected_num_exec += 0  # This request will not be scheduled for execution.
        expected_num_pubs += 0  # The delayed status change should not be published.
        self.assertEqual(
            expected_num_pubs, LiveActionPublisher.publish_state.call_count
        )
        self.assertEqual(expected_num_exec, runner.MockActionRunner.run.call_count)

        # Cancel execution.
        action_service.request_cancellation(scheduled[0], "stanley")
        expected_num_pubs += 2  # Tally the canceling and canceled states.
        self.assertEqual(
            expected_num_pubs, LiveActionPublisher.publish_state.call_count
        )

        # Run the scheduler to schedule action executions.
        self._process_scheduling_queue()

        # Once capacity freed up, the delayed execution is published as requested again.
        expected_num_exec += 1  # This request is expected to be executed.
        expected_num_pubs += 2  # Tally scheduled and running state.

        # Execution is expected to be rescheduled.
        liveaction = LiveAction.get_by_id(str(liveaction.id))
        self.assertIn(liveaction.status, SCHEDULED_STATES)
        self.assertEqual(
            expected_num_pubs, LiveActionPublisher.publish_state.call_count
        )
        self.assertEqual(expected_num_exec, runner.MockActionRunner.run.call_count)

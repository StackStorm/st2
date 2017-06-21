# Licensed to the StackStorm, Inc ('StackStorm') under one or more
# contributor license agreements.  See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.
# The ASF licenses this file to You under the Apache License, Version 2.0
# (the "License"); you may not use this file except in compliance with
# the License.  You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import eventlet
import mock
from mock import call

import st2common
from st2common.bootstrap.policiesregistrar import register_policy_types
from st2common.constants import action as action_constants
from st2common.models.db.action import LiveActionDB
from st2common.persistence.action import LiveAction
from st2common.persistence.policy import Policy
from st2common.services import action as action_service
from st2common.transport.execution import ActionExecutionPublisher
from st2common.transport.liveaction import LiveActionPublisher
from st2common.transport.publishers import CUDPublisher
from st2tests import DbTestCase, EventletTestCase
from st2tests.fixturesloader import FixturesLoader
from st2tests.mocks.execution import MockExecutionPublisher, MockExecutionPublisherNonBlocking
from st2tests.mocks.liveaction import MockLiveActionPublisherNonBlocking
from st2tests.mocks import runner

PACK = 'generic'
TEST_FIXTURES = {
    'runners': [
        'testrunner1.yaml'
    ],
    'actions': [
        'action1.yaml',
        'action2.yaml'
    ],
    'policies': [
        'policy_1.yaml',
        'policy_5.yaml'
    ]
}

NON_EMPTY_RESULT = 'non-empty'

SCHEDULED_STATES = [
    action_constants.LIVEACTION_STATUS_SCHEDULED,
    action_constants.LIVEACTION_STATUS_RUNNING,
    action_constants.LIVEACTION_STATUS_SUCCEEDED
]


@mock.patch('st2common.runners.base.register_runner',
            mock.MagicMock(return_value=runner))
@mock.patch.object(
    CUDPublisher, 'publish_update',
    mock.MagicMock(side_effect=MockExecutionPublisher.publish_update))
@mock.patch.object(
    CUDPublisher, 'publish_create',
    mock.MagicMock(return_value=None))
class ConcurrencyPolicyTest(EventletTestCase, DbTestCase):
    @classmethod
    def setUpClass(cls):
        EventletTestCase.setUpClass()
        DbTestCase.setUpClass()

        # Register common policy types
        register_policy_types(st2common)

        loader = FixturesLoader()
        loader.save_fixtures_to_db(fixtures_pack=PACK,
                                   fixtures_dict=TEST_FIXTURES)

    def tearDown(self):
        for liveaction in LiveAction.get_all():
            action_service.update_status(
                liveaction, action_constants.LIVEACTION_STATUS_CANCELED)

    @mock.patch.object(
        runner.MockActionRunner, 'run',
        mock.MagicMock(
            return_value=(action_constants.LIVEACTION_STATUS_RUNNING, NON_EMPTY_RESULT, None)))
    # Use the nonblocking variant of the mock liveaction publisher, otherwise the concurrency
    # policy will try to acquire lock twice and hang because the liveaction publisher is
    # running in the same process.
    @mock.patch.object(
        LiveActionPublisher, 'publish_state',
        mock.MagicMock(side_effect=MockLiveActionPublisherNonBlocking.publish_state))
    def test_over_threshold_delay_executions(self):
        policy_db = Policy.get_by_ref('wolfpack.action-1.concurrency')
        self.assertGreater(policy_db.parameters['threshold'], 0)

        for i in range(0, policy_db.parameters['threshold']):
            liveaction = LiveActionDB(action='wolfpack.action-1', parameters={'actionstr': 'foo'})
            action_service.request(liveaction)

        # Since states are being processed asynchronously, wait for the
        # liveactions to go into scheduled states.
        for i in range(0, 100):
            eventlet.sleep(1)
            scheduled = [item for item in LiveAction.get_all() if item.status in SCHEDULED_STATES]
            if len(scheduled) == policy_db.parameters['threshold']:
                break

        scheduled = [item for item in LiveAction.get_all() if item.status in SCHEDULED_STATES]
        self.assertEqual(len(scheduled), policy_db.parameters['threshold'])

        # Assert the correct number of published states and action executions. This is to avoid
        # duplicate executions caused by accidental publishing of state in the concurrency policies.
        # num_state_changes = len(scheduled) * len(['requested', 'scheduled', 'running'])
        expected_num_exec = len(scheduled)
        expected_num_pubs = expected_num_exec * 3
        self.assertEqual(expected_num_pubs, LiveActionPublisher.publish_state.call_count)
        self.assertEqual(expected_num_exec, runner.MockActionRunner.run.call_count)

        # Execution is expected to be delayed since concurrency threshold is reached.
        liveaction = LiveActionDB(action='wolfpack.action-1', parameters={'actionstr': 'foo'})
        liveaction, _ = action_service.request(liveaction)
        expected_num_exec += 1  # This request is expected to be executed.
        expected_num_pubs += 1  # Tally requested state.

        # Since states are being processed asynchronously, wait for the
        # liveaction to go into delayed state.
        for i in range(0, 100):
            eventlet.sleep(1)
            liveaction = LiveAction.get_by_id(str(liveaction.id))
            if liveaction.status == action_constants.LIVEACTION_STATUS_DELAYED:
                break

        # Assert the action is delayed.
        liveaction = LiveAction.get_by_id(str(liveaction.id))
        self.assertEqual(liveaction.status, action_constants.LIVEACTION_STATUS_DELAYED)

        # Mark one of the execution as completed.
        action_service.update_status(
            scheduled[0], action_constants.LIVEACTION_STATUS_SUCCEEDED, publish=True)
        expected_num_pubs += 1  # Tally requested state.

        # Once capacity freed up, the delayed execution is published as requested again.
        expected_num_pubs += 3  # Tally requested, scheduled, and running state.

        # Since states are being processed asynchronously, wait for the
        # liveaction to go into scheduled state.
        for i in range(0, 100):
            eventlet.sleep(1)
            liveaction = LiveAction.get_by_id(str(liveaction.id))
            if liveaction.status in SCHEDULED_STATES:
                break

        # Execution is expected to be rescheduled.
        liveaction = LiveAction.get_by_id(str(liveaction.id))
        self.assertIn(liveaction.status, SCHEDULED_STATES)
        self.assertEqual(expected_num_pubs, LiveActionPublisher.publish_state.call_count)
        self.assertEqual(expected_num_exec, runner.MockActionRunner.run.call_count)

    @mock.patch.object(
        runner.MockActionRunner, 'run',
        mock.MagicMock(
            return_value=(action_constants.LIVEACTION_STATUS_RUNNING, NON_EMPTY_RESULT, None)))
    # Use the nonblocking variant of the mock liveaction publisher, otherwise the concurrency
    # policy will try to acquire lock twice and hang because the liveaction publisher is
    # running in the same process.
    @mock.patch.object(
        LiveActionPublisher, 'publish_state',
        mock.MagicMock(side_effect=MockLiveActionPublisherNonBlocking.publish_state))
    # policy will try to acquire lock twice and hang because the liveaction publisher is
    # running in the same process.
    @mock.patch.object(
        LiveActionPublisher, 'publish_update',
        mock.MagicMock(side_effect=MockExecutionPublisherNonBlocking.publish_update))
    def test_over_threshold_cancel_executions(self):
        policy_db = Policy.get_by_ref('wolfpack.action-2.concurrency.cancel')
        self.assertEqual(policy_db.parameters['action'], 'cancel')
        self.assertGreater(policy_db.parameters['threshold'], 0)

        for i in range(0, policy_db.parameters['threshold']):
            liveaction = LiveActionDB(action='wolfpack.action-2', parameters={'actionstr': 'foo'})
            action_service.request(liveaction)

        # Since states are being processed asynchronously, wait for the
        # liveactions to go into scheduled states.
        for i in range(0, 100):
            eventlet.sleep(1)
            scheduled = [item for item in LiveAction.get_all() if item.status in SCHEDULED_STATES]
            if len(scheduled) == policy_db.parameters['threshold']:
                break

        scheduled = [item for item in LiveAction.get_all() if item.status in SCHEDULED_STATES]
        self.assertEqual(len(scheduled), policy_db.parameters['threshold'])

        # duplicate executions caused by accidental publishing of state in the concurrency policies.
        # num_state_changes = len(scheduled) * len(['requested', 'scheduled', 'running'])
        expected_num_exec = len(scheduled)
        expected_num_pubs = expected_num_exec * 3
        self.assertEqual(expected_num_pubs, LiveActionPublisher.publish_state.call_count)
        self.assertEqual(expected_num_exec, runner.MockActionRunner.run.call_count)

        # Execution is expected to be canceled since concurrency threshold is reached.
        liveaction = LiveActionDB(action='wolfpack.action-2', parameters={'actionstr': 'foo'})
        liveaction, _ = action_service.request(liveaction)
        expected_num_exec += 0  # This request will not be scheduled for execution.
        expected_num_pubs += 1  # Tally requested state.

        # Since states are being processed asynchronously, wait for the
        # liveaction to go into cancel state.
        for i in range(0, 100):
            eventlet.sleep(1)
            liveaction = LiveAction.get_by_id(str(liveaction.id))
            if liveaction.status in [
                    action_constants.LIVEACTION_STATUS_CANCELING,
                    action_constants.LIVEACTION_STATUS_CANCELED]:
                break

        # Assert the canceling state is being published.
        calls = [call(liveaction, action_constants.LIVEACTION_STATUS_CANCELING)]
        LiveActionPublisher.publish_state.assert_has_calls(calls)
        expected_num_pubs += 2  # Tally canceling and canceled state changes.

        # Assert the action is canceled.
        liveaction = LiveAction.get_by_id(str(liveaction.id))
        self.assertEqual(liveaction.status, action_constants.LIVEACTION_STATUS_CANCELED)
        self.assertEqual(expected_num_pubs, LiveActionPublisher.publish_state.call_count)
        self.assertEqual(expected_num_exec, runner.MockActionRunner.run.call_count)

    @mock.patch.object(
        runner.MockActionRunner, 'run',
        mock.MagicMock(
            return_value=(action_constants.LIVEACTION_STATUS_RUNNING, NON_EMPTY_RESULT, None)))
    # Use the nonblocking variant of the mock liveaction publisher, otherwise the concurrency
    # policy will try to acquire lock twice and hang because the liveaction publisher is
    # running in the same process.
    @mock.patch.object(
        LiveActionPublisher, 'publish_state',
        mock.MagicMock(side_effect=MockLiveActionPublisherNonBlocking.publish_state))
    @mock.patch.object(
        ActionExecutionPublisher, 'publish_update',
        mock.MagicMock(side_effect=MockExecutionPublisherNonBlocking.publish_update))
    def test_on_cancellation(self):
        policy_db = Policy.get_by_ref('wolfpack.action-1.concurrency')
        self.assertGreater(policy_db.parameters['threshold'], 0)

        for i in range(0, policy_db.parameters['threshold']):
            liveaction = LiveActionDB(action='wolfpack.action-1', parameters={'actionstr': 'foo'})
            action_service.request(liveaction)

        # Since states are being processed asynchronously, wait for the
        # liveactions to go into scheduled states.
        for i in range(0, 100):
            eventlet.sleep(1)
            scheduled = [item for item in LiveAction.get_all() if item.status in SCHEDULED_STATES]
            if len(scheduled) == policy_db.parameters['threshold']:
                break

        scheduled = [item for item in LiveAction.get_all() if item.status in SCHEDULED_STATES]
        self.assertEqual(len(scheduled), policy_db.parameters['threshold'])

        # duplicate executions caused by accidental publishing of state in the concurrency policies.
        # num_state_changes = len(scheduled) * len(['requested', 'scheduled', 'running'])
        expected_num_exec = len(scheduled)
        expected_num_pubs = expected_num_exec * 3
        self.assertEqual(expected_num_pubs, LiveActionPublisher.publish_state.call_count)
        self.assertEqual(expected_num_exec, runner.MockActionRunner.run.call_count)

        # Execution is expected to be delayed since concurrency threshold is reached.
        liveaction = LiveActionDB(action='wolfpack.action-1', parameters={'actionstr': 'foo'})
        liveaction, _ = action_service.request(liveaction)
        expected_num_exec += 1  # This request will be scheduled for execution.
        expected_num_pubs += 1  # Tally requested state.

        # Since states are being processed asynchronously, wait for the
        # liveaction to go into delayed state.
        for i in range(0, 100):
            eventlet.sleep(1)
            liveaction = LiveAction.get_by_id(str(liveaction.id))
            if liveaction.status == action_constants.LIVEACTION_STATUS_DELAYED:
                break

        # Assert the action is delayed.
        liveaction = LiveAction.get_by_id(str(liveaction.id))
        self.assertEqual(liveaction.status, action_constants.LIVEACTION_STATUS_DELAYED)

        # Cancel execution.
        action_service.request_cancellation(scheduled[0], 'stanley')
        expected_num_pubs += 2  # Tally the canceling and canceled states.

        # Once capacity freed up, the delayed execution is published as requested again.
        expected_num_pubs += 3  # Tally requested, scheduled, and running state.

        # Since states are being processed asynchronously, wait for the
        # liveaction to go into scheduled state.
        for i in range(0, 100):
            eventlet.sleep(1)
            liveaction = LiveAction.get_by_id(str(liveaction.id))
            if liveaction.status in SCHEDULED_STATES:
                break

        # Execution is expected to be rescheduled.
        liveaction = LiveAction.get_by_id(str(liveaction.id))
        self.assertIn(liveaction.status, SCHEDULED_STATES)
        self.assertEqual(expected_num_pubs, LiveActionPublisher.publish_state.call_count)
        self.assertEqual(expected_num_exec, runner.MockActionRunner.run.call_count)

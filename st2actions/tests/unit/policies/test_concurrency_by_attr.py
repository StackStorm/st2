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

import mock
from mock import call

import st2common
from st2common.bootstrap.policiesregistrar import register_policy_types
from st2common.constants import action as action_constants
from st2common.models.db.action import LiveActionDB
from st2common.persistence.action import LiveAction
from st2common.persistence.policy import Policy
from st2common.services import action as action_service
from st2common.transport.liveaction import LiveActionPublisher
from st2common.transport.publishers import CUDPublisher
from st2tests import DbTestCase, EventletTestCase
from st2tests.fixturesloader import FixturesLoader
from st2tests.mocks.liveaction import MockLiveActionPublisher
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
        'policy_3.yaml',
        'policy_7.yaml'
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
    mock.MagicMock(side_effect=MockLiveActionPublisher.publish_update))
@mock.patch.object(
    CUDPublisher, 'publish_create',
    mock.MagicMock(return_value=None))
@mock.patch.object(
    LiveActionPublisher, 'publish_state',
    mock.MagicMock(side_effect=MockLiveActionPublisher.publish_state))
class ConcurrencyByAttributePolicyTest(EventletTestCase, DbTestCase):

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
    def test_over_threshold_delay_executions(self):
        policy_db = Policy.get_by_ref('wolfpack.action-1.concurrency.attr')
        self.assertGreater(policy_db.parameters['threshold'], 0)
        self.assertIn('actionstr', policy_db.parameters['attributes'])

        for i in range(0, policy_db.parameters['threshold']):
            liveaction = LiveActionDB(action='wolfpack.action-1', parameters={'actionstr': 'fu'})
            action_service.request(liveaction)

        scheduled = [item for item in LiveAction.get_all() if item.status in SCHEDULED_STATES]
        self.assertEqual(len(scheduled), policy_db.parameters['threshold'])
        self.assertEqual(len(scheduled), runner.MockActionRunner.run.call_count)

        # Execution is expected to be delayed since concurrency threshold is reached.
        liveaction = LiveActionDB(action='wolfpack.action-1', parameters={'actionstr': 'fu'})
        liveaction, _ = action_service.request(liveaction)

        # Assert the action is delayed.
        delayed = LiveAction.get_by_id(str(liveaction.id))
        self.assertEqual(delayed.status, action_constants.LIVEACTION_STATUS_DELAYED)
        self.assertEqual(len(scheduled), runner.MockActionRunner.run.call_count)

        # Execution is expected to be scheduled since concurrency threshold is not reached.
        # The execution with actionstr "fu" is over the threshold but actionstr "bar" is not.
        liveaction = LiveActionDB(action='wolfpack.action-1', parameters={'actionstr': 'bar'})
        liveaction, _ = action_service.request(liveaction)
        liveaction = LiveAction.get_by_id(str(liveaction.id))
        self.assertIn(liveaction.status, SCHEDULED_STATES)
        self.assertEqual(len(scheduled) + 1, runner.MockActionRunner.run.call_count)

        # Mark one of the execution as completed.
        action_service.update_status(
            scheduled[0], action_constants.LIVEACTION_STATUS_SUCCEEDED, publish=True)

        # Execution is expected to be rescheduled.
        liveaction = LiveAction.get_by_id(str(delayed.id))
        self.assertIn(liveaction.status, SCHEDULED_STATES)
        self.assertEqual(len(scheduled) + 2, runner.MockActionRunner.run.call_count)

    @mock.patch.object(
        runner.MockActionRunner, 'run',
        mock.MagicMock(
            return_value=(action_constants.LIVEACTION_STATUS_RUNNING, NON_EMPTY_RESULT, None)))
    def test_over_threshold_cancel_executions(self):
        policy_db = Policy.get_by_ref('wolfpack.action-2.concurrency.attr.cancel')
        self.assertEqual(policy_db.parameters['action'], 'cancel')
        self.assertGreater(policy_db.parameters['threshold'], 0)
        self.assertIn('actionstr', policy_db.parameters['attributes'])

        for i in range(0, policy_db.parameters['threshold']):
            liveaction = LiveActionDB(action='wolfpack.action-2', parameters={'actionstr': 'fu'})
            action_service.request(liveaction)

        scheduled = [item for item in LiveAction.get_all() if item.status in SCHEDULED_STATES]
        self.assertEqual(len(scheduled), policy_db.parameters['threshold'])
        self.assertEqual(len(scheduled), runner.MockActionRunner.run.call_count)

        # Execution is expected to be delayed since concurrency threshold is reached.
        liveaction = LiveActionDB(action='wolfpack.action-2', parameters={'actionstr': 'fu'})
        liveaction, _ = action_service.request(liveaction)

        # Assert the canceling state is being published.
        calls = [call(liveaction, action_constants.LIVEACTION_STATUS_CANCELING)]
        LiveActionPublisher.publish_state.assert_has_calls(calls)

        # Assert the action is canceled.
        canceled = LiveAction.get_by_id(str(liveaction.id))
        self.assertEqual(canceled.status, action_constants.LIVEACTION_STATUS_CANCELED)
        self.assertEqual(len(scheduled), runner.MockActionRunner.run.call_count)

    @mock.patch.object(
        runner.MockActionRunner, 'run',
        mock.MagicMock(
            return_value=(action_constants.LIVEACTION_STATUS_RUNNING, NON_EMPTY_RESULT, None)))
    def test_on_cancellation(self):
        policy_db = Policy.get_by_ref('wolfpack.action-1.concurrency.attr')
        self.assertGreater(policy_db.parameters['threshold'], 0)
        self.assertIn('actionstr', policy_db.parameters['attributes'])

        for i in range(0, policy_db.parameters['threshold']):
            liveaction = LiveActionDB(action='wolfpack.action-1', parameters={'actionstr': 'fu'})
            action_service.request(liveaction)

        scheduled = [item for item in LiveAction.get_all() if item.status in SCHEDULED_STATES]
        self.assertEqual(len(scheduled), policy_db.parameters['threshold'])
        self.assertEqual(len(scheduled), runner.MockActionRunner.run.call_count)

        # Execution is expected to be delayed since concurrency threshold is reached.
        liveaction = LiveActionDB(action='wolfpack.action-1', parameters={'actionstr': 'fu'})
        liveaction, _ = action_service.request(liveaction)
        delayed = LiveAction.get_by_id(str(liveaction.id))
        self.assertEqual(delayed.status, action_constants.LIVEACTION_STATUS_DELAYED)
        self.assertEqual(len(scheduled), runner.MockActionRunner.run.call_count)

        # Execution is expected to be scheduled since concurrency threshold is not reached.
        # The execution with actionstr "fu" is over the threshold but actionstr "bar" is not.
        liveaction = LiveActionDB(action='wolfpack.action-1', parameters={'actionstr': 'bar'})
        liveaction, _ = action_service.request(liveaction)
        liveaction = LiveAction.get_by_id(str(liveaction.id))
        self.assertIn(liveaction.status, SCHEDULED_STATES)
        self.assertEqual(len(scheduled) + 1, runner.MockActionRunner.run.call_count)

        # Cancel execution.
        action_service.request_cancellation(scheduled[0], 'stanley')

        # Execution is expected to be rescheduled.
        liveaction = LiveAction.get_by_id(str(delayed.id))
        self.assertIn(liveaction.status, SCHEDULED_STATES)
        self.assertEqual(len(scheduled) + 2, runner.MockActionRunner.run.call_count)

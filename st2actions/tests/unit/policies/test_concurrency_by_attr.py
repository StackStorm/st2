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
import six

from st2common.constants import action as action_constants
from st2common.models.api.action import ActionAPI, RunnerTypeAPI
from st2common.models.api.policy import PolicyTypeAPI, PolicyAPI
from st2common.models.db.action import LiveActionDB
from st2common.persistence.action import Action, LiveAction
from st2common.persistence.policy import PolicyType, Policy
from st2common.persistence.runner import RunnerType
from st2common.services import action as action_service
from st2common.transport.liveaction import LiveActionPublisher
from st2common.transport.publishers import CUDPublisher
from st2tests import DbTestCase, EventletTestCase
from st2tests.fixturesloader import FixturesLoader
from tests.unit.base import MockLiveActionPublisher
from tests.unit.test_runner import TestRunner


TEST_FIXTURES = {
    'runners': [
        'testrunner1.yaml'
    ],
    'actions': [
        'action1.yaml'
    ],
    'policytypes': [
        'policy_type_2.yaml'
    ],
    'policies': [
        'policy_3.yaml'
    ]
}

PACK = 'generic'
LOADER = FixturesLoader()
FIXTURES = LOADER.load_fixtures(fixtures_pack=PACK, fixtures_dict=TEST_FIXTURES)
NON_EMPTY_RESULT = 'non-empty'

SCHEDULED_STATES = [
    action_constants.LIVEACTION_STATUS_SCHEDULED,
    action_constants.LIVEACTION_STATUS_RUNNING,
    action_constants.LIVEACTION_STATUS_SUCCEEDED
]


def mock_run(action_parameters):
    eventlet.sleep(3)
    return (action_constants.LIVEACTION_STATUS_SUCCEEDED, NON_EMPTY_RESULT, None)


@mock.patch.object(
    TestRunner, 'run',
    mock.MagicMock(side_effect=mock_run))
@mock.patch.object(
    CUDPublisher, 'publish_update',
    mock.MagicMock(side_effect=MockLiveActionPublisher.publish_update))
@mock.patch.object(
    CUDPublisher, 'publish_create',
    mock.MagicMock(side_effect=MockLiveActionPublisher.publish_create))
@mock.patch.object(
    LiveActionPublisher, 'publish_state',
    mock.MagicMock(side_effect=MockLiveActionPublisher.publish_state))
class ConcurrencyByAttributePolicyTest(EventletTestCase, DbTestCase):

    @classmethod
    def setUpClass(cls):
        EventletTestCase.setUpClass()
        DbTestCase.setUpClass()

        for _, fixture in six.iteritems(FIXTURES['runners']):
            instance = RunnerTypeAPI(**fixture)
            RunnerType.add_or_update(RunnerTypeAPI.to_model(instance))

        for _, fixture in six.iteritems(FIXTURES['actions']):
            instance = ActionAPI(**fixture)
            Action.add_or_update(ActionAPI.to_model(instance))

        for _, fixture in six.iteritems(FIXTURES['policytypes']):
            instance = PolicyTypeAPI(**fixture)
            PolicyType.add_or_update(PolicyTypeAPI.to_model(instance))

        for _, fixture in six.iteritems(FIXTURES['policies']):
            instance = PolicyAPI(**fixture)
            Policy.add_or_update(PolicyAPI.to_model(instance))

    def test_over_threshold(self):
        policy_db = Policy.get_by_ref('wolfpack.action-1.concurrency.attr')

        for i in range(0, policy_db.parameters['threshold']):
            liveaction = LiveActionDB(action='wolfpack.action-1', parameters={'actionstr': 'foo'})
            eventlet.spawn(action_service.request, liveaction)

        # Sleep here to let the threads above schedule the action execution.
        eventlet.sleep(1)

        # Execution is expected to be delayed since concurrency threshold is reached.
        liveaction = LiveActionDB(action='wolfpack.action-1', parameters={'actionstr': 'foo'})
        liveaction, _ = action_service.request(liveaction)
        liveaction = LiveAction.get_by_id(str(liveaction.id))
        self.assertEqual(liveaction.status, action_constants.LIVEACTION_STATUS_DELAYED)

        # Execution is expected to be scheduled since concurrency threshold is not reached.
        # The execution with actionstr "foo" is over the threshold but actionstr "bar" is not.
        liveaction = LiveActionDB(action='wolfpack.action-1', parameters={'actionstr': 'bar'})
        liveaction, _ = action_service.request(liveaction)
        liveaction = LiveAction.get_by_id(str(liveaction.id))
        self.assertIn(liveaction.status, SCHEDULED_STATES)

        # Sleep here to let the threads above complete the action execution.
        eventlet.sleep(3)

        # Execution is expected to be rescheduled.
        liveaction = LiveAction.get_by_id(str(liveaction.id))
        self.assertIn(liveaction.status, SCHEDULED_STATES)

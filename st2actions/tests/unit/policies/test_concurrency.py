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

from st2common.constants import action as action_constants
from st2common.models.db.action import LiveActionDB
from st2common.persistence.action import LiveAction
from st2common.persistence.policy import Policy
from st2common.services import action as action_service
from st2common.transport.liveaction import LiveActionPublisher
from st2common.transport.publishers import CUDPublisher
from st2tests import DbTestCase, EventletTestCase
from st2tests.fixturesloader import FixturesLoader
from tests.unit.base import MockLiveActionPublisher
from tests.unit.test_runner import TestRunner

PACK = 'generic'
TEST_FIXTURES = {
    'runners': [
        'testrunner1.yaml'
    ],
    'actions': [
        'action1.yaml'
    ],
    'policytypes': [
        'policy_type_1.yaml'
    ],
    'policies': [
        'policy_1.yaml'
    ]
}

NON_EMPTY_RESULT = 'non-empty'

SCHEDULED_STATES = [
    action_constants.LIVEACTION_STATUS_SCHEDULED,
    action_constants.LIVEACTION_STATUS_RUNNING,
    action_constants.LIVEACTION_STATUS_SUCCEEDED
]


@mock.patch.object(
    TestRunner, 'run',
    mock.MagicMock(
        return_value=(action_constants.LIVEACTION_STATUS_RUNNING, NON_EMPTY_RESULT, None)))
@mock.patch.object(
    CUDPublisher, 'publish_update',
    mock.MagicMock(side_effect=MockLiveActionPublisher.publish_update))
@mock.patch.object(
    CUDPublisher, 'publish_create',
    mock.MagicMock(return_value=None))
@mock.patch.object(
    LiveActionPublisher, 'publish_state',
    mock.MagicMock(side_effect=MockLiveActionPublisher.publish_state))
class ConcurrencyPolicyTest(EventletTestCase, DbTestCase):

    @classmethod
    def setUpClass(cls):
        EventletTestCase.setUpClass()
        DbTestCase.setUpClass()

        loader = FixturesLoader()
        loader.save_fixtures_to_db(fixtures_pack=PACK,
                                   fixtures_dict=TEST_FIXTURES)

    def test_over_threshold(self):
        policy_db = Policy.get_by_ref('wolfpack.action-1.concurrency')
        self.assertGreater(policy_db.parameters['threshold'], 0)

        for i in range(0, policy_db.parameters['threshold']):
            liveaction = LiveActionDB(action='wolfpack.action-1', parameters={'actionstr': 'foo'})
            action_service.request(liveaction)

        scheduled = LiveAction.get_all()
        self.assertEqual(len(scheduled), policy_db.parameters['threshold'])
        for liveaction in scheduled:
            self.assertIn(liveaction.status, SCHEDULED_STATES)

        # Execution is expected to be delayed since concurrency threshold is reached.
        liveaction = LiveActionDB(action='wolfpack.action-1', parameters={'actionstr': 'foo'})
        liveaction, _ = action_service.request(liveaction)
        liveaction = LiveAction.get_by_id(str(liveaction.id))
        self.assertEqual(liveaction.status, action_constants.LIVEACTION_STATUS_DELAYED)

        # Mark one of the execution as completed.
        action_service.update_status(
            scheduled[0], action_constants.LIVEACTION_STATUS_SUCCEEDED, publish=True)

        # Execution is expected to be rescheduled.
        liveaction = LiveAction.get_by_id(str(liveaction.id))
        self.assertIn(liveaction.status, SCHEDULED_STATES)

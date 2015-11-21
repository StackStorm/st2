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

import st2actions
from st2common.constants.action import LIVEACTION_STATUS_REQUESTED
from st2common.constants.action import LIVEACTION_STATUS_SUCCEEDED
from st2common.constants.action import LIVEACTION_STATUS_TIMED_OUT
from st2common.bootstrap.policiesregistrar import register_policy_types
from st2common.models.db.action import LiveActionDB
from st2common.persistence.action import LiveAction, ActionExecution
from st2common.services import action as action_service
from st2actions.policies.retry import ExecutionRetryPolicyApplicator
from st2tests.base import DbTestCase
from st2tests.base import CleanDbTestCase
from st2tests.fixturesloader import FixturesLoader

PACK = 'generic'
TEST_FIXTURES = {
    'runners': [
        'testrunner1.yaml'
    ],
    'actions': [
        'action1.yaml'
    ],
    'policies': [
        'policy_4.yaml'
    ]
}


class RetryPolicyTestCase(CleanDbTestCase):
    @classmethod
    def setUpClass(cls):
        DbTestCase.setUpClass()
        super(RetryPolicyTestCase, cls).setUpClass()

    def setUp(self):
        super(RetryPolicyTestCase, self).setUp()

        # Register common policy types
        register_policy_types(st2actions)

        loader = FixturesLoader()
        models = loader.save_fixtures_to_db(fixtures_pack=PACK,
                                            fixtures_dict=TEST_FIXTURES)

        # Instantiate policy applicator we will use in the tests
        policy_db = models['policies']['policy_4.yaml']
        retry_on = policy_db.parameters['retry_on']
        max_retry_count = policy_db.parameters['max_retry_count']
        self.policy = ExecutionRetryPolicyApplicator(policy_ref='test_policy',
                                                     policy_type='action.retry',
                                                     retry_on=retry_on,
                                                     max_retry_count=max_retry_count,
                                                     delay=0)

    def test_retry_on_timeout_no_retry_since_no_timeout_reached(self):
        # Verify initial state
        self.assertSequenceEqual(LiveAction.get_all(), [])
        self.assertSequenceEqual(ActionExecution.get_all(), [])

        # Start a mock action which succeeds
        liveaction = LiveActionDB(action='wolfpack.action-1', parameters={'actionstr': 'foo'})
        live_action_db, execution_db = action_service.request(liveaction)

        live_action_db.status = LIVEACTION_STATUS_SUCCEEDED
        execution_db.status = LIVEACTION_STATUS_SUCCEEDED
        LiveAction.add_or_update(live_action_db)
        ActionExecution.add_or_update(execution_db)

        # Simulate policy "apply_after" run
        self.policy.apply_after(target=live_action_db)

        # There should only be 1 object since the action didn't timeout and therefore it wasn't
        # retried
        live_action_dbs = LiveAction.get_all()
        action_execution_dbs = ActionExecution.get_all()
        self.assertEqual(len(live_action_dbs), 1)
        self.assertEqual(len(action_execution_dbs), 1)
        self.assertEqual(action_execution_dbs[0].status, LIVEACTION_STATUS_SUCCEEDED)

    def test_retry_on_timeout_first_retry_is_successful(self):
        # Verify initial state
        self.assertSequenceEqual(LiveAction.get_all(), [])
        self.assertSequenceEqual(ActionExecution.get_all(), [])

        # Start a mock action which times out
        liveaction = LiveActionDB(action='wolfpack.action-1', parameters={'actionstr': 'foo'})
        live_action_db, execution_db = action_service.request(liveaction)

        live_action_db.status = LIVEACTION_STATUS_TIMED_OUT
        execution_db.status = LIVEACTION_STATUS_TIMED_OUT
        LiveAction.add_or_update(live_action_db)
        ActionExecution.add_or_update(execution_db)

        # Simulate policy "apply_after" run
        self.policy.apply_after(target=live_action_db)

        # There should be two objects - original execution and retried execution
        live_action_dbs = LiveAction.get_all()
        action_execution_dbs = ActionExecution.get_all()
        self.assertEqual(len(live_action_dbs), 2)
        self.assertEqual(len(action_execution_dbs), 2)
        self.assertEqual(action_execution_dbs[0].status, LIVEACTION_STATUS_TIMED_OUT)
        self.assertEqual(action_execution_dbs[1].status, LIVEACTION_STATUS_REQUESTED)

        # Simulate success of second action so no it shouldn't be retried anymore
        live_action_db = live_action_dbs[1]
        live_action_db.status = LIVEACTION_STATUS_SUCCEEDED
        LiveAction.add_or_update(live_action_db)

        # Simulate policy "apply_after" run
        self.policy.apply_after(target=live_action_db)

        # There should be no new object since action succeeds so no retry was attempted
        live_action_dbs = LiveAction.get_all()
        action_execution_dbs = ActionExecution.get_all()
        self.assertEqual(len(live_action_dbs), 2)
        self.assertEqual(len(action_execution_dbs), 2)
        self.assertEqual(live_action_dbs[0].status, LIVEACTION_STATUS_TIMED_OUT)
        self.assertEqual(live_action_dbs[1].status, LIVEACTION_STATUS_SUCCEEDED)

    def test_retry_on_timeout_max_retries_reached(self):
        # Verify initial state
        self.assertSequenceEqual(LiveAction.get_all(), [])
        self.assertSequenceEqual(ActionExecution.get_all(), [])

        # Start a mock action which times out
        liveaction = LiveActionDB(action='wolfpack.action-1', parameters={'actionstr': 'foo'})
        live_action_db, execution_db = action_service.request(liveaction)

        live_action_db.status = LIVEACTION_STATUS_TIMED_OUT
        live_action_db.context['policies'] = {}
        live_action_db.context['policies']['retry'] = {'retry_count': 2}
        execution_db.status = LIVEACTION_STATUS_TIMED_OUT
        LiveAction.add_or_update(live_action_db)
        ActionExecution.add_or_update(execution_db)

        # Simulate policy "apply_after" run
        self.policy.apply_after(target=live_action_db)

        # Note: There should be no new objects since max retries has been reached
        live_action_dbs = LiveAction.get_all()
        action_execution_dbs = ActionExecution.get_all()
        self.assertEqual(len(live_action_dbs), 1)
        self.assertEqual(len(action_execution_dbs), 1)
        self.assertEqual(action_execution_dbs[0].status, LIVEACTION_STATUS_TIMED_OUT)

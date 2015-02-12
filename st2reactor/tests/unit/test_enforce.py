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

import datetime
import mock

from st2common.models.db.reactor import TriggerInstanceDB
from st2common.models.db.action import ActionExecutionDB
from st2common.services import action as action_service
from st2common.util import reference
from st2reactor.rules.enforcer import RuleEnforcer
from st2tests import DbTestCase
from st2tests.fixturesloader import FixturesLoader

PACK = 'generic'
FIXTURES_1 = {
    'runners': ['testrunner1.json', 'testrunner2.json'],
    'actions': ['action1.json', 'a2.json'],
    'triggertypes': ['triggertype1.json'],
    'triggers': ['trigger1.json']
}
FIXTURES_2 = {
    'rules': ['rule1.json', 'rule2.json']
}

MOCK_TRIGGER_INSTANCE = TriggerInstanceDB()
MOCK_TRIGGER_INSTANCE.id = 'triggerinstance-test'
MOCK_TRIGGER_INSTANCE.payload = {'t1_p': 't1_p_v'}
MOCK_TRIGGER_INSTANCE.occurrence_time = datetime.datetime.utcnow()

MOCK_ACTION_EXECUTION = ActionExecutionDB()
MOCK_ACTION_EXECUTION.id = 'actionexec-test-1.id'
MOCK_ACTION_EXECUTION.name = 'actionexec-test-1.name'
MOCK_ACTION_EXECUTION.status = 'scheduled'


class EnforceTest(DbTestCase):

    models = None

    @classmethod
    def setUpClass(cls):
        super(EnforceTest, cls).setUpClass()
        # Create TriggerTypes before creation of Rule to avoid failure. Rule requires the
        # Trigger and therefore TriggerType to be created prior to rule creation.
        cls.models = FixturesLoader().save_fixtures_to_db(
            fixtures_pack=PACK, fixtures_dict=FIXTURES_1)
        cls.models.update(FixturesLoader().save_fixtures_to_db(
            fixtures_pack=PACK, fixtures_dict=FIXTURES_2))
        MOCK_TRIGGER_INSTANCE.trigger = reference.get_ref_from_model(
            cls.models['triggers']['trigger1.json'])

    @mock.patch.object(action_service, 'schedule', mock.MagicMock(
        return_value=MOCK_ACTION_EXECUTION))
    def test_ruleenforcement_occurs(self):
        enforcer = RuleEnforcer(MOCK_TRIGGER_INSTANCE, self.models['rules']['rule1.json'])
        execution_id = enforcer.enforce()
        self.assertTrue(execution_id is not None)

    @mock.patch.object(action_service, 'schedule', mock.MagicMock(
        return_value=MOCK_ACTION_EXECUTION))
    def test_ruleenforcement_casts(self):
        enforcer = RuleEnforcer(MOCK_TRIGGER_INSTANCE, self.models['rules']['rule2.json'])
        execution_id = enforcer.enforce()
        self.assertTrue(execution_id is not None)
        self.assertTrue(action_service.schedule.called)
        self.assertTrue(isinstance(action_service.schedule.call_args[0][0].parameters['objtype'],
                                   dict))

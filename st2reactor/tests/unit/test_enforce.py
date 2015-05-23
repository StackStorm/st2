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

from st2common.models.db.trigger import TriggerInstanceDB
from st2common.models.db.liveaction import LiveActionDB
from st2common.services import action as action_service
from st2common.util import reference
from st2reactor.rules.enforcer import RuleEnforcer
from st2tests import DbTestCase
from st2tests.fixturesloader import FixturesLoader

PACK = 'generic'
FIXTURES_1 = {
    'runners': ['testrunner1.yaml', 'testrunner2.yaml'],
    'actions': ['action1.yaml', 'a2.yaml'],
    'triggertypes': ['triggertype1.yaml'],
    'triggers': ['trigger1.yaml']
}
FIXTURES_2 = {
    'rules': ['rule1.yaml', 'rule2.yaml']
}

MOCK_TRIGGER_INSTANCE = TriggerInstanceDB()
MOCK_TRIGGER_INSTANCE.id = 'triggerinstance-test'
MOCK_TRIGGER_INSTANCE.payload = {'t1_p': 't1_p_v'}
MOCK_TRIGGER_INSTANCE.occurrence_time = datetime.datetime.utcnow()

MOCK_LIVEACTION = LiveActionDB()
MOCK_LIVEACTION.id = 'liveaction-test-1.id'
MOCK_LIVEACTION.name = 'liveaction-test-1.name'
MOCK_LIVEACTION.status = 'requested'


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
            cls.models['triggers']['trigger1.yaml'])

    @mock.patch.object(action_service, 'request', mock.MagicMock(
        return_value=(MOCK_LIVEACTION, None)))
    def test_ruleenforcement_occurs(self):
        enforcer = RuleEnforcer(MOCK_TRIGGER_INSTANCE, self.models['rules']['rule1.yaml'])
        liveaction_db = enforcer.enforce()
        self.assertTrue(liveaction_db is not None)

    @mock.patch.object(action_service, 'request', mock.MagicMock(
        return_value=(MOCK_LIVEACTION, None)))
    def test_ruleenforcement_casts(self):
        enforcer = RuleEnforcer(MOCK_TRIGGER_INSTANCE, self.models['rules']['rule2.yaml'])
        liveaction_db = enforcer.enforce()
        self.assertTrue(liveaction_db is not None)
        self.assertTrue(action_service.request.called)
        self.assertTrue(isinstance(action_service.request.call_args[0][0].parameters['objtype'],
                                   dict))

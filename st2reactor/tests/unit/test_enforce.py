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
import unittest2

from st2common.models.db.reactor import TriggerDB, TriggerInstanceDB, \
    RuleDB, ActionExecutionSpecDB
from st2common.models.db.action import ActionDB, LiveActionDB
import st2common.services.action as action_service
from st2common.util import reference
from st2reactor.rules.enforcer import RuleEnforcer
import st2tests.config as tests_config

MOCK_TRIGGER = TriggerDB()
MOCK_TRIGGER.id = 'trigger-test.id'
MOCK_TRIGGER.name = 'trigger-test.name'
MOCK_TRIGGER.pack = 'dummypack1'

MOCK_TRIGGER_INSTANCE = TriggerInstanceDB()
MOCK_TRIGGER_INSTANCE.id = 'triggerinstance-test'
MOCK_TRIGGER_INSTANCE.trigger = reference.get_ref_from_model(MOCK_TRIGGER)
MOCK_TRIGGER_INSTANCE.payload = {}
MOCK_TRIGGER_INSTANCE.occurrence_time = datetime.datetime.utcnow()

MOCK_ACTION = ActionDB()
MOCK_ACTION.id = 'action-test-1.id'
MOCK_ACTION.name = 'action-test-1.name'

MOCK_LIVEACTION = LiveActionDB()
MOCK_LIVEACTION.id = 'liveaction-test-1.id'
MOCK_LIVEACTION.name = 'liveaction-test-1.name'
MOCK_LIVEACTION.status = 'scheduled'

MOCK_RULE_1 = RuleDB()
MOCK_RULE_1.id = 'rule-test-1'
MOCK_RULE_1.trigger = reference.get_str_resource_ref_from_model(MOCK_TRIGGER)
MOCK_RULE_1.criteria = {}
MOCK_RULE_1.action = ActionExecutionSpecDB()
MOCK_RULE_1.action.ref = reference.get_ref_from_model(MOCK_ACTION)
MOCK_RULE_1.enabled = True

MOCK_RULE_2 = RuleDB()
MOCK_RULE_2.id = 'rule-test-2'
MOCK_RULE_2.trigger = reference.get_str_resource_ref_from_model(MOCK_TRIGGER)
MOCK_RULE_2.criteria = {}
MOCK_RULE_2.action = ActionExecutionSpecDB()
MOCK_RULE_2.action.ref = reference.get_ref_from_model(MOCK_ACTION)
MOCK_RULE_2.enabled = True


class EnforceTest(unittest2.TestCase):

    @classmethod
    def setUpClass(cls):
        tests_config.parse_args()

    @mock.patch.object(action_service, 'schedule', mock.MagicMock(
        return_value=MOCK_LIVEACTION))
    def test_ruleenforcement_occurs(self):
        enforcer = RuleEnforcer(MOCK_TRIGGER_INSTANCE, MOCK_RULE_1)
        execution_id = enforcer.enforce()
        self.assertTrue(execution_id is not None)

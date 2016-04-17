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

from st2common.models.db.trigger import TriggerInstanceDB
from st2common.models.db.execution import ActionExecutionDB
from st2common.models.db.liveaction import LiveActionDB
from st2common.persistence.rule_enforcement import RuleEnforcement
from st2common.services import action as action_service
from st2common.util import casts
from st2common.util import reference
from st2common.util import date as date_utils
from st2common.util.jinja import NONE_MAGIC_VALUE
from st2reactor.rules.enforcer import RuleEnforcer
from st2tests import DbTestCase
from st2tests.fixturesloader import FixturesLoader

PACK = 'generic'
FIXTURES_1 = {
    'runners': ['testrunner1.yaml', 'testrunner2.yaml'],
    'actions': ['action1.yaml', 'a2.yaml'],
    'triggertypes': ['triggertype1.yaml'],
    'triggers': ['trigger1.yaml'],
    'traces': ['trace_for_test_enforce.yaml', 'trace_for_test_enforce_2.yaml',
               'trace_for_test_enforce_3.yaml']
}
FIXTURES_2 = {
    'rules': ['rule1.yaml', 'rule2.yaml', 'rule_use_none_filter.yaml',
              'rule_none_no_use_none_filter.yaml']
}

MOCK_TRIGGER_INSTANCE = TriggerInstanceDB()
MOCK_TRIGGER_INSTANCE.id = 'triggerinstance-test'
MOCK_TRIGGER_INSTANCE.payload = {'t1_p': 't1_p_v'}
MOCK_TRIGGER_INSTANCE.occurrence_time = date_utils.get_datetime_utc_now()

MOCK_TRIGGER_INSTANCE_2 = TriggerInstanceDB()
MOCK_TRIGGER_INSTANCE_2.id = 'triggerinstance-test2'
MOCK_TRIGGER_INSTANCE_2.payload = {'t1_p': None}
MOCK_TRIGGER_INSTANCE_2.occurrence_time = date_utils.get_datetime_utc_now()

MOCK_TRIGGER_INSTANCE_3 = TriggerInstanceDB()
MOCK_TRIGGER_INSTANCE_3.id = 'triggerinstance-test3'
MOCK_TRIGGER_INSTANCE_3.payload = {'t1_p': None, 't2_p': 'value2'}
MOCK_TRIGGER_INSTANCE_3.occurrence_time = date_utils.get_datetime_utc_now()

MOCK_LIVEACTION = LiveActionDB()
MOCK_LIVEACTION.id = 'liveaction-test-1.id'
MOCK_LIVEACTION.status = 'requested'

MOCK_EXECUTION = ActionExecutionDB()
MOCK_EXECUTION.id = 'exec-test-1.id'
MOCK_EXECUTION.status = 'requested'

FAILURE_REASON = "fail!"


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
        return_value=(MOCK_LIVEACTION, MOCK_EXECUTION)))
    def test_ruleenforcement_occurs(self):
        enforcer = RuleEnforcer(MOCK_TRIGGER_INSTANCE, self.models['rules']['rule1.yaml'])
        execution_db = enforcer.enforce()
        self.assertTrue(execution_db is not None)

    @mock.patch.object(action_service, 'request', mock.MagicMock(
        return_value=(MOCK_LIVEACTION, MOCK_EXECUTION)))
    def test_ruleenforcement_casts(self):
        enforcer = RuleEnforcer(MOCK_TRIGGER_INSTANCE, self.models['rules']['rule2.yaml'])
        execution_db = enforcer.enforce()
        self.assertTrue(execution_db is not None)
        self.assertTrue(action_service.request.called)
        self.assertTrue(isinstance(action_service.request.call_args[0][0].parameters['objtype'],
                                   dict))

    @mock.patch.object(action_service, 'request', mock.MagicMock(
        return_value=(MOCK_LIVEACTION, MOCK_EXECUTION)))
    @mock.patch.object(RuleEnforcement, 'add_or_update', mock.MagicMock())
    def test_ruleenforcement_create_on_success(self):
        enforcer = RuleEnforcer(MOCK_TRIGGER_INSTANCE, self.models['rules']['rule2.yaml'])
        execution_db = enforcer.enforce()
        self.assertTrue(execution_db is not None)
        self.assertTrue(RuleEnforcement.add_or_update.called)
        self.assertEqual(RuleEnforcement.add_or_update.call_args[0][0].rule.ref,
                         self.models['rules']['rule2.yaml'].ref)

    @mock.patch.object(action_service, 'request', mock.MagicMock(
        return_value=(MOCK_LIVEACTION, MOCK_EXECUTION)))
    @mock.patch.object(RuleEnforcement, 'add_or_update', mock.MagicMock())
    def test_rule_enforcement_create_rule_none_param_casting(self):
        mock_trigger_instance = MOCK_TRIGGER_INSTANCE_2

        # 1. Non None value, should be serialized as regular string
        mock_trigger_instance.payload = {'t1_p': 'somevalue'}

        def mock_cast_string(x):
            assert x == 'somevalue'
            return casts._cast_string(x)
        casts.CASTS['string'] = mock_cast_string

        enforcer = RuleEnforcer(mock_trigger_instance,
                                self.models['rules']['rule_use_none_filter.yaml'])
        execution_db = enforcer.enforce()

        # Verify value has been serialized correctly
        call_args = action_service.request.call_args[0]
        live_action_db = call_args[0]
        self.assertEqual(live_action_db.parameters['actionstr'], 'somevalue')
        self.assertTrue(execution_db is not None)
        self.assertTrue(RuleEnforcement.add_or_update.called)
        self.assertEqual(RuleEnforcement.add_or_update.call_args[0][0].rule.ref,
                         self.models['rules']['rule_use_none_filter.yaml'].ref)

        # 2. Verify that None type from trigger instance is correctly serialized to
        # None when using "use_none" Jinja filter when invoking an action
        mock_trigger_instance.payload = {'t1_p': None}

        def mock_cast_string(x):
            assert x == NONE_MAGIC_VALUE
            return casts._cast_string(x)
        casts.CASTS['string'] = mock_cast_string

        enforcer = RuleEnforcer(mock_trigger_instance,
                                self.models['rules']['rule_use_none_filter.yaml'])
        execution_db = enforcer.enforce()

        # Verify None has been correctly serialized to None
        call_args = action_service.request.call_args[0]
        live_action_db = call_args[0]
        self.assertEqual(live_action_db.parameters['actionstr'], None)
        self.assertTrue(execution_db is not None)
        self.assertTrue(RuleEnforcement.add_or_update.called)
        self.assertEqual(RuleEnforcement.add_or_update.call_args[0][0].rule.ref,
                         self.models['rules']['rule_use_none_filter.yaml'].ref)

        casts.CASTS['string'] = casts._cast_string

        # 3. Parameter value is a compound string one of which values is None, but "use_none"
        # filter is not used
        mock_trigger_instance = MOCK_TRIGGER_INSTANCE_3
        mock_trigger_instance.payload = {'t1_p': None, 't2_p': 'value2'}

        enforcer = RuleEnforcer(mock_trigger_instance,
                                self.models['rules']['rule_none_no_use_none_filter.yaml'])
        execution_db = enforcer.enforce()

        # Verify None has been correctly serialized to None
        call_args = action_service.request.call_args[0]
        live_action_db = call_args[0]
        self.assertEqual(live_action_db.parameters['actionstr'], 'None-value2')
        self.assertTrue(execution_db is not None)
        self.assertTrue(RuleEnforcement.add_or_update.called)
        self.assertEqual(RuleEnforcement.add_or_update.call_args[0][0].rule.ref,
                         self.models['rules']['rule_none_no_use_none_filter.yaml'].ref)

        casts.CASTS['string'] = casts._cast_string

    @mock.patch.object(action_service, 'request', mock.MagicMock(
        side_effect=ValueError(FAILURE_REASON)))
    @mock.patch.object(RuleEnforcement, 'add_or_update', mock.MagicMock())
    def test_ruleenforcement_create_on_fail(self):
        enforcer = RuleEnforcer(MOCK_TRIGGER_INSTANCE, self.models['rules']['rule1.yaml'])
        execution_db = enforcer.enforce()
        self.assertTrue(execution_db is None)
        self.assertTrue(RuleEnforcement.add_or_update.called)
        self.assertEqual(RuleEnforcement.add_or_update.call_args[0][0].failure_reason,
                         FAILURE_REASON)

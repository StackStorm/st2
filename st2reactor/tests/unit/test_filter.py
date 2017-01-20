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

import bson
import copy
import mock

from st2common.models.db.action import ActionDB
from st2common.models.db.rule import RuleDB, ActionExecutionSpecDB
from st2common.models.db.trigger import TriggerDB, TriggerInstanceDB
from st2common.util import reference
from st2common.util import date as date_utils
from st2reactor.rules.filter import RuleFilter
from st2tests import DbTestCase


MOCK_TRIGGER = TriggerDB(pack='dummy_pack_1', name='trigger-test.name', type='system.test')

MOCK_TRIGGER_INSTANCE = TriggerInstanceDB(trigger=MOCK_TRIGGER.get_reference().ref,
                                          occurrence_time=date_utils.get_datetime_utc_now(),
                                          payload={
                                              'p1': 'v1',
                                              'p2': 'preYYYpost',
                                              'bool': True,
                                              'int': 1,
                                              'float': 0.8})

MOCK_ACTION = ActionDB(id=bson.ObjectId(), pack='wolfpack', name='action-test-1.name')

MOCK_RULE_1 = RuleDB(id=bson.ObjectId(), pack='wolfpack', name='some1',
                     trigger=reference.get_str_resource_ref_from_model(MOCK_TRIGGER),
                     criteria={}, action=ActionExecutionSpecDB(ref="somepack.someaction"))

MOCK_RULE_2 = RuleDB(id=bson.ObjectId(), pack='wolfpack', name='some2',
                     trigger=reference.get_str_resource_ref_from_model(MOCK_TRIGGER),
                     criteria={}, action=ActionExecutionSpecDB(ref="somepack.someaction"))


@mock.patch.object(reference, 'get_model_by_resource_ref',
                   mock.MagicMock(return_value=MOCK_TRIGGER))
class FilterTest(DbTestCase):
    def test_empty_criteria(self):
        rule = MOCK_RULE_1
        rule.criteria = {}
        f = RuleFilter(MOCK_TRIGGER_INSTANCE, MOCK_TRIGGER, rule)
        self.assertTrue(f.filter(), 'equals check should have failed.')

    def test_empty_payload(self):
        rule = MOCK_RULE_1
        rule.criteria = {'trigger.p1': {'type': 'equals', 'pattern': 'v1'}}
        trigger_instance = copy.deepcopy(MOCK_TRIGGER_INSTANCE)
        trigger_instance.payload = None
        f = RuleFilter(trigger_instance, MOCK_TRIGGER, rule)
        self.assertFalse(f.filter(), 'equals check should have failed.')

    def test_empty_criteria_and_empty_payload(self):
        rule = MOCK_RULE_1
        rule.criteria = {}
        trigger_instance = copy.deepcopy(MOCK_TRIGGER_INSTANCE)
        trigger_instance.payload = None
        f = RuleFilter(trigger_instance, MOCK_TRIGGER, rule)
        self.assertTrue(f.filter(), 'equals check should have failed.')

    def test_matchregex_operator_pass_criteria(self):
        rule = MOCK_RULE_1
        rule.criteria = {'trigger.p1': {'type': 'matchregex', 'pattern': 'v1$'}}
        f = RuleFilter(MOCK_TRIGGER_INSTANCE, MOCK_TRIGGER, rule)
        self.assertTrue(f.filter(), 'Failed to pass evaluation.')

    def test_matchregex_operator_fail_criteria(self):
        rule = MOCK_RULE_1
        rule.criteria = {'trigger.p1': {'type': 'matchregex', 'pattern': 'v$'}}
        f = RuleFilter(MOCK_TRIGGER_INSTANCE, MOCK_TRIGGER, rule)
        self.assertFalse(f.filter(), 'regex check should have failed.')

    def test_equals_operator_pass_criteria(self):
        rule = MOCK_RULE_1
        rule.criteria = {'trigger.p1': {'type': 'equals', 'pattern': 'v1'}}
        f = RuleFilter(MOCK_TRIGGER_INSTANCE, MOCK_TRIGGER, rule)
        self.assertTrue(f.filter(), 'regex check should have failed.')

    def test_equals_operator_fail_criteria(self):
        rule = MOCK_RULE_1
        rule.criteria = {'trigger.p1': {'type': 'equals', 'pattern': 'v'}}
        f = RuleFilter(MOCK_TRIGGER_INSTANCE, MOCK_TRIGGER, rule)
        self.assertFalse(f.filter(), 'equals check should have failed.')

    def test_equals_bool_value(self):
        rule = MOCK_RULE_1
        rule.criteria = {'trigger.bool': {'type': 'equals', 'pattern': True}}
        f = RuleFilter(MOCK_TRIGGER_INSTANCE, MOCK_TRIGGER, rule)
        self.assertTrue(f.filter(), 'equals check should have passed.')

    def test_equals_int_value(self):
        rule = MOCK_RULE_1
        rule.criteria = {'trigger.int': {'type': 'equals', 'pattern': 1}}
        f = RuleFilter(MOCK_TRIGGER_INSTANCE, MOCK_TRIGGER, rule)
        self.assertTrue(f.filter(), 'equals check should have passed.')

    def test_equals_float_value(self):
        rule = MOCK_RULE_1
        rule.criteria = {'trigger.float': {'type': 'equals', 'pattern': 0.8}}
        f = RuleFilter(MOCK_TRIGGER_INSTANCE, MOCK_TRIGGER, rule)
        self.assertTrue(f.filter(), 'equals check should have passed.')

    def test_exists(self):
        rule = MOCK_RULE_1
        rule.criteria = {'trigger.float': {'type': 'exists'}}
        f = RuleFilter(MOCK_TRIGGER_INSTANCE, MOCK_TRIGGER, rule)
        self.assertTrue(f.filter(), '"float" key exists in trigger. Should return true.')
        rule.criteria = {'trigger.floattt': {'type': 'exists'}}
        f = RuleFilter(MOCK_TRIGGER_INSTANCE, MOCK_TRIGGER, rule)
        self.assertFalse(f.filter(), '"floattt" key ain\'t exist in trigger. Should return false.')

    def test_nexists(self):
        rule = MOCK_RULE_1
        rule.criteria = {'trigger.float': {'type': 'nexists'}}
        f = RuleFilter(MOCK_TRIGGER_INSTANCE, MOCK_TRIGGER, rule)
        self.assertFalse(f.filter(), '"float" key exists in trigger. Should return false.')
        rule.criteria = {'trigger.floattt': {'type': 'nexists'}}
        f = RuleFilter(MOCK_TRIGGER_INSTANCE, MOCK_TRIGGER, rule)
        self.assertTrue(f.filter(), '"floattt" key ain\'t exist in trigger. Should return true.')

    def test_gt_lt_falsy_pattern(self):
        # Make sure that the falsy value (number 0) is handled correctly
        rule = MOCK_RULE_1

        rule.criteria = {'trigger.int': {'type': 'gt', 'pattern': 0}}
        f = RuleFilter(MOCK_TRIGGER_INSTANCE, MOCK_TRIGGER, rule)
        self.assertTrue(f.filter(), 'trigger value is gt than 0 but didn\'t match')

        rule.criteria = {'trigger.int': {'type': 'lt', 'pattern': 0}}
        f = RuleFilter(MOCK_TRIGGER_INSTANCE, MOCK_TRIGGER, rule)
        self.assertFalse(f.filter(), 'trigger value is gt than 0 but didn\'t fail')

    @mock.patch('st2common.util.templating.KeyValueLookup')
    def test_criteria_pattern_references_a_datastore_item(self, mock_KeyValueLookup):
        class MockResultLookup(object):
            pass

        class MockSystemLookup(object):
            system = MockResultLookup()

        rule = MOCK_RULE_2

        # Using a variable in pattern, referencing an inexistent datastore value
        rule.criteria = {'trigger.p1': {
            'type': 'equals',
            'pattern': '{{ st2kv.system.inexistent_value }}'}
        }
        f = RuleFilter(MOCK_TRIGGER_INSTANCE, MOCK_TRIGGER, rule)
        self.assertFalse(f.filter())

        # Using a variable in pattern, referencing an existing value which doesn't match
        mock_result = MockSystemLookup()
        mock_result.test_value_1 = 'non matching'
        mock_KeyValueLookup.return_value = mock_result

        rule.criteria = {
            'trigger.p1': {
                'type': 'equals',
                'pattern': '{{ st2kv.system.test_value_1 }}'
            }
        }
        f = RuleFilter(MOCK_TRIGGER_INSTANCE, MOCK_TRIGGER, rule)
        self.assertFalse(f.filter())

        # Using a variable in pattern, referencing an existing value which does match
        mock_result = MockSystemLookup()
        mock_result.test_value_2 = 'v1'
        mock_KeyValueLookup.return_value = mock_result

        rule.criteria = {
            'trigger.p1': {
                'type': 'equals',
                'pattern': '{{ st2kv.system.test_value_2 }}'
            }
        }
        f = RuleFilter(MOCK_TRIGGER_INSTANCE, MOCK_TRIGGER, rule)
        self.assertTrue(f.filter())

        # Using a variable in pattern, referencing an existing value which matches partially
        mock_result = MockSystemLookup()
        mock_result.test_value_3 = 'YYY'
        mock_KeyValueLookup.return_value = mock_result

        rule.criteria = {
            'trigger.p2': {
                'type': 'equals',
                'pattern': '{{ st2kv.system.test_value_3 }}'
            }
        }
        f = RuleFilter(MOCK_TRIGGER_INSTANCE, MOCK_TRIGGER, rule)
        self.assertFalse(f.filter())

        # Using a variable in pattern, referencing an existing value which matches partially
        mock_result = MockSystemLookup()
        mock_result.test_value_3 = 'YYY'
        mock_KeyValueLookup.return_value = mock_result

        rule.criteria = {
            'trigger.p2': {
                'type': 'equals',
                'pattern': 'pre{{ st2kv.system.test_value_3 }}post'
            }
        }
        f = RuleFilter(MOCK_TRIGGER_INSTANCE, MOCK_TRIGGER, rule)
        self.assertTrue(f.filter())

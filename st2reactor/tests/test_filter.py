import datetime
import unittest2
from st2common.models.db.reactor import TriggerDB, TriggerInstanceDB, \
    RuleDB, ActionExecutionSpecDB
from st2common.models.db.action import ActionDB
from st2common.util import reference
from st2reactor.rules.filter import RuleFilter

MOCK_TRIGGER = TriggerDB()
MOCK_TRIGGER.id = 'trigger-test.id'
MOCK_TRIGGER.name = 'trigger-test.name'

MOCK_TRIGGER_INSTANCE = TriggerInstanceDB()
MOCK_TRIGGER_INSTANCE.id = 'triggerinstance-test'
MOCK_TRIGGER_INSTANCE.trigger = reference.get_ref_from_model(MOCK_TRIGGER)
MOCK_TRIGGER_INSTANCE.payload = {'trigger.p1': 'v1'}
MOCK_TRIGGER_INSTANCE.occurrence_time = datetime.datetime.now()

MOCK_ACTION = ActionDB()
MOCK_ACTION.id = 'action-test-1.id'
MOCK_ACTION.name = 'action-test-1.name'

MOCK_RULE_1 = RuleDB()
MOCK_RULE_1.id = 'rule-test-1'
MOCK_RULE_1.trigger = reference.get_ref_from_model(MOCK_TRIGGER)
MOCK_RULE_1.criteria = {}
MOCK_RULE_1.action = ActionExecutionSpecDB()
MOCK_RULE_1.action.action = reference.get_ref_from_model(MOCK_ACTION)

MOCK_RULE_2 = RuleDB()
MOCK_RULE_2.id = 'rule-test-2'
MOCK_RULE_2.trigger = reference.get_ref_from_model(MOCK_TRIGGER)
MOCK_RULE_2.criteria = {}
MOCK_RULE_2.action = ActionExecutionSpecDB()
MOCK_RULE_2.action.action = reference.get_ref_from_model(MOCK_ACTION)


class FilterTest(unittest2.TestCase):

    def test_matchregex_operator_pass_criteria(self):
        rule = MOCK_RULE_1
        rule.criteria = {'trigger.p1': {'type': 'matchregex', 'pattern': 'v1$'}}
        f = RuleFilter(MOCK_TRIGGER_INSTANCE, rule)
        self.assertTrue(f.filter(), 'Failed to pass evaluation.')

    def test_matchregex_operator_fail_criteria(self):
        rule = MOCK_RULE_1
        rule.criteria = {'trigger.p1': {'type': 'matchregex', 'pattern': 'v$'}}
        f = RuleFilter(MOCK_TRIGGER_INSTANCE, rule)
        self.assertFalse(f.filter(), 'regex check should have failed.')

    def test_equals_operator_pass_criteria(self):
        rule = MOCK_RULE_1
        rule.criteria = {'trigger.p1': {'type': 'equals', 'pattern': 'v1'}}
        f = RuleFilter(MOCK_TRIGGER_INSTANCE, rule)
        self.assertTrue(f.filter(), 'regex check should have failed.')

    def test_equals_operator_fail_criteria(self):
        rule = MOCK_RULE_1
        rule.criteria = {'trigger.p1': {'type': 'equals', 'pattern': 'v'}}
        f = RuleFilter(MOCK_TRIGGER_INSTANCE, rule)
        self.assertFalse(f.filter(), 'equals check should have failed.')

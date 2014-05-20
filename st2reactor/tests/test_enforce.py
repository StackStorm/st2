import datetime
import mock
import tests
import unittest2
from st2common.persistence.reactor import Rule, RuleEnforcement
from st2common.models.db.reactor import TriggerDB, TriggerInstanceDB, RuleDB
from st2reactor.ruleenforcement.enforce import RuleEnforcer

MOCK_TRIGGER = TriggerDB()
MOCK_TRIGGER.id = 'trigger-test'

MOCK_TRIGGER_INSTANCE = TriggerInstanceDB()
MOCK_TRIGGER_INSTANCE.id = 'triggerinstance-test'
MOCK_TRIGGER_INSTANCE.trigger = MOCK_TRIGGER
MOCK_TRIGGER_INSTANCE.payload = {}
MOCK_TRIGGER_INSTANCE.occurrence_time = datetime.datetime.now()

MOCK_RULE_1 = RuleDB()
MOCK_RULE_1.id = 'rule-test-1'
MOCK_RULE_1.trigger = MOCK_TRIGGER
MOCK_RULE_1.staction = None

MOCK_RULE_2 = RuleDB()
MOCK_RULE_2.id = 'rule-test-2'
MOCK_RULE_2.trigger = MOCK_TRIGGER
MOCK_RULE_2.staction = None


class EnforceTest(unittest2.TestCase):
    def setUp(self):
        tests.parse_args()

    @mock.patch.object(Rule, 'query', mock.MagicMock(
        return_value=[MOCK_RULE_1]))
    @mock.patch.object(RuleEnforcement, 'add_or_update')
    def test_single_ruleenforcement_creation(self, mock_ruleenforcement_add):
        enforcer = RuleEnforcer(MOCK_TRIGGER_INSTANCE)
        enforcer.enforce()
        self.assertEqual(mock_ruleenforcement_add.call_count, 1,
                         'Expected RuleEnforcement(s) not added.')

    @mock.patch.object(Rule, 'query', mock.MagicMock(
        return_value=[MOCK_RULE_1, MOCK_RULE_2]))
    @mock.patch.object(RuleEnforcement, 'add_or_update')
    def test_multiple_ruleenforcement_creation(
            self, mock_ruleenforcement_add):
        enforcer = RuleEnforcer(MOCK_TRIGGER_INSTANCE)
        enforcer.enforce()
        self.assertEqual(mock_ruleenforcement_add.call_count, 2,
                         'Expected RuleEnforcement(s) not added.')

    @mock.patch.object(Rule, 'query', mock.MagicMock(
        return_value=[MOCK_RULE_1, MOCK_RULE_2]))
    @mock.patch.object(RuleEnforcement, 'add_or_update', mock.MagicMock())
    @mock.patch.object(RuleEnforcer, '_RuleEnforcer__invoke_staction')
    def test_staction_execution(self, mock_ruleenforcer_invokestaction):
        enforcer = RuleEnforcer(MOCK_TRIGGER_INSTANCE)
        enforcer.enforce()
        self.assertEqual(mock_ruleenforcer_invokestaction.call_count, 2,
                         'Expected no of invokes not called.')
import datetime
import mock
import unittest2
from st2common.persistence.reactor import RuleEnforcement
from st2common.models.db.reactor import TriggerDB, TriggerInstanceDB, \
    RuleDB, ActionExecutionSpecDB
from st2common.models.db.action import ActionDB, ActionExecutionDB
from st2common.util import reference
from st2reactor.rules.enforcer import RuleEnforcer

MOCK_TRIGGER = TriggerDB()
MOCK_TRIGGER.id = 'trigger-test.id'
MOCK_TRIGGER.name = 'trigger-test.name'

MOCK_TRIGGER_INSTANCE = TriggerInstanceDB()
MOCK_TRIGGER_INSTANCE.id = 'triggerinstance-test'
MOCK_TRIGGER_INSTANCE.trigger = reference.get_ref_from_model(MOCK_TRIGGER)
MOCK_TRIGGER_INSTANCE.payload = {}
MOCK_TRIGGER_INSTANCE.occurrence_time = datetime.datetime.now()

MOCK_ACTION = ActionDB()
MOCK_ACTION.id = 'action-test-1.id'
MOCK_ACTION.name = 'action-test-1.name'

MOCK_ACTION_EXECUTION = ActionExecutionDB()
MOCK_ACTION_EXECUTION.id = 'actionexec-test-1.id'
MOCK_ACTION_EXECUTION.name = 'actionexec-test-1.name'

MOCK_RULE_1 = RuleDB()
MOCK_RULE_1.id = 'rule-test-1'
MOCK_RULE_1.trigger = reference.get_ref_from_model(MOCK_TRIGGER)
MOCK_RULE_1.criteria = {}
MOCK_RULE_1.action = ActionExecutionSpecDB()
MOCK_RULE_1.action.action = reference.get_ref_from_model(MOCK_ACTION)
MOCK_RULE_1.enabled = True

MOCK_RULE_2 = RuleDB()
MOCK_RULE_2.id = 'rule-test-2'
MOCK_RULE_2.trigger = reference.get_ref_from_model(MOCK_TRIGGER)
MOCK_RULE_2.criteria = {}
MOCK_RULE_2.action = ActionExecutionSpecDB()
MOCK_RULE_2.action.action = reference.get_ref_from_model(MOCK_ACTION)
MOCK_RULE_2.enabled = True


class EnforceTest(unittest2.TestCase):

    @mock.patch.object(RuleEnforcement, 'add_or_update')
    @mock.patch.object(RuleEnforcer, '_invoke_action', mock.MagicMock(
        return_value=reference.get_ref_from_model(MOCK_ACTION_EXECUTION)))
    def test_ruleenforcement_creation(self, mock_ruleenforcement_add):
        enforcer = RuleEnforcer(MOCK_TRIGGER_INSTANCE, MOCK_RULE_1)
        enforcer.enforce()
        self.assertEqual(mock_ruleenforcement_add.call_count, 1,
                         'Expected RuleEnforcement(s) not added.')

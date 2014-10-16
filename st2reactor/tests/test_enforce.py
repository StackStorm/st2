import bson
import datetime

import mock
import unittest2

from st2common.persistence.reactor import RuleEnforcement
from st2common.models.db.reactor import TriggerDB, TriggerInstanceDB, \
    RuleDB, ActionExecutionSpecDB
from st2common.models.db.action import ActionDB, ActionExecutionDB
from st2common.util import reference
from st2reactor.rules.enforcer import RuleEnforcer
import st2tests.config as tests_config

MOCK_TRIGGER = TriggerDB()
MOCK_TRIGGER.id = bson.ObjectId()
MOCK_TRIGGER.name = 'trigger-test.name'
MOCK_TRIGGER.type = {'name': 'trigger-test'}

MOCK_TRIGGER_INSTANCE = TriggerInstanceDB()
MOCK_TRIGGER_INSTANCE.id = bson.ObjectId()
MOCK_TRIGGER_INSTANCE.trigger = reference.get_ref_from_model(MOCK_TRIGGER)
MOCK_TRIGGER_INSTANCE.payload = {}
MOCK_TRIGGER_INSTANCE.occurrence_time = datetime.datetime.utcnow()

MOCK_ACTION = ActionExecutionSpecDB()
MOCK_ACTION.name = 'action-test-1.name'

MOCK_ACTION_EXECUTION = ActionExecutionDB()
MOCK_ACTION_EXECUTION.id = bson.ObjectId()
MOCK_ACTION_EXECUTION.name = 'actionexec-test-1.name'

MOCK_RULE_1 = RuleDB()
MOCK_RULE_1.id = bson.ObjectId()
MOCK_RULE_1.name = 'rule1'
MOCK_RULE_1.trigger = reference.get_ref_from_model(MOCK_TRIGGER)
MOCK_RULE_1.criteria = {}
MOCK_RULE_1.action = MOCK_ACTION
MOCK_RULE_1.enabled = True

MOCK_RULE_2 = RuleDB()
MOCK_RULE_2.id = bson.ObjectId()
MOCK_RULE_1.name = 'rule2'
MOCK_RULE_2.trigger = reference.get_ref_from_model(MOCK_TRIGGER)
MOCK_RULE_2.criteria = {}
MOCK_RULE_2.action = MOCK_ACTION
MOCK_RULE_2.enabled = True


class EnforceTest(unittest2.TestCase):

    @classmethod
    def setUpClass(cls):
        tests_config.parse_args()

    @mock.patch.object(RuleEnforcement, 'add_or_update')
    @mock.patch.object(RuleEnforcer, '_invoke_action', mock.MagicMock(
        return_value=reference.get_ref_from_model(MOCK_ACTION_EXECUTION)))
    @mock.patch.object(reference, 'get_model_from_ref', mock.MagicMock(return_value=MOCK_TRIGGER))
    def test_ruleenforcement_creation(self, mock_ruleenforcement_add):
        enforcer = RuleEnforcer(MOCK_TRIGGER_INSTANCE, MOCK_RULE_1)
        enforcer.enforce()
        self.assertEqual(mock_ruleenforcement_add.call_count, 1,
                         'Expected RuleEnforcement(s) not added.')

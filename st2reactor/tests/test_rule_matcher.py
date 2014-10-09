import datetime

from st2common.models.db.reactor import (TriggerDB, TriggerTypeDB)
from st2common.models.api.reactor import (RuleAPI, TriggerAPI)
from st2common.persistence.reactor import (TriggerType, Trigger, Rule)
from st2common.services import triggers as TriggerService
from st2common.util import reference
import st2reactor.container.utils as container_utils
from st2reactor.rules.matcher import RulesMatcher
from st2tests.base import DbTestCase


class RuleMatcherTest(DbTestCase):

    def test_get_matching_rules(self):
        self._setup_sample_triggers('st2.test.trigger1')
        trigger_instance = container_utils.create_trigger_instance(
            {'name': 'st2.test.trigger1'}, {'k1': 't1_p_v', 'k2': 'v2'}, datetime.datetime.now()
        )
        rules = self._get_sample_rules()
        rules_matcher = RulesMatcher(trigger_instance, rules)
        matching_rules = rules_matcher.get_matching_rules()
        self.assertTrue(matching_rules is not None)
        self.assertEqual(len(matching_rules), 1)

    def _setup_sample_triggers(self, name):
        trigtype = TriggerTypeDB()
        trigtype.name = name
        trigtype.description = ''
        trigtype.payload_schema = {}
        trigtype.parameters_schema = {}
        TriggerType.add_or_update(trigtype)

        created = TriggerDB()
        created.name = name
        created.description = ''
        created.type = reference.get_ref_from_model(trigtype)
        created.parameters = {}
        Trigger.add_or_update(created)

    def _get_sample_rules(self):
        rules = []

        RULE_1 = {
            'enabled': True,
            'name': 'st2.test.rule1',
            'trigger': {
                'type': 'st2.test.trigger1'
            },
            'criteria': {
                'k1': {                     # Missing prefix 'trigger'. This rule won't match.
                    'pattern': 't1_p_v',
                    'type': 'equals'
                }
            },
            'action': {
                'name': 'st2.test.action',
                'parameters': {
                    'ip2': '{{rule.k1}}',
                    'ip1': '{{trigger.t1_p}}'
                }
            },
            'id': '23',
            'description': ''
        }
        rule_api = RuleAPI(**RULE_1)
        rule_db = RuleAPI.to_model(rule_api)
        trigger_api = TriggerAPI(**rule_api.trigger)
        trigger_db = TriggerService.create_trigger_db(trigger_api)
        trigger_ref = reference.get_ref_from_model(trigger_db)
        rule_db.trigger = trigger_ref
        rule_db = Rule.add_or_update(rule_db)
        rules.append(rule_db)

        RULE_2 = {                      # Rule should match.
            'enabled': True,
            'name': 'st2.test.rule2',
            'trigger': {
                'type': 'st2.test.trigger1'
            },
            'criteria': {
                'trigger.k1': {
                    'pattern': 't1_p_v',
                    'type': 'equals'
                }
            },
            'action': {
                'name': 'st2.test.action',
                'parameters': {
                    'ip2': '{{rule.k1}}',
                    'ip1': '{{trigger.t1_p}}'
                }
            },
            'id': '23',
            'description': ''
        }
        rule_api = RuleAPI(**RULE_2)
        rule_db = RuleAPI.to_model(rule_api)
        rule_db.trigger = trigger_ref
        rule_db = Rule.add_or_update(rule_db)
        rules.append(rule_db)

        RULE_3 = {
            'enabled': False,         # Disabled rule shouldn't match.
            'name': 'st2.test.rule3',
            'trigger': {
                'type': 'st2.test.trigger1'
            },
            'criteria': {
                'trigger.k1': {
                    'pattern': 't1_p_v',
                    'type': 'equals'
                }
            },
            'action': {
                'name': 'st2.test.action',
                'parameters': {
                    'ip2': '{{rule.k1}}',
                    'ip1': '{{trigger.t1_p}}'
                }
            },
            'id': '23',
            'description': ''
        }
        rule_api = RuleAPI(**RULE_3)
        rule_db = RuleAPI.to_model(rule_api)
        rule_db.trigger = trigger_ref
        rule_db = Rule.add_or_update(rule_db)
        rules.append(rule_db)

        return rules

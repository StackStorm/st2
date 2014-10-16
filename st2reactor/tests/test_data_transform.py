import copy

from st2tests import DbTestCase
from st2common.models.db.datastore import KeyValuePairDB
from st2common.models.db.reactor import RuleDB, TriggerDB
from st2common.persistence.datastore import KeyValuePair
from st2common.persistence.reactor import Rule, Trigger
from st2common.util import reference
from st2reactor.rules import datatransform



PAYLOAD = {'k1': 'v1', 'k2': 'v2'}

PAYLOAD_WITH_KVP = copy.copy(PAYLOAD)
PAYLOAD_WITH_KVP.update({'k5': '{{system.k5}}'})

PAYLOAD_WITH_RULE = copy.copy(PAYLOAD)
PAYLOAD_WITH_RULE.update({'trigger_name': '{{ rule.trigger.name }}'})


class DataTransformTest(DbTestCase):

    def test_payload_transform(self):
        transformer = datatransform.get_transformer(PAYLOAD)
        mapping = {'ip1': '{{trigger.k1}}-static',
                   'ip2': '{{trigger.k2}} static'}
        result = transformer(mapping)
        self.assertEqual(result, {'ip1': 'v1-static', 'ip2': 'v2 static'})

    def test_system_transform(self):
        k5 = KeyValuePair.add_or_update(KeyValuePairDB(name='k5', value='v5'))
        k6 = KeyValuePair.add_or_update(KeyValuePairDB(name='k6', value='v6'))
        k7 = KeyValuePair.add_or_update(KeyValuePairDB(name='k7', value='v7'))
        try:
            transformer = datatransform.get_transformer(PAYLOAD_WITH_KVP)
            mapping = {'ip5': '{{trigger.k5}}-static',
                       'ip6': '{{system.k6}}-static',
                       'ip7': '{{system.k7}}-static'}
            result = transformer(mapping)
            expected = {'ip5': 'v5-static',
                        'ip6': 'v6-static',
                        'ip7': 'v7-static'}
            self.assertEqual(result, expected)
        finally:
            KeyValuePair.delete(k5)
            KeyValuePair.delete(k6)
            KeyValuePair.delete(k7)

    def test_rule_transform(self):
        trigger = Trigger.add_or_update(TriggerDB(name='fancytrigger',
                                                  type={'name': 'st2.trigger'},
                                                  parameters={'data': 'some'}))
        rule = Rule.add_or_update(RuleDB(name='fancyrule',
                                         trigger=reference.get_ref_from_model(trigger),
                                         action={'name': 'fancyaction'}))
        try:
            transformer = datatransform.get_transformer(PAYLOAD_WITH_RULE, rule)
            mapping = {'trigger_name': '{{trigger.trigger_name}}',
                       'trigger_id': '{{rule.trigger.id}}',
                       'trigger_type': '{{rule.trigger.type}}'}
            result = transformer(mapping)
            expected = {'trigger_name': 'fancytrigger',
                        'trigger_id': str(trigger.id),
                        'trigger_type': 'st2.trigger'}
            self.assertEquals(result, expected)
        finally:
            Rule.delete(rule)
            Trigger.delete(trigger)

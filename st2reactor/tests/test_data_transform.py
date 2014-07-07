import sys
import copy

from tests.base import DbTestCase
from st2common.models.db.datastore import KeyValuePairDB
from st2common.persistence.datastore import KeyValuePair
from st2reactor.ruleenforcement import datatransform


PAYLOAD = {'k1': 'v1', 'k2': 'v2'}
RULE_DATA = {'k3': 'v3', 'k4': 'v4'}

PAYLOAD_WITH_KVP = copy.copy(PAYLOAD)
PAYLOAD_WITH_KVP.update({'k5': '{{system.k5}}'})
RULE_DATA_WITH_KVP = copy.copy(RULE_DATA)
RULE_DATA_WITH_KVP.update({'k6': '{{system.k6}}'})


class DataTransformTest(DbTestCase):

    def test_payload_transform(self):
        transformer = datatransform.get_transformer(PAYLOAD)
        mapping = {'ip1': '{{trigger.k1}}-static',
                   'ip2': '{{trigger.k2}} static'}
        result = transformer(mapping, None)
        self.assertEquals(result, {'ip1': 'v1-static', 'ip2': 'v2 static'})

    def test_rule_data_transform(self):
        transformer = datatransform.get_transformer(None)
        mapping = {'ip3': '{{rule.k3}}-static', 'ip4': '{{rule.k4}} static'}
        result = transformer(mapping, RULE_DATA)
        self.assertEquals(result, {'ip3': 'v3-static', 'ip4': 'v4 static'})

    def test_combined_transform(self):
        transformer = datatransform.get_transformer(PAYLOAD)
        mapping = {'ip1': '{{trigger.k1}}-static', 'ip4': '{{rule.k4}} static'}
        result = transformer(mapping, RULE_DATA)
        self.assertEquals(result, {'ip1': 'v1-static', 'ip4': 'v4 static'})

    def test_system_transform(self):
        k5 = KeyValuePair.add_or_update(KeyValuePairDB(name='k5', value='v5'))
        k6 = KeyValuePair.add_or_update(KeyValuePairDB(name='k6', value='v6'))
        k7 = KeyValuePair.add_or_update(KeyValuePairDB(name='k7', value='v7'))
        try:
            transformer = datatransform.get_transformer(PAYLOAD_WITH_KVP)
            mapping = {'ip5': '{{trigger.k5}}-static',
                       'ip6': '{{rule.k6}}-static',
                       'ip7': '{{system.k7}}-static'}
            result = transformer(mapping, RULE_DATA_WITH_KVP)
            expected = {'ip5': 'v5-static',
                        'ip6': 'v6-static',
                        'ip7': 'v7-static'}
            self.assertEquals(result, expected)
        finally:
            KeyValuePair.delete(k5)
            KeyValuePair.delete(k6)
            KeyValuePair.delete(k7)

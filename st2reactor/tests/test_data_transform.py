import sys
print sys.path

import unittest2
from st2reactor.ruleenforcement import datatransform

PAYLOAD = {'k1': 'v1', 'k2': 'v2'}
RULE_DATA = {'k3': 'v3', 'k4': 'v4'}


class DataTransformTest(unittest2.TestCase):

    def test_payload_transform(self):
        transformer = datatransform.get_transformer(PAYLOAD)
        mapping = {'ip1': '{{trigger.k1}}-static', 'ip2': '{{trigger.k2}} static'}
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

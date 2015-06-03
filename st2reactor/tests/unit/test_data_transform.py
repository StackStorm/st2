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

from st2tests import DbTestCase
from st2common.models.db.keyvalue import KeyValuePairDB
from st2common.persistence.keyvalue import KeyValuePair
from st2reactor.rules import datatransform


PAYLOAD = {'k1': 'v1', 'k2': 'v2', 'k3': 3, 'k4': True, 'k5': {'foo': 'bar'}, 'k6': [1, 3]}


class DataTransformTest(DbTestCase):

    def test_payload_transform(self):
        transformer = datatransform.get_transformer(PAYLOAD)
        mapping = {'ip1': '{{trigger.k1}}-static',
                   'ip2': '{{trigger.k2}} static'}
        result = transformer(mapping)
        self.assertEqual(result, {'ip1': 'v1-static', 'ip2': 'v2 static'})

    def test_payload_transofrm_int_type(self):
        transformer = datatransform.get_transformer(PAYLOAD)
        mapping = {'int': 666}
        result = transformer(mapping)
        self.assertEqual(result, {'int': 666})

    def test_payload_transform_bool_type(self):
        transformer = datatransform.get_transformer(PAYLOAD)
        mapping = {'bool': True}
        result = transformer(mapping)
        self.assertEqual(result, {'bool': True})

    def test_payload_transform_complex_type(self):
        transformer = datatransform.get_transformer(PAYLOAD)
        mapping = {'complex_dict': {'bool': True, 'int': 666, 'str': '{{trigger.k1}}-string'}}
        result = transformer(mapping)
        expected = {'complex_dict': {'bool': True, 'int': 666, 'str': 'v1-string'}}
        self.assertEqual(result, expected)
        mapping = {'simple_list': [1, 2, 3]}
        result = transformer(mapping)
        self.assertEqual(result, mapping)

    def test_hypenated_payload_transform(self):
        payload = {'headers': {'hypenated-header': 'dont-care'}, 'k2': 'v2'}
        transformer = datatransform.get_transformer(payload)
        mapping = {'ip1': '{{trigger.headers[\'hypenated-header\']}}-static',
                   'ip2': '{{trigger.k2}} static'}
        result = transformer(mapping)
        self.assertEqual(result, {'ip1': 'dont-care-static', 'ip2': 'v2 static'})

    def test_system_transform(self):
        k5 = KeyValuePair.add_or_update(KeyValuePairDB(name='k5', value='v5'))
        k6 = KeyValuePair.add_or_update(KeyValuePairDB(name='k6', value='v6'))
        k7 = KeyValuePair.add_or_update(KeyValuePairDB(name='k7', value='v7'))
        try:
            transformer = datatransform.get_transformer(PAYLOAD)
            mapping = {'ip5': '{{trigger.k2}}-static',
                       'ip6': '{{system.k6}}-static',
                       'ip7': '{{system.k7}}-static'}
            result = transformer(mapping)
            expected = {'ip5': 'v2-static',
                        'ip6': 'v6-static',
                        'ip7': 'v7-static'}
            self.assertEqual(result, expected)
        finally:
            KeyValuePair.delete(k5)
            KeyValuePair.delete(k6)
            KeyValuePair.delete(k7)

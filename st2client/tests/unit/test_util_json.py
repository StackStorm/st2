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

import json
import logging
import unittest2

from st2client.utils import jsutil


LOG = logging.getLogger(__name__)

DOC = {
    'a01': 1,
    'b01': 2,
    'c01': {
        'c11': 3,
        'd12': 4,
        'c13': {
            'c21': 5,
            'c22': 6
        },
        'c14': [7, 8, 9]
    }
}


class TestGetValue(unittest2.TestCase):

    def test_dot_notation(self):
        self.assertEqual(jsutil.get_value(DOC, 'a01'), 1)
        self.assertEqual(jsutil.get_value(DOC, 'c01.c11'), 3)
        self.assertEqual(jsutil.get_value(DOC, 'c01.c13.c22'), 6)
        self.assertEqual(jsutil.get_value(DOC, 'c01.c13'), {'c21': 5, 'c22': 6})
        self.assertListEqual(jsutil.get_value(DOC, 'c01.c14'), [7, 8, 9])

    def test_dot_notation_with_val_error(self):
        self.assertRaises(ValueError, jsutil.get_value, DOC, None)
        self.assertRaises(ValueError, jsutil.get_value, DOC, '')
        self.assertRaises(ValueError, jsutil.get_value, json.dumps(DOC), 'a01')

    def test_dot_notation_with_key_error(self):
        self.assertIsNone(jsutil.get_value(DOC, 'd01'))
        self.assertIsNone(jsutil.get_value(DOC, 'a01.a11'))
        self.assertIsNone(jsutil.get_value(DOC, 'c01.c11.c21.c31'))
        self.assertIsNone(jsutil.get_value(DOC, 'c01.c14.c31'))


class TestGetKeyValuePairs(unittest2.TestCase):

    def test_select_kvps(self):
        self.assertEqual(jsutil.get_kvps(DOC, ['a01']),
                         {'a01': 1})
        self.assertEqual(jsutil.get_kvps(DOC, ['c01.c11']),
                         {'c01': {'c11': 3}})
        self.assertEqual(jsutil.get_kvps(DOC, ['c01.c13.c22']),
                         {'c01': {'c13': {'c22': 6}}})
        self.assertEqual(jsutil.get_kvps(DOC, ['c01.c13']),
                         {'c01': {'c13': {'c21': 5, 'c22': 6}}})
        self.assertEqual(jsutil.get_kvps(DOC, ['c01.c14']),
                         {'c01': {'c14': [7, 8, 9]}})
        self.assertEqual(jsutil.get_kvps(DOC, ['a01', 'c01.c11', 'c01.c13.c21']),
                         {'a01': 1, 'c01': {'c11': 3, 'c13': {'c21': 5}}})

    def test_select_kvps_with_val_error(self):
        self.assertRaises(ValueError, jsutil.get_kvps, DOC, [None])
        self.assertRaises(ValueError, jsutil.get_kvps, DOC, [''])
        self.assertRaises(ValueError, jsutil.get_kvps, json.dumps(DOC), ['a01'])

    def test_select_kvps_with_key_error(self):
        self.assertEqual(jsutil.get_kvps(DOC, ['d01']), {})
        self.assertEqual(jsutil.get_kvps(DOC, ['a01.a11']), {})
        self.assertEqual(jsutil.get_kvps(DOC, ['c01.c11.c21.c31']), {})
        self.assertEqual(jsutil.get_kvps(DOC, ['c01.c14.c31']), {})
        self.assertEqual(jsutil.get_kvps(DOC, ['a01', 'c01.c11', 'c01.c13.c23']),
                         {'a01': 1, 'c01': {'c11': 3}})

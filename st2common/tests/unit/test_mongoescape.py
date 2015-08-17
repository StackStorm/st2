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

import unittest

from st2common.util import mongoescape


class TestMongoEscape(unittest.TestCase):
    def test_unnested(self):
        field = {'k1.k1.k1': 'v1', 'k2$': 'v2', '$k3.': 'v3'}
        escaped = mongoescape.escape_chars(field)
        self.assertEqual(escaped, {u'k1\uff0ek1\uff0ek1': 'v1',
                                   u'k2\uff04': 'v2',
                                   u'\uff04k3\uff0e': 'v3'}, 'Escaping failed.')
        unescaped = mongoescape.unescape_chars(escaped)
        self.assertEqual(unescaped, field, 'Unescaping failed.')

    def test_nested(self):
        nested_field = {'nk1.nk1.nk1': 'v1', 'nk2$': 'v2', '$nk3.': 'v3'}
        field = {'k1.k1.k1': nested_field, 'k2$': 'v2', '$k3.': 'v3'}
        escaped = mongoescape.escape_chars(field)
        self.assertEqual(escaped, {u'k1\uff0ek1\uff0ek1': {u'\uff04nk3\uff0e': 'v3',
                                                           u'nk1\uff0enk1\uff0enk1': 'v1',
                                                           u'nk2\uff04': 'v2'},
                                   u'k2\uff04': 'v2',
                                   u'\uff04k3\uff0e': 'v3'}, 'un-escaping failed.')
        unescaped = mongoescape.unescape_chars(escaped)
        self.assertEqual(unescaped, field, 'Unescaping failed.')

    def test_unescaping_of_rule_criteria(self):
        # Verify that dot escaped in rule criteria is correctly escaped.
        # Note: In the past we used different character to escape dot in the
        # rule criteria.
        escaped = {
            u'k1\u2024k1\u2024k1': 'v1',
            u'k2$': 'v2',
            u'$k3\u2024': 'v3'
        }
        unescaped = {
            'k1.k1.k1': 'v1',
            'k2$': 'v2',
            '$k3.': 'v3'
        }

        result = mongoescape.unescape_chars(escaped)
        self.assertEqual(result, unescaped)

    def test_original_value(self):
        field = {'k1.k2.k3': 'v1'}

        escaped = mongoescape.escape_chars(field)
        self.assertIn('k1.k2.k3', field.keys())
        self.assertIn(u'k1\uff0ek2\uff0ek3', escaped.keys())

        unescaped = mongoescape.unescape_chars(escaped)
        self.assertIn('k1.k2.k3', unescaped.keys())
        self.assertIn(u'k1\uff0ek2\uff0ek3', escaped.keys())

    def test_complex(self):
        field = {
            'k1.k2': [{'l1.l2': '123'}, {'l3.l4': '456'}],
            'k3': [{'l5.l6': '789'}],
            'k4.k5': [1, 2, 3],
            'k6': ['a', 'b']
        }

        expected = {
            u'k1\uff0ek2': [{u'l1\uff0el2': '123'}, {u'l3\uff0el4': '456'}],
            'k3': [{u'l5\uff0el6': '789'}],
            u'k4\uff0ek5': [1, 2, 3],
            'k6': ['a', 'b']
        }

        escaped = mongoescape.escape_chars(field)
        self.assertDictEqual(expected, escaped)

        unescaped = mongoescape.unescape_chars(escaped)
        self.assertDictEqual(field, unescaped)

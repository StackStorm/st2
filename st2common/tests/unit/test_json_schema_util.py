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

from unittest2 import TestCase

from st2common.util import schema as util_schema

__all__ = [
    'JSONSchemaUtilsTestCase'
]


class JSONSchemaUtilsTestCase(TestCase):
    def test_get_jsonschema_type_for_value(self):
        values = [
            ('somevalue', 'string'),
            (u'somevalue', 'string'),
            (1, 'integer'),
            (200, 'integer'),
            (1.0, 'number'),
            (1.3, 'number'),
            (500.0, 'number'),
            (True, 'boolean'),
            (False, 'boolean'),
            ([1, 2, 3], 'list'),
            ((1, 2, 3), 'list'),
            ({'a': 'b'}, 'object'),
            (None, 'null')
        ]

        for value, expected_type in values:
            result = util_schema.get_jsonschema_type_for_value(value=value)
            self.assertEqual(expected_type, result, 'Expected %s for %s, got %s' %
                             (expected_type, value, result))

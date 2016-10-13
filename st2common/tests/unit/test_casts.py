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

import unittest2

from st2common.util.casts import get_cast


class CastsTestCase(unittest2.TestCase):
    def test_cast_string(self):
        cast_func = get_cast('string')

        value = 'test1'
        result = cast_func(value)
        self.assertEqual(result, 'test1')

        value = u'test2'
        result = cast_func(value)
        self.assertEqual(result, u'test2')

        value = ''
        result = cast_func(value)
        self.assertEqual(result, '')

        # None should be preserved
        value = None
        result = cast_func(value)
        self.assertEqual(result, None)

        # Non string or non, should throw a friendly exception
        value = []
        expected_msg = 'Value "\[\]" must either be a string or None. Got "list"'
        self.assertRaisesRegexp(ValueError, expected_msg, cast_func, value)

    def test_cast_array(self):
        cast_func = get_cast('array')

        # Python literal
        value = str([1, 2, 3])
        result = cast_func(value)
        self.assertEqual(result, [1, 2, 3])

        # JSON serialized
        value = json.dumps([4, 5, 6])
        result = cast_func(value)
        self.assertEqual(result, [4, 5, 6])

        # Can't cast, should throw
        value = "\\invalid"
        self.assertRaises(SyntaxError, cast_func, value)

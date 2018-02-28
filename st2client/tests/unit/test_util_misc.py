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

from __future__ import absolute_import
import unittest2

from st2client.utils.misc import merge_dicts


class MiscUtilTestCase(unittest2.TestCase):
    def test_merge_dicts(self):
        d1 = {'a': 1}
        d2 = {'a': 2}
        expected = {'a': 2}

        result = merge_dicts(d1, d2)
        self.assertEqual(result, expected)

        d1 = {'a': 1}
        d2 = {'b': 1}
        expected = {'a': 1, 'b': 1}

        result = merge_dicts(d1, d2)
        self.assertEqual(result, expected)

        d1 = {'a': 1}
        d2 = {'a': 3, 'b': 1}
        expected = {'a': 3, 'b': 1}

        result = merge_dicts(d1, d2)
        self.assertEqual(result, expected)

        d1 = {'a': 1, 'm': None}
        d2 = {'a': None, 'b': 1, 'c': None}
        expected = {'a': 1, 'b': 1, 'c': None, 'm': None}

        result = merge_dicts(d1, d2)
        self.assertEqual(result, expected)

        d1 = {'a': 1, 'b': {'a': 1, 'b': 2, 'c': 3}}
        d2 = {'b': {'b': 100}}
        expected = {'a': 1, 'b': {'a': 1, 'b': 100, 'c': 3}}

        result = merge_dicts(d1, d2)
        self.assertEqual(result, expected)

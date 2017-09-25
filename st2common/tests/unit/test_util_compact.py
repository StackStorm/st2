# -*- coding: utf-8 -*-
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

import unittest2

from st2common.util.compat import to_ascii

__all__ = [
    'CompatUtilsTestCase'
]


class CompatUtilsTestCase(unittest2.TestCase):
    def test_to_ascii(self):
        expected_values = [
            ('already ascii', 'already ascii'),
            (u'foo', 'foo'),
            ('٩(̾●̮̮̃̾•̃̾)۶', '()'),
            ('\xd9\xa9', '')
        ]

        for input_value, expected_value in expected_values:
            result = to_ascii(input_value)
            self.assertEqual(result, expected_value)

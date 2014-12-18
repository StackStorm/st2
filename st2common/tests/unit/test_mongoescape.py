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

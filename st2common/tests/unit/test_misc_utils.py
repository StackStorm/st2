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

from st2common.util.misc import strip_last_newline_char


class MiscUtilTestCase(unittest2.TestCase):

    def test_strip_last_newline_char(self):
        self.assertEqual(strip_last_newline_char(None), None)
        self.assertEqual(strip_last_newline_char(''), '')
        self.assertEqual(strip_last_newline_char('foo'), 'foo')
        self.assertEqual(strip_last_newline_char('foo\n'), 'foo')
        self.assertEqual(strip_last_newline_char('foo\n\n'), 'foo\n')

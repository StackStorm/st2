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

from st2common.util.misc import rstrip_last_char, strip_shell_chars


class MiscUtilTestCase(unittest2.TestCase):

    def test_rstrip_last_char(self):
        self.assertEqual(rstrip_last_char(None, '\n'), None)
        self.assertEqual(rstrip_last_char('stuff', None), 'stuff')
        self.assertEqual(rstrip_last_char('', '\n'), '')
        self.assertEqual(rstrip_last_char('foo', '\n'), 'foo')
        self.assertEqual(rstrip_last_char('foo\n', '\n'), 'foo')
        self.assertEqual(rstrip_last_char('foo\n\n', '\n'), 'foo\n')
        self.assertEqual(rstrip_last_char('foo\r', '\r'), 'foo')
        self.assertEqual(rstrip_last_char('foo\r\r', '\r'), 'foo\r')
        self.assertEqual(rstrip_last_char('foo\r\n', '\r\n'), 'foo')
        self.assertEqual(rstrip_last_char('foo\r\r\n', '\r\n'), 'foo\r')
        self.assertEqual(rstrip_last_char('foo\n\r', '\r\n'), 'foo\n\r')

    def test_strip_shell_chars(self):
        self.assertEqual(strip_shell_chars(None), None)
        self.assertEqual(strip_shell_chars('foo'), 'foo')
        self.assertEqual(strip_shell_chars('foo\r'), 'foo')
        self.assertEqual(strip_shell_chars('fo\ro\r'), 'fo\ro')
        self.assertEqual(strip_shell_chars('foo\n'), 'foo')
        self.assertEqual(strip_shell_chars('fo\no\n'), 'fo\no')
        self.assertEqual(strip_shell_chars('foo\r\n'), 'foo')
        self.assertEqual(strip_shell_chars('fo\no\r\n'), 'fo\no')
        self.assertEqual(strip_shell_chars('foo\r\n\r\n'), 'foo\r\n')

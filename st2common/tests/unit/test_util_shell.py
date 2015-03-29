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

from st2common.util.shell import quote_unix
from st2common.util.shell import quote_windows


class ShellUtilsTestCase(unittest2.TestCase):
    def test_quote_unix(self):
        arguments = [
            'foo',
            'foo bar',
            'foo1 bar1',
            '"foo"',
            '"foo" "bar"',
            "'foo bar'"
        ]
        expected_values = [
            """
            foo
            """,

            """
            'foo bar'
            """,

            """
            'foo1 bar1'
            """,

            """
            '"foo"'
            """,

            """
            '"foo" "bar"'
            """,

            """
            ''"'"'foo bar'"'"''
            """
        ]

        for argument, expected_value in zip(arguments, expected_values):
            actual_value = quote_unix(value=argument)
            expected_value = expected_value.lstrip()
            self.assertEqual(actual_value, expected_value.strip())

    def test_quote_windows(self):
        arguments = [
            'foo',
            'foo bar',
            'foo1 bar1',
            '"foo"',
            '"foo" "bar"',
            "'foo bar'"
        ]
        expected_values = [
            """
            foo
            """,

            """
            "foo bar"
            """,

            """
            "foo1 bar1"
            """,

            """
            \\"foo\\"
            """,

            """
            "\\"foo\\" \\"bar\\""
            """,

            """
            "'foo bar'"
            """
        ]

        for argument, expected_value in zip(arguments, expected_values):
            actual_value = quote_windows(value=argument)
            expected_value = expected_value.lstrip()
            self.assertEqual(actual_value, expected_value.strip())

# Licensed to the StackStorm, Inc ('StackStorm') under one or more
# contributor license agreements.  See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.
# The ASF licenses this file to You under the Apache License, Version 2.0
# (the 'License'); you may not use this file except in compliance with
# the License.  You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an 'AS IS' BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from unittest2 import TestCase
from st2common.exceptions.content import ParseException
from st2common.models.utils.action_alias_utils import ActionAliasFormatParser


class TestActionAliasParser(TestCase):
    def testEmptyString(self):
        alias_format = ''
        param_stream = ''
        parser = ActionAliasFormatParser(alias_format, param_stream)
        extracted_values = parser.get_extracted_param_value()
        self.assertEqual(extracted_values, {})

    def testArbitraryPairs(self):
        # single-word param
        alias_format = ''
        param_stream = 'a=foobar1'
        parser = ActionAliasFormatParser(alias_format, param_stream)
        extracted_values = parser.get_extracted_param_value()
        self.assertEqual(extracted_values, {'a': 'foobar1'})

        # multi-word double-quoted param
        alias_format = ''
        param_stream = 'foo a="foobar2 poonies bar"'
        parser = ActionAliasFormatParser(alias_format, param_stream)
        extracted_values = parser.get_extracted_param_value()
        self.assertEqual(extracted_values, {'a': 'foobar2 poonies bar'})

        # multi-word single-quoted param
        alias_format = ''
        param_stream = 'foo a=\'foobar2 poonies bar\''
        parser = ActionAliasFormatParser(alias_format, param_stream)
        extracted_values = parser.get_extracted_param_value()
        self.assertEqual(extracted_values, {'a': 'foobar2 poonies bar'})

        # JSON param
        alias_format = ''
        param_stream = 'foo a={"foobar2": "poonies"}'
        parser = ActionAliasFormatParser(alias_format, param_stream)
        extracted_values = parser.get_extracted_param_value()
        self.assertEqual(extracted_values, {'a': '{"foobar2": "poonies"}'})

        # Multiple mixed params
        alias_format = ''
        param_stream = 'a=foobar1 b="boobar2 3 4" c=\'coobar3 4\' d={"a": "b"}'
        parser = ActionAliasFormatParser(alias_format, param_stream)
        extracted_values = parser.get_extracted_param_value()
        self.assertEqual(extracted_values, {'a': 'foobar1',
                                            'b': 'boobar2 3 4',
                                            'c': 'coobar3 4',
                                            'd': '{"a": "b"}'})

        # Params along with a "normal" alias format
        alias_format = '{{ captain }} is my captain'
        param_stream = 'Malcolm Reynolds is my captain weirdo="River Tam"'
        parser = ActionAliasFormatParser(alias_format, param_stream)
        extracted_values = parser.get_extracted_param_value()
        self.assertEqual(extracted_values, {'captain': 'Malcolm Reynolds',
                                            'weirdo': 'River Tam'})

    def testSimpleParsing(self):
        alias_format = 'skip {{a}} more skip {{b}} and skip more.'
        param_stream = 'skip a1 more skip b1 and skip more.'
        parser = ActionAliasFormatParser(alias_format, param_stream)
        extracted_values = parser.get_extracted_param_value()
        self.assertEqual(extracted_values, {'a': 'a1', 'b': 'b1'})

    def testEndStringParsing(self):
        alias_format = 'skip {{a}} more skip {{b}}'
        param_stream = 'skip a1 more skip b1'
        parser = ActionAliasFormatParser(alias_format, param_stream)
        extracted_values = parser.get_extracted_param_value()
        self.assertEqual(extracted_values, {'a': 'a1', 'b': 'b1'})

    def testSpacedParsing(self):
        alias_format = 'skip {{a}} more skip {{b}} and skip more.'
        param_stream = 'skip "a1 a2" more skip b1 and skip more.'
        parser = ActionAliasFormatParser(alias_format, param_stream)
        extracted_values = parser.get_extracted_param_value()
        self.assertEqual(extracted_values, {'a': 'a1 a2', 'b': 'b1'})

    def testJsonParsing(self):
        alias_format = 'skip {{a}} more skip.'
        param_stream = 'skip {"a": "b", "c": "d"} more skip.'
        parser = ActionAliasFormatParser(alias_format, param_stream)
        extracted_values = parser.get_extracted_param_value()
        self.assertEqual(extracted_values, {'a': '{"a": "b", "c": "d"}'})

    def testMixedParsing(self):
        alias_format = 'skip {{a}} more skip {{b}}.'
        param_stream = 'skip {"a": "b", "c": "d"} more skip x.'
        parser = ActionAliasFormatParser(alias_format, param_stream)
        extracted_values = parser.get_extracted_param_value()
        self.assertEqual(extracted_values, {'a': '{"a": "b", "c": "d"}', 'b': 'x'})

    def test_stream_is_none_with_all_default_values(self):
        alias_format = 'skip {{d=test}} more skip {{e=test}}.'
        param_stream = None
        parser = ActionAliasFormatParser(alias_format, param_stream)
        extracted_values = parser.get_extracted_param_value()
        self.assertEqual(extracted_values, {'d': 'test', 'e': 'test'})

    def test_stream_is_not_none_some_default_values(self):
        alias_format = 'skip {{d=test}} more skip {{e=test}}'
        param_stream = 'skip ponies more skip'
        parser = ActionAliasFormatParser(alias_format, param_stream)
        extracted_values = parser.get_extracted_param_value()
        self.assertEqual(extracted_values, {'d': 'ponies', 'e': 'test'})

    def test_stream_is_none_no_default_values(self):
        alias_format = 'skip {{d}} more skip {{e}}.'
        param_stream = None
        parser = ActionAliasFormatParser(alias_format, param_stream)

        expected_msg = 'No value supplied and no default value found.'
        self.assertRaisesRegexp(ParseException, expected_msg,
                                parser.get_extracted_param_value)

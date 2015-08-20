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
from st2common.exceptions import content
from st2common.models.utils.action_alias_utils import DefaultParser, StringValueParser
from st2common.models.utils.action_alias_utils import JsonValueParser, ActionAliasFormatParser
from st2common.exceptions.content import ParseException


class TestDefaultParser(TestCase):

    def testDefaultParsing(self):
        stream = 'some meaningful value1 something else skippable value2 still more skip.'

        start = len('some meaningful ')
        self.assertTrue(DefaultParser.is_applicable(stream[start]), 'Should be parsable.')
        _, value, _ = DefaultParser.parse(start, stream)
        self.assertEqual(value, 'value1')

        start = len('some meaningful value1 something else skippable ')
        self.assertTrue(DefaultParser.is_applicable(stream[start]), 'Should be parsable.')
        _, value, _ = DefaultParser.parse(start, stream)
        self.assertEqual(value, 'value2')

    def testEndStringParsing(self):
        stream = 'some meaningful value1'

        start = len('some meaningful ')
        self.assertTrue(DefaultParser.is_applicable(stream[start]), 'Should be parsable.')
        _, value, _ = DefaultParser.parse(start, stream)
        self.assertEqual(value, 'value1')


class TestStringValueParser(TestCase):

    def testStringParsing(self):
        stream = 'some meaningful "spaced value1" something else skippable "double spaced value2"' \
                 'still more skip.'

        start = len('some meaningful ')
        self.assertTrue(StringValueParser.is_applicable(stream[start]), 'Should be parsable.')
        _, value, _ = StringValueParser.parse(start, stream)
        self.assertEqual(value, 'spaced value1')

        start = len('some meaningful "spaced value1" something else skippable ')
        self.assertTrue(StringValueParser.is_applicable(stream[start]), 'Should be parsable.')
        _, value, _ = StringValueParser.parse(start, stream)
        self.assertEqual(value, 'double spaced value2')

        start = len(stream) - 2
        self.assertFalse(StringValueParser.is_applicable(stream[start]), 'Should not be parsable.')

    def testEndStringParsing(self):
        stream = 'some meaningful "spaced value1"'

        start = len('some meaningful ')
        self.assertTrue(StringValueParser.is_applicable(stream[start]), 'Should be parsable.')
        _, value, _ = StringValueParser.parse(start, stream)
        self.assertEqual(value, 'spaced value1')

    def testEscapedStringParsing(self):
        stream = 'some meaningful "spaced \\"value1" something else skippable ' \
                 '"double spaced value2" still more skip.'

        start = len('some meaningful ')
        self.assertTrue(StringValueParser.is_applicable(stream[start]), 'Should be parsable.')
        _, value, _ = StringValueParser.parse(start, stream)
        self.assertEqual(value, 'spaced \\"value1')

        start = len('some meaningful "spaced \\"value1" something else skippable ')
        self.assertTrue(StringValueParser.is_applicable(stream[start]), 'Should be parsable.')
        _, value, _ = StringValueParser.parse(start, stream)
        self.assertEqual(value, 'double spaced value2')

        start = len(stream) - 2
        self.assertFalse(StringValueParser.is_applicable(stream[start]), 'Should not be parsable.')

    def testIncompleteStringParsing(self):
        stream = 'some meaningful "spaced .'

        start = len('some meaningful ')
        self.assertTrue(StringValueParser.is_applicable(stream[start]), 'Should be parsable.')
        try:
            StringValueParser.parse(start, stream)
            self.assertTrue(False, 'Parsing failure expected.')
        except content.ParseException:
            self.assertTrue(True)


class TestJsonValueParser(TestCase):

    def testJsonParsing(self):
        stream = 'some meaningful {"a": "b"} something else skippable {"c": "d"} end.'

        start = len('some meaningful ')
        self.assertTrue(JsonValueParser.is_applicable(stream[start]), 'Should be parsable.')
        _, value, _ = JsonValueParser.parse(start, stream)
        self.assertEqual(value, '{"a": "b"}')

        start = len('some meaningful {"a": "b"} something else skippable ')
        self.assertTrue(JsonValueParser.is_applicable(stream[start]), 'Should be parsable.')
        _, value, _ = JsonValueParser.parse(start, stream)
        self.assertEqual(value, '{"c": "d"}')

        start = len(stream) - 2
        self.assertFalse(JsonValueParser.is_applicable(stream[start]), 'Should not be parsable.')

    def testEndJsonParsing(self):
        stream = 'some meaningful {"a": "b"}'

        start = len('some meaningful ')
        self.assertTrue(JsonValueParser.is_applicable(stream[start]), 'Should be parsable.')
        _, value, _ = JsonValueParser.parse(start, stream)
        self.assertEqual(value, '{"a": "b"}')

    def testComplexJsonParsing(self):
        stream = 'some meaningful {"a": "b", "c": "d", "e": {"f": "g"}, "h": [1, 2]}'

        start = len('some meaningful ')
        self.assertTrue(JsonValueParser.is_applicable(stream[start]), 'Should be parsable.')
        _, value, _ = JsonValueParser.parse(start, stream)
        self.assertEqual(value, '{"a": "b", "c": "d", "e": {"f": "g"}, "h": [1, 2]}')

    def testIncompleteStringParsing(self):
        stream = 'some meaningful {"a":'

        start = len('some meaningful ')
        self.assertTrue(JsonValueParser.is_applicable(stream[start]), 'Should be parsable.')
        try:
            JsonValueParser.parse(start, stream)
            self.assertTrue(False, 'Parsing failure expected.')
        except content.ParseException:
            self.assertTrue(True)


class TestActionAliasParser(TestCase):
    def test_default_key_value_param_parsing(self):
        # Empty string
        alias_format = ''
        param_stream = ''
        parser = ActionAliasFormatParser(alias_format, param_stream)
        extracted_values = parser.get_extracted_param_value()
        self.assertEqual(extracted_values, {})

        # 1 key value pair provided in the param stream
        alias_format = ''
        param_stream = 'a=foobar1'
        parser = ActionAliasFormatParser(alias_format, param_stream)
        extracted_values = parser.get_extracted_param_value()
        self.assertEqual(extracted_values, {'a': 'foobar1'})

        alias_format = ''
        param_stream = 'foo a=foobar2 poonies bar'
        parser = ActionAliasFormatParser(alias_format, param_stream)
        extracted_values = parser.get_extracted_param_value()
        self.assertEqual(extracted_values, {'a': 'foobar2'})

        # Multiple params provided
        alias_format = ''
        param_stream = 'a=foobar1 b=boobar2 c=coobar3'
        parser = ActionAliasFormatParser(alias_format, param_stream)
        extracted_values = parser.get_extracted_param_value()
        self.assertEqual(extracted_values, {'a': 'foobar1', 'b': 'boobar2', 'c': 'coobar3'})

        # Multiple params provided
        alias_format = ''
        param_stream = 'a=foobar4 b=boobar5 c=coobar6'
        parser = ActionAliasFormatParser(alias_format, param_stream)
        extracted_values = parser.get_extracted_param_value()
        self.assertEqual(extracted_values, {'a': 'foobar4', 'b': 'boobar5', 'c': 'coobar6'})

        # Multiple params provided
        alias_format = ''
        param_stream = 'mixed a=foobar1 some more b=boobar2 text c=coobar3 yeah'
        parser = ActionAliasFormatParser(alias_format, param_stream)
        extracted_values = parser.get_extracted_param_value()
        self.assertEqual(extracted_values, {'a': 'foobar1', 'b': 'boobar2', 'c': 'coobar3'})

        # Param with quotes, make sure they are stripped
        alias_format = ''
        param_stream = 'mixed a="foobar1"'
        parser = ActionAliasFormatParser(alias_format, param_stream)
        extracted_values = parser.get_extracted_param_value()
        self.assertEqual(extracted_values, {'a': 'foobar1'})

        # Param with quotes, make sure they are stripped
        alias_format = ''
        param_stream = 'mixed a="foobar test" ponies a'
        parser = ActionAliasFormatParser(alias_format, param_stream)
        extracted_values = parser.get_extracted_param_value()
        self.assertEqual(extracted_values, {'a': 'foobar test'})

        # Param with quotes, make sure they are stripped
        alias_format = ''
        param_stream = "mixed a='foobar1 ponies' test"
        parser = ActionAliasFormatParser(alias_format, param_stream)
        extracted_values = parser.get_extracted_param_value()
        self.assertEqual(extracted_values, {'a': 'foobar1 ponies'})

        # Param with quotes, make sure they are stripped
        alias_format = ''
        param_stream = 'mixed a="foobar1"'
        parser = ActionAliasFormatParser(alias_format, param_stream)
        extracted_values = parser.get_extracted_param_value()
        self.assertEqual(extracted_values, {'a': 'foobar1'})

        # Mixed format and kv params
        alias_format = 'somestuff {{a}} more stuff {{b}}'
        param_stream = 'somestuff a=foobar more stuff coobar'
        parser = ActionAliasFormatParser(alias_format, param_stream)
        extracted_values = parser.get_extracted_param_value()
        self.assertEqual(extracted_values, {'a': 'foobar', 'b': 'coobar'})

        alias_format = 'somestuff {{a}} more stuff {{b}}'
        param_stream = 'somestuff ponies more stuff coobar'
        parser = ActionAliasFormatParser(alias_format, param_stream)
        extracted_values = parser.get_extracted_param_value()
        self.assertEqual(extracted_values, {'a': 'ponies', 'b': 'coobar'})

        alias_format = 'somestuff {{a}} more stuff {{b}}'
        param_stream = 'somestuff ponies more stuff coobar b=foo'
        parser = ActionAliasFormatParser(alias_format, param_stream)
        extracted_values = parser.get_extracted_param_value()
        self.assertEqual(extracted_values, {'a': 'ponies', 'b': 'foo'})

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
        param_stream = 'skip {"a": "b", "c": "d"} more skip x'
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
        alias_format = 'skip {{d=test}} more skip {{e=test}}.'
        param_stream = 'skip ponies'
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

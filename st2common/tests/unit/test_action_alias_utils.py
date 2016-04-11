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
    def test_empty_string(self):
        alias_format = ''
        param_stream = ''
        parser = ActionAliasFormatParser(alias_format, param_stream)
        extracted_values = parser.get_extracted_param_value()
        self.assertEqual(extracted_values, {})

    def test_arbitrary_pairs(self):
        # single-word param
        alias_format = ''
        param_stream = 'a=foobar1'
        parser = ActionAliasFormatParser(alias_format, param_stream)
        extracted_values = parser.get_extracted_param_value()
        self.assertEqual(extracted_values, {'a': 'foobar1'})

        # multi-word double-quoted param
        alias_format = 'foo'
        param_stream = 'foo a="foobar2 poonies bar"'
        parser = ActionAliasFormatParser(alias_format, param_stream)
        extracted_values = parser.get_extracted_param_value()
        self.assertEqual(extracted_values, {'a': 'foobar2 poonies bar'})

        # multi-word single-quoted param
        alias_format = 'foo'
        param_stream = 'foo a=\'foobar2 poonies bar\''
        parser = ActionAliasFormatParser(alias_format, param_stream)
        extracted_values = parser.get_extracted_param_value()
        self.assertEqual(extracted_values, {'a': 'foobar2 poonies bar'})

        # JSON param
        alias_format = 'foo'
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

    def test_simple_parsing(self):
        alias_format = 'skip {{a}} more skip {{b}} and skip more.'
        param_stream = 'skip a1 more skip b1 and skip more.'
        parser = ActionAliasFormatParser(alias_format, param_stream)
        extracted_values = parser.get_extracted_param_value()
        self.assertEqual(extracted_values, {'a': 'a1', 'b': 'b1'})

    def test_end_string_parsing(self):
        alias_format = 'skip {{a}} more skip {{b}}'
        param_stream = 'skip a1 more skip b1'
        parser = ActionAliasFormatParser(alias_format, param_stream)
        extracted_values = parser.get_extracted_param_value()
        self.assertEqual(extracted_values, {'a': 'a1', 'b': 'b1'})

    def test_spaced_parsing(self):
        alias_format = 'skip {{a}} more skip {{b}} and skip more.'
        param_stream = 'skip "a1 a2" more skip b1 and skip more.'
        parser = ActionAliasFormatParser(alias_format, param_stream)
        extracted_values = parser.get_extracted_param_value()
        self.assertEqual(extracted_values, {'a': 'a1 a2', 'b': 'b1'})

    def test_default_values(self):
        alias_format = 'acl {{a}} {{b}} {{c}} {{d=1}}'
        param_stream = 'acl "a1 a2" "b1" "c1"'
        parser = ActionAliasFormatParser(alias_format, param_stream)
        extracted_values = parser.get_extracted_param_value()
        self.assertEqual(extracted_values, {'a': 'a1 a2', 'b': 'b1',
                                            'c': 'c1', 'd': '1'})

    def test_spacing(self):
        alias_format = 'acl {{a=test}}'
        param_stream = 'acl'
        parser = ActionAliasFormatParser(alias_format, param_stream)
        extracted_values = parser.get_extracted_param_value()
        self.assertEqual(extracted_values, {'a': 'test'})

    def test_json_parsing(self):
        alias_format = 'skip {{a}} more skip.'
        param_stream = 'skip {"a": "b", "c": "d"} more skip.'
        parser = ActionAliasFormatParser(alias_format, param_stream)
        extracted_values = parser.get_extracted_param_value()
        self.assertEqual(extracted_values, {'a': '{"a": "b", "c": "d"}'})

    def test_mixed_parsing(self):
        alias_format = 'skip {{a}} more skip {{b}}.'
        param_stream = 'skip {"a": "b", "c": "d"} more skip x.'
        parser = ActionAliasFormatParser(alias_format, param_stream)
        extracted_values = parser.get_extracted_param_value()
        self.assertEqual(extracted_values, {'a': '{"a": "b", "c": "d"}',
                                            'b': 'x'})

    def test_param_spaces(self):
        alias_format = 's {{a}} more {{ b }} more {{ c=99 }} more {{ d = 99 }}'
        param_stream = 's one more two more three more'
        parser = ActionAliasFormatParser(alias_format, param_stream)
        extracted_values = parser.get_extracted_param_value()
        self.assertEqual(extracted_values, {'a': 'one', 'b': 'two',
                                            'c': 'three', 'd': '99'})

    def test_enclosed_defaults(self):
        alias_format = 'skip {{ a = value }} more'
        param_stream = 'skip one more'
        parser = ActionAliasFormatParser(alias_format, param_stream)
        extracted_values = parser.get_extracted_param_value()
        self.assertEqual(extracted_values, {'a': 'one'})

        alias_format = 'skip {{ a = value }} more'
        param_stream = 'skip more'
        parser = ActionAliasFormatParser(alias_format, param_stream)
        extracted_values = parser.get_extracted_param_value()
        self.assertEqual(extracted_values, {'a': 'value'})

    def test_template_defaults(self):
        alias_format = 'two by two hands of {{ color = {{ colors.default_color }} }}'
        param_stream = 'two by two hands of'
        parser = ActionAliasFormatParser(alias_format, param_stream)
        extracted_values = parser.get_extracted_param_value()
        self.assertEqual(extracted_values, {'color': '{{ colors.default_color }}'})

    def test_key_value_combinations(self):
        # one-word value, single extra pair
        alias_format = 'testing {{ a }}'
        param_stream = 'testing value b=value2'
        parser = ActionAliasFormatParser(alias_format, param_stream)
        extracted_values = parser.get_extracted_param_value()
        self.assertEqual(extracted_values, {'a': 'value',
                                            'b': 'value2'})

        # default value, single extra pair with quotes
        alias_format = 'testing {{ a=new }}'
        param_stream = 'testing b="another value"'
        parser = ActionAliasFormatParser(alias_format, param_stream)
        extracted_values = parser.get_extracted_param_value()
        self.assertEqual(extracted_values, {'a': 'new',
                                            'b': 'another value'})

        # multiple values and multiple extra pairs
        alias_format = 'testing {{ b=abc }} {{ c=xyz }}'
        param_stream = 'testing newvalue d={"1": "2"} e="long value"'
        parser = ActionAliasFormatParser(alias_format, param_stream)
        extracted_values = parser.get_extracted_param_value()
        self.assertEqual(extracted_values, {'b': 'newvalue',
                                            'c': 'xyz',
                                            'd': '{"1": "2"}',
                                            'e': 'long value'})

    def test_stream_is_none_with_all_default_values(self):
        alias_format = 'skip {{d=test1}} more skip {{e=test1}}.'
        param_stream = 'skip more skip'
        parser = ActionAliasFormatParser(alias_format, param_stream)
        extracted_values = parser.get_extracted_param_value()
        self.assertEqual(extracted_values, {'d': 'test1', 'e': 'test1'})

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

        expected_msg = 'Command "" doesn\'t match format string "skip {{d}} more skip {{e}}."'
        self.assertRaisesRegexp(ParseException, expected_msg,
                                parser.get_extracted_param_value)

    def test_all_the_things(self):
        # this is the most insane example I could come up with
        alias_format = "{{ p0='http' }} g {{ p1=p }} a " + \
                       "{{ url }} {{ p2={'a':'b'} }} {{ p3={{ e.i }} }}"
        param_stream = "g a http://google.com {{ execution.id }} p4='testing' p5={'a':'c'}"
        parser = ActionAliasFormatParser(alias_format, param_stream)
        extracted_values = parser.get_extracted_param_value()
        self.assertEqual(extracted_values, {'p0': 'http', 'p1': 'p',
                                            'url': 'http://google.com',
                                            'p2': '{{ execution.id }}',
                                            'p3': '{{ e.i }}',
                                            'p4': 'testing', 'p5': "{'a':'c'}"})

    def test_command_doesnt_match_format_string(self):
        alias_format = 'foo bar ponies'
        param_stream = 'foo lulz ponies'
        parser = ActionAliasFormatParser(alias_format, param_stream)

        expected_msg = 'Command "foo lulz ponies" doesn\'t match format string "foo bar ponies"'
        self.assertRaisesRegexp(ParseException, expected_msg,
                                parser.get_extracted_param_value)

    def test_ending_parameters_matching(self):
        alias_format = 'foo bar'
        param_stream = 'foo bar pony1=foo pony2=bar'
        parser = ActionAliasFormatParser(alias_format, param_stream)
        extracted_values = parser.get_extracted_param_value()
        self.assertEqual(extracted_values, {'pony1': 'foo', 'pony2': 'bar'})

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

from st2tests.base import BaseActionAliasTestCase
from st2common.exceptions.content import ParseException
from st2common.models.db.actionalias import ActionAliasDB


class PackActionAliasUnitTestUtils(BaseActionAliasTestCase):
    action_alias_name = 'mock'

    def test_assertCommandMatchesFormatString(self):
        # Matches
        format_string = self.action_alias_db.formats[0]
        command = 'show last 3 metrics for my.host'
        self.assertCommandMatchesFormatString(format_string=format_string,
                                              command=command)

        # Doesn't match
        format_string = self.action_alias_db.formats[0]
        command = 'foo bar'

        expected_msg = ('Command "foo bar" doesn\'t match format string "show '
                        'last {{count}} metrics for {{server}}"')
        self.assertRaisesRegexp(AssertionError, expected_msg,
                                self.assertCommandMatchesFormatString,
                                format_string=format_string,
                                command=command)

    def test_assertExtractedParametersMatch_success(self):
        format_string = self.action_alias_db.formats[0]
        command = 'show last 3 metrics for my.host'
        expected_parameters = {
            'count': '3',
            'server': 'my.host'
        }
        self.assertExtractedParametersMatch(format_string=format_string,
                                            command=command,
                                            values=expected_parameters)

        format_string = self.action_alias_db.formats[0]
        command = 'show last 10 metrics for my.host.example'
        expected_parameters = {
            'count': '10',
            'server': 'my.host.example'
        }
        self.assertExtractedParametersMatch(format_string=format_string,
                                            command=command,
                                            values=expected_parameters)

    def test_assertExtractedParametersMatch_command_doesnt_match_format_string(self):
        format_string = self.action_alias_db.formats[0]
        command = 'show last foo'
        expected_parameters = {}
        expected_msg = ('Command "show last foo" doesn\'t match format string '
                        '"show last {{count}} metrics for {{server}}"')

        self.assertRaisesRegexp(ParseException, expected_msg,
                                self.assertExtractedParametersMatch,
                                format_string=format_string,
                                command=command,
                                values=expected_parameters)

    def test_assertCommandMatchesSingleFormatString(self):
        # Matches single format string
        format_strings = [
            'foo bar {{bar}}',
            'foo bar {{baz}} baz'
        ]
        command = 'foo bar a test=1'
        self.assertCommandMatchesSingleFormatString(format_strings=format_strings,
                                                    command=command)

        # Matches multiple format strings
        format_strings = [
            'foo bar {{bar}}',
            'foo bar {{baz}}'
        ]
        command = 'foo bar a test=1'

        expected_msg = ('Command "foo bar a test=1" matched multiple format '
                        'strings: foo bar {{bar}}, foo bar {{baz}}')
        self.assertRaisesRegexp(AssertionError, expected_msg,
                                self.assertCommandMatchesSingleFormatString,
                                format_strings=format_strings,
                                command=command)

    # Note: We mock the original method to make testing of all the edge cases easier
    def _get_action_alias_db_by_name(self, name):
        values = {
            'name': self.action_alias_name,
            'pack': 'mock',
            'formats': [
                'show last {{count}} metrics for {{server}}',
            ]
        }
        action_alias_db = ActionAliasDB(**values)
        return action_alias_db

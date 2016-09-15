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
import mock

from st2common.models.db.actionalias import ActionAliasDB
import st2common.util.actionalias_matching as matching


MemoryActionAliasDB = ActionAliasDB


@mock.patch.object(MemoryActionAliasDB, 'get_uid')
class ActionAliasTestCase(unittest2.TestCase):
    '''
    Test scenarios must consist of 80s movie quotes.
    '''
    def test_list_format_strings_from_aliases(self, mock):
        ALIASES = [
            MemoryActionAliasDB(name="kyle_reese", ref="terminator.1",
                                formats=["Come with me if you want to live"]),
            MemoryActionAliasDB(name="terminator", ref="terminator.2",
                                formats=["I need your {{item}}, your {{item2}}"
                                         " and your {{vehicle}}"])
        ]
        result = matching.list_format_strings_from_aliases(ALIASES)

        self.assertEqual(len(result), 2)

        self.assertEqual(result[0][0], "Come with me if you want to live")
        self.assertEqual(result[1][0],
                         "I need your {{item}}, your {{item2}} and"
                         " your {{vehicle}}")

    def test_list_format_strings_from_aliases_with_display(self, mock):
        ALIASES = [
            MemoryActionAliasDB(name="johnny_five_alive", ref="short_circuit.1", formats=[
                {'display': 'Number 5 is {{status}}',
                 'representation': ['Number 5 is {{status=alive}}']},
                'Hey, laser lips, your mama was a snow blower.']),
            MemoryActionAliasDB(name="i_feel_alive", ref="short_circuit.2",
                                formats=["How do I feel? I feel... {{status}}!"])
        ]
        result = matching.list_format_strings_from_aliases(ALIASES)

        self.assertEqual(len(result), 3)

        self.assertEqual(result[0][0], "Number 5 is {{status}}")
        self.assertEqual(result[0][1], "Number 5 is {{status=alive}}")
        self.assertEqual(result[1][0], "Hey, laser lips, your mama was a snow blower.")
        self.assertEqual(result[1][1], "Hey, laser lips, your mama was a snow blower.")
        self.assertEqual(result[2][0], "How do I feel? I feel... {{status}}!")
        self.assertEqual(result[2][1], "How do I feel? I feel... {{status}}!")

    def test_normalise_alias_format_string(self, mock):
        result = matching.normalise_alias_format_string(
            'Quite an experience to live in fear, isn\'t it?')

        self.assertEqual([result[0]], result[1])
        self.assertEqual(result[0], "Quite an experience to live in fear, isn't it?")

    def test_matching(self, mock):
        ALIASES = [
            MemoryActionAliasDB(name="spengler", ref="ghostbusters.1",
                                formats=["{{choice}} cross the {{target}}"]),
        ]
        COMMAND = "Don't cross the streams"
        match = matching.match_command_to_alias(COMMAND, ALIASES)
        self.assertEqual(len(match), 1)
        self.assertEqual(match[0][0].ref, "ghostbusters.1")
        self.assertEqual(match[0][2], "{{choice}} cross the {{target}}")

    # we need some more complex scenarios in here.

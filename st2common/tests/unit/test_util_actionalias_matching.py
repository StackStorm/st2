# Copyright 2020 The StackStorm Authors.
# Copyright 2019 Extreme Networks, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import absolute_import
import unittest
import mock

from st2common.models.db.actionalias import ActionAliasDB
import st2common.util.actionalias_matching as matching


MemoryActionAliasDB = ActionAliasDB


@mock.patch.object(MemoryActionAliasDB, "get_uid")
class ActionAliasTestCase(unittest.TestCase):
    """
    Test scenarios must consist of 80s movie quotes.
    """

    def test_list_format_strings_from_aliases(self, mock):
        ALIASES = [
            MemoryActionAliasDB(
                name="kyle_reese",
                ref="terminator.1",
                formats=["Come with me if you want to live"],
            ),
            MemoryActionAliasDB(
                name="terminator",
                ref="terminator.2",
                formats=[
                    "I need your {{item}}, your {{item2}}" " and your {{vehicle}}"
                ],
            ),
        ]
        result = matching.list_format_strings_from_aliases(ALIASES)

        self.assertEqual(len(result), 2)

        self.assertEqual(result[0]["display"], "Come with me if you want to live")
        self.assertEqual(
            result[1]["display"],
            "I need your {{item}}, your {{item2}} and" " your {{vehicle}}",
        )

    def test_list_format_strings_from_aliases_with_display(self, mock):
        ALIASES = [
            MemoryActionAliasDB(
                name="johnny_five_alive",
                ref="short_circuit.1",
                formats=[
                    {
                        "display": "Number 5 is {{status}}",
                        "representation": ["Number 5 is {{status=alive}}"],
                    },
                    "Hey, laser lips, your mama was a snow blower.",
                ],
            ),
            MemoryActionAliasDB(
                name="i_feel_alive",
                ref="short_circuit.2",
                formats=["How do I feel? I feel... {{status}}!"],
            ),
        ]
        result = matching.list_format_strings_from_aliases(ALIASES)

        self.assertEqual(len(result), 3)

        self.assertEqual(result[0]["display"], "Number 5 is {{status}}")
        self.assertEqual(result[0]["representation"], "Number 5 is {{status=alive}}")
        self.assertEqual(
            result[1]["display"], "Hey, laser lips, your mama was a snow blower."
        )
        self.assertEqual(
            result[1]["representation"], "Hey, laser lips, your mama was a snow blower."
        )
        self.assertEqual(result[2]["display"], "How do I feel? I feel... {{status}}!")
        self.assertEqual(
            result[2]["representation"], "How do I feel? I feel... {{status}}!"
        )

    def test_list_format_strings_from_aliases_with_display_only(self, mock):
        ALIASES = [
            MemoryActionAliasDB(
                name="andy", ref="the_goonies.1", formats=[{"display": "Watch this."}]
            ),
            MemoryActionAliasDB(
                name="andy",
                ref="the_goonies.2",
                formats=[{"display": "He's just like his {{relation}}."}],
            ),
        ]
        result = matching.list_format_strings_from_aliases(ALIASES)
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]["display"], "Watch this.")
        self.assertEqual(result[0]["representation"], "")
        self.assertEqual(result[1]["display"], "He's just like his {{relation}}.")
        self.assertEqual(result[1]["representation"], "")

    def test_list_format_strings_from_aliases_with_representation_only(self, mock):
        ALIASES = [
            MemoryActionAliasDB(
                name="data",
                ref="the_goonies.1",
                formats=[
                    {"representation": "That's okay daddy. You can't hug a {{object}}."}
                ],
            ),
            MemoryActionAliasDB(
                name="mr_wang",
                ref="the_goonies.2",
                formats=[{"representation": "You are my greatest invention."}],
            ),
        ]
        result = matching.list_format_strings_from_aliases(ALIASES)
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]["display"], None)
        self.assertEqual(
            result[0]["representation"],
            "That's okay daddy. You can't hug a {{object}}.",
        )
        self.assertEqual(result[1]["display"], None)
        self.assertEqual(result[1]["representation"], "You are my greatest invention.")

    def test_normalise_alias_format_string(self, mock):
        result = matching.normalise_alias_format_string(
            "Quite an experience to live in fear, isn't it?"
        )

        self.assertEqual([result[0]], result[1])
        self.assertEqual(result[0], "Quite an experience to live in fear, isn't it?")

    def test_normalise_alias_format_string_error(self, mock):
        alias_list = ["Quite an experience to live in fear, isn't it?"]
        expected_msg = (
            "alias_format '%s' is neither a dictionary or string type."
            % repr(alias_list)
        )

        with self.assertRaises(TypeError) as cm:
            matching.normalise_alias_format_string(alias_list)

            self.assertEqual(str(cm), expected_msg)

    def test_matching(self, mock):
        ALIASES = [
            MemoryActionAliasDB(
                name="spengler",
                ref="ghostbusters.1",
                formats=["{{choice}} cross the {{target}}"],
            ),
        ]
        COMMAND = "Don't cross the streams"
        match = matching.match_command_to_alias(COMMAND, ALIASES)
        self.assertEqual(len(match), 1)
        self.assertEqual(match[0]["alias"].ref, "ghostbusters.1")
        self.assertEqual(match[0]["representation"], "{{choice}} cross the {{target}}")

    # we need some more complex scenarios in here.

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
import mongoengine as me

from st2common.constants.types import ResourceType
from st2common.models.db import stormbase
import st2common.util.actionalias_matching as matching


class MemoryActionAliasDB(stormbase.StormFoundationDB, stormbase.ContentPackResourceMixin,
                          stormbase.UIDFieldMixin):
    """
    Database entity that represent an Alias for an action.

    Attribute:
        pack: Pack to which this alias belongs to.
        name: Alias name.
        ref: Alias reference (pack + name).
        enabled: A flag indicating whether this alias is enabled in the system.
        action_ref: Reference of an action this alias belongs to.
        formats: Alias format strings.
    """

    RESOURCE_TYPE = ResourceType.ACTION
    UID_FIELDS = ['pack', 'name']

    name = me.StringField(required=True)
    ref = me.StringField(required=True)
    description = me.StringField()
    pack = me.StringField(
        required=True,
        help_text='Name of the content pack.',
        unique_with='name')
    enabled = me.BooleanField(
        required=True, default=True,
        help_text='A flag indicating whether the action alias is enabled.')
    action_ref = me.StringField(
        required=True,
        help_text='Reference of the Action map this alias.')
    formats = me.ListField(
        help_text='Possible parameter formats that an alias supports.')
    ack = me.DictField(
        help_text='Parameters pertaining to the acknowledgement message.'
    )
    result = me.DictField(
        help_text='Parameters pertaining to the execution result message.'
    )
    extra = me.DictField(
        help_text='Additional parameters (usually adapter-specific) not covered in the schema.'
    )

    def __init__(self, *args, **values):
        super(MemoryActionAliasDB, self).__init__(*args, **values)


class ActionAliasTestCase(unittest2.TestCase):
    '''
    Test scenarios must consist of 80s movie quotes.
    '''
    def test_list_format_strings_from_aliases(self):
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

    def test_list_format_strings_from_aliases_with_display(self):
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

    def test_normalise_alias_format_string(self):
        result = matching.normalise_alias_format_string(
            'Quite an experience to live in fear, isn\'t it?')

        self.assertEqual([result[0]], result[1])
        self.assertEqual(result[0], "Quite an experience to live in fear, isn't it?")

    def test_matching(self):
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

if __name__ == '__main__':
    unittest2.main()

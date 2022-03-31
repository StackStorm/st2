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

from st2tests.base import BaseActionAliasTestCase


class PackGet(BaseActionAliasTestCase):
    action_alias_name = "pack_get"

    def test_alias_pack_get(self):
        format_string = self.action_alias_db.formats[0]["representation"][0]
        format_strings = self.action_alias_db.get_format_strings()

        command = "pack get st2"
        expected_parameters = {"pack": "st2"}

        self.assertExtractedParametersMatch(
            format_string=format_string, command=command, parameters=expected_parameters
        )
        self.assertCommandMatchesExactlyOneFormatString(
            format_strings=format_strings, command=command
        )


class PackInstall(BaseActionAliasTestCase):
    action_alias_name = "pack_install"

    def test_alias_pack_install(self):
        format_string = self.action_alias_db.formats[0]["representation"][0]

        command = "pack install st2"
        expected_parameters = {"packs": "st2"}

        self.assertExtractedParametersMatch(
            format_string=format_string, command=command, parameters=expected_parameters
        )


class PackSearch(BaseActionAliasTestCase):
    action_alias_name = "pack_search"

    def test_alias_pack_search(self):
        format_string = self.action_alias_db.formats[0]["representation"][0]
        format_strings = self.action_alias_db.get_format_strings()

        command = "pack search st2"
        expected_parameters = {"query": "st2"}

        self.assertExtractedParametersMatch(
            format_string=format_string, command=command, parameters=expected_parameters
        )
        self.assertCommandMatchesExactlyOneFormatString(
            format_strings=format_strings, command=command
        )


class PackShow(BaseActionAliasTestCase):
    action_alias_name = "pack_show"

    def test_alias_pack_show(self):
        format_string = self.action_alias_db.formats[0]["representation"][0]
        format_strings = self.action_alias_db.get_format_strings()

        command = "pack show st2"
        expected_parameters = {"pack": "st2"}

        self.assertExtractedParametersMatch(
            format_string=format_string, command=command, parameters=expected_parameters
        )
        self.assertCommandMatchesExactlyOneFormatString(
            format_strings=format_strings, command=command
        )

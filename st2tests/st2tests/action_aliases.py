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

import os

from st2common.content.loader import ContentPackLoader
from st2common.exceptions.content import ParseException
from st2common.bootstrap.aliasesregistrar import AliasesRegistrar
from st2common.models.utils.action_alias_utils import extract_parameters_for_action_alias_db
from st2common.models.utils.action_alias_utils import extract_parameters
from st2tests.pack_resource import BasePackResourceTestCase

__all__ = [
    'BaseActionAliasTestCase'
]


class BaseActionAliasTestCase(BasePackResourceTestCase):
    """
    Base class for testing action aliases.
    """

    action_alias_name = None
    action_alias_db = None

    def setUp(self):
        super(BaseActionAliasTestCase, self).setUp()

        if not self.action_alias_name:
            raise ValueError('"action_alias_name" class attribute needs to be provided')

        self.action_alias_db = self._get_action_alias_db_by_name(name=self.action_alias_name)

    def assertCommandMatchesExactlyOneFormatString(self, format_strings, command):
        """
        Assert that the provided command matches exactly one format string from the provided list.
        """
        matched_format_strings = []

        for format_string in format_strings:
            try:
                extract_parameters(format_str=format_string,
                                   param_stream=command)
            except ParseException:
                continue

            matched_format_strings.append(format_string)

        if len(matched_format_strings) == 0:
            msg = ('Command "%s" didn\'t match any of the provided format strings' % (command))
            raise AssertionError(msg)
        elif len(matched_format_strings) > 1:
            msg = ('Command "%s" matched multiple format strings: %s' %
                   (command, ', '.join(matched_format_strings)))
            raise AssertionError(msg)

    def assertExtractedParametersMatch(self, format_string, command, parameters):
        """
        Assert that the provided command matches the format string.

        In addition to that, also assert that the parameters which have been extracted from the
        user input (command) also match the provided parameters.
        """
        extracted_params = extract_parameters_for_action_alias_db(
            action_alias_db=self.action_alias_db,
            format_str=format_string,
            param_stream=command)

        if extracted_params != parameters:
            msg = ('Extracted parameters from command string "%s" against format string "%s"'
                   ' didn\'t match the provided parameters: ' % (command, format_string))

            # Note: We intercept the exception so we can can include diff for the dictionaries
            try:
                self.assertEqual(extracted_params, parameters)
            except AssertionError as e:
                msg += str(e)

            raise AssertionError(msg)

    def _get_action_alias_db_by_name(self, name):
        """
        Retrieve ActionAlias DB object for the provided alias name.
        """
        base_pack_path = self._get_base_pack_path()
        _, pack = os.path.split(base_pack_path)

        pack_loader = ContentPackLoader()
        registrar = AliasesRegistrar(use_pack_cache=False)

        aliases_path = pack_loader.get_content_from_pack(pack_dir=base_pack_path,
                                                         content_type='aliases')
        aliases = registrar._get_aliases_from_pack(aliases_dir=aliases_path)
        for alias_path in aliases:
            action_alias_db = registrar._get_action_alias_db(pack=pack,
                                                             action_alias=alias_path)

            if action_alias_db.name == name:
                return action_alias_db

        raise ValueError('Alias with name "%s" not found' % (name))

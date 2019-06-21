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

import os

import six
import mock

from st2common.content import utils as content_utils
from st2common.bootstrap.configsregistrar import ConfigsRegistrar
from st2common.persistence.pack import Pack
from st2common.persistence.pack import Config
from st2tests.api import SUPER_SECRET_PARAMETER

from st2tests.base import CleanDbTestCase
from st2tests import fixturesloader


__all__ = [
    'ConfigsRegistrarTestCase'
]

PACK_1_PATH = os.path.join(fixturesloader.get_fixtures_packs_base_path(), 'dummy_pack_1')
PACK_6_PATH = os.path.join(fixturesloader.get_fixtures_packs_base_path(), 'dummy_pack_6')
PACK_19_PATH = os.path.join(fixturesloader.get_fixtures_packs_base_path(), 'dummy_pack_19')
PACK_11_PATH = os.path.join(fixturesloader.get_fixtures_packs_base_path(), 'dummy_pack_11')


class ConfigsRegistrarTestCase(CleanDbTestCase):
    def test_register_configs_for_all_packs(self):
        # Verify DB is empty
        pack_dbs = Pack.get_all()
        config_dbs = Config.get_all()

        self.assertEqual(len(pack_dbs), 0)
        self.assertEqual(len(config_dbs), 0)

        registrar = ConfigsRegistrar(use_pack_cache=False)
        registrar._pack_loader.get_packs = mock.Mock()
        registrar._pack_loader.get_packs.return_value = {'dummy_pack_1': PACK_1_PATH}
        packs_base_paths = content_utils.get_packs_base_paths()
        registrar.register_from_packs(base_dirs=packs_base_paths)

        # Verify pack and schema have been registered
        pack_dbs = Pack.get_all()
        config_dbs = Config.get_all()

        self.assertEqual(len(pack_dbs), 1)
        self.assertEqual(len(config_dbs), 1)

        config_db = config_dbs[0]
        self.assertEqual(config_db.values['api_key'], '{{st2kv.user.api_key}}')
        self.assertEqual(config_db.values['api_secret'], SUPER_SECRET_PARAMETER)
        self.assertEqual(config_db.values['region'], 'us-west-1')

    def test_register_all_configs_invalid_config_no_config_schema(self):
        # verify_ configs is on, but ConfigSchema for the pack doesn't exist so
        # validation should proceed normally

        # Verify DB is empty
        pack_dbs = Pack.get_all()
        config_dbs = Config.get_all()

        self.assertEqual(len(pack_dbs), 0)
        self.assertEqual(len(config_dbs), 0)

        registrar = ConfigsRegistrar(use_pack_cache=False, validate_configs=False)
        registrar._pack_loader.get_packs = mock.Mock()
        registrar._pack_loader.get_packs.return_value = {'dummy_pack_6': PACK_6_PATH}
        packs_base_paths = content_utils.get_packs_base_paths()
        registrar.register_from_packs(base_dirs=packs_base_paths)

        # Verify pack and schema have been registered
        pack_dbs = Pack.get_all()
        config_dbs = Config.get_all()

        self.assertEqual(len(pack_dbs), 1)
        self.assertEqual(len(config_dbs), 1)

    def test_register_all_configs_with_config_schema_validation_validation_failure_1(self):
        # Verify DB is empty
        pack_dbs = Pack.get_all()
        config_dbs = Config.get_all()

        self.assertEqual(len(pack_dbs), 0)
        self.assertEqual(len(config_dbs), 0)

        registrar = ConfigsRegistrar(use_pack_cache=False, fail_on_failure=True,
                                     validate_configs=True)
        registrar._pack_loader.get_packs = mock.Mock()
        registrar._pack_loader.get_packs.return_value = {'dummy_pack_6': PACK_6_PATH}

        # Register ConfigSchema for pack
        registrar._register_pack_db = mock.Mock()
        registrar._register_pack(pack_name='dummy_pack_5', pack_dir=PACK_6_PATH)
        packs_base_paths = content_utils.get_packs_base_paths()

        if six.PY3:
            expected_msg = ('Failed validating attribute "regions" in config for pack '
                            '"dummy_pack_6" (.*?): 1000 is not of type \'array\'')
        else:
            expected_msg = ('Failed validating attribute "regions" in config for pack '
                            '"dummy_pack_6" (.*?): 1000 is not of type u\'array\'')

        self.assertRaisesRegexp(ValueError, expected_msg,
                                registrar.register_from_packs,
                                base_dirs=packs_base_paths)

    def test_register_all_configs_with_config_schema_validation_validation_failure_2(self):
        # Verify DB is empty
        pack_dbs = Pack.get_all()
        config_dbs = Config.get_all()

        self.assertEqual(len(pack_dbs), 0)
        self.assertEqual(len(config_dbs), 0)

        registrar = ConfigsRegistrar(use_pack_cache=False, fail_on_failure=True,
                                     validate_configs=True)
        registrar._pack_loader.get_packs = mock.Mock()
        registrar._pack_loader.get_packs.return_value = {'dummy_pack_19': PACK_19_PATH}

        # Register ConfigSchema for pack
        registrar._register_pack_db = mock.Mock()
        registrar._register_pack(pack_name='dummy_pack_19', pack_dir=PACK_19_PATH)
        packs_base_paths = content_utils.get_packs_base_paths()

        if six.PY3:
            expected_msg = ('Failed validating attribute "instances.0.alias" in config for pack '
                            '"dummy_pack_19" (.*?): {\'not\': \'string\'} is not of type '
                            '\'string\'')
        else:
            expected_msg = ('Failed validating attribute "instances.0.alias" in config for pack '
                            '"dummy_pack_19" (.*?): {\'not\': \'string\'} is not of type '
                            'u\'string\'')

        self.assertRaisesRegexp(ValueError, expected_msg,
                                registrar.register_from_packs,
                                base_dirs=packs_base_paths)

    def test_register_all_configs_with_config_schema_validation_validation_failure_3(self):
        # Verify DB is empty
        pack_dbs = Pack.get_all()
        config_dbs = Config.get_all()

        self.assertEqual(len(pack_dbs), 0)
        self.assertEqual(len(config_dbs), 0)

        registrar = ConfigsRegistrar(use_pack_cache=False, fail_on_failure=True,
                                     validate_configs=True)
        registrar._pack_loader.get_packs = mock.Mock()
        registrar._pack_loader.get_packs.return_value = {'dummy_pack_11': PACK_11_PATH}

        # Register ConfigSchema for pack
        registrar._register_pack_db = mock.Mock()
        registrar._register_pack(pack_name='dummy_pack_11', pack_dir=PACK_11_PATH)
        packs_base_paths = content_utils.get_packs_base_paths()

        expected_msg = ('Values specified as "secret: True" in config schema are automatically '
                        'decrypted by default. Use of "decrypt_kv" jinja filter is not allowed '
                        'for such values.')

        self.assertRaisesRegexp(ValueError, expected_msg,
                                registrar.register_from_packs,
                                base_dirs=packs_base_paths)

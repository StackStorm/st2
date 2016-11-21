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

import copy

from st2tests.base import DbTestCase
from st2common.persistence.pack import Config
from st2common.services.config import set_datastore_value_for_config_key
from st2common.util.config_loader import ContentPackConfigLoader

__all__ = [
    'ContentPackConfigLoaderTestCase'
]


class ContentPackConfigLoaderTestCase(DbTestCase):
    register_packs = True
    register_pack_configs = True

    def test_get_config_all_values_are_loaded_from_local_config(self):
        # Test a scenario where all the values are loaded from pack local config and pack global
        # config (pack name.yaml) doesn't exist
        # Test a scenario where no values are overridden in the datastore
        loader = ContentPackConfigLoader(pack_name='dummy_pack_4')
        config = loader.get_config()

        expected_config = {
            'api_key': '',
            'api_secret': '',
            'regions': ['us-west-1', 'us-east-1'],
            'private_key_path': None
        }
        self.assertEqual(config, expected_config)

    def test_get_config_some_values_overriden_in_datastore(self):
        # Test a scenario where some values are overriden in datastore via pack
        # flobal config
        kvp_db = set_datastore_value_for_config_key(pack_name='dummy_pack_5',
                                                    key_name='api_secret',
                                                    value='some_api_secret',
                                                    secret=True,
                                                    user='joe')

        # This is a secret so a value should be encrypted
        self.assertTrue(kvp_db.value != 'some_api_secret')
        self.assertTrue(len(kvp_db.value) > len('some_api_secret') * 2)
        self.assertTrue(kvp_db.secret)

        kvp_db = set_datastore_value_for_config_key(pack_name='dummy_pack_5',
                                                    key_name='private_key_path',
                                                    value='some_private_key')
        self.assertEqual(kvp_db.value, 'some_private_key')
        self.assertFalse(kvp_db.secret)

        loader = ContentPackConfigLoader(pack_name='dummy_pack_5', user='joe')
        config = loader.get_config()

        # regions is provided in the pack global config
        # api_secret is dynamically loaded from the datastore for a particular user
        expected_config = {
            'api_key': 'some_api_key',
            'api_secret': 'some_api_secret',
            'regions': ['us-west-1'],
            'region': 'default-region-value',
            'private_key_path': 'some_private_key'
        }

        self.assertEqual(config, expected_config)

    def test_get_config_default_value_from_config_schema_is_used(self):
        # No value is provided for "region" in the config, default value from config schema
        # should be used
        loader = ContentPackConfigLoader(pack_name='dummy_pack_5')
        config = loader.get_config()
        self.assertEqual(config['region'], 'default-region-value')

        # Here a default value is specified in schema but an explicit value is provided in the
        # config
        loader = ContentPackConfigLoader(pack_name='dummy_pack_1')
        config = loader.get_config()
        self.assertEqual(config['region'], 'us-west-1')

    def test_get_config_nested_schema_default_values_from_config_schema_are_used(self):
        # Special case for more complex config schemas with attributes ntesting.
        # Validate that the default values are also used for one level nested object properties.
        pack_name = 'dummy_pack_schema_with_nested_object'

        # 1. None of the nested object values are provided
        loader = ContentPackConfigLoader(pack_name=pack_name)
        config = loader.get_config()

        expected_config = {
            'api_key': '',
            'api_secret': '',
            'regions': ['us-west-1', 'us-east-1'],
            'auth_settings': {
                'host': '127.0.0.3',
                'port': 8080,
                'device_uids': ['a', 'b', 'c']
            }
        }
        self.assertEqual(config, expected_config)

        # 2. Some of the nested object values are provided (host, port)
        config_db = Config.get_by_pack(value=pack_name)
        original_values = copy.deepcopy(config_db.values)

        config_db.values = {}
        config_db.values.update(original_values)
        config_db.values['auth_settings'] = {}
        config_db.values['auth_settings']['host'] = '127.0.0.6'
        config_db.values['auth_settings']['port'] = 9090
        config_db = Config.add_or_update(config_db)

        loader = ContentPackConfigLoader(pack_name=pack_name)
        config = loader.get_config()

        expected_config = {
            'api_key': '',
            'api_secret': '',
            'regions': ['us-west-1', 'us-east-1'],
            'auth_settings': {
                'host': '127.0.0.6',
                'port': 9090,
                'device_uids': ['a', 'b', 'c']
            }
        }
        self.assertEqual(config, expected_config)

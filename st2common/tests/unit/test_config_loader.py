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

from mock import Mock

from st2tests.base import CleanDbTestCase
from st2common.util.config_loader import ContentPackConfigLoader
from st2common.services import config as config_service

__all__ = [
    'ConfigLoaderTestCase'
]


class ConfigLoaderTestCase(CleanDbTestCase):
    def test_get_config_all_values_are_loaded_from_config(self):
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

    def test_get_config_some_values_are_overriden_in_datastore(self):
        # Test a scenario where some values are overridden in the datastore
        # "api_key" and "api_secret" are overridden aka provided in the datastore
        loader = ContentPackConfigLoader(pack_name='dummy_pack_4')

        # TODO: Refactor this in to services utility functions
        config_service.set_datastore_value_for_config_key(pack_name='dummy_pack_4',
                                                          key_name='api_key',
                                                          value='testapikey1')
        config_service.set_datastore_value_for_config_key(pack_name='dummy_pack_4',
                                                          key_name='api_secret',
                                                          value='testapisecret1')

        config = loader.get_config()

        expected_config = {
            'api_key': 'testapikey1',
            'api_secret': 'testapisecret1',
            'regions': ['us-west-1', 'us-east-1'],
            'private_key_path': None
        }
        self.assertEqual(config, expected_config)

        # Also override regions config item
        config_service.set_datastore_value_for_config_key(pack_name='dummy_pack_4',
                                                          key_name='regions',
                                                          value=['lon'])

        config = loader.get_config()

        expected_config = {
            'api_key': 'testapikey1',
            'api_secret': 'testapisecret1',
            'regions': ['lon'],
            'private_key_path': None
        }
        self.assertEqual(config, expected_config)

    def test_get_config_config_not_available(self):
        loader = ContentPackConfigLoader(pack_name='dummy_pack_4')
        loader._config_parser.get_config = Mock()
        loader._config_parser.get_config.return_value = None

        config = loader.get_config()
        self.assertEqual(config, {})

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

from st2tests.base import DbTestCase
from st2common.services.config import set_datastore_value_for_config_key
from st2common.constants.keyvalue import USER_SCOPE
from st2common.constants.keyvalue import SYSTEM_SCOPE
from st2common.models.db.keyvalue import KeyValuePairDB
from st2common.persistence.keyvalue import KeyValuePair
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

        # TODO: Utilize util methods which serialize the key, value, etc
        set_datastore_value_for_config_key(pack_name='dummy_pack_5',
                                           key_name='api_secret',
                                           user='joe',
                                           value='some_api_secret')

        set_datastore_value_for_config_key(pack_name='dummy_pack_5',
                                           key_name='private_key_path',
                                           value='some_private_key')

        loader = ContentPackConfigLoader(pack_name='dummy_pack_5', user='joe')
        config = loader.get_config()

        # regions is provided in the pack global config
        # api_secret is dynamically loaded from the datastore for a particular user
        expected_config = {
            'api_key': 'some_api_key',
            'api_secret': 'some_api_secret',
            'regions': ['us-west-1'],
            'private_key_path': 'some_private_key'
        }

        self.assertEqual(config, expected_config)

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

import json

from st2tests.base import CleanDbTestCase
from st2common.models.db.keyvalue import KeyValuePairDB
from st2common.persistence.keyvalue import KeyValuePair
from st2common.util.config_loader import ContentPackConfigLoader

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
        name = loader._get_datastore_key_name(pack_name='dummy_pack_4', key_name='api_key')
        value = json.dumps({'value': 'testapikey1'})
        kvp_db = KeyValuePairDB(name=name, value=value)
        kvp_db = KeyValuePair.add_or_update(kvp_db)

        name = loader._get_datastore_key_name(pack_name='dummy_pack_4', key_name='api_secret')
        value = json.dumps({'value': 'testapisecret1'})
        kvp_db = KeyValuePairDB(name=name, value=value)
        kvp_db = KeyValuePair.add_or_update(kvp_db)

        config = loader.get_config()

        expected_config = {
            'api_key': 'testapikey1',
            'api_secret': 'testapisecret1',
            'regions': ['us-west-1', 'us-east-1'],
            'private_key_path': None
        }
        self.assertEqual(config, expected_config)

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

import mock

from st2common.content import utils as content_utils
from st2common.bootstrap.base import ResourceRegistrar
from st2common.persistence.pack import Pack
from st2common.persistence.pack import ConfigSchema

from st2tests import DbTestCase
from st2tests import fixturesloader


__all__ = [
    'ResourceRegistrarTestCase'
]

PACK_PATH = os.path.join(fixturesloader.get_fixtures_packs_base_path(), 'dummy_pack_1')


class ResourceRegistrarTestCase(DbTestCase):
    def test_register_packs(self):
        # Verify DB is empty
        pack_dbs = Pack.get_all()
        config_schema_dbs = ConfigSchema.get_all()

        self.assertEqual(len(pack_dbs), 0)
        self.assertEqual(len(config_schema_dbs), 0)

        registrar = ResourceRegistrar(use_pack_cache=False)
        registrar._pack_loader.get_packs = mock.Mock()
        registrar._pack_loader.get_packs.return_value = {'dummy_pack_1': PACK_PATH}
        packs_base_paths = content_utils.get_packs_base_paths()
        registrar.register_packs(base_dirs=packs_base_paths)

        # Verify pack and schema have been registered
        pack_dbs = Pack.get_all()
        config_schema_dbs = ConfigSchema.get_all()

        self.assertEqual(len(pack_dbs), 1)
        self.assertEqual(len(config_schema_dbs), 1)

        self.assertEqual(pack_dbs[0].name, 'dummy_pack_1')
        self.assertTrue('api_key' in config_schema_dbs[0].attributes)
        self.assertTrue('api_secret' in config_schema_dbs[0].attributes)

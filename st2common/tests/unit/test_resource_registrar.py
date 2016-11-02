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
from jsonschema import ValidationError

from st2common.content import utils as content_utils
from st2common.bootstrap.base import ResourceRegistrar
from st2common.persistence.pack import Pack
from st2common.persistence.pack import ConfigSchema

from st2tests.base import CleanDbTestCase
from st2tests import fixturesloader


__all__ = [
    'ResourceRegistrarTestCase'
]

PACK_PATH_1 = os.path.join(fixturesloader.get_fixtures_packs_base_path(), 'dummy_pack_1')
PACK_PATH_6 = os.path.join(fixturesloader.get_fixtures_packs_base_path(), 'dummy_pack_6')
PACK_PATH_7 = os.path.join(fixturesloader.get_fixtures_packs_base_path(), 'dummy_pack_7')
PACK_PATH_8 = os.path.join(fixturesloader.get_fixtures_packs_base_path(), 'dummy_pack_8')
PACK_PATH_9 = os.path.join(fixturesloader.get_fixtures_packs_base_path(), 'dummy_pack_9')
PACK_PATH_10 = os.path.join(fixturesloader.get_fixtures_packs_base_path(), 'dummy_pack_10')
PACK_PATH_11 = os.path.join(fixturesloader.get_fixtures_packs_base_path(), 'dummy_pack_11')


class ResourceRegistrarTestCase(CleanDbTestCase):
    def test_register_packs(self):
        # Verify DB is empty
        pack_dbs = Pack.get_all()
        config_schema_dbs = ConfigSchema.get_all()

        self.assertEqual(len(pack_dbs), 0)
        self.assertEqual(len(config_schema_dbs), 0)

        registrar = ResourceRegistrar(use_pack_cache=False)
        registrar._pack_loader.get_packs = mock.Mock()
        registrar._pack_loader.get_packs.return_value = {'dummy_pack_1': PACK_PATH_1}
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

    def test_register_pack_pack_ref(self):
        # Verify DB is empty
        pack_dbs = Pack.get_all()

        self.assertEqual(len(pack_dbs), 0)

        registrar = ResourceRegistrar(use_pack_cache=False)
        registrar._pack_loader.get_packs = mock.Mock()
        registrar._pack_loader.get_packs.return_value = {
            'dummy_pack_1': PACK_PATH_1,
            'dummy_pack_6': PACK_PATH_6
        }
        packs_base_paths = content_utils.get_packs_base_paths()
        registrar.register_packs(base_dirs=packs_base_paths)

        # Ref is provided
        pack_db = Pack.get_by_name('dummy_pack_6')
        self.assertEqual(pack_db.ref, 'dummy_pack_6_ref')

        # Ref is not provided, directory name should be used
        pack_db = Pack.get_by_name('dummy_pack_1')
        self.assertEqual(pack_db.ref, 'dummy_pack_1')

        # "ref" is not provided, but "name" is
        registrar._register_pack_db(pack_name=None, pack_dir=PACK_PATH_7)

        pack_db = Pack.get_by_name('dummy_pack_7_name')
        self.assertEqual(pack_db.ref, 'dummy_pack_7_name')

        # "ref" is not provided and "name" contains invalid characters
        expected_msg = 'contains invalid characters'
        self.assertRaisesRegexp(ValueError, expected_msg, registrar._register_pack_db,
                                pack_name=None, pack_dir=PACK_PATH_8)

    def test_register_pack_pack_stackstorm_version_and_future_parameters(self):
        # Verify DB is empty
        pack_dbs = Pack.get_all()
        self.assertEqual(len(pack_dbs), 0)

        registrar = ResourceRegistrar(use_pack_cache=False)
        registrar._pack_loader.get_packs = mock.Mock()
        registrar._pack_loader.get_packs.return_value = {'dummy_pack_9': PACK_PATH_9}
        packs_base_paths = content_utils.get_packs_base_paths()
        registrar.register_packs(base_dirs=packs_base_paths)

        # Dependencies, stackstorm_version and future values
        pack_db = Pack.get_by_name('dummy_pack_9_deps')
        self.assertEqual(pack_db.dependencies, ['core=0.2.0'])
        self.assertEqual(pack_db.stackstorm_version, '>=1.6dev, <2.2')
        self.assertEqual(pack_db.system, {'centos': {'foo': '>= 1.0'}})

        # Note: We only store paramters which are defined in the schema, all other custom user 
        # defined attributes are ignored
        self.assertTrue(not hasattr(pack_db, 'future'))
        self.assertTrue(not hasattr(pack_db, 'this'))

        # Wrong characters in the required st2 version
        expected_msg = "'wrongstackstormversion' does not match"
        self.assertRaisesRegexp(ValidationError, expected_msg, registrar._register_pack_db,
                                pack_name=None, pack_dir=PACK_PATH_10)

    def test_register_pack_old_style_non_semver_version_is_normalized_to_valid_version(self):
        # Verify DB is empty
        pack_dbs = Pack.get_all()
        self.assertEqual(len(pack_dbs), 0)

        registrar = ResourceRegistrar(use_pack_cache=False)
        registrar._pack_loader.get_packs = mock.Mock()
        registrar._pack_loader.get_packs.return_value = {'dummy_pack_11': PACK_PATH_11}
        packs_base_paths = content_utils.get_packs_base_paths()
        registrar.register_packs(base_dirs=packs_base_paths)

        # Non-semver valid version 0.2 should be normalize to 0.2.0
        pack_db = Pack.get_by_name('dummy_pack_11')
        self.assertEqual(pack_db.version, '0.2.0')

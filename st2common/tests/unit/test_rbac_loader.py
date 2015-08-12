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

import unittest2
import mock
import jsonschema

from st2tests import config
from st2tests.fixturesloader import get_fixtures_base_path
from st2common.rbac.loader import RBACDefinitionsLoader

__all__ = [
    'RBACDefinitionsLoaderTestCase'
]


class RBACDefinitionsLoaderTestCase(unittest2.TestCase):
    @classmethod
    def setUpClass(cls):
        config.parse_args()

    def test_load_role_definition_success(self):
        loader = RBACDefinitionsLoader()

        file_path = os.path.join(get_fixtures_base_path(), 'rbac/roles/role_three.yaml')
        role_definition_api = loader.load_role_definition_from_file(file_path=file_path)

        self.assertEqual(role_definition_api.name, 'role_three')
        self.assertTrue('all the pack permissions on pack dummy_pack_1' in role_definition_api.description)
        self.assertEqual(len(role_definition_api.permission_grants), 3)
        self.assertEqual(role_definition_api.permission_grants[0]['resource_uid'], 'pack:dummy_pack_1')
        self.assertEqual(role_definition_api.permission_grants[1]['resource_uid'], 'pack:dummy_pack_2')
        self.assertTrue('rule_view' in role_definition_api.permission_grants[1]['permission_types'])
        self.assertEqual(role_definition_api.permission_grants[2]['permission_types'], ['action_execute'])

    def test_load_role_definition_validation_error(self):
        loader = RBACDefinitionsLoader()

        # Invalid permission which doesn't apply to the resource in question
        file_path = os.path.join(get_fixtures_base_path(), 'rbac_invalid/roles/role_one.yaml')
        expected_msg = 'Invalid permission type "rule_all" for resource type "action"'
        self.assertRaisesRegexp(ValueError, expected_msg, loader.load_role_definition_from_file,
                                file_path=file_path)

        # Invalid permission type which doesn't exist
        file_path = os.path.join(get_fixtures_base_path(), 'rbac_invalid/roles/role_two.yaml')
        expected_msg = '.*Failed validating \'enum\'.*'
        self.assertRaisesRegexp(jsonschema.ValidationError, expected_msg, loader.load_role_definition_from_file,
                                file_path=file_path)

    def test_load_user_role_assignments_success(self):
        loader = RBACDefinitionsLoader()

        file_path = os.path.join(get_fixtures_base_path(), 'rbac/assignments/user3.yaml')
        user_role_assignment_api = loader.load_user_role_assignments_from_file(file_path=file_path)

        self.assertEqual(user_role_assignment_api.username, 'user3')
        self.assertEqual(user_role_assignment_api.description, 'Observer assignments')
        self.assertEqual(user_role_assignment_api.roles, ['observer'])

    def test_load_role_definitions_duplicate_role_definition(self):
        loader = RBACDefinitionsLoader()

        # Try to load all the roles from disk where two definitions refer to the same role
        file_path1 = os.path.join(get_fixtures_base_path(), 'rbac_invalid/roles/role_three1.yaml')
        file_path2 = os.path.join(get_fixtures_base_path(), 'rbac_invalid/roles/role_three2.yaml')
        file_paths = [file_path1, file_path2]

        loader._get_role_definitions_file_paths = mock.Mock()
        loader._get_role_definitions_file_paths.return_value = file_paths

        expected_msg = 'Duplicate definition file found for role "role_three_name_conflict"'
        self.assertRaisesRegexp(ValueError, expected_msg, loader.load_role_definitions)

    def test_load_user_role_assignments_duplicate_user_definition(self):
        loader = RBACDefinitionsLoader()

        # Try to load all the user role assignments from disk where two definitions refer to the
        # same user
        file_path1 = os.path.join(get_fixtures_base_path(), 'rbac_invalid/assignments/user_foo1.yaml')
        file_path2 = os.path.join(get_fixtures_base_path(), 'rbac_invalid/assignments/user_foo2.yaml')
        file_paths = [file_path1, file_path2]

        loader._get_role_assiginments_file_paths = mock.Mock()
        loader._get_role_assiginments_file_paths.return_value = file_paths

        expected_msg = 'Duplicate definition file found for user "userfoo"'
        self.assertRaisesRegexp(ValueError, expected_msg, loader.load_user_role_assignments)

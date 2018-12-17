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

from __future__ import absolute_import
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
        self.assertTrue('all the pack permissions on pack dummy_pack_1' in
                        role_definition_api.description)
        self.assertEqual(len(role_definition_api.permission_grants), 4)
        self.assertEqual(role_definition_api.permission_grants[0]['resource_uid'],
                         'pack:dummy_pack_1')
        self.assertEqual(role_definition_api.permission_grants[1]['resource_uid'],
                         'pack:dummy_pack_2')
        self.assertTrue('rule_view' in role_definition_api.permission_grants[1]['permission_types'])
        self.assertEqual(role_definition_api.permission_grants[2]['permission_types'],
                         ['action_execute'])
        self.assertEqual(role_definition_api.permission_grants[3]['resource_uid'], None)
        self.assertEqual(role_definition_api.permission_grants[3]['permission_types'],
                         ['action_list', 'rule_list'])

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
        self.assertRaisesRegexp(jsonschema.ValidationError, expected_msg,
                                loader.load_role_definition_from_file, file_path=file_path)

        # Only list permissions can be used without a resource_uid
        file_path = os.path.join(get_fixtures_base_path(), 'rbac_invalid/roles/role_four.yaml')
        expected_msg = ('Invalid permission type "action_create". Valid global '
                        'permission types which can be used without a resource id are:')
        self.assertRaisesRegexp(ValueError, expected_msg,
                                loader.load_role_definition_from_file, file_path=file_path)

    def test_load_role_definition_with_all_global_permission_types(self):
        loader = RBACDefinitionsLoader()

        file_path = os.path.join(get_fixtures_base_path(), 'rbac/roles/role_seven.yaml')
        role_definition_api = loader.load_role_definition_from_file(file_path=file_path)

        self.assertEqual(role_definition_api.name, 'role_seven')

    def test_load_user_role_assignments_success(self):
        loader = RBACDefinitionsLoader()

        file_path = os.path.join(get_fixtures_base_path(), 'rbac/assignments/user3.yaml')
        user_role_assignment_api = loader.load_user_role_assignments_from_file(file_path=file_path)

        self.assertEqual(user_role_assignment_api.username, 'user3')
        self.assertEqual(user_role_assignment_api.description, 'Observer assignments')
        self.assertEqual(user_role_assignment_api.roles, ['observer'])
        self.assertEqual(user_role_assignment_api.file_path, 'assignments/user3.yaml')

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

    def test_load_role_definitions_disabled_role_definition(self):
        loader = RBACDefinitionsLoader()

        # Disabled role which means this method shouldn't include it in the result
        file_path = os.path.join(get_fixtures_base_path(), 'rbac/roles/role_disabled.yaml')
        file_paths = [file_path]

        loader._get_role_definitions_file_paths = mock.Mock()
        loader._get_role_definitions_file_paths.return_value = file_paths

        result = loader.load_role_definitions()
        self.assertItemsEqual(result, [])

    def test_load_role_definitions_empty_definition_file(self):
        loader = RBACDefinitionsLoader()

        file_path = os.path.join(get_fixtures_base_path(), 'rbac_invalid/roles/role_empty.yaml')
        file_paths = [file_path]

        loader._get_role_definitions_file_paths = mock.Mock()
        loader._get_role_definitions_file_paths.return_value = file_paths

        expected_msg = 'Role definition file .+? is empty and invalid'
        self.assertRaisesRegexp(ValueError, expected_msg, loader.load_role_definitions)

    def test_load_user_role_assignments_duplicate_user_definition(self):
        loader = RBACDefinitionsLoader()

        # Try to load all the user role assignments from disk where two definitions refer to the
        # same user
        file_path1 = os.path.join(get_fixtures_base_path(),
                                  'rbac_invalid/assignments/user_foo1.yaml')
        file_path2 = os.path.join(get_fixtures_base_path(),
                                  'rbac_invalid/assignments/user_foo2.yaml')
        file_paths = [file_path1, file_path2]

        loader._get_role_assiginments_file_paths = mock.Mock()
        loader._get_role_assiginments_file_paths.return_value = file_paths

        expected_msg = 'Duplicate definition file found for user "userfoo"'
        self.assertRaisesRegexp(ValueError, expected_msg, loader.load_user_role_assignments)

    def test_load_user_role_assignments_disabled_assignment(self):
        loader = RBACDefinitionsLoader()

        # Disabled role assignment which means this method shouldn't include it in the result
        file_path = os.path.join(get_fixtures_base_path(), 'rbac/assignments/user_disabled.yaml')
        file_paths = [file_path]

        loader._get_role_assiginments_file_paths = mock.Mock()
        loader._get_role_assiginments_file_paths.return_value = file_paths

        result = loader.load_user_role_assignments()
        self.assertItemsEqual(result, [])

    def test_load_user_role_assignments_empty_definition_file(self):
        loader = RBACDefinitionsLoader()

        file_path = os.path.join(get_fixtures_base_path(),
                                 'rbac_invalid/assignments/user_empty.yaml')
        file_paths = [file_path]

        loader._get_role_assiginments_file_paths = mock.Mock()
        loader._get_role_assiginments_file_paths.return_value = file_paths

        expected_msg = 'Role assignment file .+? is empty and invalid'
        self.assertRaisesRegexp(ValueError, expected_msg, loader.load_user_role_assignments)

    def test_load_sample_role_definition(self):
        """
        Validate that the sample role definition which we ship with default installation works.
        """
        loader = RBACDefinitionsLoader()

        file_path = os.path.join(get_fixtures_base_path(), 'rbac/roles/role_sample.yaml')
        role_api = loader.load_role_definition_from_file(file_path=file_path)
        self.assertEqual(role_api.name, 'sample')
        self.assertFalse(role_api.enabled)

    def test_load_sample_user_role_assignment_definition(self):
        """
        Validate that the sample user role assignment definition which we ship with default
        installation works.
        """
        loader = RBACDefinitionsLoader()

        file_path = os.path.join(get_fixtures_base_path(), 'rbac/assignments/user_sample.yaml')
        assignment_api = loader.load_user_role_assignments_from_file(file_path=file_path)
        self.assertEqual(assignment_api.username, 'stackstorm_user')
        self.assertFalse(assignment_api.enabled)
        self.assertEqual(assignment_api.file_path, 'assignments/user_sample.yaml')

    def test_load_group_to_role_mappings_empty_file(self):
        loader = RBACDefinitionsLoader()

        file_path = os.path.join(get_fixtures_base_path(), 'rbac_invalid/mappings/empty.yaml')
        file_paths = [file_path]

        loader._get_group_to_role_maps_file_paths = mock.Mock()
        loader._get_group_to_role_maps_file_paths.return_value = file_paths

        expected_msg = 'Group to role map assignment file .+? is empty and invalid'
        self.assertRaisesRegexp(ValueError, expected_msg, loader.load_group_to_role_maps)

    def test_load_group_to_role_mappings_missing_mandatory_attribute(self):
        loader = RBACDefinitionsLoader()

        file_path = os.path.join(get_fixtures_base_path(),
                                 'rbac_invalid/mappings/mapping_one_missing_roles.yaml')

        expected_msg = '\'roles\' is a required property'
        self.assertRaisesRegexp(jsonschema.ValidationError, expected_msg,
                                loader.load_group_to_role_map_assignment_from_file,
                                file_path=file_path)

        file_path = os.path.join(get_fixtures_base_path(),
                                 'rbac_invalid/mappings/mapping_two_missing_group.yaml')

        expected_msg = '\'group\' is a required property'
        self.assertRaisesRegexp(jsonschema.ValidationError, expected_msg,
                                loader.load_group_to_role_map_assignment_from_file,
                                file_path=file_path)

    def test_load_group_to_role_mappings_success(self):
        loader = RBACDefinitionsLoader()

        file_path = os.path.join(get_fixtures_base_path(), 'rbac/mappings/mapping_one.yaml')
        role_mapping_api = loader.load_group_to_role_map_assignment_from_file(file_path=file_path)

        self.assertEqual(role_mapping_api.group, 'some ldap group')
        self.assertEqual(role_mapping_api.roles, ['pack_admin'])
        self.assertEqual(role_mapping_api.description, None)
        self.assertTrue(role_mapping_api.enabled)
        self.assertTrue(role_mapping_api.file_path.endswith('mappings/mapping_one.yaml'))

        file_path = os.path.join(get_fixtures_base_path(), 'rbac/mappings/mapping_two.yaml')
        role_mapping_api = loader.load_group_to_role_map_assignment_from_file(file_path=file_path)

        self.assertEqual(role_mapping_api.group, 'CN=stormers,OU=groups,DC=stackstorm,DC=net')
        self.assertEqual(role_mapping_api.roles, ['role_one', 'role_two', 'role_three'])
        self.assertEqual(role_mapping_api.description, 'Grant 3 roles to stormers group members')
        self.assertFalse(role_mapping_api.enabled)
        self.assertEqual(role_mapping_api.file_path, 'mappings/mapping_two.yaml')

    @mock.patch('glob.glob')
    def test_file_paths_sorting(self, mock_glob):
        mock_glob.return_value = [
            '/tmp/bar/d.yaml',
            '/tmp/bar/c.yaml',
            '/tmp/foo/a.yaml',
            '/tmp/a/f.yaml'
        ]

        expected_result = [
            '/tmp/foo/a.yaml',
            '/tmp/bar/c.yaml',
            '/tmp/bar/d.yaml',
            '/tmp/a/f.yaml'
        ]

        loader = RBACDefinitionsLoader()

        file_paths = loader._get_role_definitions_file_paths()
        self.assertEqual(file_paths, expected_result)

        file_paths = loader._get_role_assiginments_file_paths()
        self.assertEqual(file_paths, expected_result)

        file_paths = loader._get_group_to_role_maps_file_paths()
        self.assertEqual(file_paths, expected_result)

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

from st2tests.base import CleanDbTestCase
from st2common.persistence.auth import User
from st2common.persistence.rbac import Role
from st2common.persistence.rbac import PermissionGrant
from st2common.models.db.auth import UserDB
from st2common.models.api.rbac import RoleDefinitionFileFormatAPI
from st2common.models.api.rbac import UserRoleAssignmentFileFormatAPI
from st2common.services.rbac import get_roles_for_user
from st2common.services.rbac import create_role
from st2common.rbac.syncer import RBACDefinitionsDBSyncer

__all__ = [
    'RBACDefinitionsDBSyncerTestCase'
]


class RBACDefinitionsDBSyncerTestCase(CleanDbTestCase):
    def setUp(self):
        super(RBACDefinitionsDBSyncerTestCase, self).setUp()

        self.roles = {}
        self.users = {}

        # Insert some mock users
        user_1_db = UserDB(name='user_1')
        user_1_db = User.add_or_update(user_1_db)
        self.users['user_1'] = user_1_db

        user_2_db = UserDB(name='user_2')
        user_2_db = User.add_or_update(user_2_db)
        self.users['user_2'] = user_2_db

    def test_sync_roles_no_definitions(self):
        syncer = RBACDefinitionsDBSyncer()

        # No definitions
        created_role_dbs, deleted_role_dbs = syncer.sync_roles(role_definition_apis=[])
        self.assertItemsEqual(created_role_dbs, [])
        self.assertItemsEqual(deleted_role_dbs, [])

    def test_sync_roles_single_role_definition_no_grants(self):
        syncer = RBACDefinitionsDBSyncer()

        # One role with no grants
        api = RoleDefinitionFileFormatAPI(name='test_role_1', description='test description 1',
                                          permission_grants=[])
        created_role_dbs, deleted_role_dbs = syncer.sync_roles(role_definition_apis=[api])
        self.assertEqual(len(created_role_dbs), 1)
        self.assertItemsEqual(deleted_role_dbs, [])
        self.assertEqual(created_role_dbs[0].name, 'test_role_1')
        self.assertEqual(created_role_dbs[0].description, 'test description 1')
        self.assertItemsEqual(created_role_dbs[0].permission_grants, [])

        # Assert role has been created in the DB
        self.assertRoleDBObjectExists(role_db=created_role_dbs[0])

    def test_sync_roles_single_role_definition_two_grants(self):
        syncer = RBACDefinitionsDBSyncer()

        # One role with two grants
        permission_grants = [
            {
                'resource_uid': 'pack:mapack1',
                'permission_types': ['pack_all']
            },
            {
                'resource_uid': 'pack:mapack2',
                'permission_types': ['rule_view', 'action_view']
            }
        ]
        api = RoleDefinitionFileFormatAPI(name='test_role_2', description='test description 2',
                                          permission_grants=permission_grants)
        created_role_dbs, deleted_role_dbs = syncer.sync_roles(role_definition_apis=[api])
        self.assertEqual(len(created_role_dbs), 1)
        self.assertItemsEqual(deleted_role_dbs, [])
        self.assertEqual(created_role_dbs[0].name, 'test_role_2')
        self.assertEqual(created_role_dbs[0].description, 'test description 2')
        self.assertEqual(len(created_role_dbs[0].permission_grants), 2)

        # Assert role and grants have been created in the DB
        self.assertRoleDBObjectExists(role_db=created_role_dbs[0])

        for permission_grant_id in created_role_dbs[0].permission_grants:
            self.assertGrantDBObjectExists(permission_grant_id)

    def test_sync_roles_locally_removed_roles_are_removed_from_db(self):
        syncer = RBACDefinitionsDBSyncer()

        # Initial state, DB is empty, we sync with two roles defined on disk
        self.assertEqual(len(Role.get_all()), 0)

        api1 = RoleDefinitionFileFormatAPI(name='test_role_1', description='test description 1',
                                           permission_grants=[])
        api2 = RoleDefinitionFileFormatAPI(name='test_role_2', description='test description 2',
                                           permission_grants=[])
        created_role_dbs, deleted_role_dbs = syncer.sync_roles(role_definition_apis=[api1, api2])
        self.assertEqual(len(created_role_dbs), 2)
        self.assertItemsEqual(deleted_role_dbs, [])

        # Assert role and grants have been created in the DB
        self.assertEqual(len(Role.get_all()), 2)
        self.assertRoleDBObjectExists(role_db=created_role_dbs[0])
        self.assertRoleDBObjectExists(role_db=created_role_dbs[1])

        # We sync again, this time with one role (role 1) removed locally
        created_role_dbs, deleted_role_dbs = syncer.sync_roles(role_definition_apis=[api2])
        self.assertEqual(len(created_role_dbs), 1)
        self.assertEqual(len(deleted_role_dbs), 2)

        # Assert role and grants have been created in the DB
        self.assertEqual(len(Role.get_all()), 1)
        self.assertRoleDBObjectExists(role_db=created_role_dbs[0])
        self.assertEqual(Role.get_all()[0].name, 'test_role_2')

    def test_sync_user_assignments_single_role_assignment(self):
        syncer = RBACDefinitionsDBSyncer()

        self._insert_mock_roles()

        # Initial state, no roles
        role_dbs = get_roles_for_user(user_db=self.users['user_1'])
        self.assertItemsEqual(role_dbs, [])

        # Do the sync with a single role defined
        api = UserRoleAssignmentFileFormatAPI(username='user_1',
                                              roles=['role_1'])
        syncer.sync_users_role_assignments(role_assignment_apis=[api])

        role_dbs = get_roles_for_user(user_db=self.users['user_1'])
        self.assertItemsEqual(role_dbs, [self.roles['role_1']])

    def test_sync_user_assignments_multiple_custom_roles_assignments(self):
        syncer = RBACDefinitionsDBSyncer()

        self._insert_mock_roles()

        # Initial state, no roles
        role_dbs = get_roles_for_user(user_db=self.users['user_2'])
        self.assertItemsEqual(role_dbs, [])

        # Do the sync with two roles defined
        api = UserRoleAssignmentFileFormatAPI(username='user_2',
                                              roles=['role_1', 'role_2'])
        syncer.sync_users_role_assignments(role_assignment_apis=[api])

        role_dbs = get_roles_for_user(user_db=self.users['user_2'])
        self.assertTrue(len(role_dbs), 2)
        self.assertEqual(role_dbs[0], self.roles['role_1'])
        self.assertEqual(role_dbs[1], self.roles['role_2'])

    def test_sync_user_assignments_locally_removed_assignments_are_removed_from_db(self):
        syncer = RBACDefinitionsDBSyncer()

        self._insert_mock_roles()

        # Initial state, no roles
        role_dbs = get_roles_for_user(user_db=self.users['user_2'])
        self.assertItemsEqual(role_dbs, [])

        # Do the sync with two roles defined
        api = UserRoleAssignmentFileFormatAPI(username='user_2',
                                              roles=['role_1', 'role_2'])
        syncer.sync_users_role_assignments(role_assignment_apis=[api])

        role_dbs = get_roles_for_user(user_db=self.users['user_2'])
        self.assertTrue(len(role_dbs), 2)
        self.assertEqual(role_dbs[0], self.roles['role_1'])
        self.assertEqual(role_dbs[1], self.roles['role_2'])

        # Do the sync with one role defined (one should be removed from the db)
        api = UserRoleAssignmentFileFormatAPI(username='user_2',
                                              roles=['role_2'])
        syncer.sync_users_role_assignments(role_assignment_apis=[api])

        role_dbs = get_roles_for_user(user_db=self.users['user_2'])
        self.assertTrue(len(role_dbs), 1)
        self.assertEqual(role_dbs[0], self.roles['role_2'])

    def test_sync_assignments_user_doesnt_exist_in_db(self):
        # Make sure that the assignments for the users which don't exist in the db are still saved
        syncer = RBACDefinitionsDBSyncer()

        self._insert_mock_roles()

        # Initial state, no roles
        user_db = UserDB(name='doesntexistwhaha')
        role_dbs = get_roles_for_user(user_db=user_db)
        self.assertItemsEqual(role_dbs, [])

        # Do the sync with two roles defined
        api = UserRoleAssignmentFileFormatAPI(username=user_db.name,
                                              roles=['role_1', 'role_2'])
        syncer.sync_users_role_assignments(role_assignment_apis=[api])

        role_dbs = get_roles_for_user(user_db=user_db)
        self.assertTrue(len(role_dbs), 2)
        self.assertEqual(role_dbs[0], self.roles['role_1'])
        self.assertEqual(role_dbs[1], self.roles['role_2'])

    def assertRoleDBObjectExists(self, role_db):
        result = Role.get_by_id(str(role_db.id))
        self.assertTrue(result)
        self.assertEqual(role_db.id, result.id)

    def assertGrantDBObjectExists(self, permission_grant_id):
        result = PermissionGrant.get_by_id(str(permission_grant_id))
        self.assertTrue(result)
        self.assertEqual(permission_grant_id, str(result.id))

    def _insert_mock_roles(self):
        # Create some mock roles
        role_1_db = create_role(name='role_1')
        role_2_db = create_role(name='role_2')

        self.roles['role_1'] = role_1_db
        self.roles['role_2'] = role_2_db

        return self.roles

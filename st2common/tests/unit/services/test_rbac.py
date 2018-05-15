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

from pymongo import MongoClient

from st2tests.base import CleanDbTestCase
from st2common.services import rbac as rbac_services
from st2common.rbac.types import PermissionType
from st2common.rbac.types import ResourceType
from st2common.rbac.types import SystemRole
from st2common.persistence.auth import User
from st2common.persistence.rbac import UserRoleAssignment
from st2common.persistence.rule import Rule
from st2common.models.db.auth import UserDB
from st2common.models.db.rbac import UserRoleAssignmentDB
from st2common.models.db.rule import RuleDB
from st2common.exceptions.db import StackStormDBObjectConflictError


class RBACServicesTestCase(CleanDbTestCase):
    def setUp(self):
        super(RBACServicesTestCase, self).setUp()

        # TODO: Share mocks

        self.users = {}
        self.roles = {}
        self.resources = {}

        # Create some mock users
        user_1_db = UserDB(name='admin')
        user_1_db = User.add_or_update(user_1_db)
        self.users['admin'] = user_1_db

        user_2_db = UserDB(name='observer')
        user_2_db = User.add_or_update(user_2_db)
        self.users['observer'] = user_2_db

        user_3_db = UserDB(name='no_roles')
        user_3_db = User.add_or_update(user_3_db)
        self.users['no_roles'] = user_3_db

        user_5_db = UserDB(name='user_5')
        user_5_db = User.add_or_update(user_5_db)
        self.users['user_5'] = user_5_db

        user_4_db = UserDB(name='custom_role')
        user_4_db = User.add_or_update(user_4_db)
        self.users['1_custom_role'] = user_4_db

        # Create some mock roles
        role_1_db = rbac_services.create_role(name='custom_role_1')
        role_2_db = rbac_services.create_role(name='custom_role_2',
                                              description='custom role 2')
        self.roles['custom_role_1'] = role_1_db
        self.roles['custom_role_2'] = role_2_db

        rbac_services.create_role(name='role_1')
        rbac_services.create_role(name='role_2')
        rbac_services.create_role(name='role_3')
        rbac_services.create_role(name='role_4')

        # Create some mock role assignments
        role_assignment_1 = UserRoleAssignmentDB(
            user=self.users['1_custom_role'].name, role=self.roles['custom_role_1'].name,
            source='assignments/%s.yaml' % self.users['1_custom_role'].name)
        role_assignment_1 = UserRoleAssignment.add_or_update(role_assignment_1)

        # Note: User use pymongo to insert mock data because we want to insert a
        # raw document and skip mongoengine to leave is_remote field unpopulated
        client = MongoClient()
        db = client['st2-test']
        db.user_role_assignment_d_b.insert_one({'user': 'user_5', 'role': 'role_1'})
        db.user_role_assignment_d_b.insert_one({'user': 'user_5', 'role': 'role_2'})
        db.user_role_assignment_d_b.insert_one({'user': 'user_5', 'role': 'role_3',
                                               'is_remote': False})
        db.user_role_assignment_d_b.insert_one({'user': 'user_5', 'role': 'role_4',
                                               'is_remote': True})

        # Create some mock resources on which permissions can be granted
        rule_1_db = RuleDB(pack='test1', name='rule1', ref='test1.rule1')
        rule_1_db = Rule.add_or_update(rule_1_db)

        self.resources['rule_1'] = rule_1_db

    def test_get_role_assignments_for_user(self):
        # Test a case where a document doesn't exist is_remote field and when it
        # does
        user_db = self.users['user_5']
        role_assignment_dbs = rbac_services.get_role_assignments_for_user(user_db=user_db,
                                                                          include_remote=False)
        self.assertEqual(len(role_assignment_dbs), 3)
        self.assertEqual(role_assignment_dbs[0].role, 'role_1')
        self.assertEqual(role_assignment_dbs[1].role, 'role_2')
        self.assertEqual(role_assignment_dbs[2].role, 'role_3')
        self.assertEqual(role_assignment_dbs[0].is_remote, False)
        self.assertEqual(role_assignment_dbs[1].is_remote, False)
        self.assertEqual(role_assignment_dbs[2].is_remote, False)

        user_db = self.users['user_5']
        role_assignment_dbs = rbac_services.get_role_assignments_for_user(user_db=user_db,
                                                                          include_remote=True)
        self.assertEqual(len(role_assignment_dbs), 4)
        self.assertEqual(role_assignment_dbs[3].role, 'role_4')
        self.assertEqual(role_assignment_dbs[3].is_remote, True)

    def test_get_all_roles(self):
        role_dbs = rbac_services.get_all_roles()
        self.assertEqual(len(role_dbs), len(self.roles) + 4)

    def test_get_roles_for_user(self):
        # User with no roles
        user_db = self.users['no_roles']
        role_dbs = rbac_services.get_roles_for_user(user_db=user_db)
        self.assertItemsEqual(role_dbs, [])

        role_dbs = user_db.get_roles()
        self.assertItemsEqual(role_dbs, [])

        # User with one custom role
        user_db = self.users['1_custom_role']
        role_dbs = rbac_services.get_roles_for_user(user_db=user_db)
        self.assertItemsEqual(role_dbs, [self.roles['custom_role_1']])

        role_dbs = user_db.get_roles()
        self.assertItemsEqual(role_dbs, [self.roles['custom_role_1']])

        # User with remote roles
        user_db = self.users['user_5']
        role_dbs = user_db.get_roles()
        self.assertEqual(len(role_dbs), 4)

        user_db = self.users['user_5']
        role_dbs = user_db.get_roles(include_remote=True)
        self.assertEqual(len(role_dbs), 4)

        user_db = self.users['user_5']
        role_dbs = user_db.get_roles(include_remote=False)
        self.assertEqual(len(role_dbs), 3)

    def test_get_all_role_assignments(self):
        role_assignment_dbs = rbac_services.get_all_role_assignments(include_remote=True)
        self.assertEqual(len(role_assignment_dbs), 5)

        role_assignment_dbs = rbac_services.get_all_role_assignments(include_remote=False)
        self.assertEqual(len(role_assignment_dbs), 4)

        for role_assignment_db in role_assignment_dbs:
            self.assertFalse(role_assignment_db.is_remote)

    def test_create_role_with_system_role_name(self):
        # Roles with names which match system role names can't be created
        expected_msg = '"observer" role name is blacklisted'
        self.assertRaisesRegexp(ValueError, expected_msg, rbac_services.create_role,
                                name=SystemRole.OBSERVER)

    def test_delete_system_role(self):
        # System roles can't be deleted
        system_roles = SystemRole.get_valid_values()

        for name in system_roles:
            expected_msg = 'System roles can\'t be deleted'
            self.assertRaisesRegexp(ValueError, expected_msg, rbac_services.delete_role,
                                    name=name)

    def test_grant_and_revoke_role(self):
        user_db = UserDB(name='test-user-1')
        user_db = User.add_or_update(user_db)

        # Initial state, no roles
        role_dbs = rbac_services.get_roles_for_user(user_db=user_db)
        self.assertItemsEqual(role_dbs, [])

        role_dbs = user_db.get_roles()
        self.assertItemsEqual(role_dbs, [])

        # Assign a role, should have one role assigned
        rbac_services.assign_role_to_user(
            role_db=self.roles['custom_role_1'], user_db=user_db,
            source='assignments/%s.yaml' % user_db.name)

        role_dbs = rbac_services.get_roles_for_user(user_db=user_db)
        self.assertItemsEqual(role_dbs, [self.roles['custom_role_1']])

        role_dbs = user_db.get_roles()
        self.assertItemsEqual(role_dbs, [self.roles['custom_role_1']])

        # Revoke previously assigned role, should have no roles again
        rbac_services.revoke_role_from_user(role_db=self.roles['custom_role_1'],
                                            user_db=user_db)

        role_dbs = rbac_services.get_roles_for_user(user_db=user_db)
        self.assertItemsEqual(role_dbs, [])
        role_dbs = user_db.get_roles()
        self.assertItemsEqual(role_dbs, [])

    def test_grant_duplicate_role(self):
        user_db = UserDB(name='test-user-1')
        user_db = User.add_or_update(user_db)

        # Initial state, no roles
        role_dbs = rbac_services.get_roles_for_user(user_db=user_db)
        self.assertItemsEqual(role_dbs, [])

        role_dbs = user_db.get_roles()
        self.assertItemsEqual(role_dbs, [])

        # Assign a role, should have one role assigned
        rbac_services.assign_role_to_user(
            role_db=self.roles['custom_role_1'], user_db=user_db,
            source='assignments/%s_1.yaml' % user_db.name)

        role_dbs = rbac_services.get_roles_for_user(user_db=user_db)
        self.assertItemsEqual(role_dbs, [self.roles['custom_role_1']])

        role_dbs = user_db.get_roles()
        self.assertItemsEqual(role_dbs, [self.roles['custom_role_1']])

        # Assign the same role again.
        rbac_services.assign_role_to_user(
            role_db=self.roles['custom_role_1'], user_db=user_db,
            source='assignments/%s_2.yaml' % user_db.name)

        role_dbs_2 = rbac_services.get_roles_for_user(user_db=user_db)
        self.assertItemsEqual(role_dbs_2, [self.roles['custom_role_1']])

        role_dbs = user_db.get_roles()
        self.assertItemsEqual(role_dbs_2, [self.roles['custom_role_1']])

        # Revoke previously assigned role, should have no roles again
        rbac_services.revoke_role_from_user(role_db=self.roles['custom_role_1'], user_db=user_db)

        role_dbs = rbac_services.get_roles_for_user(user_db=user_db)
        self.assertItemsEqual(role_dbs, [])
        role_dbs = user_db.get_roles()
        self.assertItemsEqual(role_dbs, [])

    def test_assign_role_to_user_ignore_already_exists_error(self):
        user_db = UserDB(name='test-user-10')
        user_db = User.add_or_update(user_db)

        role_assignment_db_1 = rbac_services.assign_role_to_user(
            role_db=self.roles['custom_role_1'], user_db=user_db,
            source='assignments/%s_10.yaml' % user_db.name)

        # 1. Without ignore errors
        self.assertRaises(StackStormDBObjectConflictError, rbac_services.assign_role_to_user,
            role_db=self.roles['custom_role_1'], user_db=user_db,
            source='assignments/%s_10.yaml' % user_db.name)

        # 2. With ignore errors
        role_assignment_db_2 = rbac_services.assign_role_to_user(
            role_db=self.roles['custom_role_1'], user_db=user_db,
            source='assignments/%s_10.yaml' % user_db.name,
            ignore_already_exists_error=True)

        self.assertEqual(role_assignment_db_1, role_assignment_db_2)
        self.assertEqual(role_assignment_db_1.id, role_assignment_db_2.id)
        self.assertEqual(role_assignment_db_1.user, role_assignment_db_2.user)
        self.assertEqual(role_assignment_db_1.role, role_assignment_db_2.role)

    def test_get_all_permission_grants_for_user(self):
        user_db = self.users['1_custom_role']
        role_db = self.roles['custom_role_1']
        permission_grants = rbac_services.get_all_permission_grants_for_user(user_db=user_db)
        self.assertItemsEqual(permission_grants, [])

        # Grant some permissions
        resource_db = self.resources['rule_1']
        permission_types = [PermissionType.RULE_CREATE, PermissionType.RULE_MODIFY]

        permission_grant = rbac_services.create_permission_grant_for_resource_db(
            role_db=role_db,
            resource_db=resource_db,
            permission_types=permission_types)

        # Retrieve all grants
        permission_grants = rbac_services.get_all_permission_grants_for_user(user_db=user_db)
        self.assertItemsEqual(permission_grants, [permission_grant])

        # Retrieve all grants, filter on resource with no grants
        permission_grants = rbac_services.get_all_permission_grants_for_user(user_db=user_db,
            resource_types=[ResourceType.PACK])
        self.assertItemsEqual(permission_grants, [])

        # Retrieve all grants, filter on resource with grants
        permission_grants = rbac_services.get_all_permission_grants_for_user(user_db=user_db,
            resource_types=[ResourceType.RULE])
        self.assertItemsEqual(permission_grants, [permission_grant])

    def test_create_and_remove_permission_grant(self):
        role_db = self.roles['custom_role_2']
        resource_db = self.resources['rule_1']

        # Grant "ALL" permission to the resource
        permission_types = [PermissionType.RULE_ALL]
        rbac_services.create_permission_grant_for_resource_db(role_db=role_db,
                                                              resource_db=resource_db,
                                                              permission_types=permission_types)

        role_db.reload()
        self.assertItemsEqual(role_db.permission_grants, role_db.permission_grants)

        # Remove the previously granted permission
        rbac_services.remove_permission_grant_for_resource_db(role_db=role_db,
                                                              resource_db=resource_db,
                                                              permission_types=permission_types)

        role_db.reload()
        self.assertItemsEqual(role_db.permission_grants, [])

    def test_manipulate_permission_grants_unsupported_resource_type(self):
        # Try to manipulate permissions on an unsupported resource
        role_db = self.roles['custom_role_2']
        resource_db = UserDB()
        permission_types = [PermissionType.RULE_ALL]

        expected_msg = 'Permissions cannot be manipulated for a resource of type'
        self.assertRaisesRegexp(ValueError, expected_msg,
                                rbac_services.create_permission_grant_for_resource_db,
                                role_db=role_db, resource_db=resource_db,
                                permission_types=permission_types)

        expected_msg = 'Permissions cannot be manipulated for a resource of type'
        self.assertRaisesRegexp(ValueError, expected_msg,
                                rbac_services.remove_permission_grant_for_resource_db,
                                role_db=role_db, resource_db=resource_db,
                                permission_types=permission_types)

    def test_manipulate_permission_grants_invalid_permission_types(self):
        # Try to assign / revoke a permission which is not supported for a particular resource
        role_db = self.roles['custom_role_2']
        resource_db = self.resources['rule_1']
        permission_types = [PermissionType.ACTION_EXECUTE]

        expected_msg = 'Invalid permission type'
        self.assertRaisesRegexp(ValueError, expected_msg,
                                rbac_services.create_permission_grant_for_resource_db,
                                role_db=role_db, resource_db=resource_db,
                                permission_types=permission_types)

        expected_msg = 'Invalid permission type'
        self.assertRaisesRegexp(ValueError, expected_msg,
                                rbac_services.remove_permission_grant_for_resource_db,
                                role_db=role_db, resource_db=resource_db,
                                permission_types=permission_types)

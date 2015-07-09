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
from st2common.services import rbac as rbac_services
from st2common.rbac.types import PermissionType
from st2common.persistence.auth import User
from st2common.persistence.rbac import UserRoleAssignment
from st2common.persistence.rule import Rule
from st2common.models.db.auth import UserDB
from st2common.models.db.rbac import UserRoleAssignmentDB
from st2common.models.db.rule import RuleDB


class RBACServicesTestCase(CleanDbTestCase):
    def setUp(self):
        super(RBACServicesTestCase, self).setUp()

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

        user_4_db = UserDB(name='custom_role')
        user_4_db = User.add_or_update(user_4_db)
        self.users['1_custom_role'] = user_4_db

        # Create some mock roles
        role_1_db = rbac_services.create_role(name='custom_role_1')
        role_2_db = rbac_services.create_role(name='custom_role_2',
                                              description='custom role 2')
        self.roles['custom_role_1'] = role_1_db
        self.roles['custom_role_2'] = role_2_db

        # Create some mock role assignments
        role_assignment_1 = UserRoleAssignmentDB(user=self.users['1_custom_role'].name,
                                                 role=self.roles['custom_role_1'].name)
        role_assignment_1 = UserRoleAssignment.add_or_update(role_assignment_1)

        # Create some mock resources on which permissions can be granted
        rule_1_db = RuleDB(pack='test1', name='rule1', ref='test1.rule1')
        rule_1_db = Rule.add_or_update(rule_1_db)

        self.resources['rule_1'] = rule_1_db

    def test_get_all_roles(self):
        role_dbs = rbac_services.get_all_roles()
        self.assertEqual(len(role_dbs), len(self.roles))

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

    def test_grant_and_revoke_role(self):
        user_db = UserDB(name='test-user-1')
        user_db = User.add_or_update(user_db)

        # Initial state, no roles
        role_dbs = rbac_services.get_roles_for_user(user_db=user_db)
        self.assertItemsEqual(role_dbs, [])

        role_dbs = user_db.get_roles()
        self.assertItemsEqual(role_dbs, [])

        # Assign a role, should have one role assigned
        rbac_services.assign_role_to_user(role_db=self.roles['custom_role_1'],
                                          user_db=user_db)

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

    def test_create_and_remove_permission_grant(self):
        role_db = self.roles['custom_role_2']
        resource_db = self.resources['rule_1']

        # Grant "ALL" permission to the resource
        permission_types = [PermissionType.ALL]
        rbac_services.create_permission_grant(role_db=role_db, resource_db=resource_db,
                                              permission_types=permission_types)

        role_db.reload()
        self.assertItemsEqual(role_db.permission_grants, role_db.permission_grants)

        # Remove the previously granted permission
        rbac_services.remove_permission_grant(role_db=role_db, resource_db=resource_db,
                                              permission_types=permission_types)

        role_db.reload()
        self.assertItemsEqual(role_db.permission_grants, [])

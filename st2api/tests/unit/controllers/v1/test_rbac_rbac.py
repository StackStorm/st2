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

import six

from st2common.persistence.auth import User
from st2common.persistence.rbac import Role
from st2common.persistence.rbac import UserRoleAssignment
from st2common.models.db.auth import UserDB
from st2common.models.db.rbac import RoleDB
from st2common.models.db.rbac import UserRoleAssignmentDB

from st2tests import config as tests_config
from tests.base import APIControllerWithRBACTestCase

tests_config.parse_args()

http_client = six.moves.http_client

__all__ = [
    'RBACRolesControllerRBACTestCase',
    'RBACRoleAssignmentsControllerRBACTestCase',
    'RBACPermissionTypesControllerRBACTestCase',
]


class RBACRolesControllerRBACTestCase(APIControllerWithRBACTestCase):
    def test_get_all_no_permissions(self):
        user_db = self.users['no_permissions']
        self.use_user(user_db)

        resp = self.app.get('/v1/rbac/roles', expect_errors=True)
        expected_msg = ('Administrator access required')
        self.assertEqual(resp.status_code, http_client.FORBIDDEN)
        self.assertEqual(resp.json['faultstring'], expected_msg)

    def test_get_one_no_permissions(self):
        user_db = self.users['no_permissions']
        self.use_user(user_db)

        resp = self.app.get('/v1/rbac/roles/admin', expect_errors=True)
        expected_msg = ('Administrator access required')
        self.assertEqual(resp.status_code, http_client.FORBIDDEN)
        self.assertEqual(resp.json['faultstring'], expected_msg)

    def test_get_all_success(self):
        user_db = self.users['admin']
        self.use_user(user_db)

        resp = self.app.get('/v1/rbac/roles')
        self.assertEqual(resp.status_code, http_client.OK)
        self.assertEqual(len(resp.json), 3)


class RBACRoleAssignmentsControllerRBACTestCase(APIControllerWithRBACTestCase):
    def setUp(self):
        super(RBACRoleAssignmentsControllerRBACTestCase, self).setUp()

        # Insert mock users, roles and assignments
        self.role_assignments = {}

        # Users
        user_1_db = UserDB(name='user_foo')
        user_1_db = User.add_or_update(user_1_db)
        self.users['user_foo'] = user_1_db

        # Roles
        role_1_db = RoleDB(name='user_foo', permission_grants=[])
        role_1_db = Role.add_or_update(role_1_db)
        self.roles['user_foo'] = role_1_db

        # Role assignments
        role_assignment_db = UserRoleAssignmentDB(
            user=self.users['user_foo'].name,
            role=self.roles['user_foo'].name,
            source='assignments/%s.yaml' % self.users['user_foo'].name)
        UserRoleAssignment.add_or_update(role_assignment_db)
        self.role_assignments['assignment_one'] = role_assignment_db

        role_assignment_db = UserRoleAssignmentDB(
            user='user_bar',
            role=self.roles['user_foo'].name,
            source='assignments/user_bar.yaml')
        UserRoleAssignment.add_or_update(role_assignment_db)
        self.role_assignments['assignment_two'] = role_assignment_db

    def test_get_all_no_permissions(self):
        user_db = self.users['no_permissions']
        self.use_user(user_db)

        resp = self.app.get('/v1/rbac/role_assignments', expect_errors=True)
        expected_msg = ('Administrator or self access required')
        self.assertEqual(resp.status_code, http_client.FORBIDDEN)
        self.assertEqual(resp.json['faultstring'], expected_msg)

        resp = self.app.get('/v1/rbac/role_assignments?user=not-me', expect_errors=True)
        expected_msg = ('Administrator or self access required')
        self.assertEqual(resp.status_code, http_client.FORBIDDEN)
        self.assertEqual(resp.json['faultstring'], expected_msg)

    def test_get_one_no_permissions(self):
        user_db = self.users['no_permissions']
        self.use_user(user_db)

        assignment_id = self.role_assignments['assignment_one']['id']
        resp = self.app.get('/v1/rbac/role_assignments/%s' % (assignment_id), expect_errors=True)
        expected_msg = ('Administrator or self access required')
        self.assertEqual(resp.status_code, http_client.FORBIDDEN)
        self.assertEqual(resp.json['faultstring'], expected_msg)

    def test_get_all_admin_success(self):
        user_db = self.users['admin']
        self.use_user(user_db)

        resp = self.app.get('/v1/rbac/role_assignments')
        self.assertEqual(resp.status_code, http_client.OK)
        self.assertTrue(len(resp.json) > 1)

        resp = self.app.get('/v1/rbac/role_assignments?user=user_foo')
        self.assertEqual(resp.status_code, http_client.OK)
        self.assertEqual(len(resp.json), 1)

    def test_get_all_user_foo_success(self):
        # Users can view their own roles, but nothing else
        user_db = self.users['user_foo']
        self.use_user(user_db)

        resp = self.app.get('/v1/rbac/role_assignments', expect_errors=True)
        expected_msg = ('Administrator or self access required')
        self.assertEqual(resp.status_code, http_client.FORBIDDEN)
        self.assertEqual(resp.json['faultstring'], expected_msg)

        resp = self.app.get('/v1/rbac/role_assignments?user=admin', expect_errors=True)
        expected_msg = ('Administrator or self access required')
        self.assertEqual(resp.status_code, http_client.FORBIDDEN)
        self.assertEqual(resp.json['faultstring'], expected_msg)

        resp = self.app.get('/v1/rbac/role_assignments?user=user_foo')
        self.assertEqual(resp.status_code, http_client.OK)
        self.assertEqual(len(resp.json), 1)

    def test_get_one_admin_success(self):
        user_db = self.users['admin']
        self.use_user(user_db)

        assignment_id = self.role_assignments['assignment_one']['id']

        resp = self.app.get('/v1/rbac/role_assignments/%s' % (assignment_id))
        self.assertEqual(resp.status_code, http_client.OK)

    def test_get_one_user_foo_success(self):
        # Users can view their own roles, but nothing else
        user_db = self.users['user_foo']
        self.use_user(user_db)

        assignment_id = self.role_assignments['assignment_one']['id']
        resp = self.app.get('/v1/rbac/role_assignments/%s' % (assignment_id))
        self.assertEqual(resp.status_code, http_client.OK)

        assignment_id = self.role_assignments['assignment_two']['id']
        resp = self.app.get('/v1/rbac/role_assignments/%s' % (assignment_id), expect_errors=True)
        expected_msg = ('Administrator or self access required')
        self.assertEqual(resp.status_code, http_client.FORBIDDEN)
        self.assertEqual(resp.json['faultstring'], expected_msg)


class RBACPermissionTypesControllerRBACTestCase(APIControllerWithRBACTestCase):
    def test_get_all_no_permissions(self):
        user_db = self.users['no_permissions']
        self.use_user(user_db)

        resp = self.app.get('/v1/rbac/permission_types', expect_errors=True)
        expected_msg = ('Administrator access required')
        self.assertEqual(resp.status_code, http_client.FORBIDDEN)
        self.assertEqual(resp.json['faultstring'], expected_msg)

    def test_get_one_no_permissions(self):
        user_db = self.users['no_permissions']
        self.use_user(user_db)

        resp = self.app.get('/v1/rbac/permission_types/action', expect_errors=True)
        expected_msg = ('Administrator access required')
        self.assertEqual(resp.status_code, http_client.FORBIDDEN)
        self.assertEqual(resp.json['faultstring'], expected_msg)

    def test_get_all_success(self):
        user_db = self.users['admin']
        self.use_user(user_db)

        resp = self.app.get('/v1/rbac/role_assignments')
        self.assertEqual(resp.status_code, http_client.OK)
        self.assertTrue(len(resp.json) >= 1)

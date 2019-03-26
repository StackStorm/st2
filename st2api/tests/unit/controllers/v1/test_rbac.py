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

from st2common.rbac.types import PermissionType
from st2common.rbac.types import ResourceType
from st2common.persistence.auth import User
from st2common.persistence.rbac import Role
from st2common.persistence.rbac import UserRoleAssignment
from st2common.persistence.rbac import PermissionGrant
from st2common.models.db.auth import UserDB
from st2common.models.db.rbac import RoleDB
from st2common.models.db.rbac import UserRoleAssignmentDB
from st2common.models.db.rbac import PermissionGrantDB
from st2tests.api import APIControllerWithRBACTestCase


class RBACControllerTestCase(APIControllerWithRBACTestCase):
    def setUp(self):
        super(RBACControllerTestCase, self).setUp()

        permissions = [PermissionType.RULE_CREATE,
                       PermissionType.RULE_VIEW,
                       PermissionType.RULE_MODIFY,
                       PermissionType.RULE_DELETE]

        for name in permissions:
            user_db = UserDB(name=name)
            user_db = User.add_or_update(user_db)
            self.users[name] = user_db

            # Roles
            # action_create grant on parent pack
            grant_db = PermissionGrantDB(resource_uid='pack:examples',
                                         resource_type=ResourceType.PACK,
                                         permission_types=[name])
            grant_db = PermissionGrant.add_or_update(grant_db)
            grant_2_db = PermissionGrantDB(resource_uid='action:wolfpack:action-1',
                                           resource_type=ResourceType.ACTION,
                                           permission_types=[PermissionType.ACTION_EXECUTE])
            grant_2_db = PermissionGrant.add_or_update(grant_2_db)
            permission_grants = [str(grant_db.id), str(grant_2_db.id)]
            role_db = RoleDB(name=name, permission_grants=permission_grants)
            role_db = Role.add_or_update(role_db)
            self.roles[name] = role_db

            # Role assignments
            role_assignment_db = UserRoleAssignmentDB(
                user=user_db.name,
                role=role_db.name,
                source='assignments/%s.yaml' % user_db.name)
            UserRoleAssignment.add_or_update(role_assignment_db)

        role_assignment_db = UserRoleAssignmentDB(
            user='user_two',
            role='role_two',
            source='assignments/user_two.yaml',
            is_remote=True)
        UserRoleAssignment.add_or_update(role_assignment_db)

    def test_role_get_one(self):
        self.use_user(self.users['admin'])

        list_resp = self.app.get('/v1/rbac/roles')
        self.assertEqual(list_resp.status_int, 200)
        self.assertTrue(len(list_resp.json) > 0,
                        '/v1/rbac/roles did not return correct roles.')
        role_id = list_resp.json[0]['id']
        get_resp = self.app.get('/v1/rbac/roles/%s' % role_id)
        retrieved_id = get_resp.json['id']
        self.assertEqual(get_resp.status_int, 200)
        self.assertEqual(retrieved_id, role_id, '/v1/rbac/role returned incorrect role.')

    def test_role_get_all(self):
        self.use_user(self.users['admin'])

        resp = self.app.get('/v1/rbac/roles')
        self.assertEqual(resp.status_int, 200)
        self.assertTrue(len(list(resp.json)) > 0,
                        '/v1/rbac/roles did not return correct roles.')

    def test_roles_get_all_system_flter(self):
        self.use_user(self.users['admin'])

        resp = self.app.get('/v1/rbac/roles?system=1')
        self.assertEqual(resp.status_int, 200)
        self.assertTrue(len(list(resp.json)) > 0,
                        '/v1/rbac/roles did not return correct roles.')

        for role in resp.json:
            self.assertTrue(role['system'])

    def test_role_get_one_fail_doesnt_exist(self):
        self.use_user(self.users['admin'])

        resp = self.app.get('/v1/rbac/roles/1', expect_errors=True)
        self.assertEqual(resp.status_int, 404)

    def test_role_assignments_get_all(self):
        self.use_user(self.users['admin'])

        resp = self.app.get('/v1/rbac/role_assignments')
        self.assertEqual(resp.status_int, 200)
        self.assertTrue(len(list(resp.json)) > 0,
                        '/v1/rbac/role_assignments did not return correct assignments.')
        self.assertEqual(resp.json[0]['role'], 'system_admin')
        self.assertEqual(resp.json[0]['user'], 'system_admin')
        self.assertEqual(resp.json[0]['is_remote'], False)

    def test_role_assignments_get_all_with_user_rold_remote_and_source_filter(self):
        # ?user filter
        self.use_user(self.users['admin'])

        resp = self.app.get('/v1/rbac/role_assignments?user=doesnt-exist')
        self.assertEqual(resp.status_int, 200)
        self.assertEqual(len(resp.json), 0)

        resp = self.app.get('/v1/rbac/role_assignments?user=system_admin')
        self.assertEqual(resp.status_int, 200)
        self.assertEqual(len(resp.json), 1)
        self.assertEqual(resp.json[0]['role'], 'system_admin')
        self.assertEqual(resp.json[0]['user'], 'system_admin')

        # ?role filter
        resp = self.app.get('/v1/rbac/role_assignments?role=doesnt-exist')
        self.assertEqual(resp.status_int, 200)
        self.assertEqual(len(resp.json), 0)

        resp = self.app.get('/v1/rbac/role_assignments?role=observer')
        self.assertEqual(resp.status_int, 200)
        self.assertEqual(len(resp.json), 1)
        self.assertEqual(resp.json[0]['role'], 'observer')
        self.assertEqual(resp.json[0]['user'], 'observer')

        # ?remote filter
        resp = self.app.get('/v1/rbac/role_assignments?remote=true')
        self.assertEqual(resp.status_int, 200)
        self.assertEqual(len(resp.json), 1)

        for role in resp.json:
            self.assertTrue(role['is_remote'])

        # ?source filter
        resp = self.app.get('/v1/rbac/role_assignments?source=doesnt_exist')
        self.assertEqual(resp.status_int, 200)
        self.assertEqual(len(resp.json), 0)

        resp = self.app.get('/v1/rbac/role_assignments?source=assignments/user_two.yaml')
        self.assertEqual(resp.status_int, 200)
        self.assertEqual(len(resp.json), 1)
        self.assertEqual(resp.json[0]['source'], 'assignments/user_two.yaml')

    def test_role_assignment_get_one(self):
        self.use_user(self.users['admin'])

        resp = self.app.get('/v1/rbac/role_assignments')
        assignment_id = resp.json[0]['id']

        resp = self.app.get('/v1/rbac/role_assignments/%s' % (assignment_id))
        self.assertEqual(resp.status_int, 200)
        self.assertEqual(resp.json['id'], assignment_id)
        self.assertEqual(resp.json['role'], 'system_admin')
        self.assertEqual(resp.json['user'], 'system_admin')

    def test_permission_type_get_one(self):
        self.use_user(self.users['admin'])

        resource_type = ResourceType.RULE
        get_resp = self.app.get('/v1/rbac/permission_types/%s' % resource_type)
        self.assertEqual(get_resp.status_int, 200)
        self.assertTrue(len(get_resp.json) > 0,
                        '/v1/rbac/permission_types did not return correct permission types.')
        self.assertTrue(PermissionType.RULE_ALL in get_resp.json)

    def test_permission_type_get_all(self):
        self.use_user(self.users['admin'])

        resp = self.app.get('/v1/rbac/permission_types')
        self.assertEqual(resp.status_int, 200)
        self.assertTrue(ResourceType.ACTION in resp.json)
        self.assertTrue(PermissionType.ACTION_LIST in resp.json[ResourceType.ACTION])
        self.assertTrue(len(list(resp.json)) > 0,
                        '/v1/rbac/permission_types did not return correct permission types.')

    def test_permission_type_get_one_fail_doesnt_exist(self):
        self.use_user(self.users['admin'])

        resp = self.app.get('/v1/rbac/permission_types/1', expect_errors=True)
        self.assertEqual(resp.status_int, 404)

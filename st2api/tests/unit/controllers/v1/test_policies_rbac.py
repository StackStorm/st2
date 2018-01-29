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

import copy

import six

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
from st2tests.fixturesloader import FixturesLoader
from tests.base import APIControllerWithRBACTestCase

http_client = six.moves.http_client

__all__ = [
    'PolicyTypeControllerRBACTestCase',
    'PolicyControllerRBACTestCase'
]

FIXTURES_PACK = 'generic'
TEST_FIXTURES = {
    'policytypes': [
        'fake_policy_type_1.yaml',
        'fake_policy_type_2.yaml',
        'fake_policy_type_3.yaml'
    ],
    'policies': [
        'policy_1.yaml',
        'policy_2.yaml',
        'policy_8.yaml'
    ]
}


class PolicyTypeControllerRBACTestCase(APIControllerWithRBACTestCase):
    fixtures_loader = FixturesLoader()

    def setUp(self):
        super(PolicyTypeControllerRBACTestCase, self).setUp()
        self.models = self.fixtures_loader.save_fixtures_to_db(fixtures_pack=FIXTURES_PACK,
                                                               fixtures_dict=TEST_FIXTURES)

        file_name = 'fake_policy_type_1.yaml'
        PolicyTypeControllerRBACTestCase.POLICY_TYPE_1 = self.fixtures_loader.load_fixtures(
            fixtures_pack=FIXTURES_PACK,
            fixtures_dict={'policytypes': [file_name]})['policytypes'][file_name]

        file_name = 'fake_policy_type_2.yaml'
        PolicyTypeControllerRBACTestCase.POLICY_TYPE_2 = self.fixtures_loader.load_fixtures(
            fixtures_pack=FIXTURES_PACK,
            fixtures_dict={'policytypes': [file_name]})['policytypes'][file_name]

        # Insert mock users, roles and assignments

        # Users
        user_1_db = UserDB(name='policy_type_list')
        user_1_db = User.add_or_update(user_1_db)
        self.users['policy_type_list'] = user_1_db

        user_2_db = UserDB(name='policy_type_view')
        user_2_db = User.add_or_update(user_2_db)
        self.users['policy_type_view'] = user_2_db

        # Roles
        # policy_type_list
        grant_db = PermissionGrantDB(resource_uid=None,
                                     resource_type=ResourceType.POLICY_TYPE,
                                     permission_types=[PermissionType.POLICY_TYPE_LIST])
        grant_db = PermissionGrant.add_or_update(grant_db)
        permission_grants = [str(grant_db.id)]
        role_1_db = RoleDB(name='policy_type_list', permission_grants=permission_grants)
        role_1_db = Role.add_or_update(role_1_db)
        self.roles['policy_type_list'] = role_1_db

        # policy_type_view on timer 1
        policy_type_uid = self.models['policytypes']['fake_policy_type_1.yaml'].get_uid()
        grant_db = PermissionGrantDB(resource_uid=policy_type_uid,
                                     resource_type=ResourceType.POLICY_TYPE,
                                     permission_types=[PermissionType.POLICY_TYPE_VIEW])
        grant_db = PermissionGrant.add_or_update(grant_db)
        permission_grants = [str(grant_db.id)]
        role_1_db = RoleDB(name='policy_type_view', permission_grants=permission_grants)
        role_1_db = Role.add_or_update(role_1_db)
        self.roles['policy_type_view'] = role_1_db

        # Role assignments
        role_assignment_db = UserRoleAssignmentDB(
            user=self.users['policy_type_list'].name,
            role=self.roles['policy_type_list'].name,
            source='assignments/%s.yaml' % self.users['policy_type_list'].name)
        UserRoleAssignment.add_or_update(role_assignment_db)

        role_assignment_db = UserRoleAssignmentDB(
            user=self.users['policy_type_view'].name,
            role=self.roles['policy_type_view'].name,
            source='assignments/%s.yaml' % self.users['policy_type_view'].name)
        UserRoleAssignment.add_or_update(role_assignment_db)

    def test_get_all_no_permissions(self):
        user_db = self.users['no_permissions']
        self.use_user(user_db)

        resp = self.app.get('/v1/policytypes', expect_errors=True)
        expected_msg = ('User "no_permissions" doesn\'t have required permission '
                        '"policy_type_list"')
        self.assertEqual(resp.status_code, http_client.FORBIDDEN)
        self.assertEqual(resp.json['faultstring'], expected_msg)

    def test_get_one_no_permissions(self):
        user_db = self.users['no_permissions']
        self.use_user(user_db)

        policy_type_id = self.models['policytypes']['fake_policy_type_1.yaml'].id
        policy_type_uid = self.models['policytypes']['fake_policy_type_1.yaml'].get_uid()
        resp = self.app.get('/v1/policytypes/%s' % (policy_type_id), expect_errors=True)
        expected_msg = ('User "no_permissions" doesn\'t have required permission "policy_type_view"'
                        ' on resource "%s"' % (policy_type_uid))
        self.assertEqual(resp.status_code, http_client.FORBIDDEN)
        self.assertEqual(resp.json['faultstring'], expected_msg)

    def test_get_all_permission_success_get_one_no_permission_failure(self):
        user_db = self.users['policy_type_list']
        self.use_user(user_db)

        # policy_type_list permission, but no policy_type_view permission
        resp = self.app.get('/v1/policytypes')
        self.assertEqual(resp.status_code, http_client.OK)
        self.assertEqual(len(resp.json), 3)

        policy_type_id = self.models['policytypes']['fake_policy_type_1.yaml'].id
        policy_type_uid = self.models['policytypes']['fake_policy_type_1.yaml'].get_uid()
        resp = self.app.get('/v1/policytypes/%s' % (policy_type_id), expect_errors=True)
        expected_msg = ('User "policy_type_list" doesn\'t have required permission '
                        '"policy_type_view" on resource "%s"' % (policy_type_uid))
        self.assertEqual(resp.status_code, http_client.FORBIDDEN)
        self.assertEqual(resp.json['faultstring'], expected_msg)

    def test_get_one_permission_success_get_all_no_permission_failure(self):
        user_db = self.users['policy_type_view']
        self.use_user(user_db)

        # policy_type_view permission, but no policy_type_list permission
        resp = self.app.get('/v1/policytypes', expect_errors=True)
        expected_msg = ('User "policy_type_view" doesn\'t have required permission '
                        '"policy_type_list"')
        self.assertEqual(resp.status_code, http_client.FORBIDDEN)
        self.assertEqual(resp.json['faultstring'], expected_msg)

        # policy_type_view in fake_policy_type_1, but not on fake_policy_type_2
        policy_type_id = self.models['policytypes']['fake_policy_type_1.yaml'].id
        policy_type_uid = self.models['policytypes']['fake_policy_type_1.yaml'].get_uid()
        resp = self.app.get('/v1/policytypes/%s' % (policy_type_id), expect_errors=True)
        resp = self.app.get('/v1/policytypes/%s' % (policy_type_id))
        self.assertEqual(resp.status_code, http_client.OK)
        self.assertEqual(resp.json['uid'], policy_type_uid)

        policy_type_id = self.models['policytypes']['fake_policy_type_2.yaml'].id
        policy_type_uid = self.models['policytypes']['fake_policy_type_2.yaml'].get_uid()
        expected_msg = ('User "policy_type_view" doesn\'t have required permission '
                        '"policy_type_view" on resource "%s"' % (policy_type_uid))
        resp = self.app.get('/v1/policytypes/%s' % (policy_type_id), expect_errors=True)
        self.assertEqual(resp.status_code, http_client.FORBIDDEN)
        self.assertEqual(resp.json['faultstring'], expected_msg)

    def test_get_all_limit_minus_one(self):
        user_db = self.users['observer']
        self.use_user(user_db)

        resp = self.app.get('/v1/policytypes?limit=-1', expect_errors=True)
        self.assertEqual(resp.status_code, http_client.FORBIDDEN)

        user_db = self.users['admin']
        self.use_user(user_db)

        resp = self.app.get('/v1/policytypes?limit=-1')
        self.assertEqual(resp.status_code, http_client.OK)


class PolicyControllerRBACTestCase(APIControllerWithRBACTestCase):
    fixtures_loader = FixturesLoader()

    def setUp(self):
        super(PolicyControllerRBACTestCase, self).setUp()
        self.models = self.fixtures_loader.save_fixtures_to_db(fixtures_pack=FIXTURES_PACK,
                                                               fixtures_dict=TEST_FIXTURES)

        file_name = 'policy_1.yaml'
        PolicyControllerRBACTestCase.POLICY_1 = self.fixtures_loader.load_fixtures(
            fixtures_pack=FIXTURES_PACK,
            fixtures_dict={'policies': [file_name]})['policies'][file_name]

        file_name = 'policy_2.yaml'
        PolicyControllerRBACTestCase.POLICY_2 = self.fixtures_loader.load_fixtures(
            fixtures_pack=FIXTURES_PACK,
            fixtures_dict={'policies': [file_name]})['policies'][file_name]

        file_name = 'policy_8.yaml'
        PolicyControllerRBACTestCase.POLICY_8 = self.fixtures_loader.load_fixtures(
            fixtures_pack=FIXTURES_PACK,
            fixtures_dict={'policies': [file_name]})['policies'][file_name]

        # Insert mock users, roles and assignments

        # Users
        user_1_db = UserDB(name='policy_list')
        user_1_db = User.add_or_update(user_1_db)
        self.users['policy_list'] = user_1_db

        user_2_db = UserDB(name='policy_view_direct_policy1')
        user_2_db = User.add_or_update(user_2_db)
        self.users['policy_view_direct_policy1'] = user_2_db

        user_3_db = UserDB(name='policy_view_policy8_parent_pack')
        user_3_db = User.add_or_update(user_3_db)
        self.users['policy_view_policy8_parent_pack'] = user_3_db

        user_4_db = UserDB(name='policy_create_policy8_parent_pack')
        user_4_db = User.add_or_update(user_4_db)
        self.users['policy_create_policy8_parent_pack'] = user_4_db

        user_5_db = UserDB(name='policy_update_direct_policy2')
        user_5_db = User.add_or_update(user_5_db)
        self.users['policy_update_direct_policy2'] = user_5_db

        user_6_db = UserDB(name='policy_delete_policy8_parent_pack')
        user_6_db = User.add_or_update(user_6_db)
        self.users['policy_delete_policy8_parent_pack'] = user_6_db

        # Roles
        # policy_list
        grant_db = PermissionGrantDB(resource_uid=None,
                                     resource_type=ResourceType.POLICY,
                                     permission_types=[PermissionType.POLICY_LIST])
        grant_db = PermissionGrant.add_or_update(grant_db)
        permission_grants = [str(grant_db.id)]
        role_1_db = RoleDB(name='policy_list', permission_grants=permission_grants)
        role_1_db = Role.add_or_update(role_1_db)
        self.roles['policy_list'] = role_1_db

        # policy_view directly on policy1
        policy_type_uid = self.models['policies']['policy_1.yaml'].get_uid()
        grant_db = PermissionGrantDB(resource_uid=policy_type_uid,
                                     resource_type=ResourceType.POLICY,
                                     permission_types=[PermissionType.POLICY_VIEW])
        grant_db = PermissionGrant.add_or_update(grant_db)
        permission_grants = [str(grant_db.id)]
        role_1_db = RoleDB(name='policy_view_direct_policy1', permission_grants=permission_grants)
        role_1_db = Role.add_or_update(role_1_db)
        self.roles['policy_view_direct_policy1'] = role_1_db

        # policy_view on a parent pack of policy 8
        policy_pack_uid = self.models['policies']['policy_8.yaml'].get_pack_uid()
        grant_db = PermissionGrantDB(resource_uid=policy_pack_uid,
                                     resource_type=ResourceType.PACK,
                                     permission_types=[PermissionType.POLICY_VIEW])
        grant_db = PermissionGrant.add_or_update(grant_db)
        permission_grants = [str(grant_db.id)]
        role_1_db = RoleDB(name='policy_view_policy8_parent_pack',
                           permission_grants=permission_grants)
        role_1_db = Role.add_or_update(role_1_db)
        self.roles['policy_view_policy8_parent_pack'] = role_1_db

        # policy_create on a parent pack of policy 8
        policy_pack_uid = self.models['policies']['policy_8.yaml'].get_pack_uid()
        grant_db = PermissionGrantDB(resource_uid=policy_pack_uid,
                                     resource_type=ResourceType.PACK,
                                     permission_types=[PermissionType.POLICY_CREATE])
        grant_db = PermissionGrant.add_or_update(grant_db)
        permission_grants = [str(grant_db.id)]
        role_1_db = RoleDB(name='policy_create_policy8_parent_pack',
                           permission_grants=permission_grants)
        role_1_db = Role.add_or_update(role_1_db)
        self.roles['policy_create_policy8_parent_pack'] = role_1_db

        # policy_view directly on policy1
        policy_uid = self.models['policies']['policy_2.yaml'].get_uid()
        grant_db = PermissionGrantDB(resource_uid=policy_uid,
                                     resource_type=ResourceType.POLICY,
                                     permission_types=[PermissionType.POLICY_MODIFY])
        grant_db = PermissionGrant.add_or_update(grant_db)
        permission_grants = [str(grant_db.id)]
        role_1_db = RoleDB(name='policy_update_direct_policy2', permission_grants=permission_grants)
        role_1_db = Role.add_or_update(role_1_db)
        self.roles['policy_update_direct_policy2'] = role_1_db

        # policy_delete on a parent pack of policy 8
        policy_pack_uid = self.models['policies']['policy_8.yaml'].get_pack_uid()
        grant_db = PermissionGrantDB(resource_uid=policy_pack_uid,
                                     resource_type=ResourceType.PACK,
                                     permission_types=[PermissionType.POLICY_DELETE])
        grant_db = PermissionGrant.add_or_update(grant_db)
        permission_grants = [str(grant_db.id)]
        role_1_db = RoleDB(name='policy_delete_policy8_parent_pack',
                           permission_grants=permission_grants)
        role_1_db = Role.add_or_update(role_1_db)
        self.roles['policy_delete_policy8_parent_pack'] = role_1_db

        # Role assignments
        role_assignment_db = UserRoleAssignmentDB(
            user=self.users['policy_list'].name,
            role=self.roles['policy_list'].name,
            source='assignments/%s.yaml' % self.users['policy_list'].name)
        UserRoleAssignment.add_or_update(role_assignment_db)

        role_assignment_db = UserRoleAssignmentDB(
            user=self.users['policy_view_direct_policy1'].name,
            role=self.roles['policy_view_direct_policy1'].name,
            source='assignments/%s.yaml' % self.users['policy_view_direct_policy1'].name)
        UserRoleAssignment.add_or_update(role_assignment_db)

        role_assignment_db = UserRoleAssignmentDB(
            user=self.users['policy_view_policy8_parent_pack'].name,
            role=self.roles['policy_view_policy8_parent_pack'].name,
            source='assignments/%s.yaml' % self.users['policy_view_policy8_parent_pack'].name)
        UserRoleAssignment.add_or_update(role_assignment_db)

        role_assignment_db = UserRoleAssignmentDB(
            user=self.users['policy_create_policy8_parent_pack'].name,
            role=self.roles['policy_create_policy8_parent_pack'].name,
            source='assignments/%s.yaml' % self.users['policy_create_policy8_parent_pack'].name)
        UserRoleAssignment.add_or_update(role_assignment_db)

        role_assignment_db = UserRoleAssignmentDB(
            user=self.users['policy_update_direct_policy2'].name,
            role=self.roles['policy_update_direct_policy2'].name,
            source='assignments/%s.yaml' % self.users['policy_update_direct_policy2'].name)
        UserRoleAssignment.add_or_update(role_assignment_db)

        role_assignment_db = UserRoleAssignmentDB(
            user=self.users['policy_delete_policy8_parent_pack'].name,
            role=self.roles['policy_delete_policy8_parent_pack'].name,
            source='assignments/%s.yaml' % self.users['policy_delete_policy8_parent_pack'].name)
        UserRoleAssignment.add_or_update(role_assignment_db)

    def test_get_all_no_permissions(self):
        user_db = self.users['no_permissions']
        self.use_user(user_db)

        resp = self.app.get('/v1/policies', expect_errors=True)
        expected_msg = ('User "no_permissions" doesn\'t have required permission '
                        '"policy_list"')
        self.assertEqual(resp.status_code, http_client.FORBIDDEN)
        self.assertEqual(resp.json['faultstring'], expected_msg)

    def test_get_one_no_permissions(self):
        user_db = self.users['no_permissions']
        self.use_user(user_db)

        policy_id = self.models['policies']['policy_1.yaml'].id
        policy_uid = self.models['policies']['policy_1.yaml'].get_uid()
        resp = self.app.get('/v1/policies/%s' % (policy_id), expect_errors=True)
        expected_msg = ('User "no_permissions" doesn\'t have required permission "policy_view"'
                        ' on resource "%s"' % (policy_uid))
        self.assertEqual(resp.status_code, http_client.FORBIDDEN)
        self.assertEqual(resp.json['faultstring'], expected_msg)

    def test_get_all_permission_success_get_one_no_permission_failure(self):
        user_db = self.users['policy_list']
        self.use_user(user_db)

        # policy_list permission, but no policy_view permission
        resp = self.app.get('/v1/policies')
        self.assertEqual(resp.status_code, http_client.OK)
        self.assertEqual(len(resp.json), 3)

        policy_id = self.models['policies']['policy_1.yaml'].id
        policy_uid = self.models['policies']['policy_1.yaml'].get_uid()
        resp = self.app.get('/v1/policies/%s' % (policy_id), expect_errors=True)
        expected_msg = ('User "policy_list" doesn\'t have required permission "policy_view"'
                        ' on resource "%s"' % (policy_uid))
        self.assertEqual(resp.status_code, http_client.FORBIDDEN)
        self.assertEqual(resp.json['faultstring'], expected_msg)

    def test_get_one_permission_success_get_all_no_permission_failure(self):
        user_db = self.users['policy_view_direct_policy1']
        self.use_user(user_db)

        # policy_view permission, but no policy_type_list permission
        resp = self.app.get('/v1/policies', expect_errors=True)
        expected_msg = ('User "policy_view_direct_policy1" doesn\'t have required permission '
                        '"policy_list"')
        self.assertEqual(resp.status_code, http_client.FORBIDDEN)
        self.assertEqual(resp.json['faultstring'], expected_msg)

        # policy_view in policy_1, but not on policy_2
        policy_id = self.models['policies']['policy_1.yaml'].id
        policy_uid = self.models['policies']['policy_1.yaml'].get_uid()
        resp = self.app.get('/v1/policies/%s' % (policy_id))
        self.assertEqual(resp.status_code, http_client.OK)
        self.assertEqual(resp.json['uid'], policy_uid)

        policy_id = self.models['policies']['policy_2.yaml'].id
        policy_uid = self.models['policies']['policy_2.yaml'].get_uid()
        resp = self.app.get('/v1/policies/%s' % (policy_id), expect_errors=True)
        expected_msg = ('User "policy_view_direct_policy1" doesn\'t have required permission'
                        ' "policy_view" on resource "%s"' % (policy_uid))
        self.assertEqual(resp.status_code, http_client.FORBIDDEN)
        self.assertEqual(resp.json['faultstring'], expected_msg)

        # policy_view on parent pack of policy8, but not on policy1
        user_db = self.users['policy_view_policy8_parent_pack']
        self.use_user(user_db)

        policy_id = self.models['policies']['policy_8.yaml'].id
        policy_uid = self.models['policies']['policy_8.yaml'].get_uid()
        resp = self.app.get('/v1/policies/%s' % (policy_id))
        self.assertEqual(resp.status_code, http_client.OK)
        self.assertEqual(resp.json['uid'], policy_uid)

        policy_id = self.models['policies']['policy_1.yaml'].id
        policy_uid = self.models['policies']['policy_1.yaml'].get_uid()
        resp = self.app.get('/v1/policies/%s' % (policy_id), expect_errors=True)
        expected_msg = ('User "policy_view_policy8_parent_pack" doesn\'t have required permission'
                        ' "policy_view" on resource "%s"' % (policy_uid))
        self.assertEqual(resp.status_code, http_client.FORBIDDEN)
        self.assertEqual(resp.json['faultstring'], expected_msg)

    def test_policy_create_no_permissions(self):
        user_db = self.users['no_permissions']
        self.use_user(user_db)

        data = self.POLICY_1
        resp = self.app.post_json('/v1/policies', data, expect_errors=True)
        expected_msg = ('User "no_permissions" doesn\'t have required permission "policy_create"')
        self.assertEqual(resp.status_code, http_client.FORBIDDEN)
        self.assertEqual(resp.json['faultstring'], expected_msg)

    def test_policy_create_success(self):
        user_db = self.users['policy_create_policy8_parent_pack']
        self.use_user(user_db)

        data = copy.deepcopy(self.POLICY_8)
        data['name'] = 'foo-bar-8'
        data['resource_ref'] = 'foo-bar-8'
        resp = self.app.post_json('/v1/policies', data)
        self.assertEqual(resp.status_code, http_client.CREATED)

    def test_policy_update_no_permissions(self):
        user_db = self.users['no_permissions']
        self.use_user(user_db)

        policy_id = self.models['policies']['policy_1.yaml'].id
        policy_uid = self.models['policies']['policy_1.yaml'].get_uid()
        data = self.POLICY_1
        resp = self.app.put_json('/v1/policies/%s' % (policy_id), data, expect_errors=True)
        expected_msg = ('User "no_permissions" doesn\'t have required permission "policy_modify"'
                        ' on resource "%s"' % (policy_uid))
        self.assertEqual(resp.status_code, http_client.FORBIDDEN)
        self.assertEqual(resp.json['faultstring'], expected_msg)

    def test_policy_update_success(self):
        user_db = self.users['policy_update_direct_policy2']
        self.use_user(user_db)

        policy_id = self.models['policies']['policy_2.yaml'].id
        data = self.POLICY_2
        data['id'] = str(policy_id)
        data['name'] = 'new-name'
        resp = self.app.put_json('/v1/policies/%s' % (policy_id), data)
        self.assertEqual(resp.status_code, http_client.OK)
        self.assertEqual(resp.json['name'], data['name'])

    def test_policy_delete_success(self):
        user_db = self.users['policy_delete_policy8_parent_pack']
        self.use_user(user_db)

        policy_id = self.models['policies']['policy_8.yaml'].id
        resp = self.app.delete('/v1/policies/%s' % (policy_id), expect_errors=True)
        self.assertEqual(resp.status_code, http_client.NO_CONTENT)

    def test_policy_delete_no_permissions(self):
        user_db = self.users['no_permissions']
        self.use_user(user_db)

        policy_id = self.models['policies']['policy_1.yaml'].id
        policy_uid = self.models['policies']['policy_1.yaml'].get_uid()
        resp = self.app.delete('/v1/policies/%s' % (policy_id), expect_errors=True)
        expected_msg = ('User "no_permissions" doesn\'t have required permission "policy_delete"'
                        ' on resource "%s"' % (policy_uid))
        self.assertEqual(resp.status_code, http_client.FORBIDDEN)
        self.assertEqual(resp.json['faultstring'], expected_msg)

    def test_get_all_limit_minus_one(self):
        user_db = self.users['observer']
        self.use_user(user_db)

        resp = self.app.get('/v1/policies?limit=-1', expect_errors=True)
        self.assertEqual(resp.status_code, http_client.FORBIDDEN)

        user_db = self.users['admin']
        self.use_user(user_db)

        resp = self.app.get('/v1/policies?limit=-1')
        self.assertEqual(resp.status_code, http_client.OK)

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
from st2tests import config as tests_config
from tests.base import APIControllerWithRBACTestCase

tests_config.parse_args()

http_client = six.moves.http_client

__all__ = [
    'ApiKeyControllerRBACTestCase'
]

FIXTURES_PACK = 'generic'
TEST_FIXTURES = {
    'apikeys': ['apikey1.yaml', 'apikey2.yaml'],
}


class ApiKeyControllerRBACTestCase(APIControllerWithRBACTestCase):
    fixtures_loader = FixturesLoader()

    def setUp(self):
        super(ApiKeyControllerRBACTestCase, self).setUp()
        self.models = self.fixtures_loader.save_fixtures_to_db(fixtures_pack=FIXTURES_PACK,
                                                               fixtures_dict=TEST_FIXTURES)

        file_name = 'apikey1.yaml'
        ApiKeyControllerRBACTestCase.API_KEY_1 = self.fixtures_loader.load_fixtures(
            fixtures_pack=FIXTURES_PACK,
            fixtures_dict={'apikeys': [file_name]})['apikeys'][file_name]

        file_name = 'apikey2.yaml'
        ApiKeyControllerRBACTestCase.API_KEY_1 = self.fixtures_loader.load_fixtures(
            fixtures_pack=FIXTURES_PACK,
            fixtures_dict={'apikeys': [file_name]})['apikeys'][file_name]

        # Insert mock users, roles and assignments

        # Users
        user_1_db = UserDB(name='api_key_list')
        user_1_db = User.add_or_update(user_1_db)
        self.users['api_key_list'] = user_1_db

        user_2_db = UserDB(name='api_key_view')
        user_2_db = User.add_or_update(user_2_db)
        self.users['api_key_view'] = user_2_db

        user_3_db = UserDB(name='api_key_create')
        user_3_db = User.add_or_update(user_3_db)
        self.users['api_key_create'] = user_3_db

        # Roles
        # api_key_list
        grant_db = PermissionGrantDB(resource_uid=None,
                                     resource_type=ResourceType.API_KEY,
                                     permission_types=[PermissionType.API_KEY_LIST])
        grant_db = PermissionGrant.add_or_update(grant_db)
        permission_grants = [str(grant_db.id)]
        role_1_db = RoleDB(name='api_key_list', permission_grants=permission_grants)
        role_1_db = Role.add_or_update(role_1_db)
        self.roles['api_key_list'] = role_1_db

        # api_key_view on apikey1
        api_key_uid = self.models['apikeys']['apikey1.yaml'].get_uid()

        grant_db = PermissionGrantDB(resource_uid=api_key_uid,
                                     resource_type=ResourceType.API_KEY,
                                     permission_types=[PermissionType.API_KEY_VIEW])
        grant_db = PermissionGrant.add_or_update(grant_db)
        permission_grants = [str(grant_db.id)]
        role_1_db = RoleDB(name='api_key_view', permission_grants=permission_grants)
        role_1_db = Role.add_or_update(role_1_db)
        self.roles['api_key_view'] = role_1_db

        # api_key_list
        grant_db = PermissionGrantDB(resource_uid=None,
                                     resource_type=ResourceType.API_KEY,
                                     permission_types=[PermissionType.API_KEY_CREATE])
        grant_db = PermissionGrant.add_or_update(grant_db)
        permission_grants = [str(grant_db.id)]
        role_1_db = RoleDB(name='api_key_create', permission_grants=permission_grants)
        role_1_db = Role.add_or_update(role_1_db)
        self.roles['api_key_create'] = role_1_db

        # Role assignments
        role_assignment_db = UserRoleAssignmentDB(
            user=self.users['api_key_list'].name,
            role=self.roles['api_key_list'].name,
            source='assignments/%s.yaml' % self.users['api_key_list'].name)
        UserRoleAssignment.add_or_update(role_assignment_db)

        role_assignment_db = UserRoleAssignmentDB(
            user=self.users['api_key_view'].name,
            role=self.roles['api_key_view'].name,
            source='assignments/%s.yaml' % self.users['api_key_view'].name)
        UserRoleAssignment.add_or_update(role_assignment_db)

        role_assignment_db = UserRoleAssignmentDB(
            user=self.users['api_key_create'].name,
            role=self.roles['api_key_create'].name,
            source='assignments/%s.yaml' % self.users['api_key_create'].name)
        UserRoleAssignment.add_or_update(role_assignment_db)

    def test_get_all_no_permissions(self):
        user_db = self.users['no_permissions']
        self.use_user(user_db)

        resp = self.app.get('/v1/apikeys', expect_errors=True)
        expected_msg = ('User "no_permissions" doesn\'t have required permission "api_key_list"')
        self.assertEqual(resp.status_code, http_client.FORBIDDEN)
        self.assertEqual(resp.json['faultstring'], expected_msg)

    def test_get_one_no_permissions(self):
        user_db = self.users['no_permissions']
        self.use_user(user_db)

        api_key_id = self.models['apikeys']['apikey1.yaml'].id
        api_key_uid = self.models['apikeys']['apikey1.yaml'].get_uid()
        resp = self.app.get('/v1/apikeys/%s' % (api_key_id), expect_errors=True)
        expected_msg = ('User "no_permissions" doesn\'t have required permission "api_key_view"'
                        ' on resource "%s"' % (api_key_uid))
        self.assertEqual(resp.status_code, http_client.FORBIDDEN)
        self.assertEqual(resp.json['faultstring'], expected_msg)

    def test_get_all_permission_success_get_one_no_permission_failure(self):
        user_db = self.users['api_key_list']
        self.use_user(user_db)

        # api_key_list permission, but no api_key_view permission
        resp = self.app.get('/v1/apikeys')
        self.assertEqual(resp.status_code, http_client.OK)
        self.assertEqual(len(resp.json), 2)

        api_key_id = self.models['apikeys']['apikey1.yaml'].id
        api_key_uid = self.models['apikeys']['apikey1.yaml'].get_uid()
        resp = self.app.get('/v1/apikeys/%s' % (api_key_id), expect_errors=True)
        expected_msg = ('User "api_key_list" doesn\'t have required permission "api_key_view"'
                        ' on resource "%s"' % (api_key_uid))
        self.assertEqual(resp.status_code, http_client.FORBIDDEN)
        self.assertEqual(resp.json['faultstring'], expected_msg)

    def test_get_one_permission_success_get_all_no_permission_failure(self):
        user_db = self.users['api_key_view']
        self.use_user(user_db)

        # api_key_view permission, but no api_key_list permission
        api_key_id = self.models['apikeys']['apikey1.yaml'].id

        resp = self.app.get('/v1/apikeys/%s' % (api_key_id))
        self.assertEqual(resp.status_code, http_client.OK)
        self.assertEqual(resp.json['user'], self.models['apikeys']['apikey1.yaml'].user)

        resp = self.app.get('/v1/apikeys', expect_errors=True)
        expected_msg = ('User "api_key_view" doesn\'t have required permission "api_key_list"')
        self.assertEqual(resp.status_code, http_client.FORBIDDEN)
        self.assertEqual(resp.json['faultstring'], expected_msg)

    def test_create_no_permissions_failure(self):
        user_db = self.users['no_permissions']
        self.use_user(user_db)

        resp = self.app.post('/v1/apikeys', {}, expect_errors=True)
        expected_msg = ('User "no_permissions" doesn\'t have required permission "api_key_create"')
        self.assertEqual(resp.status_code, http_client.FORBIDDEN)
        self.assertEqual(resp.json['faultstring'], expected_msg)

    def test_create_correct_permission_success(self):
        user_db = self.users['api_key_create']
        self.use_user(user_db)

        # User provided
        resp = self.app.post_json('/v1/apikeys', {'user': 'joe22'})
        self.assertEqual(resp.status_code, http_client.CREATED)

        # User not provide
        resp = self.app.post_json('/v1/apikeys', {'user': 'joe22'})
        self.assertEqual(resp.status_code, http_client.CREATED)

    def test_get_all_limit_minus_one(self):
        user_db = self.users['observer']
        self.use_user(user_db)

        resp = self.app.get('/v1/apikeys?limit=-1', expect_errors=True)
        self.assertEqual(resp.status_code, http_client.FORBIDDEN)

        user_db = self.users['admin']
        self.use_user(user_db)

        resp = self.app.get('/v1/apikeys?limit=-1')
        self.assertEqual(resp.status_code, http_client.OK)

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

import mock
import six

import st2common.validators.api.action as action_validator
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
    'ActionControllerRBACTestCase'
]

FIXTURES_PACK = 'generic'
TEST_FIXTURES = {
    'runners': ['testrunner1.yaml'],
    'actions': ['action1.yaml', 'local.yaml'],
}

ACTION_2 = {
    'name': 'ma.dummy.action',
    'pack': 'examples',
    'description': 'test description',
    'enabled': True,
    'entry_point': '/tmp/test/action2.py',
    'runner_type': 'local-shell-script',
    'parameters': {
        'c': {'type': 'string', 'default': 'C1', 'position': 0},
        'd': {'type': 'string', 'default': 'D1', 'immutable': True}
    }
}


class ActionControllerRBACTestCase(APIControllerWithRBACTestCase):
    fixtures_loader = FixturesLoader()

    def setUp(self):
        super(ActionControllerRBACTestCase, self).setUp()
        self.fixtures_loader.save_fixtures_to_db(fixtures_pack=FIXTURES_PACK,
                                                 fixtures_dict=TEST_FIXTURES)

        file_name = 'action1.yaml'
        ActionControllerRBACTestCase.ACTION_1 = self.fixtures_loader.load_fixtures(
            fixtures_pack=FIXTURES_PACK,
            fixtures_dict={'actions': [file_name]})['actions'][file_name]

        # Insert mock users, roles and assignments

        # Users
        user_2_db = UserDB(name='action_create')
        user_2_db = User.add_or_update(user_2_db)
        self.users['action_create'] = user_2_db

        # Roles
        # action_create grant on parent pack
        grant_db = PermissionGrantDB(resource_uid='pack:examples',
                                     resource_type=ResourceType.PACK,
                                     permission_types=[PermissionType.ACTION_CREATE])
        grant_db = PermissionGrant.add_or_update(grant_db)
        permission_grants = [str(grant_db.id)]
        role_1_db = RoleDB(name='action_create', permission_grants=permission_grants)
        role_1_db = Role.add_or_update(role_1_db)
        self.roles['action_create'] = role_1_db

        # Role assignments
        user_db = self.users['action_create']
        role_assignment_db = UserRoleAssignmentDB(
            user=user_db.name,
            role=self.roles['action_create'].name,
            source='assignments/%s.yaml' % user_db.name)
        UserRoleAssignment.add_or_update(role_assignment_db)

    def test_create_action_no_action_create_permission(self):
        user_db = self.users['no_permissions']
        self.use_user(user_db)

        resp = self.__do_post(ActionControllerRBACTestCase.ACTION_1)
        expected_msg = ('User "no_permissions" doesn\'t have required permission "action_create" '
                        'on resource "action:wolfpack:action-1"')
        self.assertEqual(resp.status_code, http_client.FORBIDDEN)
        self.assertEqual(resp.json['faultstring'], expected_msg)

    @mock.patch.object(action_validator, 'validate_action', mock.MagicMock(
        return_value=True))
    def test_create_action_success(self):
        user_db = self.users['action_create']
        self.use_user(user_db)

        resp = self.__do_post(ACTION_2)
        self.assertEqual(resp.status_code, http_client.CREATED)

    def test_get_all_limit_minus_one(self):
        # non-admin user, should return permission error
        user_db = self.users['observer']
        self.use_user(user_db)

        resp = self.app.get('/v1/actions?limit=-1', expect_errors=True)

        expected_msg = ('Administrator access required to be able to specify limit=-1 and '
                        'retrieve all the records')
        self.assertEqual(resp.status_code, http_client.FORBIDDEN)
        self.assertEqual(resp.json['faultstring'], expected_msg)

        # admin user, should return all the results
        user_db = self.users['admin']
        self.use_user(user_db)

        resp = self.app.get('/v1/actions?limit=-1')
        self.assertEqual(resp.status_code, http_client.OK)

    def test_get_all_limit_larget_than_page_size(self):
        # non-admin user, should return permission error
        # admin user, should return all the results
        user_db = self.users['observer']
        self.use_user(user_db)

        resp = self.app.get('/v1/actions?limit=20000', expect_errors=True)

        expected_msg = ('Limit "20000" specified, maximum value is "100"')
        self.assertEqual(resp.status_code, http_client.FORBIDDEN)
        self.assertEqual(resp.json['faultstring'], expected_msg)

        # admin user, should return all the results
        user_db = self.users['admin']
        self.use_user(user_db)

        resp = self.app.get('/v1/actions?limit=20000')
        self.assertEqual(resp.status_code, http_client.OK)

    @staticmethod
    def __get_action_id(resp):
        return resp.json['id']

    def __do_post(self, rule):
        return self.app.post_json('/v1/actions', rule, expect_errors=True)

    def __do_delete(self, action_id, expect_errors=False):
        return self.app.delete('/v1/actions/%s' % action_id, expect_errors=expect_errors)

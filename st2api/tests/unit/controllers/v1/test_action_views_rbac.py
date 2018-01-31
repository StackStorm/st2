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
import mock

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
from st2common.content import utils as content_utils
from st2tests.fixturesloader import FixturesLoader
from st2common.util.compat import mock_open_name
from tests.base import APIControllerWithRBACTestCase

http_client = six.moves.http_client

__all__ = [
    'ActionViewsControllerRBACTestCase'
]

FIXTURES_PACK = 'generic'
TEST_FIXTURES = {
    'runners': ['testrunner2.yaml'],
    'actions': ['a1.yaml', 'a2.yaml'],
}


class ActionViewsControllerRBACTestCase(APIControllerWithRBACTestCase):
    fixtures_loader = FixturesLoader()

    def setUp(self):
        super(ActionViewsControllerRBACTestCase, self).setUp()
        self.models = self.fixtures_loader.save_fixtures_to_db(fixtures_pack=FIXTURES_PACK,
                                                               fixtures_dict=TEST_FIXTURES)

        file_name = 'a1.yaml'
        ActionViewsControllerRBACTestCase.ACTION_1 = self.fixtures_loader.load_fixtures(
            fixtures_pack=FIXTURES_PACK,
            fixtures_dict={'actions': [file_name]})['actions'][file_name]

        file_name = 'a2.yaml'
        ActionViewsControllerRBACTestCase.ACTION_1 = self.fixtures_loader.load_fixtures(
            fixtures_pack=FIXTURES_PACK,
            fixtures_dict={'actions': [file_name]})['actions'][file_name]

        # Insert mock users, roles and assignments

        # Users
        user_2_db = UserDB(name='action_view_a1')
        user_2_db = User.add_or_update(user_2_db)
        self.users['action_view_a1'] = user_2_db

        # Roles

        # action_view on a1
        action_uid = self.models['actions']['a1.yaml'].get_uid()
        grant_db = PermissionGrantDB(resource_uid=action_uid,
                                     resource_type=ResourceType.ACTION,
                                     permission_types=[PermissionType.ACTION_VIEW])
        grant_db = PermissionGrant.add_or_update(grant_db)
        permission_grants = [str(grant_db.id)]
        role_1_db = RoleDB(name='action_view_a1', permission_grants=permission_grants)
        role_1_db = Role.add_or_update(role_1_db)
        self.roles['action_view_a1'] = role_1_db

        # Role assignments
        role_assignment_db = UserRoleAssignmentDB(
            user=self.users['action_view_a1'].name,
            role=self.roles['action_view_a1'].name,
            source='assignments/%s.yaml' % self.users['action_view_a1'].name)
        UserRoleAssignment.add_or_update(role_assignment_db)

    def test_get_entry_point_view_no_permission(self):
        user_db = self.users['no_permissions']
        self.use_user(user_db)

        action_id = self.models['actions']['a1.yaml'].id
        action_uid = self.models['actions']['a1.yaml'].get_uid()
        resp = self.app.get('/v1/actions/views/entry_point/%s' % (action_id), expect_errors=True)
        expected_msg = ('User "no_permissions" doesn\'t have required permission "action_view"'
                        ' on resource "%s"' % (action_uid))
        self.assertEqual(resp.status_code, http_client.FORBIDDEN)
        self.assertEqual(resp.json['faultstring'], expected_msg)

    @mock.patch.object(content_utils, 'get_entry_point_abs_path', mock.MagicMock(
        return_value='/path/to/file'))
    @mock.patch(mock_open_name, mock.mock_open(read_data='file content'), create=True)
    def test_get_entry_point_view_success(self):
        user_db = self.users['action_view_a1']
        self.use_user(user_db)

        # action_view on a1, but no permissions on a2
        action_id = self.models['actions']['a1.yaml'].id
        resp = self.app.get('/v1/actions/views/entry_point/%s' % (action_id))
        self.assertEqual(resp.status_code, http_client.OK)

        action_id = self.models['actions']['a2.yaml'].id
        action_uid = self.models['actions']['a2.yaml'].get_uid()
        resp = self.app.get('/v1/actions/views/entry_point/%s' % (action_id), expect_errors=True)
        expected_msg = ('User "action_view_a1" doesn\'t have required permission "action_view"'
                        ' on resource "%s"' % (action_uid))
        self.assertEqual(resp.status_code, http_client.FORBIDDEN)
        self.assertEqual(resp.json['faultstring'], expected_msg)

    def test_get_parameters_view_no_permission(self):
        user_db = self.users['no_permissions']
        self.use_user(user_db)

        action_id = self.models['actions']['a1.yaml'].id
        action_uid = self.models['actions']['a1.yaml'].get_uid()
        resp = self.app.get('/v1/actions/views/parameters/%s' % (action_id), expect_errors=True)
        expected_msg = ('User "no_permissions" doesn\'t have required permission "action_view"'
                        ' on resource "%s"' % (action_uid))
        self.assertEqual(resp.status_code, http_client.FORBIDDEN)
        self.assertEqual(resp.json['faultstring'], expected_msg)

    def test_get_parameters_view_success(self):
        user_db = self.users['action_view_a1']
        self.use_user(user_db)

        # action_view on a1, but no permissions on a2
        action_id = self.models['actions']['a1.yaml'].id
        resp = self.app.get('/v1/actions/views/parameters/%s' % (action_id))
        self.assertEqual(resp.status_code, http_client.OK)

        action_id = self.models['actions']['a2.yaml'].id
        action_uid = self.models['actions']['a2.yaml'].get_uid()
        resp = self.app.get('/v1/actions/views/parameters/%s' % (action_id), expect_errors=True)
        expected_msg = ('User "action_view_a1" doesn\'t have required permission "action_view"'
                        ' on resource "%s"' % (action_uid))
        self.assertEqual(resp.status_code, http_client.FORBIDDEN)
        self.assertEqual(resp.json['faultstring'], expected_msg)

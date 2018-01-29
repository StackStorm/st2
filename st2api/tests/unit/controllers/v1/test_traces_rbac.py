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
from tests.base import APIControllerWithRBACTestCase

http_client = six.moves.http_client

__all__ = [
    'TraceControllerRBACTestCase'
]

FIXTURES_PACK = 'generic'
TEST_FIXTURES = {
    'traces': ['trace_for_test_enforce.yaml', 'trace_for_test_enforce_2.yaml',
               'trace_for_test_enforce_3.yaml'],
}


class TraceControllerRBACTestCase(APIControllerWithRBACTestCase):
    fixtures_loader = FixturesLoader()

    def setUp(self):
        super(TraceControllerRBACTestCase, self).setUp()
        self.models = self.fixtures_loader.save_fixtures_to_db(fixtures_pack=FIXTURES_PACK,
                                                               fixtures_dict=TEST_FIXTURES)

        file_name = 'trace_for_test_enforce.yaml'
        TraceControllerRBACTestCase.TRACE_1 = self.fixtures_loader.load_fixtures(
            fixtures_pack=FIXTURES_PACK,
            fixtures_dict={'traces': [file_name]})['traces'][file_name]

        file_name = 'trace_for_test_enforce_2.yaml'
        TraceControllerRBACTestCase.TRACE_1 = self.fixtures_loader.load_fixtures(
            fixtures_pack=FIXTURES_PACK,
            fixtures_dict={'traces': [file_name]})['traces'][file_name]

        file_name = 'trace_for_test_enforce_3.yaml'
        TraceControllerRBACTestCase.TRACE_1 = self.fixtures_loader.load_fixtures(
            fixtures_pack=FIXTURES_PACK,
            fixtures_dict={'traces': [file_name]})['traces'][file_name]

        # Insert mock users, roles and assignments

        # Users
        user_1_db = UserDB(name='trace_list')
        user_1_db = User.add_or_update(user_1_db)
        self.users['trace_list'] = user_1_db

        user_2_db = UserDB(name='trace_view')
        user_2_db = User.add_or_update(user_2_db)
        self.users['trace_view'] = user_2_db

        # Roles
        # trace_list
        grant_db = PermissionGrantDB(resource_uid=None,
                                     resource_type=ResourceType.TRACE,
                                     permission_types=[PermissionType.TRACE_LIST])
        grant_db = PermissionGrant.add_or_update(grant_db)
        permission_grants = [str(grant_db.id)]
        role_1_db = RoleDB(name='trace_list', permission_grants=permission_grants)
        role_1_db = Role.add_or_update(role_1_db)
        self.roles['trace_list'] = role_1_db

        # trace_view on trace 1
        trace_uid = self.models['traces']['trace_for_test_enforce.yaml'].get_uid()
        grant_db = PermissionGrantDB(resource_uid=trace_uid,
                                     resource_type=ResourceType.TRACE,
                                     permission_types=[PermissionType.TRACE_VIEW])
        grant_db = PermissionGrant.add_or_update(grant_db)
        permission_grants = [str(grant_db.id)]
        role_1_db = RoleDB(name='trace_view', permission_grants=permission_grants)
        role_1_db = Role.add_or_update(role_1_db)
        self.roles['trace_view'] = role_1_db

        # Role assignments
        role_assignment_db = UserRoleAssignmentDB(
            user=self.users['trace_list'].name,
            role=self.roles['trace_list'].name,
            source='assignments/%s.yaml' % self.users['trace_list'].name)
        UserRoleAssignment.add_or_update(role_assignment_db)

        role_assignment_db = UserRoleAssignmentDB(
            user=self.users['trace_view'].name,
            role=self.roles['trace_view'].name,
            source='assignments/%s.yaml' % self.users['trace_view'].name)
        UserRoleAssignment.add_or_update(role_assignment_db)

    def test_get_all_no_permissions(self):
        user_db = self.users['no_permissions']
        self.use_user(user_db)

        resp = self.app.get('/v1/traces', expect_errors=True)
        expected_msg = ('User "no_permissions" doesn\'t have required permission "trace_list"')
        self.assertEqual(resp.status_code, http_client.FORBIDDEN)
        self.assertEqual(resp.json['faultstring'], expected_msg)

    def test_get_one_no_permissions(self):
        user_db = self.users['no_permissions']
        self.use_user(user_db)

        trace_id = self.models['traces']['trace_for_test_enforce.yaml'].id
        trace_uid = self.models['traces']['trace_for_test_enforce.yaml'].get_uid()
        resp = self.app.get('/v1/traces/%s' % (trace_id), expect_errors=True)
        expected_msg = ('User "no_permissions" doesn\'t have required permission "trace_view"'
                        ' on resource "%s"' % (trace_uid))
        self.assertEqual(resp.status_code, http_client.FORBIDDEN)
        self.assertEqual(resp.json['faultstring'], expected_msg)

    def test_get_all_permission_success_get_one_no_permission_failure(self):
        user_db = self.users['trace_list']
        self.use_user(user_db)

        # trace_list permission, but no trace_view permission
        resp = self.app.get('/v1/traces')
        self.assertEqual(resp.status_code, http_client.OK)
        self.assertEqual(len(resp.json), 3)

        trace_id = self.models['traces']['trace_for_test_enforce.yaml'].id
        trace_uid = self.models['traces']['trace_for_test_enforce.yaml'].get_uid()
        resp = self.app.get('/v1/traces/%s' % (trace_id), expect_errors=True)
        expected_msg = ('User "trace_list" doesn\'t have required permission "trace_view"'
                        ' on resource "%s"' % (trace_uid))
        self.assertEqual(resp.status_code, http_client.FORBIDDEN)
        self.assertEqual(resp.json['faultstring'], expected_msg)

    def test_get_one_permission_success_get_all_no_permission_failure(self):
        user_db = self.users['trace_view']
        self.use_user(user_db)

        # trace_view permission, but no trace_list permission
        trace_id = self.models['traces']['trace_for_test_enforce.yaml'].id
        trace_uid = self.models['traces']['trace_for_test_enforce.yaml'].get_uid()

        resp = self.app.get('/v1/traces/%s' % (trace_id))
        self.assertEqual(resp.status_code, http_client.OK)
        self.assertEqual(resp.json['uid'], trace_uid)

        resp = self.app.get('/v1/traces', expect_errors=True)
        expected_msg = ('User "trace_view" doesn\'t have required permission "trace_list"')
        self.assertEqual(resp.status_code, http_client.FORBIDDEN)
        self.assertEqual(resp.json['faultstring'], expected_msg)

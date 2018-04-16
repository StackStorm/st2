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
from tests.base import APIControllerWithRBACTestCase

http_client = six.moves.http_client

__all__ = [
    'ExecutionViewsFiltersControllerRBACTestCase'
]


class ExecutionViewsFiltersControllerRBACTestCase(APIControllerWithRBACTestCase):
    def setUp(self):
        super(ExecutionViewsFiltersControllerRBACTestCase, self).setUp()

        # Insert mock users, roles and assignments

        # Users
        user_1_db = UserDB(name='execution_views_filters_list')
        user_1_db = User.add_or_update(user_1_db)
        self.users['execution_views_filters_list'] = user_1_db

        # Roles
        # trace_list
        permission_types = [PermissionType.EXECUTION_VIEWS_FILTERS_LIST]
        grant_db = PermissionGrantDB(resource_uid=None,
                                     resource_type=ResourceType.EXECUTION,
                                     permission_types=permission_types)
        grant_db = PermissionGrant.add_or_update(grant_db)
        permission_grants = [str(grant_db.id)]
        role_1_db = RoleDB(name='execution_views_filters_list',
                           permission_grants=permission_grants)
        role_1_db = Role.add_or_update(role_1_db)
        self.roles['execution_views_filters_list'] = role_1_db

        # Role assignments
        role_assignment_db = UserRoleAssignmentDB(
            user=self.users['execution_views_filters_list'].name,
            role=self.roles['execution_views_filters_list'].name,
            source='assignments/%s.yaml' % self.users['execution_views_filters_list'].name)
        UserRoleAssignment.add_or_update(role_assignment_db)

    def test_get_view_filters_no_permissions(self):
        user_db = self.users['no_permissions']
        self.use_user(user_db)

        resp = self.app.get('/v1/executions/views/filters', expect_errors=True)
        expected_msg = ('User "no_permissions" doesn\'t have required permission '
                        '"execution_views_filters_list"')
        self.assertEqual(resp.status_code, http_client.FORBIDDEN)
        self.assertEqual(resp.json['faultstring'], expected_msg)

    def test_get_view_filters_success(self):
        user_db = self.users['execution_views_filters_list']
        self.use_user(user_db)

        resp = self.app.get('/v1/executions/views/filters')
        self.assertEqual(resp.status_code, http_client.OK)
        self.assertTrue('status' in resp.json)
        self.assertTrue('action' in resp.json)

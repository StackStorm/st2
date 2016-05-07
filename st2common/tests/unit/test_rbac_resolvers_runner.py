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
from st2common.models.db.action import RunnerTypeDB
from st2common.rbac.resolvers import RunnerPermissionsResolver
from tests.unit.test_rbac_resolvers import BasePermissionsResolverTestCase

__all__ = [
    'RunnerPermissionsResolverTestCase'
]


class RunnerPermissionsResolverTestCase(BasePermissionsResolverTestCase):
    def setUp(self):
        super(RunnerPermissionsResolverTestCase, self).setUp()

        # Create some mock users
        user_1_db = UserDB(name='custom_role_runner_view_grant')
        user_1_db = User.add_or_update(user_1_db)
        self.users['custom_role_runner_view_grant'] = user_1_db

        user_2_db = UserDB(name='custom_role_runner_modify_grant')
        user_2_db = User.add_or_update(user_2_db)
        self.users['custom_role_runner_modify_grant'] = user_2_db

        # Create some mock resources on which permissions can be granted
        runner_1_db = RunnerTypeDB(name='runner_1')
        self.resources['runner_1'] = runner_1_db

        runner_2_db = RunnerTypeDB(name='runner_2')
        self.resources['runner_2'] = runner_2_db

        # Create some mock roles with associated permission grants
        # Custom role - "runner_view" grant on runner_1
        grant_db = PermissionGrantDB(resource_uid=self.resources['runner_1'].get_uid(),
                                     resource_type=ResourceType.RUNNER,
                                     permission_types=[PermissionType.RUNNER_VIEW])
        grant_db = PermissionGrant.add_or_update(grant_db)
        permission_grants = [str(grant_db.id)]
        role_db = RoleDB(name='custom_role_runner_view_grant',
                         permission_grants=permission_grants)
        role_db = Role.add_or_update(role_db)
        self.roles['custom_role_runner_view_grant'] = role_db

        # Custom role - "runner_modify" grant on runner_2
        grant_db = PermissionGrantDB(resource_uid=self.resources['runner_2'].get_uid(),
                                     resource_type=ResourceType.RUNNER,
                                     permission_types=[PermissionType.RUNNER_MODIFY])
        grant_db = PermissionGrant.add_or_update(grant_db)
        permission_grants = [str(grant_db.id)]
        role_db = RoleDB(name='custom_role_runner_modify_grant',
                         permission_grants=permission_grants)
        role_db = Role.add_or_update(role_db)
        self.roles['custom_role_runner_modify_grant'] = role_db

        # Create some mock role assignments
        user_db = self.users['custom_role_runner_view_grant']
        role_assignment_db = UserRoleAssignmentDB(
            user=user_db.name,
            role=self.roles['custom_role_runner_view_grant'].name)
        UserRoleAssignment.add_or_update(role_assignment_db)

        user_db = self.users['custom_role_runner_modify_grant']
        role_assignment_db = UserRoleAssignmentDB(
            user=user_db.name,
            role=self.roles['custom_role_runner_modify_grant'].name)
        UserRoleAssignment.add_or_update(role_assignment_db)

    def test_user_has_resource_db_permission(self):
        resolver = RunnerPermissionsResolver()
        all_permission_types = PermissionType.get_valid_permissions_for_resource_type(
            ResourceType.RUNNER)

        # Admin user, should always return true
        resource_db = self.resources['runner_1']
        user_db = self.users['admin']
        self.assertUserHasResourceDbPermissions(
            resolver=resolver,
            user_db=user_db,
            resource_db=resource_db,
            permission_types=all_permission_types)

        # Custom role with "runner_view" grant on runner_1
        resource_db = self.resources['runner_1']
        user_db = self.users['custom_role_runner_view_grant']
        self.assertUserHasResourceDbPermission(
            resolver=resolver,
            user_db=user_db,
            resource_db=resource_db,
            permission_type=PermissionType.RUNNER_VIEW)

        permission_types = [
            PermissionType.RUNNER_MODIFY,
            PermissionType.RUNNER_ALL
        ]
        self.assertUserDoesntHaveResourceDbPermissions(
            resolver=resolver,
            user_db=user_db,
            resource_db=resource_db,
            permission_types=permission_types)

        # Custom role with "runner_modify" grant on runner_2
        resource_db = self.resources['runner_2']
        user_db = self.users['custom_role_runner_modify_grant']
        self.assertUserHasResourceDbPermission(
            resolver=resolver,
            user_db=user_db,
            resource_db=resource_db,
            permission_type=PermissionType.RUNNER_MODIFY)

        permission_types = [
            PermissionType.RUNNER_VIEW,
            PermissionType.RUNNER_ALL
        ]
        self.assertUserDoesntHaveResourceDbPermissions(
            resolver=resolver,
            user_db=user_db,
            resource_db=resource_db,
            permission_types=permission_types)

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
from st2common.models.db.webhook import WebhookDB
from st2common.rbac.resolvers import WebhookPermissionsResolver
from tests.unit.test_rbac_resolvers import BasePermissionsResolverTestCase

__all__ = [
    'WebhookPermissionsResolverTestCase'
]


class WebhookPermissionsResolverTestCase(BasePermissionsResolverTestCase):
    def setUp(self):
        super(WebhookPermissionsResolverTestCase, self).setUp()

        # Create some mock users
        user_1_db = UserDB(name='custom_role_webhook_grant')
        user_1_db = User.add_or_update(user_1_db)
        self.users['custom_role_webhook_grant'] = user_1_db

        # Create some mock resources on which permissions can be granted
        webhook_1_db = WebhookDB(name='st2/')
        self.resources['webhook_1'] = webhook_1_db

        # Create some mock roles with associated permission grants
        # Custom role - "webhook_send" grant on webhook_1
        grant_db = PermissionGrantDB(resource_uid=self.resources['webhook_1'].get_uid(),
                                     resource_type=ResourceType.WEBHOOK,
                                     permission_types=[PermissionType.WEBHOOK_SEND])
        grant_db = PermissionGrant.add_or_update(grant_db)
        permission_grants = [str(grant_db.id)]
        role_db = RoleDB(name='custom_role_webhook_grant',
                         permission_grants=permission_grants)
        role_db = Role.add_or_update(role_db)
        self.roles['custom_role_webhook_grant'] = role_db

        # Create some mock role assignments
        user_db = self.users['custom_role_webhook_grant']
        role_assignment_db = UserRoleAssignmentDB(
            user=user_db.name,
            role=self.roles['custom_role_webhook_grant'].name)
        UserRoleAssignment.add_or_update(role_assignment_db)

    def test_user_has_resource_db_permission(self):
        resolver = WebhookPermissionsResolver()
        all_permission_types = PermissionType.get_valid_permissions_for_resource_type(
            ResourceType.WEBHOOK)

        # Admin user, should always return true
        resource_db = self.resources['webhook_1']
        user_db = self.users['admin']
        self.assertUserHasResourceDbPermissions(
            resolver=resolver,
            user_db=user_db,
            resource_db=resource_db,
            permission_types=all_permission_types)

        # Custom role with "webhook_send" grant on webhook_1
        user_db = self.users['custom_role_webhook_grant']
        self.assertUserHasResourceDbPermission(
            resolver=resolver,
            user_db=user_db,
            resource_db=resource_db,
            permission_type=PermissionType.WEBHOOK_SEND)

        permission_types = [
            PermissionType.WEBHOOK_CREATE,
            PermissionType.WEBHOOK_DELETE,
            PermissionType.WEBHOOK_ALL
        ]
        self.assertUserDoesntHaveResourceDbPermissions(
            resolver=resolver,
            user_db=user_db,
            resource_db=resource_db,
            permission_types=permission_types)

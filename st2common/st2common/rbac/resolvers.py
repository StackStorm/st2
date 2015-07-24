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

"""
Module containing resolver classes which contain permission resolving logic for different resource
types.
"""

from st2common.rbac.types import PermissionType
from st2common.rbac.types import ResourceType
from st2common.rbac.types import SystemRole
from st2common.services.rbac import get_roles_for_user
from st2common.services.rbac import get_all_permission_grants_for_user

__all__ = [
    'ActionPermissionsResolver',

    'get_resolver_for_resource_type'
]


class PermissionsResolver(object):
    """
    Base Permissions Resolver class.

    Permission resolver classes implement permission resolving / checking logic for a particular
    resource type.
    """

    def user_has_system_role_permission(self, user_db, permission_type):
        """
        Check the user system roles and return True if user has the required permission.

        :rtype: ``bool``
        """
        permission_name = PermissionType.get_permission_name(permission_type)

        user_role_dbs = get_roles_for_user(user_db=user_db)
        user_role_names = [role_db.name for role_db in user_role_dbs]

        # System admin has all the permissions
        if SystemRole.SYSTEM_ADMIN in user_role_names:
            return True
        elif SystemRole.ADMIN in user_role_names:
            return True
        elif SystemRole.OBSERVER in user_role_names and permission_name == 'view':
            return True

        return False


class ActionPermissionsResolver(PermissionsResolver):
    def user_has_permission(self, user_db, permission_type):
        # First check the system role permissions
        has_system_role_permission = self.user_has_system_role_permission(user_db=user_db,
            permission_type=permission_type)

        if has_system_role_permission:
            return True

        # Check custom roles
        resource_types = [ResourceType.PACK, ResourceType.ACTION]
        permission_grants = get_all_permission_grants_for_user(user_db=user_db,
                                                               resource_types=resource_types)

        return len(permission_grants) >= 1

    def user_has_resource_permission(self, user_db, resource_db, permission_type):
        # First check the system role permissions
        has_system_role_permission = self.user_has_system_role_permission(user_db=user_db,
            permission_type=permission_type)

        if has_system_role_permission:
            return True

        # Check custom roles
        resource_types = [ResourceType.PACK, ResourceType.ACTION]
        permission_grants = get_all_permission_grants_for_user(user_db=user_db,
                                                               resource_types=resource_types)

        action_uid = resource_db.get_uid()
        pack_uid = resource_db.get_pack_uid()

        for permission_grant in permission_grants:
            matches_pack_grant = self._matches_permission_grant(resource_db=resource_db,
                                                                permission_grant=permission_grant,
                                                                permission_type=permission_type,
                                                                all_permission_type=PermissionType.PACK_ALL)
            matches_action_grant = self._matches_permission_grant(resource_db=resource_db,
                                                                  permission_grant=permission_grant,
                                                                  permission_type=permission_type,
                                                                  all_permission_type=PermissionType.ACTION_ALL)

            # Permissions assigned to the pack are inherited by all the pack resources
            if permission_grant.resource_uid == pack_uid and matches_pack_grant:
                return True
            elif permission_grant.resource_uid == action_uid and matches_action_grant:
                return True

        return False

    def _matches_permission_grant(self, resource_db, permission_grant, permission_type,
                                  all_permission_type):
        """
        :rtype: ``bool``
        """
        resource_type = resource_db.get_resource_type()
        all_permission_type = getattr(PermissionType, '%s_ALL' % (resource_type.upper()))

        if permission_type in permission_grant.permission_types:
            return True
        elif all_permission_type in permission_grant.permission_types:
            return True

        return False


def get_resolver_for_resource_type(resource_type):
    if resource_type == ResourceType.ACTION:
        return ActionPermissionsResolver
    pass

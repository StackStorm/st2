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
    'PackPermissionsResolver',
    'SensorPermissionsResolver',
    'ActionPermissionsResolver',
    'RulePermissionsResolver',

    'get_resolver_for_resource_type',
    'get_resolver_for_permission_type'
]


class PermissionsResolver(object):
    """
    Base Permissions Resolver class.

    Permission resolver classes implement permission resolving / checking logic for a particular
    resource type.
    """

    def _user_has_system_role_permission(self, user_db, permission_type):
        """
        Check the user system roles and return True if user has the required permission.

        :rtype: ``bool``
        """
        permission_name = PermissionType.get_permission_name(permission_type)

        user_role_dbs = get_roles_for_user(user_db=user_db)
        user_role_names = [role_db.name for role_db in user_role_dbs]

        if SystemRole.SYSTEM_ADMIN in user_role_names:
            # System admin has all the permissions
            return True
        elif SystemRole.ADMIN in user_role_names:
            # Admin has all the permissions
            return True
        elif SystemRole.OBSERVER in user_role_names and permission_name == 'view':
            # Observer role has "view" permission on all the resources
            return True

        return False

    def _matches_permission_grant(self, resource_db, permission_grant, permission_type,
                                  all_permission_type):
        """
        :rtype: ``bool``
        """
        if permission_type in permission_grant.permission_types:
            # Direct permission grant
            return True
        elif all_permission_type in permission_grant.permission_types:
            # "ALL" permission grant
            return True

        return False

    def _get_all_permission_type_for_resource(self, resource_db):
        """
        Retrieve "ALL" permission type for the provided resource.
        """
        resource_type = resource_db.get_resource_type()
        permission_type = PermissionType.get_permission_type(resource_type=resource_type,
                                                             permission_name='all')
        return permission_type


class PackPermissionsResolver(PermissionsResolver):
    """
    Permission resolver for "pack" resource type.
    """

    def user_has_permission(self, user_db, permission_type):
        # TODO
        # First check the system role permissions
        has_system_role_permission = self._user_has_system_role_permission(
            user_db=user_db, permission_type=permission_type)

        if has_system_role_permission:
            return True

        # Check custom roles
        resource_types = [ResourceType.PACK]
        permission_grants = get_all_permission_grants_for_user(user_db=user_db,
                                                               resource_types=resource_types,
                                                               permission_type=permission_type)

        if len(permission_grants) >= 1:
            return True

        return False

    def user_has_resource_permission(self, user_db, resource_db, permission_type):
        # First check the system role permissions
        has_system_role_permission = self._user_has_system_role_permission(
            user_db=user_db, permission_type=permission_type)

        if has_system_role_permission:
            return True

        # Check custom roles
        resource_uid = resource_db.get_uid()
        resource_types = [ResourceType.PACK]
        permission_grants = get_all_permission_grants_for_user(user_db=user_db,
                                                               resource_uid=resource_uid,
                                                               resource_types=resource_types)

        if len(permission_grants) >= 1:
            return True

        return False


class SensorPermissionsResolver(PermissionsResolver):
    """
    Permission resolver for "sensor" resource type.
    """

    def user_has_permission(self, user_db, permission_type):
        # TODO
        raise NotImplementedError()

    def user_has_resource_permission(self, user_db, resource_db, permission_type):
        # First check the system role permissions
        has_system_role_permission = self._user_has_system_role_permission(
            user_db=user_db, permission_type=permission_type)

        if has_system_role_permission:
            return True

        # Check custom roles
        sensor_uid = resource_db.get_uid()
        pack_uid = resource_db.get_pack_uid()

        # Check direct grants on the specified resource
        resource_types = [ResourceType.SENSOR]
        permission_grants = get_all_permission_grants_for_user(user_db=user_db,
                                                               resource_uid=sensor_uid,
                                                               resource_types=resource_types,
                                                               permission_type=permission_type)
        if len(permission_grants) >= 1:
            return True

        # Check grants on the parent pack
        resource_types = [ResourceType.PACK]
        permission_grants = get_all_permission_grants_for_user(user_db=user_db,
                                                               resource_uid=pack_uid,
                                                               resource_types=resource_types,
                                                               permission_type=permission_type)

        if len(permission_grants) >= 1:
            return True

        return False


class ActionPermissionsResolver(PermissionsResolver):
    """
    Permission resolver for "action" resource type.
    """

    def user_has_permission(self, user_db, permission_type):
        # TODO
        # First check the system role permissions
        has_system_role_permission = self._user_has_system_role_permission(
            user_db=user_db, permission_type=permission_type)

        if has_system_role_permission:
            return True

        # Check custom roles
        resource_types = [ResourceType.PACK, ResourceType.ACTION]
        permission_grants = get_all_permission_grants_for_user(user_db=user_db,
                                                               resource_types=resource_types,
                                                               permission_type=permission_type)

        if len(permission_grants) >= 1:
            return True

        return False

    def user_has_resource_permission(self, user_db, resource_db, permission_type):
        # First check the system role permissions
        has_system_role_permission = self._user_has_system_role_permission(
            user_db=user_db, permission_type=permission_type)

        if has_system_role_permission:
            return True

        # Check custom roles
        action_uid = resource_db.get_uid()
        pack_uid = resource_db.get_pack_uid()

        # Check direct grants on the specified resource
        resource_types = [ResourceType.ACTION]
        permission_grants = get_all_permission_grants_for_user(user_db=user_db,
                                                               resource_uid=action_uid,
                                                               resource_types=resource_types,
                                                               permission_type=permission_type)
        if len(permission_grants) >= 1:
            return True

        # Check grants on the parent pack
        resource_types = [ResourceType.PACK]
        permission_grants = get_all_permission_grants_for_user(user_db=user_db,
                                                               resource_uid=pack_uid,
                                                               resource_types=resource_types,
                                                               permission_type=permission_type)

        if len(permission_grants) >= 1:
            return True

        return False


class RulePermissionsResolver(PermissionsResolver):
    """
    Permission resolver for "rule" resource type.
    """

    def user_has_permission(self, user_db, permission_type):
        # TODO
        raise NotImplementedError()

    def user_has_resource_permission(self, user_db, resource_db, permission_type):
        # First check the system role permissions
        has_system_role_permission = self._user_has_system_role_permission(
            user_db=user_db, permission_type=permission_type)

        if has_system_role_permission:
            return True

        # Check custom roles
        rule_uid = resource_db.get_uid()
        pack_uid = resource_db.get_pack_uid()

        # Check direct grants on the specified resource
        resource_types = [ResourceType.RULE]
        permission_grants = get_all_permission_grants_for_user(user_db=user_db,
                                                               resource_uid=rule_uid,
                                                               resource_types=resource_types,
                                                               permission_type=permission_type)
        if len(permission_grants) >= 1:
            return True

        # Check grants on the parent pack
        resource_types = [ResourceType.PACK]
        permission_grants = get_all_permission_grants_for_user(user_db=user_db,
                                                               resource_uid=pack_uid,
                                                               resource_types=resource_types,
                                                               permission_type=permission_type)

        if len(permission_grants) >= 1:
            return True

        return False


def get_resolver_for_resource_type(resource_type):
    """
    Return resolver instance for the provided resource type.

    :rtype: :class:`PermissionsResolver`
    """
    if resource_type == ResourceType.ACTION:
        return ActionPermissionsResolver
    else:
        raise ValueError('Unsupported resource: %s' % (resource_type))


def get_resolver_for_permission_type(permission_type):
    """
    Return resolver instance for the provided permission type.

    :rtype: :class:`PermissionsResolver`
    """
    resource_type = PermissionType.get_resource_type(permission_type=permission_type)
    resolver_cls = get_resolver_for_resource_type(resource_type=resource_type)
    resolver_instance = resolver_cls()
    return resolver_instance

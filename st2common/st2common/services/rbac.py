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
from st2common.rbac.types import SystemRole
from st2common.persistence.rbac import Role
from st2common.persistence.rbac import UserRoleAssignment
from st2common.persistence.rbac import PermissionGrant
from st2common.models.db.rbac import RoleDB
from st2common.models.db.rbac import UserRoleAssignmentDB
from st2common.models.db.rbac import PermissionGrantDB


__all__ = [
    'get_all_roles',
    'get_system_roles',
    'get_roles_for_user',

    'create_role',
    'delete_role',

    'assign_role_to_user',
    'revoke_role_from_user',

    'get_all_permission_grants_for_user',
    'create_permission_grant',
    'remove_permission_grant'
]


def get_all_roles():
    """
    Retrieve all the available roles.

    :rtype: ``list`` of :class:`RoleDB`
    """
    result = Role.get_all()
    return result


def get_system_roles():
    """
    Retrieve all the available system roles.

    :rtype: ``list`` of :class:`RoleDB`
    """
    result = Role.query(system=True)
    return result


def get_roles_for_user(user_db):
    """
    Retrieve all the roles assignment to the provided user.

    :param user_db: User to retrieve the roles for.
    :type user_db: :class:`UserDB`

    :rtype: ``list`` of :class:`RoleDB`
    """
    role_names = UserRoleAssignment.query(user=user_db.name).only('role').scalar('role')
    result = Role.query(name__in=role_names)
    return result


def create_role(name, description=None):
    """
    Create a new role.
    """
    if name in SystemRole.get_valid_values():
        raise ValueError('"%s" role name is blacklisted' % (name))

    role_db = RoleDB(name=name, description=description)
    role_db = Role.add_or_update(role_db)
    return role_db


def delete_role(name):
    """"
    Delete role with the provided name.
    """
    if name in SystemRole.get_valid_values():
        raise ValueError('System roles can\'t be deleted')

    role_db = Role.get(name=name)
    result = Role.delete(role_db)
    return result


def assign_role_to_user(role_db, user_db):
    """
    Assign role to a user.

    :param role_db: Role to assign.
    :type role_db: :class:`RoleDB`

    :param user_db: User to assign the role to.
    :type user_db: :class:`UserDB`
    """
    role_assignment_db = UserRoleAssignmentDB(user=user_db.name, role=role_db.name)
    role_assignment_db = UserRoleAssignment.add_or_update(role_assignment_db)
    return role_db


def revoke_role_from_user(role_db, user_db):
    """
    Revoke role from a user.

    :param role_db: Role to revoke.
    :type role_db: :class:`RoleDB`

    :param user_db: User to revoke the role from.
    :type user_db: :class:`UserDB`
    """
    role_assignment_db = UserRoleAssignment.get(user=user_db.name, role=role_db.name)
    result = UserRoleAssignment.delete(role_assignment_db)
    return result


def get_all_permission_grants_for_user(user_db):
    """
    Retrieve all the permission grants for a particular user.

    The result is a union of all the permission grants assigned to the roles which are assigned to
    the user.

    :rtype: ``list`` or :class:`PermissionGrantDB`
    """
    role_names = UserRoleAssignment.query(user=user_db.name).only('role').scalar('role')
    permission_grant_ids = Role.query(name__in=role_names).scalar('permission_grants')
    permission_grant_ids = sum(permission_grant_ids, [])
    permission_grant_dbs = PermissionGrant.query(id__in=permission_grant_ids)

    return permission_grant_dbs


def create_permission_grant(role_db, resource_db, permission_types):
    """
    Add a permission grant to the provided role.

    :param role_db: Role to add the permission assignment to.
    :type role_db: :class:`RoleDB`

    :param resource_db: Resource to create the permission assignment for.
    :type resource_db: :class:`StormFoundationDB`
    """
    permission_types = _validate_permission_types(resource_db=resource_db,
                                                  permission_types=permission_types)
    resource_uid = resource_db.get_uid()
    resource_type = resource_db.get_resource_type()

    # Create or update the PermissionGrantDB
    permission_grant_db = PermissionGrantDB(resource_uid=resource_uid,
                                            resource_type=resource_type,
                                            permission_types=permission_types)
    permission_grant_db = PermissionGrant.add_or_update(permission_grant_db)

    # Add assignment to the role
    role_db.update(push__permission_grants=permission_grant_db.id)

    return permission_grant_db


def remove_permission_grant(role_db, resource_db, permission_types):
    """
    Remove a permission grant from a role.

    :param role_db: Role to remove the permission assignment from.
    :type role_db: :class:`RoleDB`

    :param resource_db: Resource to remove the permission assignment from.
    :type resource_db: :class:`StormFoundationDB`
    """
    permission_types = _validate_permission_types(resource_db=resource_db,
                                                  permission_types=permission_types)
    resource_uid = resource_db.get_uid()
    resource_type = resource_db.get_resource_type()
    permission_grant_db = PermissionGrant.get(resource_uid=resource_uid,
                                              resource_type=resource_type,
                                              permission_types=permission_types)

    # Remove assignment from a role
    role_db.update(pull__permission_grants=permission_grant_db.id)

    return permission_grant_db


def _validate_resource_type(resource_db):
    """
    Validate that the permissions can be manipulated for the provided resource type.
    """
    resource_type = resource_db.get_resource_type()
    valid_resource_types = ResourceType.get_valid_values()

    if resource_type not in valid_resource_types:
        raise ValueError('Permissions cannot be manipulated for a resource of type: %s' %
                         (resource_type))

    return resource_db


def _validate_permission_types(resource_db, permission_types):
    """
    Validate that the permission_types list only contains valid values for the
    provided resource.
    """
    resource_db = _validate_resource_type(resource_db=resource_db)
    resource_type = resource_db.get_resource_type()
    valid_permission_types = PermissionType.get_valid_permissions_for_resource_type(resource_type)

    for permission_type in permission_types:
        if permission_type not in valid_permission_types:
            raise ValueError('Invalid permission type: %s' % (permission_type))

    return permission_types

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

from st2common.persistence.rbac import Role
from st2common.persistence.rbac import UserRoleAssignment
from st2common.persistence.rbac import PermissionAssignment
from st2common.models.db.rbac import RoleDB
from st2common.models.db.rbac import UserRoleAssignmentDB
from st2common.models.db.rbac import PermissionAssignmentDB


__all__ = [
    'get_all_roles',
    'get_roles_for_user',

    'create_role',
    'delete_role',

    'assign_role_to_user',
    'revoke_role_from_user',

    'create_permission_assignment',
    'remove_permission_assignment'
]


def get_all_roles():
    """
    Retrieve all the available roles.

    :rtype: ``list`` of :class:`RoleDB`
    """
    result = Role.get_all()
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
    # TODO: Special case - don't allow creating roles with system role names
    role_db = RoleDB(name=name, description=description)
    role_db = Role.add_or_update(role_db)
    return role_db


def delete_role(name):
    """"
    Delete role with the provided name.
    """
    # TODO: Special case for system roles - those can't be deleted
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


def create_permission_assignment(role_db, resource_db, permission_types):
    """
    Add a permission assignment to the provided role.

    :param role_db: Role to add the permission assignment to.
    :type role_db: :class:`RoleDB`

    :param resource_db: Resource to create the permission assignment for.
    :type resource_db: :class:`StormFoundationDB`
    """
    resource_ref = resource_db.get_uuid()

    # Create or update the PermissionAssignmentDB
    permission_assignment_db = PermissionAssignmentDB(resource_ref=resource_ref,
                                                      permission_types=permission_types)
    permission_assignment_db = PermissionAssignment.add_or_update(permission_assignment_db)

    # Add assignment to the role
    role_db.update(push__permission_assignments=permission_assignment_db.id)

    return permission_assignment_db


def remove_permission_assignment(role_db, resource_db, permission_types):
    """
    Remove a permission assignment from a role.

    :param role_db: Role to remove the permission assignment from.
    :type role_db: :class:`RoleDB`

    :param resource_db: Resource to remove the permission assignment from.
    :type resource_db: :class:`StormFoundationDB`
    """
    resource_ref = resource_db.get_uuid()
    permission_assignment_db = PermissionAssignment.get(resource_ref=resource_ref,
                                                        permission_types=permission_types)

    # Remove assignment from a role
    role_db.update(pull__permission_assignments=permission_assignment_db.id)

    return permission_assignment_db

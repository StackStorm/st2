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
RBAC related utility functions.
"""

import six

from oslo_config import cfg

from st2common.constants.rbac import SystemRole
from st2common.exceptions.rbac import AccessDeniedError
from st2common.exceptions.rbac import ResourceTypeAccessDeniedError
from st2common.exceptions.rbac import ResourceAccessDeniedError
from st2common.rbac import resolvers
from st2common.services import rbac as rbac_services

__all__ = [
    'request_user_is_admin',
    'request_user_has_role',
    'request_user_has_permission',
    'request_user_has_resource_permission',

    'assert_request_user_is_admin',
    'assert_request_user_has_permission',
    'assert_request_user_has_resource_permission',

    'user_is_admin',
    'user_has_permission',
    'user_has_resource_permission',
    'user_has_role'
]


def request_user_is_admin(request):
    """
    Check if the logged-in request user has admin role.

    :rtype: ``bool``
    """
    return request_user_has_role(request=request, role=SystemRole.ADMIN)


def request_user_has_role(request, role):
    """
    Check if the logged-in request user has the provided role.

    :param role: Name of the role to check for.
    :type role: ``str``

    :rtype: ``bool``
    """
    # TODO: Once RBAC is implemented, we should not support running production (non-dev)
    # deployments with auth disabled.
    if not cfg.CONF.auth.enable:
        return True

    user_db = _get_user_db_from_request(request=request)
    return user_has_role(user_db=user_db, role=role)


def request_user_has_permission(request, permission_type):
    """
    Check that currently logged-in user has specified permission.

    :rtype: ``bool``
    """
    user_db = _get_user_db_from_request(request=request)
    return user_has_permission(user_db=user_db, permission_type=permission_type)


def request_user_has_resource_permission(request, resource_db, permission_type):
    """
    Check that currently logged-in user has specified permission on the provied resource.

    :rtype: ``bool``
    """
    user_db = _get_user_db_from_request(request=request)
    return user_has_resource_permission(user_db=user_db, resource_db=resource_db,
                                        permission_type=permission_type)


def assert_request_user_is_admin(request):
    """
    Assert that the currently logged in user is an administrator.

    If the user is not an administrator, an exception is thrown.
    """
    is_admin = request_user_is_admin(request=request)

    if not is_admin:
        user_db = _get_user_db_from_request(request=request)
        raise AccessDeniedError(message='Administrator access required',
                                user_db=user_db)


def assert_request_user_has_permission(request, permission_type):
    """
    Check that currently logged-in user has specified permission.

    If user doesn't have a required permission, AccessDeniedError s thrown.
    """
    has_permission = request_user_has_permission(request=request,
                                                 permission_type=permission_type)

    if not has_permission:
        user_db = _get_user_db_from_request(request=request)
        raise ResourceTypeAccessDeniedError(user_db=user_db, permission_type=permission_type)


def assert_request_user_has_resource_permission(request, resource_db, permission_type):
    """
    Check that currently logged-in user has specified permission on the provied resource.

    If user doesn't have a required permission, AccessDeniedError s thrown.
    """
    has_permission = request_user_has_resource_permission(request=request, resource_db=resource_db,
                                                          permission_type=permission_type)

    if not has_permission:
        user_db = _get_user_db_from_request(request=request)
        raise ResourceAccessDeniedError(user_db=user_db, resource_db=resource_db,
                                        permission_type=permission_type)


def user_is_admin(user_db):
    """
    Return True if the provided user has admin rule, false otherwise.

    :param user_db: User object to check for.
    :type user_db: :class:`UserDB`

    :rtype: ``bool``
    """
    return user_has_role(user_db=user_db, role=SystemRole.ADMIN)


def user_has_role(user_db, role):
    """
    :param user: User object to check for.
    :type user: :class:`UserDB`

    :param role: Role name to check for.
    :type role: ``str``

    :rtype: ``bool``
    """
    assert isinstance(role, six.string_types)

    if not cfg.CONF.rbac.enable:
        return True

    user_role_dbs = rbac_services.get_roles_for_user(user_db=user_db)
    user_role_names = [role_db.name for role_db in user_role_dbs]

    return role in user_role_names


def user_has_permission(user_db, permission_type):
    """
    Check that the provided user has specified permission.
    """
    if not cfg.CONF.rbac.enable:
        return True

    # TODO
    # TODO Verify permission type for the provided resource type
    resolver = resolvers.get_resolver_for_permission_type(permission_type=permission_type)
    result = resolver.user_has_permission(user_db=user_db, permission_type=permission_type)
    return result


def user_has_resource_permission(user_db, resource_db, permission_type):
    """
    Check that the provided user has specified permission on the provided resource.
    """
    if not cfg.CONF.rbac.enable:
        return True

    # TODO
    # TODO Verify permission type for the provided resource type
    resolver = resolvers.get_resolver_for_permission_type(permission_type=permission_type)
    result = resolver.user_has_resource_permission(user_db=user_db, resource_db=resource_db,
                                                   permission_type=permission_type)
    return result


def _get_user_db_from_request(request):
    """
    Retrieve UserDB object from the provided request.
    """
    auth_context = request.context.get('auth', {})

    if not auth_context:
        return None

    user_db = auth_context.get('user', None)
    return user_db

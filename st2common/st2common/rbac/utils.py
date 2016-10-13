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

from st2common.exceptions.rbac import AccessDeniedError
from st2common.exceptions.rbac import ResourceTypeAccessDeniedError
from st2common.exceptions.rbac import ResourceAccessDeniedError
from st2common.rbac.types import PermissionType
from st2common.rbac.types import ResourceType
from st2common.rbac.types import SystemRole
from st2common.rbac import resolvers
from st2common.services import rbac as rbac_services
from st2common.util import action_db as action_utils
from st2common.util.api import get_requester

__all__ = [
    'request_user_is_admin',
    'request_user_is_system_admin',
    'request_user_has_role',
    'request_user_has_permission',
    'request_user_has_resource_api_permission',
    'request_user_has_resource_db_permission',

    'request_user_has_rule_trigger_permission',
    'request_user_has_rule_action_permission',

    'assert_request_user_is_admin',
    'assert_request_user_is_system_admin',
    'assert_request_user_has_permission',
    'assert_request_user_has_resource_db_permission',

    'assert_request_user_is_admin_if_user_query_param_is_provider',

    'assert_request_user_has_rule_trigger_and_action_permission',

    'user_is_admin',
    'user_is_system_admin',
    'user_has_permission',
    'user_has_resource_api_permission',
    'user_has_resource_db_permission',
    'user_has_role',

    'get_user_db_from_request'
]


def request_user_is_admin(request):
    """
    Check if the logged-in request user has admin (either system admin or admin) role.

    :rtype: ``bool``
    """
    user_db = get_user_db_from_request(request=request)
    return user_is_admin(user_db=user_db)


def request_user_is_system_admin(request):
    """
    Check if the logged-in request user has system admin role.

    :rtype: ``bool``
    """
    user_db = get_user_db_from_request(request=request)
    return user_is_system_admin(user_db=user_db)


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

    user_db = get_user_db_from_request(request=request)
    return user_has_role(user_db=user_db, role=role)


def request_user_has_permission(request, permission_type):
    """
    Check that currently logged-in user has specified permission.

    :rtype: ``bool``
    """
    user_db = get_user_db_from_request(request=request)
    return user_has_permission(user_db=user_db, permission_type=permission_type)


def request_user_has_resource_api_permission(request, resource_api, permission_type):
    """
    Check that currently logged-in user has specified permission for the resource which is to be
    created.
    """
    user_db = get_user_db_from_request(request=request)
    return user_has_resource_api_permission(user_db=user_db, resource_api=resource_api,
                                            permission_type=permission_type)


def request_user_has_resource_db_permission(request, resource_db, permission_type):
    """
    Check that currently logged-in user has specified permission on the provied resource.

    :rtype: ``bool``
    """
    user_db = get_user_db_from_request(request=request)
    return user_has_resource_db_permission(user_db=user_db, resource_db=resource_db,
                                           permission_type=permission_type)


def assert_request_user_is_admin(request):
    """
    Assert that the currently logged in user is an administrator.

    If the user is not an administrator, an exception is thrown.
    """
    is_admin = request_user_is_admin(request=request)

    if not is_admin:
        user_db = get_user_db_from_request(request=request)
        raise AccessDeniedError(message='Administrator access required',
                                user_db=user_db)


def assert_request_user_is_system_admin(request):
    """
    Assert that the currently logged in user is a system administrator.

    If the user is not a system administrator, an exception is thrown.
    """
    is_system_admin = request_user_is_system_admin(request=request)

    if not is_system_admin:
        user_db = get_user_db_from_request(request=request)
        raise AccessDeniedError(message='System Administrator access required',
                                user_db=user_db)


def assert_request_user_has_permission(request, permission_type):
    """
    Check that currently logged-in user has specified permission.

    If user doesn't have a required permission, AccessDeniedError s thrown.
    """
    has_permission = request_user_has_permission(request=request,
                                                 permission_type=permission_type)

    if not has_permission:
        user_db = get_user_db_from_request(request=request)
        raise ResourceTypeAccessDeniedError(user_db=user_db, permission_type=permission_type)


def assert_request_user_has_resource_api_permission(request, resource_api, permission_type):
    """
    Check that currently logged-in user has specified permission for the resource which is to be
    created.
    """
    has_permission = request_user_has_resource_api_permission(request=request,
                                                              resource_api=resource_api,
                                                              permission_type=permission_type)

    if not has_permission:
        user_db = get_user_db_from_request(request=request)
        # TODO: Refactor exception
        raise ResourceAccessDeniedError(user_db=user_db, resource_db=resource_api,
                                        permission_type=permission_type)


def assert_request_user_has_resource_db_permission(request, resource_db, permission_type):
    """
    Check that currently logged-in user has specified permission on the provied resource.

    If user doesn't have a required permission, AccessDeniedError is thrown.
    """
    has_permission = request_user_has_resource_db_permission(request=request,
                                                             resource_db=resource_db,
                                                             permission_type=permission_type)

    if not has_permission:
        user_db = get_user_db_from_request(request=request)
        raise ResourceAccessDeniedError(user_db=user_db, resource_db=resource_db,
                                        permission_type=permission_type)


def request_user_has_rule_trigger_permission(request, trigger):
    """
    Check that the currently logged-in has necessary permissions on the trigger used / referenced
    inside the rule.
    """
    if not cfg.CONF.rbac.enable:
        return True

    user_db = get_user_db_from_request(request=request)
    rules_resolver = resolvers.get_resolver_for_resource_type(ResourceType.RULE)
    has_trigger_permission = rules_resolver.user_has_trigger_permission(user_db=user_db,
                                                                        trigger=trigger)

    if has_trigger_permission:
        return True

    return False


def request_user_has_rule_action_permission(request, action_ref):
    """
    Check that the currently logged-in has necessary permissions on the action used / referenced
    inside the rule.
    """
    if not cfg.CONF.rbac.enable:
        return True

    user_db = get_user_db_from_request(request=request)
    action_db = action_utils.get_action_by_ref(ref=action_ref)
    action_resolver = resolvers.get_resolver_for_resource_type(ResourceType.ACTION)
    has_action_permission = action_resolver.user_has_resource_db_permission(
        user_db=user_db, resource_db=action_db, permission_type=PermissionType.ACTION_EXECUTE)

    if has_action_permission:
        return True

    return False


def assert_request_user_has_rule_trigger_and_action_permission(request, rule_api):
    """
    Check that the currently logged-in has necessary permissions on trhe trigger and action
    used / referenced inside the rule.
    """

    if not cfg.CONF.rbac.enable:
        return True

    trigger = rule_api.trigger
    action = rule_api.action
    trigger_type = trigger['type']
    action_ref = action['ref']

    user_db = get_user_db_from_request(request=request)

    # Check that user has access to the specified trigger - right now we only check for
    # webhook permissions
    has_trigger_permission = request_user_has_rule_trigger_permission(request=request,
                                                                      trigger=trigger)

    if not has_trigger_permission:
        msg = ('User "%s" doesn\'t have required permission (%s) to use trigger %s' %
               (user_db.name, PermissionType.WEBHOOK_CREATE, trigger_type))
        raise AccessDeniedError(message=msg, user_db=user_db)

    # Check that user has access to the specified action
    has_action_permission = request_user_has_rule_action_permission(request=request,
                                                                    action_ref=action_ref)

    if not has_action_permission:
        msg = ('User "%s" doesn\'t have required (%s) permission to use action %s' %
               (user_db.name, PermissionType.ACTION_EXECUTE, action_ref))
        raise AccessDeniedError(message=msg, user_db=user_db)

    return True


def assert_request_user_is_admin_if_user_query_param_is_provider(request, user):
    """
    Function which asserts that the request user is administator if "user" query parameter is
    provided and doesn't match the current user.
    """
    requester_user = get_requester()
    is_admin = request_user_is_admin(request=request)

    if user != requester_user and not is_admin:
        msg = '"user" attribute can only be provided by admins'
        raise AccessDeniedError(message=msg, user_db=requester_user)


def user_is_admin(user_db):
    """
    Return True if the provided user has admin role (either system admin or admin), false
    otherwise.

    :param user_db: User object to check for.
    :type user_db: :class:`UserDB`

    :rtype: ``bool``
    """
    is_system_admin = user_is_system_admin(user_db=user_db)
    if is_system_admin:
        return True

    is_admin = user_has_role(user_db=user_db, role=SystemRole.ADMIN)
    if is_admin:
        return True

    return False


def user_is_system_admin(user_db):
    """
    Return True if the provided user has system admin rule, false otherwise.

    :param user_db: User object to check for.
    :type user_db: :class:`UserDB`

    :rtype: ``bool``
    """
    return user_has_role(user_db=user_db, role=SystemRole.SYSTEM_ADMIN)


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

    # TODO Verify permission type for the provided resource type
    resolver = resolvers.get_resolver_for_permission_type(permission_type=permission_type)
    result = resolver.user_has_permission(user_db=user_db, permission_type=permission_type)
    return result


def user_has_resource_api_permission(user_db, resource_api, permission_type):
    """
    Check that the provided user has specified permission on the provided resource API.
    """
    if not cfg.CONF.rbac.enable:
        return True

    # TODO Verify permission type for the provided resource type
    resolver = resolvers.get_resolver_for_permission_type(permission_type=permission_type)
    result = resolver.user_has_resource_api_permission(user_db=user_db, resource_api=resource_api,
                                                       permission_type=permission_type)
    return result


def user_has_resource_db_permission(user_db, resource_db, permission_type):
    """
    Check that the provided user has specified permission on the provided resource.
    """
    if not cfg.CONF.rbac.enable:
        return True

    # TODO Verify permission type for the provided resource type
    resolver = resolvers.get_resolver_for_permission_type(permission_type=permission_type)
    result = resolver.user_has_resource_db_permission(user_db=user_db, resource_db=resource_db,
                                                      permission_type=permission_type)
    return result


def get_user_db_from_request(request):
    """
    Retrieve UserDB object from the provided request.
    """
    auth_context = request.context.get('auth', {})

    if not auth_context:
        return None

    user_db = auth_context.get('user', None)
    return user_db

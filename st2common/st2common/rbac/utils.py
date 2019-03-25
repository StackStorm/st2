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

from __future__ import absolute_import

import six

from oslo_config import cfg

from st2common.models.db.action import ActionDB
from st2common.models.system.common import ResourceReference
from st2common.exceptions.rbac import AccessDeniedError
from st2common.exceptions.rbac import ResourceTypeAccessDeniedError
from st2common.exceptions.rbac import ResourceAccessDeniedError
from st2common.rbac.types import PermissionType
from st2common.rbac.types import ResourceType
from st2common.rbac.types import SystemRole
from st2common.rbac.backends import get_backend_instance
from st2common.services import rbac as rbac_services
from st2common.util import action_db as action_utils

__all__ = [
    'user_has_rule_trigger_permission',
    'user_has_rule_action_permission',

    'assert_user_is_admin',
    'assert_user_is_system_admin',
    'assert_user_is_admin_or_operating_on_own_resource',
    'assert_user_has_permission',
    'assert_user_has_resource_db_permission',

    'assert_user_is_admin_if_user_query_param_is_provided',

    'assert_user_has_rule_trigger_and_action_permission',

    'user_is_admin',
    'user_is_system_admin',
    'user_has_permission',
    'user_has_resource_api_permission',
    'user_has_resource_db_permission',
    'user_has_role',

    'get_user_db_from_request'
]


def assert_user_is_admin(user_db):
    """
    Assert that the currently logged in user is an administrator.

    If the user is not an administrator, an exception is thrown.
    """
    is_admin = user_is_admin(user_db=user_db)

    if not is_admin:
        raise AccessDeniedError(message='Administrator access required',
                                user_db=user_db)


def assert_user_is_system_admin(user_db):
    """
    Assert that the currently logged in user is a system administrator.

    If the user is not a system administrator, an exception is thrown.
    """
    is_system_admin = user_is_system_admin(user_db=user_db)

    if not is_system_admin:
        raise AccessDeniedError(message='System Administrator access required',
                                user_db=user_db)


def assert_user_is_admin_or_operating_on_own_resource(user_db, user=None):
    """
    Assert that the currently logged in user is an administrator or operating on a resource which
    belongs to that user.
    """
    if not cfg.CONF.rbac.enable:
        return True

    is_admin = user_is_admin(user_db=user_db)
    is_self = user is not None and (user_db.name == user)

    if not is_admin and not is_self:
        raise AccessDeniedError(message='Administrator or self access required',
                                user_db=user_db)


def assert_user_has_permission(user_db, permission_type):
    """
    Check that currently logged-in user has specified permission.

    If user doesn't have a required permission, AccessDeniedError s thrown.
    """
    has_permission = user_has_permission(user_db=user_db, permission_type=permission_type)

    if not has_permission:
        raise ResourceTypeAccessDeniedError(user_db=user_db, permission_type=permission_type)


def assert_user_has_resource_api_permission(user_db, resource_api, permission_type):
    """
    Check that currently logged-in user has specified permission for the resource which is to be
    created.
    """
    has_permission = user_has_resource_api_permission(user_db=user_db,
                                                      resource_api=resource_api,
                                                      permission_type=permission_type)

    if not has_permission:
        # TODO: Refactor exception
        raise ResourceAccessDeniedError(user_db=user_db, resource_api_or_db=resource_api,
                                        permission_type=permission_type)


def assert_user_has_resource_db_permission(user_db, resource_db, permission_type):
    """
    Check that currently logged-in user has specified permission on the provied resource.

    If user doesn't have a required permission, AccessDeniedError is thrown.
    """
    has_permission = user_has_resource_db_permission(user_db=user_db,
                                                     resource_db=resource_db,
                                                     permission_type=permission_type)

    if not has_permission:
        raise ResourceAccessDeniedError(user_db=user_db, resource_api_or_db=resource_db,
                                        permission_type=permission_type)


def user_has_rule_trigger_permission(user_db, trigger):
    """
    Check that the currently logged-in has necessary permissions on the trigger used / referenced
    inside the rule.
    """
    if not cfg.CONF.rbac.enable:
        return True

    rbac_backend = get_backend_instance(cfg.CONF.rbac.backend)

    rules_resolver = rbac_backend.get_resolver_for_resource_type(ResourceType.RULE)
    has_trigger_permission = rules_resolver.user_has_trigger_permission(user_db=user_db,
                                                                        trigger=trigger)

    if has_trigger_permission:
        return True

    return False


def user_has_rule_action_permission(user_db, action_ref):
    """
    Check that the currently logged-in has necessary permissions on the action used / referenced
    inside the rule.

    Note: Rules can reference actions which don't yet exist in the system.
    """
    if not cfg.CONF.rbac.enable:
        return True

    action_db = action_utils.get_action_by_ref(ref=action_ref)

    if not action_db:
        # We allow rules to be created for actions which don't yet exist in the
        # system
        ref = ResourceReference.from_string_reference(ref=action_ref)
        action_db = ActionDB(pack=ref.pack, name=ref.name, ref=action_ref)

    rbac_backend = get_backend_instance(cfg.CONF.rbac.backend)

    action_resolver = rbac_backend.get_resolver_for_resource_type(ResourceType.ACTION)
    has_action_permission = action_resolver.user_has_resource_db_permission(
        user_db=user_db, resource_db=action_db, permission_type=PermissionType.ACTION_EXECUTE)

    if has_action_permission:
        return True

    return False


def assert_user_has_rule_trigger_and_action_permission(user_db, rule_api):
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

    # Check that user has access to the specified trigger - right now we only check for
    # webhook permissions
    has_trigger_permission = user_has_rule_trigger_permission(user_db=user_db,
                                                              trigger=trigger)

    if not has_trigger_permission:
        msg = ('User "%s" doesn\'t have required permission (%s) to use trigger %s' %
               (user_db.name, PermissionType.WEBHOOK_CREATE, trigger_type))
        raise AccessDeniedError(message=msg, user_db=user_db)

    # Check that user has access to the specified action
    has_action_permission = user_has_rule_action_permission(user_db=user_db,
                                                            action_ref=action_ref)

    if not has_action_permission:
        msg = ('User "%s" doesn\'t have required (%s) permission to use action %s' %
               (user_db.name, PermissionType.ACTION_EXECUTE, action_ref))
        raise AccessDeniedError(message=msg, user_db=user_db)

    return True


def assert_user_is_admin_if_user_query_param_is_provided(user_db, user, require_rbac=False):
    """
    Function which asserts that the request user is administator if "user" query parameter is
    provided and doesn't match the current user.
    """
    is_admin = user_is_admin(user_db=user_db)
    is_rbac_enabled = bool(cfg.CONF.rbac.enable)

    if user != user_db.name:
        if require_rbac and not is_rbac_enabled:
            msg = '"user" attribute can only be provided by admins when RBAC is enabled'
            raise AccessDeniedError(message=msg, user_db=user_db)

        if not is_admin:
            msg = '"user" attribute can only be provided by admins'
            raise AccessDeniedError(message=msg, user_db=user_db)


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
    rbac_backend = get_backend_instance(cfg.CONF.rbac.backend)

    resolver = rbac_backend.get_resolver_for_permission_type(permission_type=permission_type)
    result = resolver.user_has_permission(user_db=user_db, permission_type=permission_type)
    return result


def user_has_resource_api_permission(user_db, resource_api, permission_type):
    """
    Check that the provided user has specified permission on the provided resource API.
    """
    if not cfg.CONF.rbac.enable:
        return True

    # TODO Verify permission type for the provided resource type
    rbac_backend = get_backend_instance(cfg.CONF.rbac.backend)

    resolver = rbac_backend.get_resolver_for_permission_type(permission_type=permission_type)
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
    rbac_backend = get_backend_instance(cfg.CONF.rbac.backend)

    resolver = rbac_backend.get_resolver_for_permission_type(permission_type=permission_type)
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

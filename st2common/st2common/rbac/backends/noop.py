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

from __future__ import absolute_import

from oslo_config import cfg

from st2common.rbac.backends.base import BaseRBACBackend
from st2common.rbac.backends.base import BaseRBACPermissionResolver
from st2common.rbac.backends.base import BaseRBACUtils
from st2common.rbac.backends.base import BaseRBACRemoteGroupToRoleSyncer
from st2common.exceptions.rbac import AccessDeniedError

__all__ = [
    'NoOpRBACBackend',
    'NoOpRBACPermissionResolver',
    'NoOpRBACUtils',
    'NoOpRBACRemoteGroupToRoleSyncer'
]


class NoOpRBACBackend(BaseRBACBackend):
    """
    NoOp RBAC backend.
    """
    def get_resolver_for_resource_type(self, resource_type):
        return NoOpRBACPermissionResolver()

    def get_resolver_for_permission_type(self, permission_type):
        return NoOpRBACPermissionResolver()

    def get_remote_group_to_role_syncer(self):
        return NoOpRBACRemoteGroupToRoleSyncer()

    def get_utils_class(self):
        return NoOpRBACUtils


class NoOpRBACPermissionResolver(BaseRBACPermissionResolver):
    """
    No-op RBAC permission resolver for installations without RBAC.
    """

    def user_has_permission(self, user_db, permission_type):
        return True

    def user_has_resource_api_permission(self, user_db, resource_api, permission_type):
        return True

    def user_has_resource_db_permission(self, user_db, resource_db, permission_type):
        return True


class NoOpRBACUtils(BaseRBACUtils):

    @staticmethod
    def assert_user_is_admin(user_db):
        """
        Assert that the currently logged in user is an administrator.

        If the user is not an administrator, an exception is thrown.
        """
        return True

    @staticmethod
    def assert_user_is_system_admin(user_db):
        """
        Assert that the currently logged in user is a system administrator.

        If the user is not a system administrator, an exception is thrown.
        """
        return True

    @staticmethod
    def assert_user_is_admin_or_operating_on_own_resource(user_db, user=None):
        """
        Assert that the currently logged in user is an administrator or operating on a resource
        which belongs to that user.
        """
        return True

    @staticmethod
    def assert_user_has_permission(user_db, permission_type):
        """
        Check that currently logged-in user has specified permission.

        If user doesn't have a required permission, AccessDeniedError is thrown.
        """
        return True

    @staticmethod
    def assert_user_has_resource_api_permission(user_db, resource_api, permission_type):
        """
        Check that currently logged-in user has specified permission for the resource which is to be
        created.
        """
        return True

    @staticmethod
    def assert_user_has_resource_db_permission(user_db, resource_db, permission_type):
        """
        Check that currently logged-in user has specified permission on the provied resource.

        If user doesn't have a required permission, AccessDeniedError is thrown.
        """
        return True

    @staticmethod
    def assert_user_has_rule_trigger_and_action_permission(user_db, rule_api):
        """
        Check that the currently logged-in has necessary permissions on trhe trigger and action
        used / referenced inside the rule.
        """
        return True

    @staticmethod
    def assert_user_is_admin_if_user_query_param_is_provided(user_db, user, require_rbac=False):
        """
        Function which asserts that the request user is administator if "user" query parameter is
        provided and doesn't match the current user.
        """
        # To avoid potential security issues when RBAC is disabled, we don't support ?user=foo
        # query param when RBAC is disabled
        is_rbac_enabled = bool(cfg.CONF.rbac.enable)

        if user != user_db.name and require_rbac and not is_rbac_enabled:
            msg = '"user" attribute can only be provided by admins when RBAC is enabled'
            raise AccessDeniedError(message=msg, user_db=user_db)

    # Regular methods
    @staticmethod
    def user_is_admin(user_db):
        """
        Return True if the provided user has admin role (either system admin or admin), false
        otherwise.

        :param user_db: User object to check for.
        :type user_db: :class:`UserDB`

        :rtype: ``bool``
        """
        return True

    @staticmethod
    def user_is_system_admin(user_db):
        """
        Return True if the provided user has system admin rule, false otherwise.

        :param user_db: User object to check for.
        :type user_db: :class:`UserDB`

        :rtype: ``bool``
        """
        return True

    @staticmethod
    def user_has_role(user_db, role):
        """
        :param user: User object to check for.
        :type user: :class:`UserDB`

        :param role: Role name to check for.
        :type role: ``str``

        :rtype: ``bool``
        """
        return True

    @staticmethod
    def user_has_rule_trigger_permission(user_db, trigger):
        """
        Check that the currently logged-in has necessary permissions on the trigger used /
        referenced inside the rule.
        """
        return True

    @staticmethod
    def user_has_rule_action_permission(user_db, action_ref):
        """
        Check that the currently logged-in has necessary permissions on the action used / referenced
        inside the rule.

        Note: Rules can reference actions which don't yet exist in the system.
        """
        return True

    @staticmethod
    def user_has_permission(user_db, permission_type):
        """
        Check that the provided user has specified permission.
        """
        return True

    @staticmethod
    def user_has_resource_api_permission(user_db, resource_api, permission_type):
        """
        Check that the provided user has specified permission on the provided resource API.
        """
        return True

    @staticmethod
    def user_has_resource_db_permission(user_db, resource_db, permission_type):
        """
        Check that the provided user has specified permission on the provided resource.
        """
        return True


class NoOpRBACRemoteGroupToRoleSyncer(BaseRBACRemoteGroupToRoleSyncer):
    def sync(self, user_db, groups):
        return []

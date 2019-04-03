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

import abc

from oslo_config import cfg
import six

from st2common.exceptions.rbac import AccessDeniedError

__all__ = [
    'BaseRBACBackend',
    'BaseRBACPermissionResolver',
    'BaseRBACRemoteGroupToRoleSyncer'
]


@six.add_metaclass(abc.ABCMeta)
class BaseRBACBackend(object):

    def get_resolver_for_resource_type(self, resource_type):
        """
        Method which returns PermissionResolver class for the provided resource type.
        """
        raise NotImplementedError()

    def get_resolver_for_permission_type(self, permission_type):
        """
        Method which returns PermissionResolver class for the provided permission type.
        """
        raise NotImplementedError()

    def get_remote_group_to_role_syncer(self):
        """
        Return instance of RBACRemoteGroupToRoleSyncer class.
        """
        raise NotImplementedError()

    def get_utils_class(self):
        """
        Method which returns reference to a class with various RBAC related utility static methods.
        """
        raise NotImplementedError()


@six.add_metaclass(abc.ABCMeta)
class BaseRBACPermissionResolver(object):

    def user_has_permission(self, user_db, permission_type):
        """
        Method for checking user permissions which are not tied to a particular resource.
        """
        raise NotImplementedError()

    def user_has_resource_api_permission(self, user_db, resource_api, permission_type):
        """
        Method for checking user permissions on a resource which is to be created (e.g.
        create operation).
        """
        raise NotImplementedError()

    def user_has_resource_db_permission(self, user_db, resource_db, permission_type):
        """
        Method for checking user permissions on an existing resource (e.g. get one, edit, delete
        operations).
        """
        raise NotImplementedError()


@six.add_metaclass(abc.ABCMeta)
class BaseRBACUtilsClass(object):

    # Assertion methods which throw an exception if assertion fails
    @staticmethod
    def assert_user_is_admin(user_db):
        """
        Assert that the currently logged in user is an administrator.

        If the user is not an administrator, an exception is thrown.
        """
        raise NotImplementedError()

    @staticmethod
    def assert_user_is_system_admin(user_db):
        """
        Assert that the currently logged in user is a system administrator.

        If the user is not a system administrator, an exception is thrown.
        """
        raise NotImplementedError()

    @staticmethod
    def assert_user_is_admin_or_operating_on_own_resource(user_db, user=None):
        """
        Assert that the currently logged in user is an administrator or operating on a resource
        which belongs to that user.
        """
        raise NotImplementedError()

    @staticmethod
    def assert_user_has_permission(user_db, permission_type):
        """
        Check that currently logged-in user has specified permission.

        If user doesn't have a required permission, AccessDeniedError is thrown.
        """
        raise NotImplementedError()

    @staticmethod
    def assert_user_has_resource_api_permission(user_db, resource_api, permission_type):
        """
        Check that currently logged-in user has specified permission for the resource which is to be
        created.
        """
        raise NotImplementedError()

    @staticmethod
    def assert_user_has_resource_db_permission(user_db, resource_db, permission_type):
        """
        Check that currently logged-in user has specified permission on the provied resource.

        If user doesn't have a required permission, AccessDeniedError is thrown.
        """
        raise NotImplementedError()

    @staticmethod
    def assert_user_has_rule_trigger_and_action_permission(user_db, rule_api):
        """
        Check that the currently logged-in has necessary permissions on trhe trigger and action
        used / referenced inside the rule.
        """
        raise NotImplementedError()

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
        raise NotImplementedError()

    @staticmethod
    def user_is_system_admin(user_db):
        """
        Return True if the provided user has system admin rule, false otherwise.

        :param user_db: User object to check for.
        :type user_db: :class:`UserDB`

        :rtype: ``bool``
        """
        raise NotImplementedError()

    @staticmethod
    def user_has_role(user_db, role):
        """
        :param user: User object to check for.
        :type user: :class:`UserDB`

        :param role: Role name to check for.
        :type role: ``str``

        :rtype: ``bool``
        """
        raise NotImplementedError()

    @staticmethod
    def user_has_rule_trigger_permission(user_db, trigger):
        """
        Check that the currently logged-in has necessary permissions on the trigger used /
        referenced inside the rule.
        """
        raise NotImplementedError()

    @staticmethod
    def user_has_rule_action_permission(user_db, action_ref):
        """
        Check that the currently logged-in has necessary permissions on the action used / referenced
        inside the rule.

        Note: Rules can reference actions which don't yet exist in the system.
        """
        raise NotImplementedError()

    @staticmethod
    def user_has_permission(user_db, permission_type):
        """
        Check that the provided user has specified permission.
        """
        raise NotImplementedError()

    @staticmethod
    def user_has_resource_api_permission(user_db, resource_api, permission_type):
        """
        Check that the provided user has specified permission on the provided resource API.
        """
        raise NotImplementedError()

    @staticmethod
    def user_has_resource_db_permission(user_db, resource_db, permission_type):
        """
        Check that the provided user has specified permission on the provided resource.
        """
        raise NotImplementedError()

    @staticmethod
    def get_user_db_from_request(request):
        """
        Retrieve UserDB object from the provided request.
        """
        auth_context = request.context.get('auth', {})

        if not auth_context:
            return None

        user_db = auth_context.get('user', None)
        return user_db


@six.add_metaclass(abc.ABCMeta)
class BaseRBACRemoteGroupToRoleSyncer(object):
    """
    Class reponsible for syncing remote LDAP groups to local RBAC roles.
    """

    def sync(self, user_db, groups):
        """
        :param user_db: User to sync the assignments for.
        :type user: :class:`UserDB`

        :param groups: A list of remote groups user is a member of.
        :type groups: ``list`` of ``str``

        :return: A list of mappings which have been created.
        :rtype: ``list`` of :class:`UserRoleAssignmentDB`
        """
        raise NotImplementedError()

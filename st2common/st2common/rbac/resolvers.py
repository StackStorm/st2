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

import sys
import logging as stdlib_logging

from st2common import log as logging
from st2common.models.db.pack import PackDB
from st2common.models.db.webhook import WebhookDB
from st2common.models.system.common import ResourceReference
from st2common.constants.triggers import WEBHOOK_TRIGGER_TYPE
from st2common.rbac.types import PermissionType
from st2common.rbac.types import ResourceType
from st2common.rbac.types import SystemRole
from st2common.services.rbac import get_roles_for_user
from st2common.services.rbac import get_all_permission_grants_for_user

LOG = logging.getLogger(__name__)

__all__ = [
    'RunnerPermissionsResolver',
    'PackPermissionsResolver',
    'SensorPermissionsResolver',
    'ActionPermissionsResolver',
    'ActionAliasPermissionsResolver',
    'RulePermissionsResolver',
    'RuleEnforcementPermissionsResolver',
    'KeyValuePermissionsResolver',
    'ExecutionPermissionsResolver',
    'WebhookPermissionsResolver',

    'get_resolver_for_resource_type',
    'get_resolver_for_permission_type'
]

# "Read" permission names which are granted to observer role by default
READ_PERMISSION_NAMES = [
    'view',
    'list'
]


class PermissionsResolver(object):
    """
    Base Permissions Resolver class.

    Permission resolver classes implement permission resolving / checking logic for a particular
    resource type.
    """

    resource_type = None  # Constant for the resource type this resolver refers to

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

    def _user_has_list_permission(self, user_db, permission_type):
        """
        Common method for checking if a user has specific "list" resource permission (e.g.
        rules_list, action_list, etc.).
        """
        assert PermissionType.get_permission_name(permission_type) == 'list'

        log_context = {
            'user_db': user_db,
            'permission_type': permission_type,
            'resolver': self.__class__.__name__
        }
        self._log('Checking user permissions', extra=log_context)

        # First check the system role permissions
        has_system_role_permission = self._user_has_system_role_permission(
            user_db=user_db, permission_type=permission_type)

        if has_system_role_permission:
            self._log('Found a matching grant via system role', extra=log_context)
            return True

        # Check custom roles
        permission_types = [permission_type]

        # Check direct grants
        permission_grants = get_all_permission_grants_for_user(user_db=user_db,
                                                               permission_types=permission_types)
        if len(permission_grants) >= 1:
            self._log('Found a direct grant', extra=log_context)
            return True

        self._log('No matching grants found', extra=log_context)
        return False

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
        elif SystemRole.OBSERVER in user_role_names and permission_name in READ_PERMISSION_NAMES:
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

    def _log(self, message, extra, level=stdlib_logging.DEBUG, **kwargs):
        """
        Custom logger method which prefix message with the class and caller method name.
        """
        class_name = self.__class__.__name__
        method_name = sys._getframe().f_back.f_code.co_name
        message_prefix = '%s.%s: ' % (class_name, method_name)
        message = message_prefix + message

        LOG.log(level, message, extra=extra, **kwargs)


class ContentPackResourcePermissionsResolver(PermissionsResolver):
    """
    Base permissions resolver class which contains common functionality for resources which belong
    to a pack (sensors, actions, action aliases, rules, ...).
    """

    resource_type = None

    # A list of resource-specific permission types which grant / imply "view" permission type
    view_grant_permission_types = []

    def _user_has_resource_permission(self, user_db, pack_uid, resource_uid, permission_type):
        log_context = {
            'user_db': user_db,
            'pack_uid': pack_uid,
            'resource_uid': resource_uid,
            'resource_type': self.resource_type,
            'permission_type': permission_type,
            'resolver': self.__class__.__name__
        }
        self._log('Checking user resource permissions', extra=log_context)

        # First check the system role permissions
        has_system_role_permission = self._user_has_system_role_permission(
            user_db=user_db, permission_type=permission_type)

        if has_system_role_permission:
            self._log('Found a matching grant via system role', extra=log_context)
            return True

        # Check custom roles
        view_permission_type = PermissionType.get_permission_type(resource_type=self.resource_type,
                                                                  permission_name='view')
        all_permission_type = PermissionType.get_permission_type(resource_type=self.resource_type,
                                                                 permission_name='all')

        if permission_type == view_permission_type:
            # Note: Some permissions such as "create", "modify", "delete" and "execute" also
            # grant / imply "view" permission
            permission_types = self.view_grant_permission_types[:] + [permission_type]
        elif permission_type not in all_permission_type:
            permission_types = [all_permission_type, permission_type]
        else:
            permission_types = [permission_type]

        # Check direct grants on the specified resource
        resource_types = [self.resource_type]
        permission_grants = get_all_permission_grants_for_user(user_db=user_db,
                                                               resource_uid=resource_uid,
                                                               resource_types=resource_types,
                                                               permission_types=permission_types)
        if len(permission_grants) >= 1:
            self._log('Found a direct grant on the action', extra=log_context)
            return True

        # Check grants on the parent pack
        resource_types = [ResourceType.PACK]
        permission_grants = get_all_permission_grants_for_user(user_db=user_db,
                                                               resource_uid=pack_uid,
                                                               resource_types=resource_types,
                                                               permission_types=permission_types)

        if len(permission_grants) >= 1:
            self._log('Found a grant on the action parent pack', extra=log_context)
            return True

        self._log('No matching grants found', extra=log_context)
        return False


class RunnerPermissionsResolver(PermissionsResolver):
    """
    Permission resolver for "runner_type" resource type.
    """
    resource_type = ResourceType.RUNNER

    def user_has_permission(self, user_db, permission_type):
        assert permission_type in [PermissionType.RUNNER_LIST]
        return self._user_has_list_permission(user_db=user_db, permission_type=permission_type)

    def user_has_resource_db_permission(self, user_db, resource_db, permission_type):
        log_context = {
            'user_db': user_db,
            'resource_db': resource_db,
            'permission_type': permission_type,
            'resolver': self.__class__.__name__
        }
        self._log('Checking user resource permissions', extra=log_context)

        # First check the system role permissions
        has_system_role_permission = self._user_has_system_role_permission(
            user_db=user_db, permission_type=permission_type)

        if has_system_role_permission:
            self._log('Found a matching grant via system role', extra=log_context)
            return True

        # Check custom roles
        resource_uid = resource_db.get_uid()
        resource_types = [ResourceType.RUNNER]
        permission_types = [permission_type]
        permission_grants = get_all_permission_grants_for_user(user_db=user_db,
                                                               resource_uid=resource_uid,
                                                               resource_types=resource_types,
                                                               permission_types=permission_types)

        if len(permission_grants) >= 1:
            self._log('Found a direct grant on the runner type', extra=log_context)
            return True

        self._log('No matching grants found', extra=log_context)
        return False


class PackPermissionsResolver(PermissionsResolver):
    """
    Permission resolver for "pack" resource type.
    """

    resource_type = ResourceType.PACK

    def user_has_permission(self, user_db, permission_type):
        assert permission_type in [PermissionType.PACK_LIST]
        return self._user_has_list_permission(user_db=user_db, permission_type=permission_type)

    def user_has_resource_db_permission(self, user_db, resource_db, permission_type):
        log_context = {
            'user_db': user_db,
            'resource_db': resource_db,
            'permission_type': permission_type,
            'resolver': self.__class__.__name__
        }
        self._log('Checking user resource permissions', extra=log_context)

        # First check the system role permissions
        has_system_role_permission = self._user_has_system_role_permission(
            user_db=user_db, permission_type=permission_type)

        if has_system_role_permission:
            self._log('Found a matching grant via system role', extra=log_context)
            return True

        # Check custom roles
        resource_uid = resource_db.get_uid()
        resource_types = [ResourceType.PACK]
        permission_types = [permission_type]
        permission_grants = get_all_permission_grants_for_user(user_db=user_db,
                                                               resource_uid=resource_uid,
                                                               resource_types=resource_types,
                                                               permission_types=permission_types)

        if len(permission_grants) >= 1:
            self._log('Found a direct grant on the pack', extra=log_context)
            return True

        self._log('No matching grants found', extra=log_context)
        return False


class SensorPermissionsResolver(ContentPackResourcePermissionsResolver):
    """
    Permission resolver for "sensor" resource type.
    """

    resource_type = ResourceType.SENSOR
    view_grant_permission_types = [
        PermissionType.SENSOR_ALL,
        PermissionType.SENSOR_MODIFY
    ]

    def user_has_permission(self, user_db, permission_type):
        assert permission_type in [PermissionType.SENSOR_LIST]
        return self._user_has_list_permission(user_db=user_db, permission_type=permission_type)

    def user_has_resource_db_permission(self, user_db, resource_db, permission_type):
        sensor_uid = resource_db.get_uid()
        pack_uid = resource_db.get_pack_uid()
        return self._user_has_resource_permission(user_db=user_db, pack_uid=pack_uid,
                                                  resource_uid=sensor_uid,
                                                  permission_type=permission_type)


class ActionPermissionsResolver(ContentPackResourcePermissionsResolver):
    """
    Permission resolver for "action" resource type.
    """

    resource_type = ResourceType.ACTION
    view_grant_permission_types = [
        PermissionType.ACTION_ALL,
        PermissionType.ACTION_CREATE,
        PermissionType.ACTION_MODIFY,
        PermissionType.ACTION_DELETE,
        PermissionType.ACTION_EXECUTE,
    ]

    def user_has_permission(self, user_db, permission_type):
        assert permission_type in [PermissionType.ACTION_LIST]
        return self._user_has_list_permission(user_db=user_db, permission_type=permission_type)

    def user_has_resource_api_permission(self, user_db, resource_api, permission_type):
        assert permission_type in [PermissionType.ACTION_CREATE]

        action_uid = resource_api.get_uid()
        pack_uid = resource_api.get_pack_uid()
        return self._user_has_resource_permission(user_db=user_db, pack_uid=pack_uid,
                                                  resource_uid=action_uid,
                                                  permission_type=permission_type)

    def user_has_resource_db_permission(self, user_db, resource_db, permission_type):
        action_uid = resource_db.get_uid()
        pack_uid = resource_db.get_pack_uid()
        return self._user_has_resource_permission(user_db=user_db, pack_uid=pack_uid,
                                                  resource_uid=action_uid,
                                                  permission_type=permission_type)


class ActionAliasPermissionsResolver(ContentPackResourcePermissionsResolver):
    """
    Permission resolver for "action_alias" resource type.
    """

    resource_type = ResourceType.ACTION_ALIAS
    view_grant_permission_types = [
        PermissionType.ACTION_ALIAS_ALL,
        PermissionType.ACTION_ALIAS_CREATE,
        PermissionType.ACTION_ALIAS_MODIFY,
        PermissionType.ACTION_ALIAS_DELETE
    ]

    def user_has_permission(self, user_db, permission_type):
        assert permission_type in [PermissionType.ACTION_ALIAS_LIST]
        return self._user_has_list_permission(user_db=user_db, permission_type=permission_type)

    def user_has_resource_api_permission(self, user_db, resource_api, permission_type):
        assert permission_type in [PermissionType.ACTION_ALIAS_CREATE]

        action_alias_uid = resource_api.get_uid()
        pack_uid = resource_api.get_pack_uid()
        return self._user_has_resource_permission(user_db=user_db, pack_uid=pack_uid,
                                                  resource_uid=action_alias_uid,
                                                  permission_type=permission_type)

    def user_has_resource_db_permission(self, user_db, resource_db, permission_type):
        action_alias_uid = resource_db.get_uid()
        pack_uid = resource_db.get_pack_uid()
        return self._user_has_resource_permission(user_db=user_db, pack_uid=pack_uid,
                                                  resource_uid=action_alias_uid,
                                                  permission_type=permission_type)


class RulePermissionsResolver(ContentPackResourcePermissionsResolver):
    """
    Permission resolver for "rule" resource type.
    """

    resource_type = ResourceType.RULE
    view_grant_permission_types = [
        PermissionType.RULE_ALL,
        PermissionType.RULE_CREATE,
        PermissionType.RULE_MODIFY,
        PermissionType.RULE_DELETE
    ]

    def user_has_trigger_permission(self, user_db, trigger):
        """
        Check if the user has access to the provided trigger.

        This method is to be used during rule create and update where we check if the user has the
        necessary trigger permissions.

        Note: Right now we only support webhook triggers.

        :param trigger: "trigger" attribute of the RuleAPI object.
        :type trigger: ``dict``
        """
        log_context = {
            'user_db': user_db,
            'trigger': trigger,
            'resolver': self.__class__.__name__
        }

        trigger_type = trigger['type']
        trigger_parameters = trigger.get('parameters', {})

        if trigger_type != WEBHOOK_TRIGGER_TYPE:
            self._log('Not a webhook trigger type, ignoring trigger permission checking',
                      extra=log_context)
            return True

        resolver = get_resolver_for_resource_type(ResourceType.WEBHOOK)
        webhook_db = WebhookDB(name=trigger_parameters['url'])
        permission_type = PermissionType.WEBHOOK_CREATE
        result = resolver.user_has_resource_db_permission(user_db=user_db,
                                                          resource_db=webhook_db,
                                                          permission_type=permission_type)

        if result is True:
            self._log('Found a matching trigger grant', extra=log_context)
            return True

        self._log('No matching trigger grants found', extra=log_context)
        return False

    def user_has_action_permission(self, user_db, action_ref):
        """
        Check if the user has "execute" permission on the provided action.
        """
        pass

    def user_has_permission(self, user_db, permission_type):
        assert permission_type in [PermissionType.RULE_LIST]
        return self._user_has_list_permission(user_db=user_db, permission_type=permission_type)

    def user_has_resource_api_permission(self, user_db, resource_api, permission_type):
        assert permission_type in [PermissionType.RULE_CREATE]

        rule_uid = resource_api.get_uid()
        pack_uid = resource_api.get_pack_uid()
        return self._user_has_resource_permission(user_db=user_db, pack_uid=pack_uid,
                                                  resource_uid=rule_uid,
                                                  permission_type=permission_type)

    def user_has_resource_db_permission(self, user_db, resource_db, permission_type):
        rule_uid = resource_db.get_uid()
        pack_uid = resource_db.get_pack_uid()
        return self._user_has_resource_permission(user_db=user_db, pack_uid=pack_uid,
                                                  resource_uid=rule_uid,
                                                  permission_type=permission_type)


class RuleEnforcementPermissionsResolver(PermissionsResolver):
    """
    Permission resolver for "rule enforcement" resource type.
    """
    resource_type = ResourceType.RULE_ENFORCEMENT

    def user_has_permission(self, user_db, permission_type):
        assert permission_type in [PermissionType.RULE_ENFORCEMENT_LIST]
        permission_type = PermissionType.RULE_LIST
        return self._user_has_list_permission(user_db=user_db, permission_type=permission_type)

    def user_has_resource_db_permission(self, user_db, resource_db, permission_type):
        log_context = {
            'user_db': user_db,
            'resource_db': resource_db,
            'permission_type': permission_type,
            'resolver': self.__class__.__name__
        }
        self._log('Checking user resource permissions', extra=log_context)

        # First check the system role permissions
        has_system_role_permission = self._user_has_system_role_permission(
            user_db=user_db, permission_type=permission_type)

        if has_system_role_permission:
            self._log('Found a matching grant via system role', extra=log_context)
            return True

        # Check custom roles
        rule_spec = getattr(resource_db, 'rule', None)
        rule_uid = rule_spec.uid
        rule_id = rule_spec.id
        rule_pack = ResourceReference.get_pack(rule_spec.ref)

        if not rule_uid or not rule_id or not rule_pack:
            LOG.error('Rule UID or ID or PACK not present in enforcement object. ' +
                      ('UID = %s, ID = %s, PACK = %s' % (rule_uid, rule_id, rule_pack)) +
                      'Cannot assess access permissions without it. Defaulting to DENY.')
            return False

        # TODO: Add utility methods for constructing uids from parts
        pack_db = PackDB(ref=rule_pack)
        rule_pack_uid = pack_db.get_uid()

        rule_permission_type = None
        if permission_type == PermissionType.RULE_ENFORCEMENT_VIEW:
            rule_permission_type = PermissionType.RULE_VIEW
        elif permission_type == PermissionType.RULE_ENFORCEMENT_LIST:
            rule_permission_type = PermissionType.RULE_LIST
        else:
            raise ValueError('Invalid permission type: %s' % (permission_type))

        permission_types = [PermissionType.RULE_ALL, rule_permission_type]

        view_permission_type = PermissionType.get_permission_type(resource_type=ResourceType.RULE,
                                                                  permission_name='view')

        if rule_permission_type == view_permission_type:
            permission_types = (RulePermissionsResolver.view_grant_permission_types[:] +
                                [rule_permission_type])

        # Check grants on the pack of the rule to which enforcement belongs to
        resource_types = [ResourceType.PACK]
        permission_grants = get_all_permission_grants_for_user(user_db=user_db,
                                                               resource_uid=rule_pack_uid,
                                                               resource_types=resource_types,
                                                               permission_types=permission_types)

        if len(permission_grants) >= 1:
            self._log('Found a grant on the enforcement rule parent pack', extra=log_context)
            return True

        # Check grants on the rule the enforcement belongs to
        resource_types = [ResourceType.RULE]
        permission_grants = get_all_permission_grants_for_user(user_db=user_db,
                                                               resource_uid=rule_uid,
                                                               resource_types=resource_types,
                                                               permission_types=permission_types)

        if len(permission_grants) >= 1:
            self._log('Found a grant on the enforcement\'s rule.', extra=log_context)
            return True

        self._log('No matching grants found', extra=log_context)
        return False


class KeyValuePermissionsResolver(PermissionsResolver):
    """
    Permission resolver for "key value pair" resource type.
    """

    resource_type = ResourceType.KEY_VALUE_PAIR

    def user_has_permission(self, user_db, permission_type):
        # TODO: We don't support assigning permissions on key value pairs yet
        return True

    def user_has_resource_db_permission(self, user_db, resource_db, permission_type):
        # TODO: We don't support assigning permissions on key value pairs yet
        return True


class ExecutionPermissionsResolver(PermissionsResolver):
    """
    Permission resolver for "execution" resource type.
    """

    resource_type = ResourceType.EXECUTION

    def user_has_permission(self, user_db, permission_type):
        assert permission_type in [PermissionType.EXECUTION_LIST]
        return self._user_has_list_permission(user_db=user_db, permission_type=permission_type)

    def user_has_resource_db_permission(self, user_db, resource_db, permission_type):
        log_context = {
            'user_db': user_db,
            'resource_db': resource_db,
            'permission_type': permission_type,
            'resolver': self.__class__.__name__
        }
        self._log('Checking user resource permissions', extra=log_context)

        # First check the system role permissions
        has_system_role_permission = self._user_has_system_role_permission(
            user_db=user_db, permission_type=permission_type)

        if has_system_role_permission:
            self._log('Found a matching grant via system role', extra=log_context)
            return True

        # Check custom roles
        action = resource_db['action']

        # TODO: Add utility methods for constructing uids from parts
        pack_db = PackDB(ref=action['pack'])

        action_uid = action['uid']
        action_pack_uid = pack_db.get_uid()

        # Note: "action_execute" also grants / implies "execution_re_run" and "execution_stop"
        if permission_type == PermissionType.EXECUTION_VIEW:
            action_permission_type = PermissionType.ACTION_VIEW
        elif permission_type in [PermissionType.EXECUTION_RE_RUN,
                                 PermissionType.EXECUTION_STOP]:
            action_permission_type = PermissionType.ACTION_EXECUTE
        elif permission_type == PermissionType.EXECUTION_ALL:
            action_permission_type = PermissionType.ACTION_ALL
        else:
            raise ValueError('Invalid permission type: %s' % (permission_type))

        # Check grants on the pack of the action to which execution belongs to
        resource_types = [ResourceType.PACK]
        permission_types = [PermissionType.ACTION_ALL, action_permission_type]
        permission_grants = get_all_permission_grants_for_user(user_db=user_db,
                                                               resource_uid=action_pack_uid,
                                                               resource_types=resource_types,
                                                               permission_types=permission_types)

        if len(permission_grants) >= 1:
            self._log('Found a grant on the execution action parent pack', extra=log_context)
            return True

        # Check grants on the action the execution belongs to
        resource_types = [ResourceType.ACTION]
        permission_types = [PermissionType.ACTION_ALL, action_permission_type]
        permission_grants = get_all_permission_grants_for_user(user_db=user_db,
                                                               resource_uid=action_uid,
                                                               resource_types=resource_types,
                                                               permission_types=permission_types)

        if len(permission_grants) >= 1:
            self._log('Found a grant on the execution action', extra=log_context)
            return True

        self._log('No matching grants found', extra=log_context)
        return False


class WebhookPermissionsResolver(PermissionsResolver):

    resource_type = ResourceType.WEBHOOK

    def user_has_permission(self, user_db, permission_type):
        # TODO
        return True

    def user_has_resource_db_permission(self, user_db, resource_db, permission_type):
        log_context = {
            'user_db': user_db,
            'resource_db': resource_db,
            'permission_type': permission_type,
            'resolver': self.__class__.__name__
        }
        self._log('Checking user resource permissions', extra=log_context)

        # First check the system role permissions
        has_system_role_permission = self._user_has_system_role_permission(
            user_db=user_db, permission_type=permission_type)

        if has_system_role_permission:
            self._log('Found a matching grant via system role', extra=log_context)
            return True

        # Check custom roles
        webhook_uid = resource_db.get_uid()

        # Check direct grants on the webhook
        resource_types = [ResourceType.WEBHOOK]
        permission_types = [PermissionType.WEBHOOK_ALL, permission_type]
        permission_grants = get_all_permission_grants_for_user(user_db=user_db,
                                                               resource_uid=webhook_uid,
                                                               resource_types=resource_types,
                                                               permission_types=permission_types)

        if len(permission_grants) >= 1:
            self._log('Found a grant on the webhook', extra=log_context)
            return True

        self._log('No matching grants found', extra=log_context)
        return False


class ApiKeyPermissionResolver(PermissionsResolver):
    """
    Permission resolver for "api key" resource type.
    """

    resource_type = ResourceType.API_KEY

    def user_has_permission(self, user_db, permission_type):
        assert permission_type in [PermissionType.API_KEY_LIST]
        return self._user_has_list_permission(user_db=user_db, permission_type=permission_type)

    def user_has_resource_api_permission(self, user_db, resource_api, permission_type):
        assert permission_type in [PermissionType.API_KEY_CREATE]
        # TODO:
        return True

    def user_has_resource_db_permission(self, user_db, resource_db, permission_type):
        # Desired impl is as under. Permission grants as of now are to
        # a role while for this to work right the permission grant would have to
        # be to a specific user. The user ofcourse has to belong to a role
        # that can create API keys however ALL permissions for specific API Key
        # should only be granted if the user created the key or has system role.
        # Until we introduce an ability to support per user this is disabled.

        # log_context = {
        #     'user_db': user_db,
        #     'resource_db': resource_db,
        #     'permission_type': permission_type,
        #     'resolver': self.__class__.__name__
        # }
        # self._log('Checking user resource permissions', extra=log_context)

        # # First check the system role permissions
        # has_system_role_permission = self._user_has_system_role_permission(
        #     user_db=user_db, permission_type=permission_type)

        # if has_system_role_permission:
        #     self._log('Found a matching grant via system role', extra=log_context)
        #     return True

        # # Check custom roles
        # api_key_uid = resource_db.get_uid()

        # if permission_type == PermissionType.API_KEY_VIEW:
        #     # Note: "create", and "delete" do not grant/imply "view" permission
        #     permission_types = [
        #         PermissionType.API_KEY_ALL,
        #         permission_type
        #     ]
        # else:
        #     permission_types = [PermissionType.ACTION_ALL, permission_type]

        # # Check direct grants on the specified resource
        # resource_types = [ResourceType.API_KEY]
        # permission_grants = get_all_permission_grants_for_user(user_db=user_db,
        #                                                        resource_uid=api_key_uid,
        #                                                        resource_types=resource_types,
        #                                                        permission_types=permission_types)
        # if len(permission_grants) >= 1:
        #     self._log('Found a direct grant on the api_key', extra=log_context)
        #     return True

        # self._log('No matching grants found', extra=log_context)
        # return False
        return True


def get_resolver_for_resource_type(resource_type):
    """
    Return resolver instance for the provided resource type.

    :rtype: Instance of :class:`PermissionsResolver`
    """
    if resource_type == ResourceType.RUNNER:
        resolver_cls = RunnerPermissionsResolver
    elif resource_type == ResourceType.PACK:
        resolver_cls = PackPermissionsResolver
    elif resource_type == ResourceType.SENSOR:
        resolver_cls = SensorPermissionsResolver
    elif resource_type == ResourceType.ACTION:
        resolver_cls = ActionPermissionsResolver
    elif resource_type == ResourceType.ACTION_ALIAS:
        resolver_cls = ActionAliasPermissionsResolver
    elif resource_type == ResourceType.RULE:
        resolver_cls = RulePermissionsResolver
    elif resource_type == ResourceType.EXECUTION:
        resolver_cls = ExecutionPermissionsResolver
    elif resource_type == ResourceType.KEY_VALUE_PAIR:
        resolver_cls = KeyValuePermissionsResolver
    elif resource_type == ResourceType.WEBHOOK:
        resolver_cls = WebhookPermissionsResolver
    elif resource_type == ResourceType.API_KEY:
        resolver_cls = ApiKeyPermissionResolver
    elif resource_type == ResourceType.RULE_ENFORCEMENT:
        resolver_cls = RuleEnforcementPermissionsResolver
    else:
        raise ValueError('Unsupported resource: %s' % (resource_type))

    resolver_instance = resolver_cls()
    return resolver_instance


def get_resolver_for_permission_type(permission_type):
    """
    Return resolver instance for the provided permission type.

    :rtype: Instance of :class:`PermissionsResolver`
    """
    resource_type = PermissionType.get_resource_type(permission_type=permission_type)
    resolver_instance = get_resolver_for_resource_type(resource_type=resource_type)
    return resolver_instance

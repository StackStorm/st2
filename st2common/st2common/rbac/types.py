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

from st2common.util.enum import Enum
from st2common.constants.types import ResourceType as SystemResourceType

__all__ = [
    'SystemRole',
    'PermissionType',
    'ResourceType',

    'RESOURCE_TYPE_TO_PERMISSION_TYPES_MAP',
    'PERMISION_TYPE_TO_DESCRIPTION_MAP'
]


class PermissionType(Enum):
    """
    Available permission types.
    """

    # Note: There is no create endpoint for runner types right now
    RUNNER_LIST = 'runner_type_list'
    RUNNER_VIEW = 'runner_type_view'
    RUNNER_MODIFY = 'runner_type_modify'
    RUNNER_ALL = 'runner_type_all'

    PACK_LIST = 'pack_list'
    PACK_VIEW = 'pack_view'
    PACK_CREATE = 'pack_create'
    PACK_MODIFY = 'pack_modify'
    PACK_DELETE = 'pack_delete'
    PACK_ALL = 'pack_all'

    # Note: Right now we only have read endpoints + update for sensors types
    SENSOR_LIST = 'sensor_type_list'
    SENSOR_VIEW = 'sensor_type_view'
    SENSOR_MODIFY = 'sensor_type_modify'
    SENSOR_ALL = 'sensor_type_all'

    ACTION_LIST = 'action_list'
    ACTION_VIEW = 'action_view'
    ACTION_CREATE = 'action_create'
    ACTION_MODIFY = 'action_modify'
    ACTION_DELETE = 'action_delete'
    ACTION_EXECUTE = 'action_execute'
    ACTION_ALL = 'action_all'

    ACTION_ALIAS_LIST = 'action_alias_list'
    ACTION_ALIAS_VIEW = 'action_alias_view'
    ACTION_ALIAS_CREATE = 'action_alias_create'
    ACTION_ALIAS_MODIFY = 'action_alias_modify'
    ACTION_ALIAS_DELETE = 'action_alias_delete'
    ACTION_ALIAS_ALL = 'action_alias_all'

    # Note: Execution create is granted with "action_execute"
    EXECUTION_LIST = 'execution_list'
    EXECUTION_VIEW = 'execution_view'
    EXECUTION_RE_RUN = 'execution_rerun'
    EXECUTION_STOP = 'execution_stop'
    EXECUTION_ALL = 'execution_all'

    RULE_LIST = 'rule_list'
    RULE_VIEW = 'rule_view'
    RULE_CREATE = 'rule_create'
    RULE_MODIFY = 'rule_modify'
    RULE_DELETE = 'rule_delete'
    RULE_ALL = 'rule_all'

    RULE_ENFORCEMENT_LIST = 'rule_enforcement_list'
    RULE_ENFORCEMENT_VIEW = 'rule_enforcement_view'

    # TODO - Maybe "datastore_item" / key_value_item ?
    KEY_VALUE_VIEW = 'key_value_pair_view'
    KEY_VALUE_SET = 'key_value_pair_set'
    KEY_VALUE_DELETE = 'key_value_pair_delete'

    WEBHOOK_CREATE = 'webhook_create'
    WEBHOOK_SEND = 'webhook_send'
    WEBHOOK_DELETE = 'webhook_delete'
    WEBHOOK_ALL = 'webhook_all'

    API_KEY_LIST = 'api_key_list'
    API_KEY_VIEW = 'api_key_view'
    API_KEY_CREATE = 'api_key_create'
    API_KEY_MODIFY = 'api_key_modify'
    API_KEY_DELETE = 'api_key_delete'
    API_KEY_ALL = 'api_key_all'

    @classmethod
    def get_valid_permissions_for_resource_type(cls, resource_type):
        """
        Return valid permissions for the provided resource type.

        :rtype: ``list``
        """
        valid_permissions = RESOURCE_TYPE_TO_PERMISSION_TYPES_MAP[resource_type]
        return valid_permissions

    @classmethod
    def get_resource_type(cls, permission_type):
        """
        Retrieve resource type from the provided permission type.

        :rtype: ``str``
        """
        split = permission_type.split('_')
        assert len(split) >= 2
        return '_'.join(split[:-1])

    @classmethod
    def get_permission_name(cls, permission_type):
        """
        Retrieve permission name from the provided permission type.

        :rtype: ``str``
        """
        split = permission_type.split('_')
        assert len(split) >= 2
        return split[-1]

    @classmethod
    def get_permission_description(cls, permission_type):
        """
        Retrieve a description for the provided permission_type.

        :rtype: ``str``
        """
        description = PERMISION_TYPE_TO_DESCRIPTION_MAP[permission_type]
        return description

    @classmethod
    def get_permission_type(cls, resource_type, permission_name):
        """
        Retrieve permission type enum value for the provided resource type and permission name.

        :rtype: ``str``
        """
        # Special case for sensor type (sensor_type -> sensor)
        if resource_type == ResourceType.SENSOR:
            resource_type = 'sensor'

        permission_enum = '%s_%s' % (resource_type.upper(), permission_name.upper())
        result = getattr(cls, permission_enum, None)

        if not result:
            raise ValueError('Unsupported permission type for type "%s" and name "%s"' %
                             (resource_type, permission_name))

        return result


class ResourceType(Enum):
    """
    Resource types on which permissions can be granted.
    """
    RUNNER = SystemResourceType.RUNNER_TYPE

    PACK = SystemResourceType.PACK
    SENSOR = SystemResourceType.SENSOR_TYPE
    ACTION = SystemResourceType.ACTION
    ACTION_ALIAS = SystemResourceType.ACTION_ALIAS
    RULE = SystemResourceType.RULE
    RULE_ENFORCEMENT = SystemResourceType.RULE_ENFORCEMENT

    EXECUTION = SystemResourceType.EXECUTION
    KEY_VALUE_PAIR = SystemResourceType.KEY_VALUE_PAIR
    WEBHOOK = SystemResourceType.WEBHOOK
    API_KEY = SystemResourceType.API_KEY


class SystemRole(Enum):
    """
    Default system roles which can't be manipulated (modified or removed).
    """
    SYSTEM_ADMIN = 'system_admin'  # Special role which can't be revoked.
    ADMIN = 'admin'
    OBSERVER = 'observer'


# Maps a list of available permission types for each resource
RESOURCE_TYPE_TO_PERMISSION_TYPES_MAP = {
    ResourceType.RUNNER: [
        PermissionType.RUNNER_LIST,
        PermissionType.RUNNER_VIEW,
        PermissionType.RUNNER_MODIFY,
        PermissionType.RUNNER_ALL,
    ],
    ResourceType.PACK: [
        PermissionType.PACK_VIEW,
        PermissionType.PACK_CREATE,
        PermissionType.PACK_MODIFY,
        PermissionType.PACK_DELETE,
        PermissionType.PACK_ALL,

        PermissionType.SENSOR_VIEW,
        PermissionType.SENSOR_MODIFY,
        PermissionType.SENSOR_ALL,

        PermissionType.ACTION_VIEW,
        PermissionType.ACTION_CREATE,
        PermissionType.ACTION_MODIFY,
        PermissionType.ACTION_DELETE,
        PermissionType.ACTION_EXECUTE,
        PermissionType.ACTION_ALL,

        PermissionType.ACTION_ALIAS_VIEW,
        PermissionType.ACTION_ALIAS_CREATE,
        PermissionType.ACTION_ALIAS_MODIFY,
        PermissionType.ACTION_ALIAS_DELETE,
        PermissionType.ACTION_ALIAS_ALL,

        PermissionType.RULE_VIEW,
        PermissionType.RULE_CREATE,
        PermissionType.RULE_MODIFY,
        PermissionType.RULE_DELETE,
        PermissionType.RULE_ALL
    ],
    ResourceType.SENSOR: [
        PermissionType.SENSOR_LIST,
        PermissionType.SENSOR_VIEW,
        PermissionType.SENSOR_MODIFY,
        PermissionType.SENSOR_ALL
    ],
    ResourceType.ACTION: [
        PermissionType.ACTION_LIST,
        PermissionType.ACTION_VIEW,
        PermissionType.ACTION_CREATE,
        PermissionType.ACTION_MODIFY,
        PermissionType.ACTION_DELETE,
        PermissionType.ACTION_EXECUTE,
        PermissionType.ACTION_ALL
    ],
    ResourceType.ACTION_ALIAS: [
        PermissionType.ACTION_ALIAS_LIST,
        PermissionType.ACTION_ALIAS_VIEW,
        PermissionType.ACTION_ALIAS_CREATE,
        PermissionType.ACTION_ALIAS_MODIFY,
        PermissionType.ACTION_ALIAS_DELETE,
        PermissionType.ACTION_ALIAS_ALL
    ],
    ResourceType.RULE: [
        PermissionType.RULE_LIST,
        PermissionType.RULE_VIEW,
        PermissionType.RULE_CREATE,
        PermissionType.RULE_MODIFY,
        PermissionType.RULE_DELETE,
        PermissionType.RULE_ALL
    ],
    ResourceType.RULE_ENFORCEMENT: [
        PermissionType.RULE_ENFORCEMENT_LIST,
        PermissionType.RULE_ENFORCEMENT_VIEW,
    ],
    ResourceType.EXECUTION: [
        PermissionType.EXECUTION_LIST,
        PermissionType.EXECUTION_VIEW,
        PermissionType.EXECUTION_RE_RUN,
        PermissionType.EXECUTION_STOP,
        PermissionType.EXECUTION_ALL,
    ],
    ResourceType.KEY_VALUE_PAIR: [
        PermissionType.KEY_VALUE_VIEW,
        PermissionType.KEY_VALUE_SET,
        PermissionType.KEY_VALUE_DELETE
    ],
    ResourceType.WEBHOOK: [
        PermissionType.WEBHOOK_CREATE,
        PermissionType.WEBHOOK_SEND,
        PermissionType.WEBHOOK_DELETE,
        PermissionType.WEBHOOK_ALL
    ],
    ResourceType.API_KEY: [
        PermissionType.API_KEY_LIST,
        PermissionType.API_KEY_VIEW,
        PermissionType.API_KEY_CREATE,
        PermissionType.API_KEY_MODIFY,
        PermissionType.API_KEY_DELETE,
        PermissionType.API_KEY_ALL
    ]
}


# Maps a permission type to the corresponding description
PERMISION_TYPE_TO_DESCRIPTION_MAP = {
    PermissionType.PACK_LIST: 'Ability list (view all) packs.',
    PermissionType.PACK_VIEW: 'Ability to view a pack.',
    PermissionType.PACK_CREATE: 'Ability to create a new pack.',
    PermissionType.PACK_MODIFY: 'Ability to modify (update) an existing pack.',
    PermissionType.PACK_DELETE: 'Ability to delete an existing pack.',
    PermissionType.PACK_ALL: ('Ability to perform all the supported operations on a particular '
                              'pack.'),

    PermissionType.SENSOR_LIST: 'Ability list (view all) sensors.',
    PermissionType.SENSOR_VIEW: 'Ability to view a sensor',
    PermissionType.SENSOR_MODIFY: ('Ability to modify (update) an existing sensor. Also implies '
                                   '"sensor_view" permission.'),
    PermissionType.SENSOR_ALL: ('Ability to perform all the supported operations on a particular '
                                'sensor.'),

    PermissionType.ACTION_LIST: 'Ability list (view all) actions.',
    PermissionType.ACTION_VIEW: 'Ability to view an action.',
    PermissionType.ACTION_CREATE: ('Ability to create a new action. Also implies "action_view" '
                                   'permission.'),
    PermissionType.ACTION_MODIFY: ('Ability to modify (update) an existing action. Also implies '
                                   '"action_view" permission.'),
    PermissionType.ACTION_DELETE: ('Ability to delete an existing action. Also implies '
                                   '"action_view" permission.'),
    PermissionType.ACTION_EXECUTE: ('Ability to execute (run) an action. Also implies '
                                    '"action_view" permission.'),
    PermissionType.ACTION_ALL: ('Ability to perform all the supported operations on a particular '
                                'action.'),

    PermissionType.ACTION_ALIAS_LIST: 'Ability list (view all) action aliases.',
    PermissionType.ACTION_ALIAS_VIEW: 'Ability to view an action alias.',
    PermissionType.ACTION_ALIAS_CREATE: ('Ability to create a new action alias. Also implies '
                                         ' "action_alias_view" permission.'),
    PermissionType.ACTION_ALIAS_MODIFY: ('Ability to modify (update) an existing action alias. '
                                         'Also implies "action_alias_view" permission.'),
    PermissionType.ACTION_ALIAS_DELETE: ('Ability to delete an existing action alias. Also '
                                         'imples "action_alias_view" permission.'),
    PermissionType.ACTION_ALIAS_ALL: ('Ability to perform all the supported operations on a '
                                      'particular action alias.'),

    PermissionType.EXECUTION_LIST: 'Ability list (view all) executions.',
    PermissionType.EXECUTION_VIEW: 'Ability to view an execution.',
    PermissionType.EXECUTION_RE_RUN: 'Ability to create a new action.',
    PermissionType.EXECUTION_STOP: 'Ability to stop (cancel) a running execution.',
    PermissionType.EXECUTION_ALL: ('Ability to perform all the supported operations on a '
                                   'particular execution.'),

    PermissionType.RULE_LIST: 'Ability list (view all) rules.',
    PermissionType.RULE_VIEW: 'Ability to view a rule.',
    PermissionType.RULE_CREATE: ('Ability to create a new rule. Also implies "rule_view" '
                                 'permission'),
    PermissionType.RULE_MODIFY: ('Ability to modify (update) an existing rule. Also implies '
                                 '"rule_view" permission.'),
    PermissionType.RULE_DELETE: ('Ability to delete an existing rule. Also implies "rule_view" '
                                 'permission.'),
    PermissionType.RULE_ALL: ('Ability to perform all the supported operations on a particular '
                              'rule.'),

    PermissionType.RULE_ENFORCEMENT_LIST: 'Ability to list (view all) rule enforcements.',
    PermissionType.RULE_ENFORCEMENT_VIEW: 'Ability to view a rule enforcement.',

    PermissionType.WEBHOOK_CREATE: ('Ability to create a new webhook.'),
    PermissionType.WEBHOOK_SEND: ('Ability to send / POST data to an existing webhook.'),
    PermissionType.WEBHOOK_DELETE: ('Ability to delete an existing webhook.'),
    PermissionType.WEBHOOK_ALL: ('Ability to perform all the supported operations on a particular '
                                 'webhook.'),

    PermissionType.API_KEY_LIST: 'Ability list (view all) API keys.',
    PermissionType.API_KEY_VIEW: ('Ability view API Keys.'),
    PermissionType.API_KEY_CREATE: ('Ability to create a new API Key.'),
    PermissionType.API_KEY_MODIFY: ('Ability to modify (update) an existing API key. Also implies '
                                    '"api_key_view" permission.'),
    PermissionType.API_KEY_DELETE: ('Ability to delete an existing API Keys.'),
    PermissionType.API_KEY_ALL: ('Ability to perform all the supported operations on an API Key.')
}

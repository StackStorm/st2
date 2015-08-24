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

from st2common.util.misc import Enum
from st2common.constants.types import ResourceType as SystemResourceType

__all__ = [
    'SystemRole',
    'PermissionType',
    'ResourceType',

    'RESOURCE_TYPE_TO_PERMISSION_TYPES_MAP'
]


class PermissionType(Enum):
    """
    Available permission types.
    """

    PACK_VIEW = 'pack_view'
    PACK_CREATE = 'pack_create'
    PACK_MODIFY = 'pack_modify'
    PACK_DELETE = 'pack_delete'
    PACK_ALL = 'pack_all'

    # Note: Right now we only have read endpoints for sensors types
    SENSOR_VIEW = 'sensor_view'
    SENSOR_ALL = 'sensor_all'

    ACTION_VIEW = 'action_view'
    ACTION_CREATE = 'action_create'
    ACTION_MODIFY = 'action_modify'
    ACTION_DELETE = 'action_delete'
    ACTION_EXECUTE = 'action_execute'
    ACTION_ALL = 'action_all'

    # Note: Execution create is granted with "action_execute"
    EXECUTION_VIEW = 'execution_view'
    EXECUTION_RE_RUN = 'execution_re_run'
    EXECUTION_STOP = 'execution_stop'
    EXECUTION_ALL = 'execution_all'

    RULE_VIEW = 'rule_view'
    RULE_CREATE = 'rule_create'
    RULE_MODIFY = 'rule_modify'
    RULE_DELETE = 'rule_delete'
    RULE_ALL = 'rule_all'

    # TODO - Maybe "datastore_item" / key_value_item ?
    KEY_VALUE_VIEW = 'key_value_view'
    KEY_VALUE_SET = 'key_value_set'
    KEY_VALUE_DELETE = 'key_value_delete'

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
        return split[0]

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
    def get_permission_type(cls, resource_type, permission_name):
        """
        Retrieve permission type for the provided resource type and permission name.

        :rtype: ``str``
        """
        permission_enum = '%s_%s' % (resource_type, permission_name.lower())
        result = getattr(cls, permission_enum, None)

        if not result:
            raise ValueError('Unsupported permission type')

        return result


class ResourceType(Enum):
    """
    Resource types on which permissions can be granted.
    """
    PACK = SystemResourceType.PACK
    SENSOR = SystemResourceType.SENSOR_TYPE
    ACTION = SystemResourceType.ACTION
    RULE = SystemResourceType.RULE

    EXECUTION = SystemResourceType.EXECUTION
    KEY_VALUE = SystemResourceType.KEY_VALUE


class SystemRole(Enum):
    """
    Default system roles which can't be manipulated (modified or removed).
    """
    SYSTEM_ADMIN = ' system_admin'  # Special role which can't be revoked.
    ADMIN = 'admin'
    OPERATOR = 'operator'
    OBSERVER = 'observer'


# Maps a list of available permission types for each resource
RESOURCE_TYPE_TO_PERMISSION_TYPES_MAP = {
    ResourceType.PACK: [
        PermissionType.PACK_VIEW,
        PermissionType.PACK_CREATE,
        PermissionType.PACK_MODIFY,
        PermissionType.PACK_DELETE,
        PermissionType.PACK_ALL,

        PermissionType.SENSOR_VIEW,
        PermissionType.SENSOR_ALL,

        PermissionType.ACTION_VIEW,
        PermissionType.ACTION_CREATE,
        PermissionType.ACTION_MODIFY,
        PermissionType.ACTION_DELETE,
        PermissionType.ACTION_EXECUTE,
        PermissionType.ACTION_ALL,

        PermissionType.RULE_VIEW,
        PermissionType.RULE_CREATE,
        PermissionType.RULE_MODIFY,
        PermissionType.RULE_DELETE,
        PermissionType.RULE_ALL
    ],
    ResourceType.SENSOR: [
        PermissionType.SENSOR_VIEW,
        PermissionType.SENSOR_ALL
    ],
    ResourceType.ACTION: [
        PermissionType.ACTION_VIEW,
        PermissionType.ACTION_CREATE,
        PermissionType.ACTION_MODIFY,
        PermissionType.ACTION_DELETE,
        PermissionType.ACTION_EXECUTE,
        PermissionType.ACTION_ALL
    ],
    ResourceType.RULE: [
        PermissionType.RULE_VIEW,
        PermissionType.RULE_CREATE,
        PermissionType.RULE_MODIFY,
        PermissionType.RULE_DELETE,
        PermissionType.RULE_ALL
    ],
    ResourceType.EXECUTION: [
        PermissionType.EXECUTION_VIEW,
        PermissionType.EXECUTION_RE_RUN,

        PermissionType.EXECUTION_STOP,
        PermissionType.EXECUTION_ALL,
    ],
    ResourceType.KEY_VALUE: [
        PermissionType.KEY_VALUE_VIEW,
        PermissionType.KEY_VALUE_SET,
        PermissionType.KEY_VALUE_DELETE
    ]
}

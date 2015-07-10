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

import abc

from st2common.util.misc import Enum
from st2common.constants.types import ResourceType as SystemResourceType

__all__ = [
    'SystemRole',
    'PermissionType',
    'ResourceType',

    'PackPermissionTypes',
    'ActionPermissionTypes',
    'RulePermissionTypes'
]


class PermissionType(Enum):
    """
    Available permission types.
    """
    VIEW = 'view'
    CREATE = 'create'  # modify?
    DELETE = 'delete'
    EXECUTE = 'execute'
    USE = 'use'
    ALL = 'all'


class SystemRole(Enum):
    """
    Default system roles which can't be manipulated (modified or removed).
    """
    SYSTEM_ADMIN = ' system_admin'  # Special role which can't be revoked.
    ADMIN = 'admin'
    OPERATOR = 'operator'
    OBSERVER = 'observer'


class ResourceType(Enum):
    """
    Resource types on which permissions can be granted.
    """
    PACK = SystemResourceType.PACK
    ACTION = SystemResourceType.ACTION
    RULE = SystemResourceType.RULE
    TRIGGER_TYPE = SystemResourceType.TRIGGER_TYPE


class ResourcePermissionType(object):
    """
    Base class representing permissions which can be granted on a particular
    resource type.
    """
    resource_type = abc.abstractproperty
    valid_permission_types = abc.abstractproperty

    def get_valid_permission_types(self):
        return self.valid_permission_types


class PackPermissionTypes(object):
    """
    Permissions which can be granted on a pack.
    """
    resource_type = ResourceType.PACK
    valid_permission_types = [
        PermissionType.VIEW,
        PermissionType.EXECUTE,
        PermissionType.ALL
    ]


class ActionPermissionTypes(object):
    """
    Permissions which can be granted on an action.
    """
    resource_type = ResourceType.ACTION
    valid_permission_types = [
        PermissionType.VIEW,
        PermissionType.CREATE,
        PermissionType.DELETE,
        PermissionType.EXECUTE,
        PermissionType.ALL
    ]


class RulePermissionTypes(object):
    """
    Permissions which can be granted on a rule.
    """
    resource_type = ResourceType.RULE
    valid_permission_types = [
        PermissionType.VIEW,
        PermissionType.CREATE,
        PermissionType.DELETE,
        PermissionType.EXECUTE,
        PermissionType.ALL
    ]

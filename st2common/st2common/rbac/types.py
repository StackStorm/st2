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

__all__ = [
    'SystemRole',
    'PermissionType',
    'ResourceType'
]


class PermissionType(Enum):
    """
    Available permission types.
    """
    VIEW = 'view'
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
    PACK = 'pack'
    WORKFLOW = 'workflow'
    ACTION = 'action'
    RULE = 'rule'
    TRIGGER = 'trigger'

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

from st2common.models.api.base import BaseAPI
from st2common.models.db.pack import PackDB
from st2common.rbac.types import PermissionType

__all__ = [
    'RoleAPI',

    'RoleDefinitionFileFormatAPI',
    'UserRoleAssignmentFileFormatAPI'
]


class RoleAPI(BaseAPI):
    model = PackDB
    schema = {
        'type': 'object',
        'properties': {
            'id': {
                'type': 'string',
                'default': None
            },
            'name': {
                'type': 'string',
                'required': True
            },
            'description': {
                'type': 'string'
            }
        },
        'additionalProperties': False
    }


class RoleDefinitionFileFormatAPI(BaseAPI):
    """
    JSON schema for the role definition file format.
    """

    schema = {
        'type': 'object',
        'properties': {
            'name': {
                'type': 'string',
                'description': 'Role name',
                'required': True,
                'default': None
            },
            'description': {
                'type': 'string',
                'description': 'Role description',
                'required': False
            },
            'permission_grants': {
                'type': 'array',
                'items': {
                    'type': 'object',
                    'properties': {
                        'resource_ref': {
                            'type': 'string',
                            'description': 'Resource to which this grant applies to. Can be empty if it\'s a global permission',
                            'required': False,
                            'default': None
                        },
                        'permission_types': {
                            'type': 'array',
                            'description': 'A list of permission types to grant',
                            'uniqueItems': True,
                            'items': {
                                'type': 'string',
                                # Note: We permission aditional validation for based on the
                                # resource type in other place
                                'enum': PermissionType.get_valid_values()
                            }
                            'default': None
                        }
                    }
                }
            }
        },
        'additionalProperties': False
    }


class UserRoleAssignmentFileFormatAPI(BaseAPI):
    schema = {
        'type': 'object',
        'properties': {
            'name': {
                'type': 'string',
                'description': 'Role name',
                'required': True,
                'default': None
            },
            'description': {
                'type': 'string',
                'description': 'Assignment description',
                'required': False
            },
            'roles': {
                'type': 'array',
                'description': 'Roles assigned to this user',
                'uniqueItems': True,
                'items': {
                    'type': 'string'
                }
                'required': True
            }
        },
        'additionalProperties': False
    }

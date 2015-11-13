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
from st2common.services.rbac import get_all_roles
from st2common.rbac.types import PermissionType
from st2common.util.uid import parse_uid

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
            },
            'description': {
                'type': 'boolean'
            },
            'permission_grants': {
                'type': 'array',
                'items': {
                    'type': 'string'
                }
            }
        },
        'additionalProperties': False
    }

    @classmethod
    def from_model(cls, model, mask_secrets=False):
        role = cls._from_model(model, mask_secrets=mask_secrets)

        # Convert ObjectIDs to strings
        role['permission_grants'] = [str(permission_grant) for permission_grant in
                                     model.permission_grants]

        return cls(**role)


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
            'enabled': {
                'type': 'boolean',
                'description': ('Flag indicating if this role is enabled. Note: Disabled roles '
                                'are simply ignored when loading definitions from disk.'),
                'default': True
            },
            'permission_grants': {
                'type': 'array',
                'items': {
                    'type': 'object',
                    'properties': {
                        'resource_uid': {
                            'type': 'string',
                            'description': 'UID of a resource to which this grant applies to.',
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
                            },
                            'default': None
                        }
                    }
                }
            }
        },
        'additionalProperties': False
    }

    def validate(self):
        # Parent JSON schema validation
        cleaned = super(RoleDefinitionFileFormatAPI, self).validate()

        # Custom validation

        # Validate that only the correct permission types are used
        permission_grants = getattr(self, 'permission_grants', [])
        for permission_grant in permission_grants:
            resource_uid = permission_grant.get('resource_uid', None)
            permission_types = permission_grant.get('permission_types', [])

            if resource_uid:
                # Permission types which apply to a resource
                resource_type, _ = parse_uid(uid=resource_uid)
                valid_permission_types = PermissionType.get_valid_permissions_for_resource_type(
                    resource_type=resource_type)

                for permission_type in permission_types:
                    if permission_type not in valid_permission_types:
                        message = ('Invalid permission type "%s" for resource type "%s"' %
                                   (permission_type, resource_type))
                        raise ValueError(message)
            else:
                # Right now we only support single permission type (list) which is global and
                # doesn't apply to a resource
                for permission_type in permission_types:
                    if not permission_type.endswith('_list'):
                        message = ('Invalid permission type "%s". Only "list" permission types '
                                   'can be used without a resource id' % (permission_type))
                        raise ValueError(message)

            return cleaned


class UserRoleAssignmentFileFormatAPI(BaseAPI):
    schema = {
        'type': 'object',
        'properties': {
            'username': {
                'type': 'string',
                'description': 'Username',
                'required': True,
                'default': None
            },
            'description': {
                'type': 'string',
                'description': 'Assignment description',
                'required': False,
                'default': None
            },
            'enabled': {
                'type': 'boolean',
                'description': ('Flag indicating if this assignment is enabled. Note: Disabled '
                                'assignments are simply ignored when loading definitions from '
                                ' disk.'),
                'default': True
            },
            'roles': {
                'type': 'array',
                'description': 'Roles assigned to this user',
                'uniqueItems': True,
                'items': {
                    'type': 'string'
                },
                'required': True
            }
        },
        'additionalProperties': False
    }

    def validate(self, validate_role_exists=False):
        # Parent JSON schema validation
        cleaned = super(UserRoleAssignmentFileFormatAPI, self).validate()

        # Custom validation
        if validate_role_exists:
            # Validate that the referenced roles exist in the db
            role_dbs = get_all_roles()
            role_names = [role_db.name for role_db in role_dbs]
            roles = self.roles

            for role in roles:
                if role not in role_names:
                    raise ValueError('Role "%s" doesn\'t exist in the database' % (role))

        return cleaned

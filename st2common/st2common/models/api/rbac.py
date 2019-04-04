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

from st2common.models.api.base import BaseAPI
from st2common.models.db.rbac import RoleDB
from st2common.models.db.rbac import UserRoleAssignmentDB
from st2common.models.db.rbac import PermissionGrantDB
from st2common.rbac.backends import get_rbac_backend
from st2common.rbac.types import PermissionType
from st2common.rbac.types import GLOBAL_PERMISSION_TYPES
from st2common.util.uid import parse_uid

__all__ = [
    'RoleAPI',
    'UserRoleAssignmentAPI',

    'RoleDefinitionFileFormatAPI',
    'UserRoleAssignmentFileFormatAPI',

    'AuthGroupToRoleMapAssignmentFileFormatAPI'
]


class RoleAPI(BaseAPI):
    model = RoleDB
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
            'permission_grant_ids': {
                'type': 'array',
                'items': {
                    'type': 'string'
                }
            },
            'permission_grant_objects': {
                'type': 'array',
                'items': {
                    'type': 'object'
                }
            }
        },
        'additionalProperties': False
    }

    @classmethod
    def from_model(cls, model, mask_secrets=False, retrieve_permission_grant_objects=True):
        role = cls._from_model(model, mask_secrets=mask_secrets)

        # Convert ObjectIDs to strings
        role['permission_grant_ids'] = [str(permission_grant) for permission_grant in
                                        model.permission_grants]

        # Retrieve and include corresponding permission grant objects
        if retrieve_permission_grant_objects:
            from st2common.persistence.rbac import PermissionGrant
            permission_grant_dbs = PermissionGrant.query(id__in=role['permission_grants'])

            permission_grant_apis = []
            for permission_grant_db in permission_grant_dbs:
                permission_grant_api = PermissionGrantAPI.from_model(permission_grant_db)
                permission_grant_apis.append(permission_grant_api)

            role['permission_grant_objects'] = permission_grant_apis

        return cls(**role)


class UserRoleAssignmentAPI(BaseAPI):
    model = UserRoleAssignmentDB
    schema = {
        'type': 'object',
        'properties': {
            'id': {
                'type': 'string',
                'default': None
            },
            'user': {
                'type': 'string',
                'required': True
            },
            'role': {
                'type': 'string',
                'required': True
            },
            'description': {
                'type': 'string'
            },
            'is_remote': {
                'type': 'boolean'
            },
            'source': {
                'type': 'string'
            }
        },
        'additionalProperties': False
    }


class PermissionGrantAPI(BaseAPI):
    model = PermissionGrantDB
    schema = {
        'type': 'object',
        'properties': {
            'id': {
                'type': 'string',
                'default': None
            },
            'resource_uid': {
                'type': 'string',
                'required': True
            },
            'resource_type': {
                'type': 'string',
                'required': True
            },
            'permission_types': {
                'type': 'array'
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
                            'default': []
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
                    if permission_type not in GLOBAL_PERMISSION_TYPES:
                        valid_global_permission_types = ', '.join(GLOBAL_PERMISSION_TYPES)
                        message = ('Invalid permission type "%s". Valid global permission types '
                                   'which can be used without a resource id are: %s' %
                                   (permission_type, valid_global_permission_types))
                        raise ValueError(message)

        return cleaned


class BaseRoleAssigmentAPI(BaseAPI):
    """
    Base class for various derived role assignment classes which includes commmon functionality
    such as validation.
    """

    def validate(self, validate_role_exists=False):
        # Parent JSON schema validation
        cleaned = super(BaseRoleAssigmentAPI, self).validate()

        # Custom validation
        if validate_role_exists:
            # Validate that the referenced roles exist in the db
            rbac_service = get_rbac_backend().get_service_class()
            rbac_service.validate_roles_exists(role_names=self.roles)  # pylint: disable=no-member

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
            },
            'file_path': {
                'type': 'string',
                'description': 'Path of the file of where this assignment comes from.',
                'default': None,
                'required': False
            }

        },
        'additionalProperties': False
    }

    def validate(self, validate_role_exists=False):
        cleaned = super(UserRoleAssignmentFileFormatAPI, self).validate()
        return cleaned


class AuthGroupToRoleMapAssignmentFileFormatAPI(BaseAPI):
    schema = {
        'type': 'object',
        'properties': {
            'group': {
                'type': 'string',
                'description': 'Name of the group as returned by auth backend.',
                'required': True
            },
            'description': {
                'type': 'string',
                'description': 'Mapping description',
                'required': False,
                'default': None
            },
            'enabled': {
                'type': 'boolean',
                'description': ('Flag indicating if this mapping is enabled. Note: Disabled '
                                'assignments are simply ignored when loading definitions from '
                                ' disk.'),
                'default': True
            },
            'roles': {
                'type': 'array',
                'description': ('StackStorm roles which are assigned to each user which belongs '
                                'to that group.'),
                'uniqueItems': True,
                'items': {
                    'type': 'string'
                },
                'required': True
            },
            'file_path': {
                'type': 'string',
                'description': 'Path of the file of where this assignment comes from.',
                'default': None,
                'required': False
            }
        },
        'additionalProperties': False
    }

    def validate(self, validate_role_exists=False):
        cleaned = super(AuthGroupToRoleMapAssignmentFileFormatAPI, self).validate()
        return cleaned

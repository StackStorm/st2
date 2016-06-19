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

import copy

from pecan import rest

from st2api.controllers.controller_transforms import transform_to_bool
from st2api.controllers.resource import ResourceController
from st2common.models.api.base import jsexpose
from st2common.models.api.rbac import RoleAPI
from st2common.persistence.rbac import Role
from st2common.rbac.types import RESOURCE_TYPE_TO_PERMISSION_TYPES_MAP
from st2common.rbac.decorators import request_user_is_admin

__all__ = [
    'RolesController',
    'PermissionTypesController'
]


class RolesController(ResourceController):
    model = RoleAPI
    access = Role
    supported_filters = {
        'name': 'name',
        'system': 'system'
    }

    filter_transform_functions = {
        'system': transform_to_bool
    }

    query_options = {
        'sort': ['name']
    }

    @request_user_is_admin()
    @jsexpose(arg_types=[str])
    def get_one(self, name_or_id):
        return self._get_one_by_name_or_id(name_or_id=name_or_id)


class PermissionTypesController(rest.RestController):
    """
    Meta controller for listing all the available permission types.
    """

    @request_user_is_admin()
    @jsexpose()
    def get_all(self):
        """
            List all the available permission types.

            Handles requests:
                GET /rbac/permission_types
        """
        result = copy.deepcopy(RESOURCE_TYPE_TO_PERMISSION_TYPES_MAP)
        return result

    @request_user_is_admin()
    @jsexpose(arg_types=[str])
    def get_one(self, resource_type):
        """
            List all the available permission types for a particular resource type.

            Handles requests:
                GET /rbac/permission_types
        """
        permission_types = RESOURCE_TYPE_TO_PERMISSION_TYPES_MAP.get(resource_type, None)
        if permission_types is None:
            raise ValueError('Invalid resource type: %s' % (resource_type))

        return permission_types


class RBACController(rest.RestController):
    roles = RolesController()
    permission_types = PermissionTypesController()

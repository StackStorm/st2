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


from st2api.controllers.resource import ResourceController
from st2common.models.api.rbac import RoleAPI
from st2common.models.api.rbac import UserRoleAssignmentAPI
from st2common.persistence.rbac import Role
from st2common.rbac.types import get_resource_permission_types_with_descriptions
from st2common.persistence.rbac import UserRoleAssignment
from st2common.rbac.backends import get_rbac_backend
from st2common.router import exc

__all__ = [
    'RolesController',
    'RoleAssignmentsController',
    'PermissionTypesController'
]


class RolesController(ResourceController):
    model = RoleAPI
    access = Role
    supported_filters = {
        'name': 'name',
        'system': 'system'
    }

    query_options = {
        'sort': ['name']
    }

    def get_one(self, name_or_id, requester_user):
        rbac_utils = get_rbac_backend().get_utils_class()
        rbac_utils.assert_user_is_admin(user_db=requester_user)

        return self._get_one_by_name_or_id(name_or_id=name_or_id,
                                           permission_type=None,
                                           requester_user=requester_user)

    def get_all(self, requester_user, sort=None, offset=0, limit=None, **raw_filters):
        rbac_utils = get_rbac_backend().get_utils_class()
        rbac_utils.assert_user_is_admin(user_db=requester_user)

        return self._get_all(sort=sort,
                             offset=offset,
                             limit=limit,
                             raw_filters=raw_filters,
                             requester_user=requester_user)


class RoleAssignmentsController(ResourceController):
    """
    Meta controller for listing role assignments.
    """
    model = UserRoleAssignmentAPI
    access = UserRoleAssignment
    supported_filters = {
        'user': 'user',
        'role': 'role',
        'source': 'source',
        'remote': 'is_remote'
    }

    def get_all(self, requester_user, sort=None, offset=0, limit=None, **raw_filters):
        user = raw_filters.get('user', None)
        rbac_utils = get_rbac_backend().get_utils_class()
        rbac_utils.assert_user_is_admin_or_operating_on_own_resource(user_db=requester_user,
                                                                     user=user)

        return self._get_all(sort=sort,
                             offset=offset,
                             limit=limit,
                             raw_filters=raw_filters,
                             requester_user=requester_user)

    def get_one(self, id, requester_user):
        result = self._get_one_by_id(id,
                                   requester_user=requester_user,
                                   permission_type=None)
        user = getattr(result, 'user', None)

        rbac_utils = get_rbac_backend().get_utils_class()
        rbac_utils.assert_user_is_admin_or_operating_on_own_resource(user_db=requester_user,
                                                                     user=user)

        return result


class PermissionTypesController(object):
    """
    Meta controller for listing all the available permission types.
    """

    def get_all(self, requester_user):
        """
            List all the available permission types.

            Handles requests:
                GET /rbac/permission_types
        """
        rbac_utils = get_rbac_backend().get_utils_class()
        rbac_utils.assert_user_is_admin(user_db=requester_user)

        result = get_resource_permission_types_with_descriptions()
        return result

    def get_one(self, resource_type, requester_user):
        """
            List all the available permission types for a particular resource type.

            Handles requests:
                GET /rbac/permission_types/<resource type>
        """
        rbac_utils = get_rbac_backend().get_utils_class()
        rbac_utils.assert_user_is_admin(user_db=requester_user)

        all_permission_types = get_resource_permission_types_with_descriptions()
        permission_types = all_permission_types.get(resource_type, None)

        if permission_types is None:
            raise exc.HTTPNotFound('Invalid resource type: %s' % (resource_type))

        return permission_types


roles_controller = RolesController()
role_assignments_controller = RoleAssignmentsController()
permission_types_controller = PermissionTypesController()

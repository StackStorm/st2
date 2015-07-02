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

import mongoengine as me

from st2common.models.db import MongoDBAccess
from st2common.models.db import stormbase


__all__ = [
    'RoleDB',
    'UserRoleAssignmentDB',
    'PermissionAssignmentDB',

    'role_access',
    'user_role_assignment_access',
    'permission_assignment_access'
]


class RoleDB(stormbase.StormFoundationDB):
    """
    An entity representing a role which can be assigned to the user.

    Attribute:
        name: Role name. Also servers as a primary key.
        description: Role description (optional).
    """
    name = me.StringField(required=True, unique=True)
    description = me.StringField()


class UserRoleAssignmentDB(stormbase.StormFoundationDB):
    """
    An entity which represents a user role assingnment.

    Attribute:
        user: A reference to the user name to which the role is assigned.
        role: A reference to the role name which is assigned to the user.
        permission_assignments: A list of IDs to the permission assignments which apply to this
        role.
    """
    user = me.StringField(required=True)
    role = me.StringField(required=True, unique_with='user')
    permission_assignments = me.ListField(field=me.StringField())


# TODO: PermissionAssignment -> PermissionGrant?
class PermissionAssignmentDB(stormbase.StormFoundationDB):
    """
    An entity which represents permission assignment.

    Attribute:
        resource: Target resource to which this permission applies to.
        permission_types: A list of permission type granted to that resources.
    """
    resource_ref = me.StringField(required=True)
    permission_types = me.ListField(field=me.StringField(),
                                    unique_with='resource_ref')

# Specialized access objects
role_access = MongoDBAccess(RoleDB)
user_role_assignment_access = MongoDBAccess(UserRoleAssignmentDB)
permission_assignment_access = MongoDBAccess(PermissionAssignmentDB)

MODELS = [RoleDB, UserRoleAssignmentDB, PermissionAssignmentDB]

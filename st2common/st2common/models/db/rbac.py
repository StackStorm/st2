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
    'PermissionGrantDB',

    'role_access',
    'user_role_assignment_access',
    'permission_grant_access'
]


class RoleDB(stormbase.StormFoundationDB):
    """
    An entity representing a role which can be assigned to the user.

    Attribute:
        name: Role name. Also servers as a primary key.
        description: Role description (optional).
        system: Flag indicating if this is system role which can't be manipulated.
        permission_grants: A list of IDs to the permission grant which apply to this
        role.
    """
    name = me.StringField(required=True, unique=True)
    description = me.StringField()
    system = me.BooleanField(default=False)
    permission_grants = me.ListField(field=me.StringField())


class UserRoleAssignmentDB(stormbase.StormFoundationDB):
    """
    An entity which represents a user role assingnment.

    Attribute:
        user: A reference to the user name to which the role is assigned.
        role: A reference to the role name which is assigned to the user.
    """
    user = me.StringField(required=True)
    role = me.StringField(required=True, unique_with='user')
    description = me.StringField()


class PermissionGrantDB(stormbase.StormFoundationDB):
    """
    An entity which represents permission assignment.

    Attribute:
        resource_uid: UID of a target resource to which this permission applies to.
        resource_type: Type of a resource this permission applies to. This attribute is here for
        convenience and to allow for more efficient queries.
        permission_types: A list of permission type granted to that resources.
    """
    resource_uid = me.StringField(required=True)
    resource_type = me.StringField(required=True)
    permission_types = me.ListField(field=me.StringField(),
                                    unique_with='resource_uid')

# Specialized access objects
role_access = MongoDBAccess(RoleDB)
user_role_assignment_access = MongoDBAccess(UserRoleAssignmentDB)
permission_grant_access = MongoDBAccess(PermissionGrantDB)

MODELS = [RoleDB, UserRoleAssignmentDB, PermissionGrantDB]

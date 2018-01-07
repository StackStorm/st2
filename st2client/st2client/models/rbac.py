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

from st2client.models import core

__all__ = [
    'Role',
    'UserRoleAssignment'
]


class Role(core.Resource):
    _alias = 'role'
    _display_name = 'Role'
    _plural = 'Roles'
    _plural_display_name = 'Roles'
    _repr_attributes = ['id', 'name', 'system']
    _url_path = 'rbac/roles'


class UserRoleAssignment(core.Resource):
    _alias = 'role-assignment'
    _display_name = 'Role Assignment'
    _plural = 'RoleAssignments'
    _plural_display_name = 'Role Assignments'
    _repr_attributes = ['id', 'role', 'user', 'is_remote']
    _url_path = 'rbac/role_assignments'

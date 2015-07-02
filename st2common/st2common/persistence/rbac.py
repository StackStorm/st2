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

from st2common.persistence import base
from st2common.models.db.rbac import role_access
from st2common.models.db.rbac import user_role_assignment_access
from st2common.models.db.rbac import permission_assignment_access

__all__ = [
    'Role',
    'UserRoleAssignment',
    'PermissionAssignment'
]


class Role(base.Access):
    impl = role_access

    @classmethod
    def _get_impl(cls):
        return cls.impl


class UserRoleAssignment(base.Access):
    impl = user_role_assignment_access

    @classmethod
    def _get_impl(cls):
        return cls.impl


class PermissionAssignment(base.Access):
    imp = permission_assignment_access

    @classmethod
    def _get_impl(cls):
        return cls.impl

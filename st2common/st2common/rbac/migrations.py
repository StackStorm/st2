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

from st2common.rbac.types import SystemRole
from st2common.persistence.rbac import Role
from st2common.models.db.rbac import RoleDB
from st2common.exceptions.db import StackStormDBObjectConflictError

__all__ = [
    'insert_system_roles'
]


def insert_system_roles():
    system_roles = SystemRole.get_valid_values()

    for role_name in system_roles:
        description = role_name
        role_db = RoleDB(name=role_name, description=description, system=True)

        # TODO: This it not ideal, we need to modify add_or_update so it allows atomic updates
        # by non-id PK
        try:
            Role.add_or_update(role_db)
        except StackStormDBObjectConflictError:
            pass

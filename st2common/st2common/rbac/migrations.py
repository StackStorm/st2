# Copyright 2020 The StackStorm Authors.
# Copyright 2019 Extreme Networks, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import absolute_import
from mongoengine import NotUniqueError

from st2common import log as logging
from st2common.rbac.types import SystemRole
from st2common.models.db.rbac import RoleDB
from st2common.exceptions.db import StackStormDBObjectConflictError

LOG = logging.getLogger(__name__)

__all__ = ["run_all", "insert_system_roles"]


def run_all():
    insert_system_roles()


def insert_system_roles():
    """
    Migration which inserts the default system roles.
    """
    system_roles = SystemRole.get_valid_values()

    LOG.debug("Inserting system roles (%s)" % (str(system_roles)))

    for role_name in system_roles:
        description = role_name
        role_db = RoleDB(name=role_name, description=description, system=True)

        try:
            role_db.save()
        except (StackStormDBObjectConflictError, NotUniqueError):
            # Role already exists error is not fatal
            pass

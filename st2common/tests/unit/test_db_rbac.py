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
from st2common.models.db.rbac import RoleDB
from st2common.models.db.rbac import UserRoleAssignmentDB
from st2common.models.db.rbac import PermissionGrantDB
from st2common.models.db.rbac import GroupToRoleMappingDB
from st2common.persistence.rbac import Role
from st2common.persistence.rbac import UserRoleAssignment
from st2common.persistence.rbac import PermissionGrant
from st2common.persistence.rbac import GroupToRoleMapping
from st2tests import DbTestCase

from tests.unit.base import BaseDBModelCRUDTestCase


__all__ = [
    "RoleDBModelCRUDTestCase",
    "UserRoleAssignmentDBModelCRUDTestCase",
    "PermissionGrantDBModelCRUDTestCase",
    "GroupToRoleMappingDBModelCRUDTestCase",
]


class RoleDBModelCRUDTestCase(BaseDBModelCRUDTestCase, DbTestCase):
    model_class = RoleDB
    persistance_class = Role
    model_class_kwargs = {
        "name": "role_one",
        "description": None,
        "system": False,
        "permission_grants": [],
    }
    update_attribute_name = "name"


class UserRoleAssignmentDBModelCRUDTestCase(BaseDBModelCRUDTestCase, DbTestCase):
    model_class = UserRoleAssignmentDB
    persistance_class = UserRoleAssignment
    model_class_kwargs = {
        "user": "user_one",
        "role": "role_one",
        "source": "source_one",
        "is_remote": True,
    }
    update_attribute_name = "role"


class PermissionGrantDBModelCRUDTestCase(BaseDBModelCRUDTestCase, DbTestCase):
    model_class = PermissionGrantDB
    persistance_class = PermissionGrant
    model_class_kwargs = {
        "resource_uid": "pack:core",
        "resource_type": "pack",
        "permission_types": [],
    }
    update_attribute_name = "resource_uid"


class GroupToRoleMappingDBModelCRUDTestCase(BaseDBModelCRUDTestCase, DbTestCase):
    model_class = GroupToRoleMappingDB
    persistance_class = GroupToRoleMapping
    model_class_kwargs = {
        "group": "some group",
        "roles": ["role_one", "role_two"],
        "description": "desc",
        "enabled": True,
    }
    update_attribute_name = "group"

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
from st2tests.api import FunctionalTest

from st2common.constants.keyvalue import SYSTEM_SCOPE, FULL_SYSTEM_SCOPE
from st2common.constants.keyvalue import USER_SCOPE, FULL_USER_SCOPE
from st2common.exceptions.keyvalue import InvalidScopeException, InvalidUserException
from st2common.services.keyvalues import get_key_reference
from st2common.services.keyvalues import get_all_system_kvp_names_for_user
from st2common.persistence.auth import User
from st2common.models.db.auth import UserDB
from st2common.models.db.rbac import UserRoleAssignmentDB
from st2common.models.db.rbac import PermissionGrantDB
from st2common.rbac.types import PermissionType
from st2common.rbac.types import ResourceType
from st2common.persistence.rbac import UserRoleAssignment
from st2common.persistence.rbac import PermissionGrant
from st2common.persistence.rbac import Role
from st2common.models.db.rbac import RoleDB


class KeyValueServicesTest(FunctionalTest):
    def test_get_key_reference_system_scope(self):
        ref = get_key_reference(scope=SYSTEM_SCOPE, name="foo")
        self.assertEqual(ref, "foo")

    def test_get_key_reference_user_scope(self):
        ref = get_key_reference(scope=USER_SCOPE, name="foo", user="stanley")
        self.assertEqual(ref, "stanley:foo")
        self.assertRaises(
            InvalidUserException,
            get_key_reference,
            scope=USER_SCOPE,
            name="foo",
            user="",
        )

    def test_get_key_reference_invalid_scope_raises_exception(self):
        self.assertRaises(
            InvalidScopeException, get_key_reference, scope="sketchy", name="foo"
        )

    def test_get_all_system_kvp_names_for_user(self):
        user1, user2 = "user1", "user2"
        kvp_1_uid = "%s:%s:s101" % (ResourceType.KEY_VALUE_PAIR, FULL_SYSTEM_SCOPE)
        kvp_2_uid = "%s:%s:s102" % (ResourceType.KEY_VALUE_PAIR, FULL_SYSTEM_SCOPE)
        kvp_3_uid = "%s:%s:%s:u101" % (
            ResourceType.KEY_VALUE_PAIR,
            FULL_USER_SCOPE,
            user1,
        )
        kvp_4_uid = "%s:%s:echo" % (ResourceType.ACTION, "core")
        kvp_5_uid = "%s:%s:new_action" % (ResourceType.ACTION, "dummy")
        kvp_6_uid = "%s:%s:s103" % (ResourceType.KEY_VALUE_PAIR, FULL_SYSTEM_SCOPE)

        # Setup user1, grant, role, and assignment records
        user_1_db = UserDB(name=user1)
        user_1_db = User.add_or_update(user_1_db)

        grant_1_db = PermissionGrantDB(
            resource_uid=kvp_1_uid,
            resource_type=ResourceType.KEY_VALUE_PAIR,
            permission_types=[PermissionType.KEY_VALUE_PAIR_LIST],
        )
        grant_1_db = PermissionGrant.add_or_update(grant_1_db)

        grant_2_db = PermissionGrantDB(
            resource_uid=kvp_2_uid,
            resource_type=ResourceType.KEY_VALUE_PAIR,
            permission_types=[PermissionType.KEY_VALUE_PAIR_VIEW],
        )
        grant_2_db = PermissionGrant.add_or_update(grant_2_db)

        grant_3_db = PermissionGrantDB(
            resource_uid=kvp_3_uid,
            resource_type=ResourceType.KEY_VALUE_PAIR,
            permission_types=[PermissionType.KEY_VALUE_PAIR_ALL],
        )
        grant_3_db = PermissionGrant.add_or_update(grant_3_db)

        grant_4_db = PermissionGrantDB(
            resource_uid=kvp_4_uid,
            resource_type=ResourceType.ACTION,
            permission_types=[PermissionType.ACTION_VIEW],
        )
        grant_4_db = PermissionGrant.add_or_update(grant_4_db)

        grant_5_db = PermissionGrantDB(
            resource_uid=kvp_5_uid,
            resource_type=ResourceType.ACTION,
            permission_types=[PermissionType.ACTION_LIST],
        )
        grant_5_db = PermissionGrant.add_or_update(grant_5_db)

        role_1_db = RoleDB(
            name="user1_custom_role_grant",
            permission_grants=[
                str(grant_1_db.id),
                str(grant_2_db.id),
                str(grant_3_db.id),
                str(grant_4_db.id),
            ],
        )
        role_1_db = Role.add_or_update(role_1_db)

        role_1_assignment_db = UserRoleAssignmentDB(
            user=user_1_db.name,
            role=role_1_db.name,
            source="assignments/%s.yaml" % user_1_db.name,
        )
        UserRoleAssignment.add_or_update(role_1_assignment_db)

        # Setup user2, grant, role, and assignment records
        user_2_db = UserDB(name=user2)
        user_2_db = User.add_or_update(user_2_db)

        grant_6_db = PermissionGrantDB(
            resource_uid=kvp_6_uid,
            resource_type=ResourceType.KEY_VALUE_PAIR,
            permission_types=[PermissionType.KEY_VALUE_PAIR_ALL],
        )
        grant_6_db = PermissionGrant.add_or_update(grant_6_db)

        role_2_db = RoleDB(
            name="user2_custom_role_grant",
            permission_grants=[
                str(grant_5_db.id),
                str(grant_6_db.id),
            ],
        )
        role_2_db = Role.add_or_update(role_2_db)

        role_2_assignment_db = UserRoleAssignmentDB(
            user=user_2_db.name,
            role=role_2_db.name,
            source="assignments/%s.yaml" % user_2_db.name,
        )
        UserRoleAssignment.add_or_update(role_2_assignment_db)

        # Assert result of get_all_system_kvp_names_for_user for user1
        # The uids for non key value pair resource type should not be included in the result.
        # The user scoped key should not be included in the result.
        actual_result = get_all_system_kvp_names_for_user(user=user_1_db.name)
        expected_result = ["s101", "s102"]
        self.assertListEqual(actual_result, expected_result)

        # Assert result of get_all_system_kvp_names_for_user for user2
        # The uids for non key value pair resource type should not be included in the result.
        # The user scoped key should not be included in the result.
        actual_result = get_all_system_kvp_names_for_user(user=user_2_db.name)
        expected_result = ["s103"]
        self.assertListEqual(actual_result, expected_result)

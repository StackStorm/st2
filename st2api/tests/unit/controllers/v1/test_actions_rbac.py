# Copyright 2020 The StackStorm Authors.
# Copyright (C) 2020 Extreme Networks, Inc - All Rights Reserved
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

import mock
import os
import six

import st2common.validators.api.action as action_validator
from st2common.rbac.types import PermissionType
from st2common.rbac.types import ResourceType
from st2common.persistence.auth import User
from st2common.persistence.rbac import Role
from st2common.persistence.rbac import UserRoleAssignment
from st2common.persistence.rbac import PermissionGrant
from st2common.models.db.auth import UserDB
from st2common.models.db.rbac import RoleDB
from st2common.models.db.rbac import UserRoleAssignmentDB
from st2common.models.db.rbac import PermissionGrantDB
from st2tests.fixturesloader import FixturesLoader
from st2api.controllers.v1.actions import ActionsController

from tests.base import APIControllerWithRBACTestCase
from st2tests.api import APIControllerWithIncludeAndExcludeFilterTestCase

http_client = six.moves.http_client

__all__ = ["ActionControllerRBACTestCase"]

FIXTURES_PACK = "generic"
TEST_FIXTURES = {
    "runners": ["testrunner1.yaml"],
    "actions": ["action1.yaml", "local.yaml"],
}

ACTION_2 = {
    "name": "ma.dummy.action",
    "pack": "examples",
    "description": "test description",
    "enabled": True,
    "entry_point": "/tmp/test/action2.py",
    "runner_type": "local-shell-script",
    "parameters": {
        "c": {"type": "string", "default": "C1", "position": 0},
        "d": {"type": "string", "default": "D1", "immutable": True},
    },
}

ACTION_3 = {
    "name": "ma.dummy.clone_action",
    "pack": "clonepack",
    "description": "test description",
    "enabled": True,
    "entry_point": "/tmp/test/clone_action.sh",
    "runner_type": "local-shell-script",
    "parameters": {
        "x": {"type": "string", "default": "A1"},
        "y": {"type": "string", "default": "B1"},
    },
}


class ActionControllerRBACTestCase(
    APIControllerWithRBACTestCase, APIControllerWithIncludeAndExcludeFilterTestCase
):

    # Attributes used by APIControllerWithIncludeAndExcludeFilterTestCase
    get_all_path = "/v1/actions"
    controller_cls = ActionsController
    include_attribute_field_name = "parameters"
    exclude_attribute_field_name = "parameters"
    test_exact_object_count = False
    rbac_enabled = True

    fixtures_loader = FixturesLoader()

    def setUp(self):
        super(ActionControllerRBACTestCase, self).setUp()
        self.models = self.fixtures_loader.save_fixtures_to_db(
            fixtures_pack=FIXTURES_PACK, fixtures_dict=TEST_FIXTURES
        )

        # Insert mock users, roles and assignments
        # Users
        user_2_db = UserDB(name="action_create")
        user_2_db = User.add_or_update(user_2_db)
        self.users["action_create"] = user_2_db

        # Roles
        # action_create grant on parent pack
        grant_db = PermissionGrantDB(
            resource_uid="pack:examples",
            resource_type=ResourceType.PACK,
            permission_types=[PermissionType.ACTION_CREATE],
        )
        grant_db = PermissionGrant.add_or_update(grant_db)
        permission_grants = [str(grant_db.id)]
        role_1_db = RoleDB(name="action_create", permission_grants=permission_grants)
        role_1_db = Role.add_or_update(role_1_db)
        self.roles["action_create"] = role_1_db

        # Role assignments
        user_db = self.users["action_create"]
        role_assignment_db = UserRoleAssignmentDB(
            user=user_db.name,
            role=self.roles["action_create"].name,
            source="assignments/%s.yaml" % user_db.name,
        )
        UserRoleAssignment.add_or_update(role_assignment_db)

        # creating `action_clone` user with all permissions related to cloning an action
        user_3_db = UserDB(name="action_clone")
        user_3_db = User.add_or_update(user_3_db)
        self.users["action_clone"] = user_3_db

        # roles of action_clone user
        grant_db = PermissionGrantDB(
            resource_uid="pack:clonepack",
            resource_type=ResourceType.PACK,
            permission_types=[PermissionType.ACTION_CREATE],
        )
        grant_db = PermissionGrant.add_or_update(grant_db)
        grant_db_view = PermissionGrantDB(
            resource_uid="pack:examples",
            resource_type=ResourceType.PACK,
            permission_types=[PermissionType.ACTION_VIEW],
        )
        grant_db_view = PermissionGrant.add_or_update(grant_db_view)
        grant_db_create = PermissionGrantDB(
            resource_uid="pack:examples",
            resource_type=ResourceType.PACK,
            permission_types=[PermissionType.ACTION_CREATE],
        )
        grant_db_create = PermissionGrant.add_or_update(grant_db_create)
        grant_db_delete = PermissionGrantDB(
            resource_uid="pack:clonepack",
            resource_type=ResourceType.PACK,
            permission_types=[PermissionType.ACTION_DELETE],
        )
        grant_db_delete = PermissionGrant.add_or_update(grant_db_delete)
        permission_grants = [
            str(grant_db.id),
            str(grant_db_view.id),
            str(grant_db_create.id),
            str(grant_db_delete.id),
        ]
        role_1_db = RoleDB(name="action_clone", permission_grants=permission_grants)
        role_1_db = Role.add_or_update(role_1_db)
        self.roles["action_clone"] = role_1_db

        # role assignments for action_clone user
        user_db = self.users["action_clone"]
        role_assignment_db = UserRoleAssignmentDB(
            user=user_db.name,
            role=self.roles["action_clone"].name,
            source="assignments/%s.yaml" % user_db.name,
        )
        UserRoleAssignment.add_or_update(role_assignment_db)

        # creating `no_create_permission` user with action_view permission on source action
        # but no create_action permission on destination pack
        user_2_db = UserDB(name="no_create_permission")
        user_2_db = User.add_or_update(user_2_db)
        self.users["no_create_permission"] = user_2_db

        # roles of no_create_permission user
        grant_db = PermissionGrantDB(
            resource_uid="pack:examples",
            resource_type=ResourceType.PACK,
            permission_types=[PermissionType.ACTION_VIEW],
        )
        grant_db = PermissionGrant.add_or_update(grant_db)
        grant_db_delete = PermissionGrantDB(
            resource_uid="pack:clonepack",
            resource_type=ResourceType.PACK,
            permission_types=[PermissionType.ACTION_DELETE],
        )
        grant_db_delete = PermissionGrant.add_or_update(grant_db_delete)
        permission_grants = [str(grant_db.id), str(grant_db_delete.id)]
        role_1_db = RoleDB(
            name="no_create_permission", permission_grants=permission_grants
        )
        role_1_db = Role.add_or_update(role_1_db)
        self.roles["no_create_permission"] = role_1_db

        # role assignments for no_create_permission user
        user_db = self.users["no_create_permission"]
        role_assignment_db = UserRoleAssignmentDB(
            user=user_db.name,
            role=self.roles["no_create_permission"].name,
            source="assignments/%s.yaml" % user_db.name,
        )
        UserRoleAssignment.add_or_update(role_assignment_db)

        # creating `no_delete_permission` user with action_view permission on source action,
        # action_create on destination pack but no create_delete permission on destination pack
        user_2_db = UserDB(name="no_delete_permission")
        user_2_db = User.add_or_update(user_2_db)
        self.users["no_delete_permission"] = user_2_db

        # roles of no_delete_permission user
        grant_db_view = PermissionGrantDB(
            resource_uid="pack:examples",
            resource_type=ResourceType.PACK,
            permission_types=[PermissionType.ACTION_VIEW],
        )
        grant_db_view = PermissionGrant.add_or_update(grant_db_view)
        grant_db_create = PermissionGrantDB(
            resource_uid="pack:clonepack",
            resource_type=ResourceType.PACK,
            permission_types=[PermissionType.ACTION_CREATE],
        )
        grant_db_create = PermissionGrant.add_or_update(grant_db_create)
        permission_grants = [str(grant_db_view.id), str(grant_db_create.id)]
        role_1_db = RoleDB(
            name="no_delete_permission", permission_grants=permission_grants
        )
        role_1_db = Role.add_or_update(role_1_db)
        self.roles["no_delete_permission"] = role_1_db

        # role assignments for no_delete_permission user
        user_db = self.users["no_delete_permission"]
        role_assignment_db = UserRoleAssignmentDB(
            user=user_db.name,
            role=self.roles["no_delete_permission"].name,
            source="assignments/%s.yaml" % user_db.name,
        )
        UserRoleAssignment.add_or_update(role_assignment_db)

    @mock.patch.object(os.path, "isdir", mock.MagicMock(return_value=True))
    @mock.patch("st2api.controllers.v1.actions.clone_action")
    @mock.patch.object(
        action_validator, "validate_action", mock.MagicMock(return_value=True)
    )
    def test_clone_action_success(self, mock_clone_action):
        user_db = self.users["action_clone"]
        self.use_user(user_db)
        self.__do_post(ACTION_2)
        self.__do_post(ACTION_3)
        dest_data_body = {
            "dest_pack": ACTION_3["pack"],
            "dest_action": "clone_action_2",
        }
        source_ref_or_id = "%s.%s" % (ACTION_2["pack"], ACTION_2["name"])
        clone_resp = self.__do_clone(dest_data_body, source_ref_or_id)
        self.assertEqual(clone_resp.status_code, http_client.CREATED)

    @mock.patch.object(os.path, "isdir", mock.MagicMock(return_value=True))
    @mock.patch("st2api.controllers.v1.actions.clone_action")
    @mock.patch.object(
        action_validator, "validate_action", mock.MagicMock(return_value=True)
    )
    def test_clone_overwrite_action_success(self, mock_clone_action):
        user_db = self.users["action_clone"]
        self.use_user(user_db)
        self.__do_post(ACTION_2)
        self.__do_post(ACTION_3)
        dest_data_body = {
            "dest_pack": ACTION_3["pack"],
            "dest_action": ACTION_3["name"],
            "overwrite": True,
        }
        source_ref_or_id = "%s.%s" % (ACTION_2["pack"], ACTION_2["name"])
        clone_resp = self.__do_clone(dest_data_body, source_ref_or_id)
        self.assertEqual(clone_resp.status_code, http_client.CREATED)

    @mock.patch.object(
        action_validator, "validate_action", mock.MagicMock(return_value=True)
    )
    def test_clone_action_no_source_action_view_permission(self):
        user_db = self.users["action_create"]
        self.use_user(user_db)
        self.__do_post(ACTION_2)
        user_db = self.users["no_permissions"]
        self.use_user(user_db)
        dest_data_body = {
            "dest_pack": ACTION_3["pack"],
            "dest_action": "clone_action_3",
        }
        source_ref_or_id = "%s.%s" % (ACTION_2["pack"], ACTION_2["name"])
        clone_resp = self.__do_clone(
            dest_data_body, source_ref_or_id, expect_errors=True
        )
        expected_msg = (
            'User "no_permissions" doesn\'t have required permission "action_view" '
            'on resource "action:examples:ma.dummy.action"'
        )
        self.assertEqual(clone_resp.status_code, http_client.UNAUTHORIZED)
        self.assertEqual(clone_resp.json["faultstring"], expected_msg)

    @mock.patch.object(os.path, "isdir", mock.MagicMock(return_value=True))
    @mock.patch.object(
        action_validator, "validate_action", mock.MagicMock(return_value=True)
    )
    def test_clone_action_no_destination_action_create_permission(self):
        user_db = self.users["action_clone"]
        self.use_user(user_db)
        self.__do_post(ACTION_2)
        self.__do_post(ACTION_3)
        user_db = self.users["no_create_permission"]
        self.use_user(user_db)
        dest_data_body = {
            "dest_pack": ACTION_3["pack"],
            "dest_action": "clone_action_4",
        }
        source_ref_or_id = "%s.%s" % (ACTION_2["pack"], ACTION_2["name"])
        clone_resp = self.__do_clone(
            dest_data_body, source_ref_or_id, expect_errors=True
        )
        expected_msg = (
            'User "no_create_permission" doesn\'t have required permission "action_create" '
            'on resource "action:clonepack:clone_action_4"'
        )
        self.assertEqual(clone_resp.status_code, http_client.UNAUTHORIZED)
        self.assertEqual(clone_resp.json["faultstring"], expected_msg)

    @mock.patch.object(os.path, "isdir", mock.MagicMock(return_value=True))
    @mock.patch.object(
        action_validator, "validate_action", mock.MagicMock(return_value=True)
    )
    def test_clone_overwrite_no_destination_action_create_permission(self):
        user_db = self.users["action_clone"]
        self.use_user(user_db)
        self.__do_post(ACTION_2)
        self.__do_post(ACTION_3)
        user_db = self.users["no_create_permission"]
        self.use_user(user_db)
        dest_data_body = {
            "dest_pack": ACTION_3["pack"],
            "dest_action": ACTION_3["name"],
            "overwrite": True,
        }
        source_ref_or_id = "%s.%s" % (ACTION_2["pack"], ACTION_2["name"])
        clone_resp = self.__do_clone(
            dest_data_body, source_ref_or_id, expect_errors=True
        )
        expected_msg = (
            'User "no_create_permission" doesn\'t have required permission "action_create" '
            'on resource "action:clonepack:ma.dummy.clone_action"'
        )
        self.assertEqual(clone_resp.status_code, http_client.UNAUTHORIZED)
        self.assertEqual(clone_resp.json["faultstring"], expected_msg)

    @mock.patch.object(os.path, "isdir", mock.MagicMock(return_value=True))
    @mock.patch.object(
        action_validator, "validate_action", mock.MagicMock(return_value=True)
    )
    def test_clone_overwrite_no_destination_action_delete_permission(self):
        user_db = self.users["action_clone"]
        self.use_user(user_db)
        self.__do_post(ACTION_2)
        self.__do_post(ACTION_3)
        user_db = self.users["no_delete_permission"]
        self.use_user(user_db)
        dest_data_body = {
            "dest_pack": ACTION_3["pack"],
            "dest_action": ACTION_3["name"],
            "overwrite": True,
        }
        source_ref_or_id = "%s.%s" % (ACTION_2["pack"], ACTION_2["name"])
        clone_resp = self.__do_clone(
            dest_data_body, source_ref_or_id, expect_errors=True
        )
        expected_msg = (
            'User "no_delete_permission" doesn\'t have required permission "action_delete" '
            'on resource "action:clonepack:ma.dummy.clone_action"'
        )
        self.assertEqual(clone_resp.status_code, http_client.UNAUTHORIZED)
        self.assertEqual(clone_resp.json["faultstring"], expected_msg)

    def _insert_mock_models(self):
        action_ids = [action["id"] for action in self.models["actions"].values()]
        return action_ids

    def __do_post(self, rule):
        return self.app.post_json("/v1/actions", rule, expect_errors=True)

    def __do_clone(self, dest_data, action_id, expect_errors=False):
        return self.app.post_json(
            "/v1/actions/%s/clone" % (action_id), dest_data, expect_errors=expect_errors
        )

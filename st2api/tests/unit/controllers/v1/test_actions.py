# -*- coding: utf-8 -*-
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

import os
import os.path
import copy
import urllib

try:
    import simplejson as json
except ImportError:
    import json

import mock
import unittest
from six.moves import http_client

from st2common.persistence.action import Action
import st2common.validators.api.action as action_validator
from st2common.constants.pack import SYSTEM_PACK_NAME
from st2common.persistence.pack import Pack
from st2api.controllers.v1.actions import ActionsController
from st2tests.fixtures.packs.dummy_pack_1.fixture import (
    PACK_NAME as DUMMY_PACK_1,
    PACK_PATH as DUMMY_PACK_1_PATH,
)
from st2tests.base import CleanFilesTestCase

from st2tests.api import FunctionalTest
from st2tests.api import APIControllerWithIncludeAndExcludeFilterTestCase

# ACTION_1: Good action definition.
ACTION_1 = {
    "name": "st2.dummy.action1",
    "description": "test description",
    "enabled": True,
    "pack": "wolfpack",
    "entry_point": "/tmp/test/action1.sh",
    "runner_type": "local-shell-script",
    "parameters": {
        "a": {"type": "string", "default": "A1"},
        "b": {"type": "string", "default": "B1"},
    },
    "tags": [
        {"name": "tag1", "value": "dont-care"},
        {"name": "tag2", "value": "dont-care"},
    ],
}

# ACTION_2: Good action definition. No content pack.
ACTION_2 = {
    "name": "st2.dummy.action2",
    "description": "test description",
    "enabled": True,
    "entry_point": "/tmp/test/action2.py",
    "runner_type": "local-shell-script",
    "parameters": {
        "c": {"type": "string", "default": "C1", "position": 0},
        "d": {"type": "string", "default": "D1", "immutable": True},
    },
}

# ACTION_3: No enabled field
ACTION_3 = {
    "name": "st2.dummy.action3",
    "description": "test description",
    "pack": "wolfpack",
    "entry_point": "/tmp/test/action1.sh",
    "runner_type": "local-shell-script",
    "parameters": {
        "a": {"type": "string", "default": "A1"},
        "b": {"type": "string", "default": "B1"},
    },
}

# ACTION_4: Enabled field is False
ACTION_4 = {
    "name": "st2.dummy.action4",
    "description": "test description",
    "enabled": False,
    "pack": "wolfpack",
    "entry_point": "/tmp/test/action1.sh",
    "runner_type": "local-shell-script",
    "parameters": {
        "a": {"type": "string", "default": "A1"},
        "b": {"type": "string", "default": "B1"},
    },
}

# ACTION_5: Invalid runner_type
ACTION_5 = {
    "name": "st2.dummy.action5",
    "description": "test description",
    "enabled": False,
    "pack": "wolfpack",
    "entry_point": "/tmp/test/action1.sh",
    "runner_type": "xyzxyz",
    "parameters": {
        "a": {"type": "string", "default": "A1"},
        "b": {"type": "string", "default": "B1"},
    },
}

# ACTION_6: No description field.
ACTION_6 = {
    "name": "st2.dummy.action6",
    "enabled": False,
    "pack": "wolfpack",
    "entry_point": "/tmp/test/action1.sh",
    "runner_type": "local-shell-script",
    "parameters": {
        "a": {"type": "string", "default": "A1"},
        "b": {"type": "string", "default": "B1"},
    },
}

# ACTION_7: id field provided
ACTION_7 = {
    "id": "foobar",
    "name": "st2.dummy.action7",
    "description": "test description",
    "enabled": False,
    "pack": "wolfpack",
    "entry_point": "/tmp/test/action1.sh",
    "runner_type": "local-shell-script",
    "parameters": {
        "a": {"type": "string", "default": "A1"},
        "b": {"type": "string", "default": "B1"},
    },
}

# ACTION_8: id field provided
ACTION_8 = {
    "name": "st2.dummy.action8",
    "description": "test description",
    "enabled": True,
    "pack": "wolfpack",
    "entry_point": "/tmp/test/action1.sh",
    "runner_type": "local-shell-script",
    "parameters": {
        "cmd": {"type": "string", "default": "A1"},
        "b": {"type": "string", "default": "B1"},
    },
}

# ACTION_9: Parameter dict has fields not part of JSONSchema spec.
ACTION_9 = {
    "name": "st2.dummy.action9",
    "description": "test description",
    "enabled": True,
    "pack": "wolfpack",
    "entry_point": "/tmp/test/action1.sh",
    "runner_type": "local-shell-script",
    "parameters": {
        "a": {
            "type": "string",
            "default": "A1",
            "dummyfield": True,
        },  # dummyfield is invalid.
        "b": {"type": "string", "default": "B1"},
    },
}

# Same name as ACTION_1. Different pack though.
# Ensure that this remains the only action with pack == wolfpack1,
# otherwise take care of the test test_get_one_using_pack_parameter
ACTION_10 = {
    "name": "st2.dummy.action1",
    "description": "test description",
    "enabled": True,
    "pack": "wolfpack1",
    "entry_point": "/tmp/test/action1.sh",
    "runner_type": "local-shell-script",
    "parameters": {
        "a": {"type": "string", "default": "A1"},
        "b": {"type": "string", "default": "B1"},
    },
}

# Good action with a system pack
ACTION_11 = {
    "name": "st2.dummy.action11",
    "pack": SYSTEM_PACK_NAME,
    "description": "test description",
    "enabled": True,
    "entry_point": "/tmp/test/action2.py",
    "runner_type": "local-shell-script",
    "parameters": {
        "c": {"type": "string", "default": "C1", "position": 0},
        "d": {"type": "string", "default": "D1", "immutable": True},
    },
}

# Good action inside dummy pack
ACTION_12 = {
    "name": "st2.dummy.action1",
    "description": "test description",
    "enabled": True,
    "pack": DUMMY_PACK_1,
    "entry_point": "/tmp/test/action1.sh",
    "runner_type": "local-shell-script",
    "parameters": {
        "a": {"type": "string", "default": "A1"},
        "b": {"type": "string", "default": "B1"},
    },
    "tags": [
        {"name": "tag1", "value": "dont-care"},
        {"name": "tag2", "value": "dont-care"},
    ],
}

# Action with invalid parameter type attribute
ACTION_13 = {
    "name": "st2.dummy.action2",
    "description": "test description",
    "enabled": True,
    "pack": DUMMY_PACK_1,
    "entry_point": "/tmp/test/action1.sh",
    "runner_type": "local-shell-script",
    "parameters": {
        "a": {"type": ["string", "object"], "default": "A1"},
        "b": {"type": "string", "default": "B1"},
    },
}

ACTION_14 = {
    "name": "st2.dummy.action14",
    "description": "test description",
    "enabled": True,
    "pack": DUMMY_PACK_1,
    "entry_point": "/tmp/test/action1.sh",
    "runner_type": "local-shell-script",
    "parameters": {
        "a": {"type": "string", "default": "A1"},
        "b": {"type": "string", "default": "B1"},
        "sudo": {"type": "string"},
    },
}

ACTION_15 = {
    "name": "st2.dummy.action15",
    "description": "test description",
    "enabled": True,
    "pack": DUMMY_PACK_1,
    "entry_point": "/tmp/test/action1.sh",
    "runner_type": "local-shell-script",
    "parameters": {
        "a": {"type": "string", "default": "A1"},
        "b": {"type": "string", "default": "B1"},
        "sudo": {"default": True, "immutable": True},
    },
}

ACTION_16 = {
    "name": "st2.dummy.source_action",
    "description": "test description",
    "enabled": True,
    "pack": "sourcepack",
    "entry_point": "/tmp/test/source_action.py",
    "runner_type": "python-script",
    "parameters": {
        "x": {"type": "string", "default": "X1"},
        "y": {"type": "string", "default": "Y1"},
    },
    "tags": [
        {"name": "tag1", "value": "dont-care1"},
        {"name": "tag2", "value": "dont-care2"},
    ],
}

ACTION_17 = {
    "name": "st2.dummy.clone_action",
    "description": "test description",
    "enabled": True,
    "pack": "clonepack",
    "entry_point": "/tmp/test/clone_action.sh",
    "runner_type": "local-shell-script",
    "parameters": {
        "a": {"type": "string", "default": "A1"},
    },
}

ACTION_WITH_NOTIFY = {
    "name": "st2.dummy.action_notify_test",
    "description": "test description",
    "enabled": True,
    "pack": DUMMY_PACK_1,
    "entry_point": "/tmp/test/action1.sh",
    "runner_type": "local-shell-script",
    "parameters": {
        "a": {"type": "string", "default": "A1"},
        "b": {"type": "string", "default": "B1"},
        "sudo": {"default": True, "immutable": True},
    },
    "notify": {"on-complete": {"message": "Woohoo! I completed!!!"}},
}


ACTION_WITH_UNICODE_NAME = {
    "name": "st2.dummy.action_unicode_我爱狗",
    "description": "test description",
    "enabled": True,
    "pack": DUMMY_PACK_1,
    "entry_point": "/tmp/test/action1.sh",
    "runner_type": "local-shell-script",
    "parameters": {
        "a": {"type": "string", "default": "A1"},
        "b": {"type": "string", "default": "B1"},
        "sudo": {"default": True, "immutable": True},
    },
    "notify": {"on-complete": {"message": "Woohoo! I completed!!!"}},
}


class ActionsControllerTestCase(
    FunctionalTest, APIControllerWithIncludeAndExcludeFilterTestCase, CleanFilesTestCase
):
    get_all_path = "/v1/actions"
    controller_cls = ActionsController
    include_attribute_field_name = "entry_point"
    exclude_attribute_field_name = "parameters"

    register_packs = True

    to_delete_files = [os.path.join(DUMMY_PACK_1_PATH, "actions/filea.txt")]

    @mock.patch.object(
        action_validator, "validate_action", mock.MagicMock(return_value=True)
    )
    def test_get_one_using_id(self):
        post_resp = self.__do_post(ACTION_1)
        action_id = self.__get_action_id(post_resp)
        get_resp = self.__do_get_one(action_id)
        self.assertEqual(get_resp.status_int, 200)
        self.assertEqual(self.__get_action_id(get_resp), action_id)
        self.__do_delete(action_id)

    @mock.patch.object(
        action_validator, "validate_action", mock.MagicMock(return_value=True)
    )
    def test_get_one_using_ref(self):
        ref = ".".join([ACTION_1["pack"], ACTION_1["name"]])
        action_id = self.__get_action_id(self.__do_post(ACTION_1))
        get_resp = self.__do_get_one(ref)
        self.assertEqual(get_resp.status_int, 200)
        self.assertEqual(self.__get_action_id(get_resp), action_id)
        self.assertEqual(get_resp.json["ref"], ref)
        self.__do_delete(action_id)

    @mock.patch.object(
        action_validator, "validate_action", mock.MagicMock(return_value=True)
    )
    def test_get_one_validate_params(self):
        post_resp = self.__do_post(ACTION_1)
        action_id = self.__get_action_id(post_resp)
        get_resp = self.__do_get_one(action_id)
        self.assertEqual(get_resp.status_int, 200)
        self.assertEqual(self.__get_action_id(get_resp), action_id)
        expected_args = ACTION_1["parameters"]
        self.assertEqual(get_resp.json["parameters"], expected_args)
        self.__do_delete(action_id)

    @mock.patch.object(
        action_validator, "validate_action", mock.MagicMock(return_value=True)
    )
    def test_get_all_and_with_minus_one(self):
        action_1_ref = ".".join([ACTION_1["pack"], ACTION_1["name"]])
        action_1_id = self.__get_action_id(self.__do_post(ACTION_1))
        action_2_id = self.__get_action_id(self.__do_post(ACTION_2))
        resp = self.app.get("/v1/actions")
        self.assertEqual(resp.status_int, 200)
        self.assertEqual(len(resp.json), 2, "/v1/actions did not return all actions.")

        item = [i for i in resp.json if i["id"] == action_1_id][0]
        self.assertEqual(item["ref"], action_1_ref)

        resp = self.app.get("/v1/actions?limit=-1")
        self.assertEqual(resp.status_int, 200)
        self.assertEqual(len(resp.json), 2, "/v1/actions did not return all actions.")

        item = [i for i in resp.json if i["id"] == action_1_id][0]
        self.assertEqual(item["ref"], action_1_ref)

        self.__do_delete(action_1_id)
        self.__do_delete(action_2_id)

    @mock.patch(
        "st2common.rbac.backends.noop.NoOpRBACUtils.user_is_admin",
        mock.Mock(return_value=False),
    )
    def test_get_all_invalid_limit_too_large_none_admin(self):
        # limit > max_page_size, but user is not admin
        resp = self.app.get("/v1/actions?limit=1000", expect_errors=True)
        self.assertEqual(resp.status_int, http_client.FORBIDDEN)
        self.assertEqual(
            resp.json["faultstring"],
            'Limit "1000" specified, maximum value is' ' "100"',
        )

    def test_get_all_limit_negative_number(self):
        resp = self.app.get("/v1/actions?limit=-22", expect_errors=True)
        self.assertEqual(resp.status_int, 400)
        self.assertEqual(
            resp.json["faultstring"],
            'Limit, "-22" specified, must be a positive number.',
        )

    @mock.patch.object(
        action_validator, "validate_action", mock.MagicMock(return_value=True)
    )
    def test_get_all_include_attributes_filter(self):
        return super(
            ActionsControllerTestCase, self
        ).test_get_all_include_attributes_filter()

    @mock.patch.object(
        action_validator, "validate_action", mock.MagicMock(return_value=True)
    )
    def test_get_all_exclude_attributes_filter(self):
        return super(
            ActionsControllerTestCase, self
        ).test_get_all_include_attributes_filter()

    @mock.patch.object(
        action_validator, "validate_action", mock.MagicMock(return_value=True)
    )
    def test_query(self):
        action_1_id = self.__get_action_id(self.__do_post(ACTION_1))
        action_2_id = self.__get_action_id(self.__do_post(ACTION_2))
        resp = self.app.get("/v1/actions?name=%s" % ACTION_1["name"])
        self.assertEqual(resp.status_int, 200)
        self.assertEqual(len(resp.json), 1, "/v1/actions did not return all actions.")
        self.__do_delete(action_1_id)
        self.__do_delete(action_2_id)

    @mock.patch.object(
        action_validator, "validate_action", mock.MagicMock(return_value=True)
    )
    def test_get_one_fail(self):
        resp = self.app.get("/v1/actions/1", expect_errors=True)
        self.assertEqual(resp.status_int, 404)

    @mock.patch.object(
        action_validator, "validate_action", mock.MagicMock(return_value=True)
    )
    def test_post_delete(self):
        post_resp = self.__do_post(ACTION_1)
        self.assertEqual(post_resp.status_int, 201)
        self.__do_delete(self.__get_action_id(post_resp))

    @mock.patch.object(
        action_validator, "validate_action", mock.MagicMock(return_value=True)
    )
    def test_post_action_with_bad_params(self):
        post_resp = self.__do_post(ACTION_9, expect_errors=True)
        self.assertEqual(post_resp.status_int, 400)

    @mock.patch.object(
        action_validator, "validate_action", mock.MagicMock(return_value=True)
    )
    def test_post_no_description_field(self):
        post_resp = self.__do_post(ACTION_6)
        self.assertEqual(post_resp.status_int, 201)
        self.__do_delete(self.__get_action_id(post_resp))

    @mock.patch.object(
        action_validator, "validate_action", mock.MagicMock(return_value=True)
    )
    def test_post_no_enable_field(self):
        post_resp = self.__do_post(ACTION_3)
        self.assertEqual(post_resp.status_int, 201)
        self.assertIn(b"enabled", post_resp.body)

        # If enabled field is not provided it should default to True
        data = json.loads(post_resp.body)
        self.assertDictContainsSubset({"enabled": True}, data)

        self.__do_delete(self.__get_action_id(post_resp))

    @mock.patch.object(
        action_validator, "validate_action", mock.MagicMock(return_value=True)
    )
    def test_post_false_enable_field(self):
        post_resp = self.__do_post(ACTION_4)
        self.assertEqual(post_resp.status_int, 201)

        data = json.loads(post_resp.body)
        self.assertDictContainsSubset({"enabled": False}, data)

        self.__do_delete(self.__get_action_id(post_resp))

    @mock.patch.object(
        action_validator, "validate_action", mock.MagicMock(return_value=True)
    )
    def test_post_name_unicode_action_already_exists(self):
        # Verify that exception messages containing unicode characters don't result in internal
        # server errors
        action = copy.deepcopy(ACTION_1)
        # NOTE: We explicitly don't prefix this string value with u""
        action["name"] = "žactionćšžži💩"

        # 1. Initial creation
        post_resp = self.__do_post(action, expect_errors=True)
        self.assertEqual(post_resp.status_int, 201)

        # 2. Action already exists
        post_resp = self.__do_post(action, expect_errors=True)
        self.assertEqual(post_resp.status_int, 409)
        self.assertIn(
            "Tried to save duplicate unique keys", post_resp.json["faultstring"]
        )

        # 3. Action already exists (this time with unicode type)
        action["name"] = "žactionćšžži💩"
        post_resp = self.__do_post(action, expect_errors=True)
        self.assertEqual(post_resp.status_int, 409)
        self.assertIn(
            "Tried to save duplicate unique keys", post_resp.json["faultstring"]
        )

    @mock.patch.object(
        action_validator, "validate_action", mock.MagicMock(return_value=True)
    )
    def test_post_parameter_type_is_array_and_invalid(self):
        post_resp = self.__do_post(ACTION_13, expect_errors=True)
        self.assertEqual(post_resp.status_int, 400)

        expected_error = (
            b"['string', 'object'] is not valid under any of the given schemas"
        )

        self.assertIn(expected_error, post_resp.body)

    @mock.patch.object(
        action_validator, "validate_action", mock.MagicMock(return_value=True)
    )
    def test_post_discard_id_field(self):
        post_resp = self.__do_post(ACTION_7)
        self.assertEqual(post_resp.status_int, 201)
        self.assertIn(b"id", post_resp.body)
        data = json.loads(post_resp.body)
        # Verify that user-provided id is discarded.
        self.assertNotEqual(data["id"], ACTION_7["id"])
        self.__do_delete(self.__get_action_id(post_resp))

    @mock.patch.object(
        action_validator, "validate_action", mock.MagicMock(return_value=True)
    )
    def test_post_duplicate(self):
        action_ids = []

        post_resp = self.__do_post(ACTION_1)
        self.assertEqual(post_resp.status_int, 201)
        action_in_db = Action.get_by_name(ACTION_1.get("name"))
        self.assertIsNotNone(action_in_db, "Action must be in db.")
        action_ids.append(self.__get_action_id(post_resp))

        post_resp = self.__do_post(ACTION_1, expect_errors=True)
        # Verify name conflict
        self.assertEqual(post_resp.status_int, 409)
        self.assertEqual(post_resp.json["conflict-id"], action_ids[0])

        post_resp = self.__do_post(ACTION_10)
        action_ids.append(self.__get_action_id(post_resp))
        # Verify action with same name but different pack is written.
        self.assertEqual(post_resp.status_int, 201)

        for i in action_ids:
            self.__do_delete(i)

    @mock.patch.object(
        action_validator, "validate_action", mock.MagicMock(return_value=True)
    )
    def test_post_include_files(self):
        # Verify initial state
        pack_db = Pack.get_by_ref(ACTION_12["pack"])
        self.assertNotIn("actions/filea.txt", pack_db.files)

        action = copy.deepcopy(ACTION_12)
        action["data_files"] = [{"file_path": "filea.txt", "content": "test content"}]
        post_resp = self.__do_post(action)

        # Verify file has been written on disk
        for file_path in self.to_delete_files:
            self.assertTrue(os.path.exists(file_path))

        # Verify PackDB.files has been updated
        pack_db = Pack.get_by_ref(ACTION_12["pack"])
        self.assertIn("actions/filea.txt", pack_db.files)
        self.__do_delete(self.__get_action_id(post_resp))

    @mock.patch.object(
        action_validator, "validate_action", mock.MagicMock(return_value=True)
    )
    def test_post_put_delete(self):
        action = copy.copy(ACTION_1)
        post_resp = self.__do_post(action)
        self.assertEqual(post_resp.status_int, 201)
        self.assertIn(b"id", post_resp.body)
        body = json.loads(post_resp.body)
        action["id"] = body["id"]
        action["description"] = "some other test description"
        pack = action["pack"]
        del action["pack"]
        self.assertNotIn("pack", action)
        put_resp = self.__do_put(action["id"], action)
        self.assertEqual(put_resp.status_int, 200)
        self.assertIn(b"description", put_resp.body)
        body = json.loads(put_resp.body)
        self.assertEqual(body["description"], action["description"])
        self.assertEqual(body["pack"], pack)
        delete_resp = self.__do_delete(self.__get_action_id(post_resp))
        self.assertEqual(delete_resp.status_int, 204)

    def test_post_invalid_runner_type(self):
        post_resp = self.__do_post(ACTION_5, expect_errors=True)
        self.assertEqual(post_resp.status_int, 400)

    def test_post_override_runner_param_not_allowed(self):
        post_resp = self.__do_post(ACTION_14, expect_errors=True)
        self.assertEqual(post_resp.status_int, 400)
        expected = (
            'The attribute "type" for the runner parameter "sudo" '
            'in action "dummy_pack_1.st2.dummy.action14" cannot be overridden.'
        )
        self.assertEqual(post_resp.json.get("faultstring"), expected)

    def test_post_override_runner_param_allowed(self):
        post_resp = self.__do_post(ACTION_15)
        self.assertEqual(post_resp.status_int, 201)

    @mock.patch("st2api.controllers.v1.actions.delete_action_files_from_pack")
    @mock.patch.object(
        action_validator, "validate_action", mock.MagicMock(return_value=True)
    )
    def test_delete(self, mock_remove_files):
        post_resp = self.__do_post(ACTION_1)
        action_id = self.__get_action_id(post_resp)
        del_resp = self.__do_delete(action_id)
        self.assertEqual(del_resp.status_int, 204)
        mock_remove_files.assert_not_called()

        # asserting ACTION_1 database entry has removed
        get_resp = self.__do_get_one(action_id, expect_errors=True)
        expected_msg = 'Resource with a reference or id "%s" not found' % action_id
        actual_msg = get_resp.json["faultstring"]
        self.assertEqual(actual_msg, expected_msg)

    @mock.patch("st2api.controllers.v1.actions.delete_action_files_from_pack")
    @mock.patch.object(
        action_validator, "validate_action", mock.MagicMock(return_value=True)
    )
    def test_delete_remove_files_false(self, mock_remove_files):
        post_resp = self.__do_post(ACTION_1)
        action_id = self.__get_action_id(post_resp)
        payload = {"remove_files": False}
        del_resp = self.__do_delete_action_with_files(payload, action_id)
        self.assertEqual(del_resp.status_int, 204)
        mock_remove_files.assert_not_called()
        get_resp = self.__do_get_one(action_id, expect_errors=True)
        expected_msg = 'Resource with a reference or id "%s" not found' % action_id
        actual_msg = get_resp.json["faultstring"]
        self.assertEqual(actual_msg, expected_msg)

    @mock.patch("st2api.controllers.v1.actions.delete_action_files_from_pack")
    @mock.patch.object(
        action_validator, "validate_action", mock.MagicMock(return_value=True)
    )
    def test_delete_remove_files_true(self, mock_remove_files):
        post_resp = self.__do_post(ACTION_1)
        action_id = self.__get_action_id(post_resp)
        payload = {"remove_files": True}
        del_resp = self.__do_delete_action_with_files(payload, action_id)
        self.assertEqual(del_resp.status_int, 204)
        self.assertTrue(mock_remove_files.called)
        get_resp = self.__do_get_one(action_id, expect_errors=True)
        expected_msg = 'Resource with a reference or id "%s" not found' % action_id
        actual_msg = get_resp.json["faultstring"]
        self.assertEqual(actual_msg, expected_msg)

    @mock.patch.object(
        action_validator, "validate_action", mock.MagicMock(return_value=True)
    )
    def test_delete_permission_error_and_action_reregistered_to_database(self):
        post_resp = self.__do_post(ACTION_1)

        with mock.patch(
            "st2api.controllers.v1.actions.delete_action_files_from_pack"
        ) as mock_remove_files:
            msg = "No permission to delete action files from disk"
            mock_remove_files.side_effect = PermissionError(msg)
            payload = {"remove_files": True}
            del_resp = self.__do_delete_action_with_files(
                payload, self.__get_action_id(post_resp), expect_errors=True
            )
            self.assertEqual(del_resp.status_int, 403)
            self.assertEqual(del_resp.json["faultstring"], msg)

        # retrieving reregistered action
        get_resp = self.__do_get_actions_by_url_parameter("name", ACTION_1["name"])
        expected_uid = post_resp.json["uid"]
        actual_uid = get_resp.json[0]["uid"]
        self.assertEqual(actual_uid, expected_uid)
        action_id = get_resp.json[0]["id"]
        del_resp = self.__do_delete(action_id)
        self.assertEqual(del_resp.status_int, 204)

    @mock.patch.object(
        action_validator, "validate_action", mock.MagicMock(return_value=True)
    )
    def test_delete_exception_and_action_reregistered_to_database(self):
        post_resp = self.__do_post(ACTION_1)

        with mock.patch(
            "st2api.controllers.v1.actions.delete_action_files_from_pack"
        ) as mock_remove_files:
            msg = "Exception encountered during removing files from disk"
            mock_remove_files.side_effect = Exception(msg)
            payload = {"remove_files": True}
            del_resp = self.__do_delete_action_with_files(
                payload, self.__get_action_id(post_resp), expect_errors=True
            )
            self.assertEqual(del_resp.status_int, 500)
            self.assertEqual(del_resp.json["faultstring"], msg)

        # retrieving reregistered action
        get_resp = self.__do_get_actions_by_url_parameter("name", ACTION_1["name"])
        expected_uid = post_resp.json["uid"]
        actual_uid = get_resp.json[0]["uid"]
        self.assertEqual(actual_uid, expected_uid)
        action_id = get_resp.json[0]["id"]
        del_resp = self.__do_delete(action_id)
        self.assertEqual(del_resp.status_int, 204)

    @mock.patch.object(
        action_validator, "validate_action", mock.MagicMock(return_value=True)
    )
    def test_action_with_tags(self):
        post_resp = self.__do_post(ACTION_1)
        action_id = self.__get_action_id(post_resp)
        get_resp = self.__do_get_one(action_id)
        self.assertEqual(get_resp.status_int, 200)
        self.assertEqual(self.__get_action_id(get_resp), action_id)
        self.assertEqual(get_resp.json["tags"], ACTION_1["tags"])
        self.__do_delete(action_id)

    @mock.patch.object(
        action_validator, "validate_action", mock.MagicMock(return_value=True)
    )
    def test_action_with_notify_update(self):
        post_resp = self.__do_post(ACTION_WITH_NOTIFY)
        action_id = self.__get_action_id(post_resp)
        get_resp = self.__do_get_one(action_id)
        self.assertEqual(get_resp.status_int, 200)
        self.assertEqual(self.__get_action_id(get_resp), action_id)
        self.assertIsNotNone(get_resp.json["notify"]["on-complete"])
        # Now post the same action with no notify
        ACTION_WITHOUT_NOTIFY = copy.copy(ACTION_WITH_NOTIFY)
        del ACTION_WITHOUT_NOTIFY["notify"]
        self.__do_put(action_id, ACTION_WITHOUT_NOTIFY)
        # Validate that notify section has vanished
        get_resp = self.__do_get_one(action_id)
        self.assertEqual(get_resp.json["notify"], {})
        self.__do_delete(action_id)

    @mock.patch.object(
        action_validator, "validate_action", mock.MagicMock(return_value=True)
    )
    def test_action_with_unicode_name_create(self):
        post_resp = self.__do_post(ACTION_WITH_UNICODE_NAME)
        action_id = self.__get_action_id(post_resp)
        get_resp = self.__do_get_one(action_id)
        self.assertEqual(get_resp.status_int, 200)
        self.assertEqual(self.__get_action_id(get_resp), action_id)
        self.assertEqual(get_resp.json["name"], "st2.dummy.action_unicode_我爱狗")
        self.assertEqual(
            get_resp.json["ref"], "dummy_pack_1.st2.dummy.action_unicode_我爱狗"
        )
        self.assertEqual(
            get_resp.json["uid"], "action:dummy_pack_1:st2.dummy.action_unicode_我爱狗"
        )

        get_resp = self.__do_get_one("dummy_pack_1.st2.dummy.action_unicode_我爱狗")
        self.assertEqual(get_resp.json["name"], "st2.dummy.action_unicode_我爱狗")
        self.assertEqual(
            get_resp.json["ref"], "dummy_pack_1.st2.dummy.action_unicode_我爱狗"
        )
        self.assertEqual(
            get_resp.json["uid"], "action:dummy_pack_1:st2.dummy.action_unicode_我爱狗"
        )

        # Now retrieve the action using the ref and ensure it works correctly
        # NOTE: We need to use urlquoted value when retrieving the item since that's how all the
        # http clients work - non ascii characters get escaped / quoted. Passing in unquoted
        # value will result in exception (as expected).
        ref_quoted = urllib.parse.quote("dummy_pack_1.st2.dummy.action_unicode_我爱狗")
        get_resp = self.__do_get_one(ref_quoted)
        self.assertEqual(get_resp.json["name"], "st2.dummy.action_unicode_我爱狗")
        self.assertEqual(
            get_resp.json["ref"], "dummy_pack_1.st2.dummy.action_unicode_我爱狗"
        )
        self.assertEqual(
            get_resp.json["uid"], "action:dummy_pack_1:st2.dummy.action_unicode_我爱狗"
        )

        self.__do_delete(action_id)

    @mock.patch.object(
        action_validator, "validate_action", mock.MagicMock(return_value=True)
    )
    def test_get_one_using_name_parameter(self):
        action_id, action_name = self.__get_action_id_and_additional_attribute(
            self.__do_post(ACTION_1), "name"
        )
        get_resp = self.__do_get_actions_by_url_parameter("name", action_name)
        self.assertEqual(get_resp.status_int, 200)
        self.assertEqual(get_resp.json[0]["id"], action_id)
        self.assertEqual(get_resp.json[0]["name"], action_name)
        self.__do_delete(action_id)

    @mock.patch.object(
        action_validator, "validate_action", mock.MagicMock(return_value=True)
    )
    def test_get_one_using_pack_parameter(self):
        action_id, action_pack = self.__get_action_id_and_additional_attribute(
            self.__do_post(ACTION_10), "pack"
        )
        get_resp = self.__do_get_actions_by_url_parameter("pack", action_pack)
        self.assertEqual(get_resp.status_int, 200)
        self.assertEqual(get_resp.json[0]["id"], action_id)
        self.assertEqual(get_resp.json[0]["pack"], action_pack)
        self.__do_delete(action_id)

    @mock.patch.object(
        action_validator, "validate_action", mock.MagicMock(return_value=True)
    )
    def test_get_one_using_tag_parameter(self):
        action_id, action_tags = self.__get_action_id_and_additional_attribute(
            self.__do_post(ACTION_1), "tags"
        )
        get_resp = self.__do_get_actions_by_url_parameter(
            "tags", action_tags[0]["name"]
        )
        self.assertEqual(get_resp.status_int, 200)
        self.assertEqual(get_resp.json[0]["id"], action_id)
        self.assertEqual(get_resp.json[0]["tags"], action_tags)
        self.__do_delete(action_id)

    # TODO: Re-enable those tests after we ensure DB is flushed in setUp
    # and each test starts in a clean state

    @unittest.skip("Skip because of test polution")
    def test_update_action_belonging_to_system_pack(self):
        post_resp = self.__do_post(ACTION_11)
        action_id = self.__get_action_id(post_resp)
        put_resp = self.__do_put(action_id, ACTION_11, expect_errors=True)
        self.assertEqual(put_resp.status_int, 400)

    @unittest.skip("Skip because of test polution")
    def test_delete_action_belonging_to_system_pack(self):
        post_resp = self.__do_post(ACTION_11)
        action_id = self.__get_action_id(post_resp)
        del_resp = self.__do_delete(action_id, expect_errors=True)
        self.assertEqual(del_resp.status_int, 400)

    @mock.patch.object(os.path, "isdir", mock.MagicMock(return_value=True))
    @mock.patch("st2api.controllers.v1.actions.clone_action_files")
    @mock.patch.object(
        action_validator, "validate_action", mock.MagicMock(return_value=True)
    )
    def test_clone(self, mock_clone_action):
        source_post_resp = self.__do_post(ACTION_16)
        self.assertEqual(source_post_resp.status_int, 201)
        dest_data_body = {
            "dest_pack": ACTION_17["pack"],
            "dest_action": ACTION_17["name"],
        }
        source_ref_or_id = "%s.%s" % (ACTION_16["pack"], ACTION_16["name"])
        clone_resp = self.__do_clone(dest_data_body, source_ref_or_id)
        self.assertEqual(clone_resp.status_int, 201)
        get_resp = self.__do_get_actions_by_url_parameter("name", ACTION_17["name"])
        self.assertEqual(get_resp.status_int, 200)
        self.assertTrue(mock_clone_action.called)
        self.__do_delete(self.__get_action_id(source_post_resp))
        self.__do_delete(self.__get_action_id(clone_resp))

    @mock.patch.object(os.path, "isdir", mock.MagicMock(return_value=True))
    @mock.patch("st2api.controllers.v1.actions.remove_temp_action_files")
    @mock.patch("st2api.controllers.v1.actions.temp_backup_action_files")
    @mock.patch("st2api.controllers.v1.actions.clone_action_files")
    @mock.patch.object(
        action_validator, "validate_action", mock.MagicMock(return_value=True)
    )
    def test_clone_overwrite(
        self, mock_clone_action, mock_temp_backup, mock_clean_backup
    ):
        source_post_resp = self.__do_post(ACTION_16)
        self.assertEqual(source_post_resp.status_int, 201)
        dest_post_resp = self.__do_post(ACTION_17)
        self.assertEqual(dest_post_resp.status_int, 201)
        dest_data_body = {
            "dest_pack": ACTION_17["pack"],
            "dest_action": ACTION_17["name"],
            "overwrite": True,
        }
        source_ref_or_id = "%s.%s" % (ACTION_16["pack"], ACTION_16["name"])
        clone_resp = self.__do_clone(dest_data_body, source_ref_or_id)
        self.assertEqual(clone_resp.status_int, 201)
        get_resp = self.__do_get_actions_by_url_parameter("name", ACTION_17["name"])
        expected_params_dict = ACTION_16["parameters"]
        actual_prams_dict = get_resp.json[0]["parameters"]
        self.assertDictEqual(actual_prams_dict, expected_params_dict)
        actual_runner_type = get_resp.json[0]["runner_type"]
        self.assertNotEqual(actual_runner_type, ACTION_17["runner_type"])
        self.assertTrue(mock_clone_action.called)
        self.assertTrue(mock_temp_backup.called)
        self.assertTrue(mock_clean_backup.called)
        self.__do_delete(self.__get_action_id(source_post_resp))
        self.__do_delete(self.__get_action_id(clone_resp))

    @mock.patch.object(
        action_validator, "validate_action", mock.MagicMock(return_value=True)
    )
    def test_clone_source_does_not_exist(self):
        dest_data_body = {
            "dest_pack": ACTION_17["pack"],
            "dest_action": ACTION_17["name"],
        }
        source_ref_or_id = "%s.%s" % (ACTION_16["pack"], ACTION_16["name"])
        clone_resp = self.__do_clone(
            dest_data_body,
            source_ref_or_id,
            expect_errors=True,
        )
        # clone operation failed and asserting response status code and error msg
        self.assertEqual(clone_resp.status_int, 404)
        msg = 'Resource with a reference or id "%s" not found' % source_ref_or_id
        self.assertEqual(clone_resp.json["faultstring"], msg)

    @mock.patch.object(
        action_validator, "validate_action", mock.MagicMock(return_value=True)
    )
    def test_clone_destination_pack_does_not_exist(self):
        source_post_resp = self.__do_post(ACTION_16)
        dest_data_body = {
            "dest_pack": ACTION_17["pack"],
            "dest_action": ACTION_17["name"],
        }
        source_ref_or_id = "%s.%s" % (ACTION_16["pack"], ACTION_16["name"])
        clone_resp = self.__do_clone(
            dest_data_body,
            source_ref_or_id,
            expect_errors=True,
        )
        self.assertEqual(clone_resp.status_int, 400)
        msg = "Destination pack '%s' doesn't exist" % ACTION_17["pack"]
        self.assertEqual(clone_resp.json["faultstring"], msg)
        self.__do_delete(self.__get_action_id(source_post_resp))

    @mock.patch.object(os.path, "isdir", mock.MagicMock(return_value=True))
    @mock.patch.object(
        action_validator, "validate_action", mock.MagicMock(return_value=True)
    )
    def test_clone_destination_action_already_exist(self):
        source_post_resp = self.__do_post(ACTION_16)
        dest_post_resp = self.__do_post(ACTION_17)
        dest_data_body = {
            "dest_pack": ACTION_17["pack"],
            "dest_action": ACTION_17["name"],
        }
        source_ref_or_id = "%s.%s" % (ACTION_16["pack"], ACTION_16["name"])
        clone_resp = self.__do_clone(
            dest_data_body,
            source_ref_or_id,
            expect_errors=True,
        )
        self.assertEqual(clone_resp.status_int, 400)
        msg = "The requested destination action already exists"
        self.assertEqual(clone_resp.json["faultstring"], msg)
        self.__do_delete(self.__get_action_id(source_post_resp))
        self.__do_delete(self.__get_action_id(dest_post_resp))

    @mock.patch.object(os.path, "isdir", mock.MagicMock(return_value=True))
    @mock.patch("st2api.controllers.v1.actions.clone_action_files")
    @mock.patch.object(
        action_validator, "validate_action", mock.MagicMock(return_value=True)
    )
    def test_clone_permission_error(self, mock_clone_action):
        msg = "No permission to access the files for cloning operation"
        mock_clone_action.side_effect = PermissionError(msg)
        source_post_resp = self.__do_post(ACTION_16)
        dest_data_body = {
            "dest_pack": ACTION_17["pack"],
            "dest_action": "clone_action_3",
        }
        source_ref_or_id = "%s.%s" % (ACTION_16["pack"], ACTION_16["name"])
        clone_resp = self.__do_clone(
            dest_data_body,
            source_ref_or_id,
            expect_errors=True,
        )
        self.assertEqual(clone_resp.status_int, 403)
        self.assertEqual(clone_resp.json["faultstring"], msg)
        self.__do_delete(self.__get_action_id(source_post_resp))

    @mock.patch.object(os.path, "isdir", mock.MagicMock(return_value=True))
    @mock.patch("st2api.controllers.v1.actions.delete_action_files_from_pack")
    @mock.patch("st2api.controllers.v1.actions.clone_action_files")
    @mock.patch.object(
        action_validator, "validate_action", mock.MagicMock(return_value=True)
    )
    def test_clone_exception(self, mock_clone_action, mock_delete_files):
        msg = "Exception encountered during cloning action."
        mock_clone_action.side_effect = Exception(msg)
        source_post_resp = self.__do_post(ACTION_16)
        dest_data_body = {
            "dest_pack": ACTION_17["pack"],
            "dest_action": "clone_action_4",
        }
        source_ref_or_id = "%s.%s" % (ACTION_16["pack"], ACTION_16["name"])
        clone_resp = self.__do_clone(
            dest_data_body,
            source_ref_or_id,
            expect_errors=True,
        )
        self.assertEqual(clone_resp.status_int, 500)
        self.assertEqual(clone_resp.json["faultstring"], msg)
        # asserting delete_action_files_from_pack function called i.e. cloned files are cleaned up
        self.assertTrue(mock_delete_files.called)
        self.__do_delete(self.__get_action_id(source_post_resp))

    @mock.patch.object(os.path, "isdir", mock.MagicMock(return_value=True))
    @mock.patch("st2api.controllers.v1.actions.delete_action_files_from_pack")
    @mock.patch("st2api.controllers.v1.actions.remove_temp_action_files")
    @mock.patch("st2api.controllers.v1.actions.restore_temp_action_files")
    @mock.patch("st2api.controllers.v1.actions.temp_backup_action_files")
    @mock.patch("st2api.controllers.v1.actions.clone_action_files")
    @mock.patch.object(
        action_validator, "validate_action", mock.MagicMock(return_value=True)
    )
    def test_clone_overwrite_exception_destination_recovered(
        self,
        mock_clone_overwrite,
        mock_backup_files,
        mock_restore_files,
        mock_remove_backup,
        mock_clean_files,
    ):
        msg = "Exception encountered during overwriting action."
        mock_clone_overwrite.side_effect = Exception(msg)
        source_post_resp = self.__do_post(ACTION_16)
        self.__do_post(ACTION_17)
        dest_data_body = {
            "dest_pack": ACTION_17["pack"],
            "dest_action": ACTION_17["name"],
            "overwrite": True,
        }
        source_ref_or_id = "%s.%s" % (ACTION_16["pack"], ACTION_16["name"])
        clone_resp = self.__do_clone(
            dest_data_body,
            source_ref_or_id,
            expect_errors=True,
        )
        self.assertEqual(clone_resp.status_int, 500)
        # asserting temp_backup_action_files function called
        self.assertTrue(mock_backup_files.called)
        # asserting restore_temp_action_files called i.e. original ACTION_17 restored
        self.assertTrue(mock_restore_files.called)
        # asserting remove_temp_action_files function called
        self.assertTrue(mock_remove_backup.called)
        # asserting delete_action_files_from_pack called i.e. cloned files are cleaned up
        self.assertTrue(mock_clean_files.called)
        # retrieving oringinal ACTION_17 from db which is reregistered after exception
        dest_get_resp = self.__do_get_actions_by_url_parameter(
            "name", ACTION_17["name"]
        )
        self.assertEqual(dest_get_resp.status_int, 200)
        expected_runner_type = ACTION_17["runner_type"]
        actual_runner_type = dest_get_resp.json[0]["runner_type"]
        # asserting ACTION_17 has original runner type
        self.assertEqual(actual_runner_type, expected_runner_type)
        expeted_parameters = ACTION_17["parameters"]
        actual_parameters = dest_get_resp.json[0]["parameters"]
        # asserting ACTION_17 has original parameters
        self.assertDictEqual(actual_parameters, expeted_parameters)
        self.__do_delete(self.__get_action_id(source_post_resp))
        self.__do_delete(dest_get_resp.json[0]["id"])

    def _insert_mock_models(self):
        action_1_id = self.__get_action_id(self.__do_post(ACTION_1))
        action_2_id = self.__get_action_id(self.__do_post(ACTION_2))

        return [action_1_id, action_2_id]

    def _do_delete(self, action_id, expect_errors=False):
        return self.__do_delete(action_id=action_id, expect_errors=expect_errors)

    @staticmethod
    def __get_action_id(resp):
        return resp.json["id"]

    @staticmethod
    def __get_action_name(resp):
        return resp.json["name"]

    @staticmethod
    def __get_action_tags(resp):
        return resp.json["tags"]

    @staticmethod
    def __get_action_id_and_additional_attribute(resp, attribute):
        return resp.json["id"], resp.json[attribute]

    def __do_get_one(self, action_id, expect_errors=False):
        return self.app.get("/v1/actions/%s" % action_id, expect_errors=expect_errors)

    def __do_get_actions_by_url_parameter(self, filter, value, expect_errors=False):
        return self.app.get(
            "/v1/actions?%s=%s" % (filter, value), expect_errors=expect_errors
        )

    def __do_post(self, action, expect_errors=False):
        return self.app.post_json("/v1/actions", action, expect_errors=expect_errors)

    def __do_put(self, action_id, action, expect_errors=False):
        return self.app.put_json(
            "/v1/actions/%s" % action_id, action, expect_errors=expect_errors
        )

    def __do_delete(self, action_id, expect_errors=False):
        return self.app.delete(
            "/v1/actions/%s" % action_id, expect_errors=expect_errors
        )

    def __do_delete_action_with_files(self, options, action_id, expect_errors=False):
        return self.app.delete_json(
            "/v1/actions/%s" % action_id,
            options,
            expect_errors=expect_errors,
        )

    def __do_clone(
        self,
        dest_data,
        ref_or_id,
        expect_errors=False,
    ):
        return self.app.post_json(
            "/v1/actions/%s/clone" % (ref_or_id),
            dest_data,
            expect_errors=expect_errors,
        )

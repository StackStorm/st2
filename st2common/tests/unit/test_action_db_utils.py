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

from __future__ import absolute_import
import copy
import uuid

import mock

from st2common.exceptions.db import StackStormDBObjectNotFoundError
from st2common.transport.publishers import PoolPublisher
from st2common.models.api.action import RunnerTypeAPI
from st2common.models.db.action import ActionDB
from st2common.models.db.liveaction import LiveActionDB
from st2common.models.system.common import ResourceReference
from st2common.persistence.action import Action
from st2common.persistence.liveaction import LiveAction
from st2common.persistence.runner import RunnerType
from st2common.transport.liveaction import LiveActionPublisher
from st2common.util.date import get_datetime_utc_now
import st2common.util.action_db as action_db_utils
from st2tests.base import DbTestCase


@mock.patch.object(PoolPublisher, "publish", mock.MagicMock())
class ActionDBUtilsTestCase(DbTestCase):
    runnertype_db = None
    action_db = None
    liveaction_db = None

    @classmethod
    def setUpClass(cls):
        super(ActionDBUtilsTestCase, cls).setUpClass()
        ActionDBUtilsTestCase._setup_test_models()

    def test_get_runnertype_nonexisting(self):
        # By id.
        self.assertRaises(
            StackStormDBObjectNotFoundError,
            action_db_utils.get_runnertype_by_id,
            "somedummyrunnerid",
        )
        # By name.
        self.assertRaises(
            StackStormDBObjectNotFoundError,
            action_db_utils.get_runnertype_by_name,
            "somedummyrunnername",
        )

    def test_get_runnertype_existing(self):
        # Lookup by id and verify name equals.
        runner = action_db_utils.get_runnertype_by_id(
            ActionDBUtilsTestCase.runnertype_db.id
        )
        self.assertEqual(runner.name, ActionDBUtilsTestCase.runnertype_db.name)
        # Lookup by name and verify id equals.
        runner = action_db_utils.get_runnertype_by_name(
            ActionDBUtilsTestCase.runnertype_db.name
        )
        self.assertEqual(runner.id, ActionDBUtilsTestCase.runnertype_db.id)

    def test_get_action_nonexisting(self):
        # By id.
        self.assertRaises(
            StackStormDBObjectNotFoundError,
            action_db_utils.get_action_by_id,
            "somedummyactionid",
        )
        # By ref.
        action = action_db_utils.get_action_by_ref("packaintexist.somedummyactionname")
        self.assertIsNone(action)

    def test_get_action_existing(self):
        # Lookup by id and verify name equals
        action = action_db_utils.get_action_by_id(ActionDBUtilsTestCase.action_db.id)
        self.assertEqual(action.name, ActionDBUtilsTestCase.action_db.name)
        # Lookup by reference as string.
        action_ref = ResourceReference.to_string_reference(
            pack=ActionDBUtilsTestCase.action_db.pack,
            name=ActionDBUtilsTestCase.action_db.name,
        )
        action = action_db_utils.get_action_by_ref(action_ref)
        self.assertEqual(action.id, ActionDBUtilsTestCase.action_db.id)

    def test_get_actionexec_nonexisting(self):
        # By id.
        self.assertRaises(
            StackStormDBObjectNotFoundError,
            action_db_utils.get_liveaction_by_id,
            "somedummyactionexecid",
        )

    def test_get_actionexec_existing(self):
        liveaction = action_db_utils.get_liveaction_by_id(
            ActionDBUtilsTestCase.liveaction_db.id
        )
        self.assertEqual(liveaction, ActionDBUtilsTestCase.liveaction_db)

    @mock.patch.object(LiveActionPublisher, "publish_state", mock.MagicMock())
    def test_update_liveaction_with_incorrect_output_schema(self):
        liveaction_db = LiveActionDB()
        liveaction_db.status = "initializing"
        liveaction_db.start_timestamp = get_datetime_utc_now()
        liveaction_db.action = ResourceReference(
            name=ActionDBUtilsTestCase.action_db.name,
            pack=ActionDBUtilsTestCase.action_db.pack,
        ).ref
        params = {
            "actionstr": "foo",
            "some_key_that_aint_exist_in_action_or_runner": "bar",
            "runnerint": 555,
        }
        liveaction_db.parameters = params
        runner = mock.MagicMock()
        runner.output_schema = {"notaparam": {"type": "boolean"}}
        liveaction_db.runner = runner
        liveaction_db = LiveAction.add_or_update(liveaction_db)
        origliveaction_db = copy.copy(liveaction_db)

        now = get_datetime_utc_now()
        status = "succeeded"
        result = {"result": "Work is done."}
        context = {"third_party_id": uuid.uuid4().hex}
        newliveaction_db = action_db_utils.update_liveaction_status(
            status=status,
            result=result,
            context=context,
            end_timestamp=now,
            liveaction_id=liveaction_db.id,
        )

        self.assertEqual(origliveaction_db.id, newliveaction_db.id)
        self.assertEqual(newliveaction_db.status, status)
        self.assertEqual(newliveaction_db.result, result)
        self.assertDictEqual(newliveaction_db.context, context)
        self.assertEqual(newliveaction_db.end_timestamp, now)

    @mock.patch.object(LiveActionPublisher, "publish_state", mock.MagicMock())
    def test_update_liveaction_status(self):
        liveaction_db = LiveActionDB()
        liveaction_db.status = "initializing"
        liveaction_db.start_timestamp = get_datetime_utc_now()
        liveaction_db.action = ResourceReference(
            name=ActionDBUtilsTestCase.action_db.name,
            pack=ActionDBUtilsTestCase.action_db.pack,
        ).ref
        params = {
            "actionstr": "foo",
            "some_key_that_aint_exist_in_action_or_runner": "bar",
            "runnerint": 555,
        }
        liveaction_db.parameters = params
        liveaction_db = LiveAction.add_or_update(liveaction_db)
        origliveaction_db = copy.copy(liveaction_db)

        # Update by id.
        newliveaction_db = action_db_utils.update_liveaction_status(
            status="running", liveaction_id=liveaction_db.id
        )

        # Verify id didn't change.
        self.assertEqual(origliveaction_db.id, newliveaction_db.id)
        self.assertEqual(newliveaction_db.status, "running")

        # Verify that state is published.
        self.assertTrue(LiveActionPublisher.publish_state.called)
        LiveActionPublisher.publish_state.assert_called_once_with(
            newliveaction_db, "running"
        )

        # Update status, result, context, and end timestamp.
        now = get_datetime_utc_now()
        status = "succeeded"
        result = {"result": "Work is done."}
        context = {"third_party_id": uuid.uuid4().hex}
        newliveaction_db = action_db_utils.update_liveaction_status(
            status=status,
            result=result,
            context=context,
            end_timestamp=now,
            liveaction_id=liveaction_db.id,
        )

        self.assertEqual(origliveaction_db.id, newliveaction_db.id)
        self.assertEqual(newliveaction_db.status, status)
        self.assertEqual(newliveaction_db.result, result)
        self.assertDictEqual(newliveaction_db.context, context)
        self.assertEqual(newliveaction_db.end_timestamp, now)

    @mock.patch.object(LiveActionPublisher, "publish_state", mock.MagicMock())
    def test_update_canceled_liveaction(self):
        liveaction_db = LiveActionDB()
        liveaction_db.status = "initializing"
        liveaction_db.start_timestamp = get_datetime_utc_now()
        liveaction_db.action = ResourceReference(
            name=ActionDBUtilsTestCase.action_db.name,
            pack=ActionDBUtilsTestCase.action_db.pack,
        ).ref
        params = {
            "actionstr": "foo",
            "some_key_that_aint_exist_in_action_or_runner": "bar",
            "runnerint": 555,
        }
        liveaction_db.parameters = params
        liveaction_db = LiveAction.add_or_update(liveaction_db)
        origliveaction_db = copy.copy(liveaction_db)

        # Update by id.
        newliveaction_db = action_db_utils.update_liveaction_status(
            status="running", liveaction_id=liveaction_db.id
        )

        # Verify id didn't change.
        self.assertEqual(origliveaction_db.id, newliveaction_db.id)
        self.assertEqual(newliveaction_db.status, "running")

        # Verify that state is published.
        self.assertTrue(LiveActionPublisher.publish_state.called)
        LiveActionPublisher.publish_state.assert_called_once_with(
            newliveaction_db, "running"
        )

        # Cancel liveaction.
        now = get_datetime_utc_now()
        status = "canceled"
        newliveaction_db = action_db_utils.update_liveaction_status(
            status=status, end_timestamp=now, liveaction_id=liveaction_db.id
        )
        self.assertEqual(origliveaction_db.id, newliveaction_db.id)
        self.assertEqual(newliveaction_db.status, status)
        self.assertEqual(newliveaction_db.end_timestamp, now)

        # Since liveaction has already been canceled, check that anymore update of
        # status, result, context, and end timestamp are not processed.
        now = get_datetime_utc_now()
        status = "succeeded"
        result = "Work is done."
        context = {"third_party_id": uuid.uuid4().hex}
        newliveaction_db = action_db_utils.update_liveaction_status(
            status=status,
            result=result,
            context=context,
            end_timestamp=now,
            liveaction_id=liveaction_db.id,
        )

        self.assertEqual(origliveaction_db.id, newliveaction_db.id)
        self.assertEqual(newliveaction_db.status, "canceled")
        self.assertNotEqual(newliveaction_db.result, result)
        self.assertNotEqual(newliveaction_db.context, context)
        self.assertNotEqual(newliveaction_db.end_timestamp, now)

    @mock.patch.object(LiveActionPublisher, "publish_state", mock.MagicMock())
    def test_update_liveaction_result_with_dotted_key(self):
        liveaction_db = LiveActionDB()
        liveaction_db.status = "initializing"
        liveaction_db.start_timestamp = get_datetime_utc_now()
        liveaction_db.action = ResourceReference(
            name=ActionDBUtilsTestCase.action_db.name,
            pack=ActionDBUtilsTestCase.action_db.pack,
        ).ref
        params = {
            "actionstr": "foo",
            "some_key_that_aint_exist_in_action_or_runner": "bar",
            "runnerint": 555,
        }
        liveaction_db.parameters = params
        liveaction_db = LiveAction.add_or_update(liveaction_db)
        origliveaction_db = copy.copy(liveaction_db)

        # Update by id.
        newliveaction_db = action_db_utils.update_liveaction_status(
            status="running", liveaction_id=liveaction_db.id
        )

        # Verify id didn't change.
        self.assertEqual(origliveaction_db.id, newliveaction_db.id)
        self.assertEqual(newliveaction_db.status, "running")

        # Verify that state is published.
        self.assertTrue(LiveActionPublisher.publish_state.called)
        LiveActionPublisher.publish_state.assert_called_once_with(
            newliveaction_db, "running"
        )

        now = get_datetime_utc_now()
        status = "succeeded"
        result = {"a": 1, "b": True, "a.b.c": "abc"}
        context = {"third_party_id": uuid.uuid4().hex}
        newliveaction_db = action_db_utils.update_liveaction_status(
            status=status,
            result=result,
            context=context,
            end_timestamp=now,
            liveaction_id=liveaction_db.id,
        )

        self.assertEqual(origliveaction_db.id, newliveaction_db.id)
        self.assertEqual(newliveaction_db.status, status)
        self.assertIn("a.b.c", list(result.keys()))
        self.assertDictEqual(newliveaction_db.result, result)
        self.assertDictEqual(newliveaction_db.context, context)
        self.assertEqual(newliveaction_db.end_timestamp, now)

    @mock.patch.object(LiveActionPublisher, "publish_state", mock.MagicMock())
    def test_update_LiveAction_status_invalid(self):
        liveaction_db = LiveActionDB()
        liveaction_db.status = "initializing"
        liveaction_db.start_timestamp = get_datetime_utc_now()
        liveaction_db.action = ResourceReference(
            name=ActionDBUtilsTestCase.action_db.name,
            pack=ActionDBUtilsTestCase.action_db.pack,
        ).ref
        params = {
            "actionstr": "foo",
            "some_key_that_aint_exist_in_action_or_runner": "bar",
            "runnerint": 555,
        }
        liveaction_db.parameters = params
        liveaction_db = LiveAction.add_or_update(liveaction_db)

        # Update by id.
        self.assertRaises(
            ValueError,
            action_db_utils.update_liveaction_status,
            status="mea culpa",
            liveaction_id=liveaction_db.id,
        )

        # Verify that state is not published.
        self.assertFalse(LiveActionPublisher.publish_state.called)

    @mock.patch.object(LiveActionPublisher, "publish_state", mock.MagicMock())
    def test_update_same_liveaction_status(self):
        liveaction_db = LiveActionDB()
        liveaction_db.status = "requested"
        liveaction_db.start_timestamp = get_datetime_utc_now()
        liveaction_db.action = ResourceReference(
            name=ActionDBUtilsTestCase.action_db.name,
            pack=ActionDBUtilsTestCase.action_db.pack,
        ).ref
        params = {
            "actionstr": "foo",
            "some_key_that_aint_exist_in_action_or_runner": "bar",
            "runnerint": 555,
        }
        liveaction_db.parameters = params
        liveaction_db = LiveAction.add_or_update(liveaction_db)
        origliveaction_db = copy.copy(liveaction_db)

        # Update by id.
        newliveaction_db = action_db_utils.update_liveaction_status(
            status="requested", liveaction_id=liveaction_db.id
        )

        # Verify id didn't change.
        self.assertEqual(origliveaction_db.id, newliveaction_db.id)
        self.assertEqual(newliveaction_db.status, "requested")

        # Verify that state is not published.
        self.assertFalse(LiveActionPublisher.publish_state.called)

    def test_get_args(self):
        params = {"actionstr": "foo", "actionint": 20, "runnerint": 555}
        pos_args, named_args = action_db_utils.get_args(
            params, ActionDBUtilsTestCase.action_db
        )
        self.assertListEqual(
            pos_args,
            ["20", "", "foo", "", "", "", "", ""],
            "Positional args not parsed correctly.",
        )
        self.assertNotIn("actionint", named_args)
        self.assertNotIn("actionstr", named_args)
        self.assertEqual(named_args.get("runnerint"), 555)

        # Test serialization for different positional argument types and values
        # Test all the values provided
        params = {
            "actionint": 1,
            "actionfloat": 1.5,
            "actionstr": "string value",
            "actionbool": True,
            "actionarray": ["foo", "bar", "baz", "qux"],
            "actionlist": ["foo", "bar", "baz"],
            "actionobject": {"a": 1, "b": "2"},
        }
        expected_pos_args = [
            "1",
            "1.5",
            "string value",
            "1",
            "foo,bar,baz,qux",
            "foo,bar,baz",
            '{"a":1,"b":"2"}',
            "",
        ]
        pos_args, _ = action_db_utils.get_args(params, ActionDBUtilsTestCase.action_db)
        self.assertListEqual(
            pos_args,
            expected_pos_args,
            "Positional args not parsed / serialized correctly.",
        )

        params = {
            "actionint": 1,
            "actionfloat": 1.5,
            "actionstr": "string value",
            "actionbool": False,
            "actionarray": [],
            "actionlist": [],
            "actionobject": {"a": 1, "b": "2"},
        }
        expected_pos_args = [
            "1",
            "1.5",
            "string value",
            "0",
            "",
            "",
            '{"a":1,"b":"2"}',
            "",
        ]
        pos_args, _ = action_db_utils.get_args(params, ActionDBUtilsTestCase.action_db)
        self.assertListEqual(
            pos_args,
            expected_pos_args,
            "Positional args not parsed / serialized correctly.",
        )

        # Test none values
        params = {
            "actionint": None,
            "actionfloat": None,
            "actionstr": None,
            "actionbool": None,
            "actionarray": None,
            "actionlist": None,
            "actionobject": None,
        }
        expected_pos_args = ["", "", "", "", "", "", "", ""]
        pos_args, _ = action_db_utils.get_args(params, ActionDBUtilsTestCase.action_db)
        self.assertListEqual(
            pos_args,
            expected_pos_args,
            "Positional args not parsed / serialized correctly.",
        )

        # Test unicode values
        params = {
            "actionstr": "bar č š hello đ č p ž Ž a 💩😁",
            "actionint": 20,
            "runnerint": 555,
        }
        expected_pos_args = [
            "20",
            "",
            "bar č š hello đ č p ž Ž a 💩😁",
            "",
            "",
            "",
            "",
            "",
        ]
        pos_args, named_args = action_db_utils.get_args(
            params, ActionDBUtilsTestCase.action_db
        )
        self.assertListEqual(
            pos_args, expected_pos_args, "Positional args not parsed correctly."
        )

        # Test arrays and lists with values of different types
        params = {
            "actionarray": [None, False, 1, 4.2e1, "1e3", "foo"],
            "actionlist": [None, False, 1, 73e-2, "1e2", "bar"],
        }
        expected_pos_args = [
            "",
            "",
            "",
            "",
            "None,False,1,42.0,1e3,foo",
            "None,False,1,0.73,1e2,bar",
            "",
            "",
        ]
        pos_args, _ = action_db_utils.get_args(params, ActionDBUtilsTestCase.action_db)
        self.assertListEqual(
            pos_args,
            expected_pos_args,
            "Positional args not parsed / serialized correctly.",
        )

        self.assertNotIn("actionint", named_args)
        self.assertNotIn("actionstr", named_args)
        self.assertEqual(named_args.get("runnerint"), 555)

    @classmethod
    def _setup_test_models(cls):
        ActionDBUtilsTestCase.setup_runner()
        ActionDBUtilsTestCase.setup_action_models()

    @classmethod
    def setup_runner(cls):
        test_runner = {
            "name": "test-runner",
            "description": "A test runner.",
            "enabled": True,
            "runner_parameters": {
                "runnerstr": {
                    "description": "Foo str param.",
                    "type": "string",
                    "default": "defaultfoo",
                },
                "runnerint": {"description": "Foo int param.", "type": "number"},
                "runnerdummy": {
                    "description": "Dummy param.",
                    "type": "string",
                    "default": "runnerdummy",
                },
            },
            "runner_module": "tests.test_runner",
        }
        runnertype_api = RunnerTypeAPI(**test_runner)
        ActionDBUtilsTestCase.runnertype_db = RunnerType.add_or_update(
            RunnerTypeAPI.to_model(runnertype_api)
        )

    @classmethod
    @mock.patch.object(PoolPublisher, "publish", mock.MagicMock())
    def setup_action_models(cls):
        pack = "wolfpack"
        name = "action-1"
        parameters = {
            "actionint": {"type": "number", "default": 10, "position": 0},
            "actionfloat": {"type": "float", "required": False, "position": 1},
            "actionstr": {"type": "string", "required": True, "position": 2},
            "actionbool": {"type": "boolean", "required": False, "position": 3},
            "actionarray": {"type": "array", "required": False, "position": 4},
            "actionlist": {"type": "list", "required": False, "position": 5},
            "actionobject": {"type": "object", "required": False, "position": 6},
            "actionnull": {"type": "null", "required": False, "position": 7},
            "runnerdummy": {"type": "string", "default": "actiondummy"},
        }
        action_db = ActionDB(
            pack=pack,
            name=name,
            description="awesomeness",
            enabled=True,
            ref=ResourceReference(name=name, pack=pack).ref,
            entry_point="",
            runner_type={"name": "test-runner"},
            parameters=parameters,
        )
        ActionDBUtilsTestCase.action_db = Action.add_or_update(action_db)

        liveaction_db = LiveActionDB()
        liveaction_db.status = "initializing"
        liveaction_db.start_timestamp = get_datetime_utc_now()
        liveaction_db.action = ActionDBUtilsTestCase.action_db.ref
        params = {
            "actionstr": "foo",
            "some_key_that_aint_exist_in_action_or_runner": "bar",
            "runnerint": 555,
        }
        liveaction_db.parameters = params
        ActionDBUtilsTestCase.liveaction_db = LiveAction.add_or_update(liveaction_db)

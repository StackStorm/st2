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
import datetime

import bson
import mock

# This import must be early for import-time side-effects.
from st2tests.base import CleanDbTestCase

from st2actions.notifier.notifier import Notifier
from st2common.constants.action import LIVEACTION_COMPLETED_STATES
from st2common.constants.action import LIVEACTION_STATUSES
from st2common.constants.triggers import INTERNAL_TRIGGER_TYPES
from st2common.models.api.action import LiveActionAPI
from st2common.models.db.action import ActionDB
from st2common.models.db.execution import ActionExecutionDB
from st2common.models.db.liveaction import LiveActionDB
from st2common.models.db.notification import NotificationSchema
from st2common.models.db.notification import NotificationSubSchema
from st2common.models.db.runner import RunnerTypeDB
from st2common.persistence.action import Action
from st2common.persistence.liveaction import LiveAction
from st2common.persistence.policy import Policy
from st2common.models.system.common import ResourceReference
from st2common.util import date as date_utils
from st2common.util import isotime

ACTION_TRIGGER_TYPE = INTERNAL_TRIGGER_TYPES["action"][0]
NOTIFY_TRIGGER_TYPE = INTERNAL_TRIGGER_TYPES["action"][1]
MOCK_EXECUTION = ActionExecutionDB(
    id=bson.ObjectId(), result={"stdout": "stuff happens"}
)


class NotifierTestCase(CleanDbTestCase):
    class MockDispatcher(object):
        def __init__(self, tester):
            self.tester = tester
            self.notify_trigger = ResourceReference.to_string_reference(
                pack=NOTIFY_TRIGGER_TYPE["pack"], name=NOTIFY_TRIGGER_TYPE["name"]
            )
            self.action_trigger = ResourceReference.to_string_reference(
                pack=ACTION_TRIGGER_TYPE["pack"], name=ACTION_TRIGGER_TYPE["name"]
            )

        def dispatch(self, *args, **kwargs):
            try:
                self.tester.assertEqual(len(args), 1)
                self.tester.assertTrue("payload" in kwargs)
                payload = kwargs["payload"]

                if args[0] == self.notify_trigger:
                    self.tester.assertEqual(payload["status"], "succeeded")
                    self.tester.assertTrue("execution_id" in payload)
                    self.tester.assertEqual(
                        payload["execution_id"], str(MOCK_EXECUTION.id)
                    )
                    self.tester.assertTrue("start_timestamp" in payload)
                    self.tester.assertTrue("end_timestamp" in payload)
                    self.tester.assertEqual("core.local", payload["action_ref"])
                    self.tester.assertEqual("Action succeeded.", payload["message"])
                    self.tester.assertTrue("data" in payload)
                    self.tester.assertTrue("local-shell-cmd", payload["runner_ref"])

                if args[0] == self.action_trigger:
                    self.tester.assertEqual(payload["status"], "succeeded")
                    self.tester.assertTrue("execution_id" in payload)
                    self.tester.assertEqual(
                        payload["execution_id"], str(MOCK_EXECUTION.id)
                    )
                    self.tester.assertTrue("start_timestamp" in payload)
                    self.tester.assertEqual("core.local", payload["action_name"])
                    self.tester.assertEqual("core.local", payload["action_ref"])
                    self.tester.assertTrue("result" in payload)
                    self.tester.assertTrue("parameters" in payload)
                    self.tester.assertTrue("local-shell-cmd", payload["runner_ref"])

            except Exception:
                self.tester.fail("Test failed")

    @mock.patch(
        "st2common.util.action_db.get_action_by_ref",
        mock.MagicMock(
            return_value=ActionDB(
                pack="core",
                name="local",
                runner_type={"name": "local-shell-cmd"},
                parameters={},
            )
        ),
    )
    @mock.patch(
        "st2common.util.action_db.get_runnertype_by_name",
        mock.MagicMock(return_value=RunnerTypeDB(name="foo", runner_parameters={})),
    )
    @mock.patch.object(
        Action,
        "get_by_ref",
        mock.MagicMock(return_value={"runner_type": {"name": "local-shell-cmd"}}),
    )
    @mock.patch.object(Policy, "query", mock.MagicMock(return_value=[]))
    @mock.patch.object(Notifier, "_get_trace_context", mock.MagicMock(return_value={}))
    def test_notify_triggers(self):
        liveaction_db = LiveActionDB(action="core.local")
        liveaction_db.id = bson.ObjectId()
        liveaction_db.description = ""
        liveaction_db.status = "succeeded"
        liveaction_db.parameters = {}
        on_success = NotificationSubSchema(message="Action succeeded.")
        on_failure = NotificationSubSchema(message="Action failed.")
        liveaction_db.notify = NotificationSchema(
            on_success=on_success, on_failure=on_failure
        )
        liveaction_db.start_timestamp = date_utils.get_datetime_utc_now()
        liveaction_db.end_timestamp = (
            liveaction_db.start_timestamp + datetime.timedelta(seconds=50)
        )
        LiveAction.add_or_update(liveaction_db)

        execution = MOCK_EXECUTION
        execution.liveaction = vars(LiveActionAPI.from_model(liveaction_db))
        execution.status = liveaction_db.status

        dispatcher = NotifierTestCase.MockDispatcher(self)
        notifier = Notifier(connection=None, queues=[], trigger_dispatcher=dispatcher)
        notifier.process(execution)

    @mock.patch(
        "st2common.util.action_db.get_action_by_ref",
        mock.MagicMock(
            return_value=ActionDB(
                pack="core",
                name="local",
                runner_type={"name": "local-shell-cmd"},
                parameters={},
            )
        ),
    )
    @mock.patch(
        "st2common.util.action_db.get_runnertype_by_name",
        mock.MagicMock(return_value=RunnerTypeDB(name="foo", runner_parameters={})),
    )
    @mock.patch.object(
        Action,
        "get_by_ref",
        mock.MagicMock(return_value={"runner_type": {"name": "local-shell-cmd"}}),
    )
    @mock.patch.object(Policy, "query", mock.MagicMock(return_value=[]))
    @mock.patch.object(Notifier, "_get_trace_context", mock.MagicMock(return_value={}))
    def test_notify_triggers_end_timestamp_none(self):
        liveaction_db = LiveActionDB(action="core.local")
        liveaction_db.id = bson.ObjectId()
        liveaction_db.description = ""
        liveaction_db.status = "succeeded"
        liveaction_db.parameters = {}
        on_success = NotificationSubSchema(message="Action succeeded.")
        on_failure = NotificationSubSchema(message="Action failed.")
        liveaction_db.notify = NotificationSchema(
            on_success=on_success, on_failure=on_failure
        )
        liveaction_db.start_timestamp = date_utils.get_datetime_utc_now()

        # This tests for end_timestamp being set to None, which can happen when a policy cancels
        # a request.
        # The assertions within "MockDispatcher.dispatch" will validate that the underlying code
        # handles this properly, so all we need to do is keep the call to "notifier.process" below
        liveaction_db.end_timestamp = None
        LiveAction.add_or_update(liveaction_db)

        execution = MOCK_EXECUTION
        execution.liveaction = vars(LiveActionAPI.from_model(liveaction_db))
        execution.status = liveaction_db.status

        dispatcher = NotifierTestCase.MockDispatcher(self)
        notifier = Notifier(connection=None, queues=[], trigger_dispatcher=dispatcher)
        notifier.process(execution)

    @mock.patch(
        "st2common.util.action_db.get_action_by_ref",
        mock.MagicMock(
            return_value=ActionDB(
                pack="core", name="local", runner_type={"name": "local-shell-cmd"}
            )
        ),
    )
    @mock.patch(
        "st2common.util.action_db.get_runnertype_by_name",
        mock.MagicMock(
            return_value=RunnerTypeDB(
                name="foo", runner_parameters={"runner_foo": "foo"}
            )
        ),
    )
    @mock.patch.object(
        Action,
        "get_by_ref",
        mock.MagicMock(return_value={"runner_type": {"name": "local-shell-cmd"}}),
    )
    @mock.patch.object(Policy, "query", mock.MagicMock(return_value=[]))
    @mock.patch.object(
        Notifier, "_post_generic_trigger", mock.MagicMock(return_value=True)
    )
    @mock.patch.object(Notifier, "_get_trace_context", mock.MagicMock(return_value={}))
    @mock.patch("st2common.transport.reactor.TriggerDispatcher.dispatch")
    def test_notify_triggers_jinja_patterns(self, dispatch):
        liveaction_db = LiveActionDB(action="core.local")
        liveaction_db.id = bson.ObjectId()
        liveaction_db.description = ""
        liveaction_db.status = "succeeded"
        liveaction_db.parameters = {"cmd": "mamma mia", "runner_foo": "foo"}
        on_success = NotificationSubSchema(
            message="Command {{action_parameters.cmd}} succeeded.",
            data={"stdout": "{{action_results.stdout}}"},
        )
        liveaction_db.notify = NotificationSchema(on_success=on_success)
        liveaction_db.start_timestamp = date_utils.get_datetime_utc_now()
        liveaction_db.end_timestamp = (
            liveaction_db.start_timestamp + datetime.timedelta(seconds=50)
        )

        LiveAction.add_or_update(liveaction_db)

        execution = MOCK_EXECUTION
        execution.liveaction = vars(LiveActionAPI.from_model(liveaction_db))
        execution.status = liveaction_db.status

        notifier = Notifier(connection=None, queues=[])
        notifier.process(execution)
        exp = {
            "status": "succeeded",
            "start_timestamp": isotime.format(liveaction_db.start_timestamp),
            "route": "notify.default",
            "runner_ref": "local-shell-cmd",
            "channel": "notify.default",
            "message": "Command mamma mia succeeded.",
            "data": {"result": "{}", "stdout": "stuff happens"},
            "action_ref": "core.local",
            "execution_id": str(MOCK_EXECUTION.id),
            "end_timestamp": isotime.format(liveaction_db.end_timestamp),
        }
        dispatch.assert_called_once_with(
            "core.st2.generic.notifytrigger", payload=exp, trace_context={}
        )
        notifier.process(execution)

    @mock.patch.object(
        Notifier, "_get_runner_ref", mock.MagicMock(return_value="local-shell-cmd")
    )
    @mock.patch.object(Notifier, "_get_trace_context", mock.MagicMock(return_value={}))
    @mock.patch("st2common.transport.reactor.TriggerDispatcher.dispatch")
    def test_post_generic_trigger_emit_when_default_value_is_used(self, dispatch):
        for status in LIVEACTION_STATUSES:
            liveaction_db = LiveActionDB(action="core.local")
            liveaction_db.status = status
            execution = MOCK_EXECUTION
            execution.liveaction = vars(LiveActionAPI.from_model(liveaction_db))
            execution.status = liveaction_db.status

            notifier = Notifier(connection=None, queues=[])
            notifier._post_generic_trigger(liveaction_db, execution)

            if status in LIVEACTION_COMPLETED_STATES:
                exp = {
                    "status": status,
                    "start_timestamp": str(liveaction_db.start_timestamp),
                    "result": {},
                    "parameters": {},
                    "action_ref": "core.local",
                    "runner_ref": "local-shell-cmd",
                    "execution_id": str(MOCK_EXECUTION.id),
                    "action_name": "core.local",
                }
                dispatch.assert_called_with(
                    "core.st2.generic.actiontrigger", payload=exp, trace_context={}
                )

        self.assertEqual(dispatch.call_count, len(LIVEACTION_COMPLETED_STATES))

    @mock.patch(
        "oslo_config.cfg.CONF.action_sensor",
        mock.MagicMock(emit_when=["scheduled", "pending", "abandoned"]),
    )
    @mock.patch.object(
        Notifier, "_get_runner_ref", mock.MagicMock(return_value="local-shell-cmd")
    )
    @mock.patch.object(Notifier, "_get_trace_context", mock.MagicMock(return_value={}))
    @mock.patch("st2common.transport.reactor.TriggerDispatcher.dispatch")
    def test_post_generic_trigger_with_emit_condition(self, dispatch):
        for status in LIVEACTION_STATUSES:
            liveaction_db = LiveActionDB(action="core.local")
            liveaction_db.status = status
            execution = MOCK_EXECUTION
            execution.liveaction = vars(LiveActionAPI.from_model(liveaction_db))
            execution.status = liveaction_db.status

            notifier = Notifier(connection=None, queues=[])
            notifier._post_generic_trigger(liveaction_db, execution)

            if status in ["scheduled", "pending", "abandoned"]:
                exp = {
                    "status": status,
                    "start_timestamp": str(liveaction_db.start_timestamp),
                    "result": {},
                    "parameters": {},
                    "action_ref": "core.local",
                    "runner_ref": "local-shell-cmd",
                    "execution_id": str(MOCK_EXECUTION.id),
                    "action_name": "core.local",
                }
                dispatch.assert_called_with(
                    "core.st2.generic.actiontrigger", payload=exp, trace_context={}
                )

        self.assertEqual(dispatch.call_count, 3)

    @mock.patch(
        "oslo_config.cfg.CONF.action_sensor.enable", mock.MagicMock(return_value=True)
    )
    @mock.patch.object(
        Notifier, "_get_runner_ref", mock.MagicMock(return_value="local-shell-cmd")
    )
    @mock.patch.object(Notifier, "_get_trace_context", mock.MagicMock(return_value={}))
    @mock.patch("st2common.transport.reactor.TriggerDispatcher.dispatch")
    @mock.patch("st2actions.notifier.notifier.LiveAction")
    @mock.patch(
        "st2actions.notifier.notifier.policy_service.apply_post_run_policies",
        mock.Mock(),
    )
    def test_process_post_generic_notify_trigger_on_completed_state_default(
        self, mock_LiveAction, mock_dispatch
    ):
        # Verify that generic action trigger is posted on all completed states when action sensor
        # is enabled
        for status in LIVEACTION_STATUSES:
            notifier = Notifier(connection=None, queues=[])

            liveaction_db = LiveActionDB(id=bson.ObjectId(), action="core.local")
            liveaction_db.status = status
            execution = MOCK_EXECUTION
            execution.liveaction = vars(LiveActionAPI.from_model(liveaction_db))
            execution.status = liveaction_db.status

            mock_LiveAction.get_by_id.return_value = liveaction_db

            notifier = Notifier(connection=None, queues=[])
            notifier.process(execution)

            if status in LIVEACTION_COMPLETED_STATES:
                exp = {
                    "status": status,
                    "start_timestamp": str(liveaction_db.start_timestamp),
                    "result": {},
                    "parameters": {},
                    "action_ref": "core.local",
                    "runner_ref": "local-shell-cmd",
                    "execution_id": str(MOCK_EXECUTION.id),
                    "action_name": "core.local",
                }
                mock_dispatch.assert_called_with(
                    "core.st2.generic.actiontrigger", payload=exp, trace_context={}
                )

        self.assertEqual(mock_dispatch.call_count, len(LIVEACTION_COMPLETED_STATES))

    @mock.patch(
        "oslo_config.cfg.CONF.action_sensor",
        mock.MagicMock(enable=True, emit_when=["scheduled", "pending", "abandoned"]),
    )
    @mock.patch.object(
        Notifier, "_get_runner_ref", mock.MagicMock(return_value="local-shell-cmd")
    )
    @mock.patch.object(Notifier, "_get_trace_context", mock.MagicMock(return_value={}))
    @mock.patch("st2common.transport.reactor.TriggerDispatcher.dispatch")
    @mock.patch("st2actions.notifier.notifier.LiveAction")
    @mock.patch(
        "st2actions.notifier.notifier.policy_service.apply_post_run_policies",
        mock.Mock(),
    )
    def test_process_post_generic_notify_trigger_on_custom_emit_when_states(
        self, mock_LiveAction, mock_dispatch
    ):
        # Verify that generic action trigger is posted on all completed states when action sensor
        # is enabled
        for status in LIVEACTION_STATUSES:
            notifier = Notifier(connection=None, queues=[])

            liveaction_db = LiveActionDB(id=bson.ObjectId(), action="core.local")
            liveaction_db.status = status
            execution = MOCK_EXECUTION
            execution.liveaction = vars(LiveActionAPI.from_model(liveaction_db))
            execution.status = liveaction_db.status

            mock_LiveAction.get_by_id.return_value = liveaction_db

            notifier = Notifier(connection=None, queues=[])
            notifier.process(execution)

            if status in ["scheduled", "pending", "abandoned"]:
                exp = {
                    "status": status,
                    "start_timestamp": str(liveaction_db.start_timestamp),
                    "result": {},
                    "parameters": {},
                    "action_ref": "core.local",
                    "runner_ref": "local-shell-cmd",
                    "execution_id": str(MOCK_EXECUTION.id),
                    "action_name": "core.local",
                }
                mock_dispatch.assert_called_with(
                    "core.st2.generic.actiontrigger", payload=exp, trace_context={}
                )

        self.assertEqual(mock_dispatch.call_count, 3)

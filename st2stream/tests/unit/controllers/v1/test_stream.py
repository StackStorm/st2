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

import mock

from oslo_config import cfg

from st2common.models.api.action import ActionAPI
from st2common.models.api.action import RunnerTypeAPI
from st2common.models.api.execution import ActionExecutionAPI
from st2common.models.api.execution import LiveActionAPI
from st2common.models.api.execution import ActionExecutionOutputAPI
from st2common.models.db.liveaction import LiveActionDB
from st2common.models.db.execution import ActionExecutionDB
from st2common.models.db.execution import ActionExecutionOutputDB
from st2common.persistence.action import Action, RunnerType
import st2common.stream.listener
from st2stream.controllers.v1 import stream
from st2tests.api import SUPER_SECRET_PARAMETER

from .base import FunctionalTest


RUNNER_TYPE_1 = {
    "description": "",
    "enabled": True,
    "name": "local-shell-cmd",
    "runner_module": "local_runner",
    "runner_parameters": {},
}

ACTION_1 = {
    "name": "st2.dummy.action1",
    "description": "test description",
    "enabled": True,
    "entry_point": "/tmp/test/action1.sh",
    "pack": "sixpack",
    "runner_type": "local-shell-cmd",
    "parameters": {
        "a": {"type": "string", "default": "abc"},
        "b": {"type": "number", "default": 123},
        "c": {"type": "number", "default": 123, "immutable": True},
        "d": {"type": "string", "secret": True},
    },
}

LIVE_ACTION_1 = {
    "action": "sixpack.st2.dummy.action1",
    "parameters": {
        "hosts": "localhost",
        "cmd": "uname -a",
        "d": SUPER_SECRET_PARAMETER,
    },
}

EXECUTION_1 = {
    "id": "598dbf0c0640fd54bffc688b",
    "action": {"ref": "sixpack.st2.dummy.action1"},
    "parameters": {
        "hosts": "localhost",
        "cmd": "uname -a",
        "d": SUPER_SECRET_PARAMETER,
    },
}

STDOUT_1 = {
    "execution_id": "598dbf0c0640fd54bffc688b",
    "action_ref": "dummy.action1",
    "output_type": "stdout",
}

STDERR_1 = {
    "execution_id": "598dbf0c0640fd54bffc688b",
    "action_ref": "dummy.action1",
    "output_type": "stderr",
}


class META(object):
    delivery_info = {}

    def __init__(self, exchange="some", routing_key="thing"):
        self.delivery_info["exchange"] = exchange
        self.delivery_info["routing_key"] = routing_key

    def ack(self):
        pass


class TestStreamController(FunctionalTest):
    @classmethod
    def setUpClass(cls):
        super(TestStreamController, cls).setUpClass()

        instance = RunnerTypeAPI(**RUNNER_TYPE_1)
        RunnerType.add_or_update(RunnerTypeAPI.to_model(instance))

        instance = ActionAPI(**ACTION_1)
        Action.add_or_update(ActionAPI.to_model(instance))

    @mock.patch.object(st2common.stream.listener, "listen", mock.Mock())
    @mock.patch("st2stream.controllers.v1.stream.DEFAULT_EVENTS_WHITELIST", None)
    def test_get_all(self):
        resp = stream.StreamController().get_all()
        self.assertEqual(resp._status, "200 OK")
        self.assertIn(
            ("Content-Type", "text/event-stream; charset=UTF-8"), resp._headerlist
        )

        listener = st2common.stream.listener.get_listener(name="stream")
        process = listener.processor(LiveActionAPI)

        message = None

        for message in resp._app_iter:
            message = message.decode("utf-8")
            if message != "\n":
                break
            process(LiveActionDB(**LIVE_ACTION_1), META())

        self.assertIn("event: some__thing", message)
        self.assertIn('data: {"', message)
        self.assertNotIn(SUPER_SECRET_PARAMETER, message)

    @mock.patch.object(st2common.stream.listener, "listen", mock.Mock())
    def test_get_all_with_filters(self):
        cfg.CONF.set_override(name="heartbeat", group="stream", override=0.02)

        listener = st2common.stream.listener.get_listener(name="stream")
        process_execution = listener.processor(ActionExecutionAPI)
        process_liveaction = listener.processor(LiveActionAPI)
        process_output = listener.processor(ActionExecutionOutputAPI)
        process_no_api_model = listener.processor()

        execution_api = ActionExecutionDB(**EXECUTION_1)
        liveaction_api = LiveActionDB(**LIVE_ACTION_1)
        output_api_stdout = ActionExecutionOutputDB(**STDOUT_1)
        output_api_stderr = ActionExecutionOutputDB(**STDERR_1)

        def dispatch_and_handle_mock_data(resp):
            received_messages_data = ""
            for index, message in enumerate(resp._app_iter):
                if message.strip():
                    received_messages_data += message.decode("utf-8")

                # Dispatch some mock events
                if index == 0:
                    meta = META("st2.execution", "create")
                    process_execution(execution_api, meta)
                elif index == 1:
                    meta = META("st2.execution", "update")
                    process_execution(execution_api, meta)
                elif index == 2:
                    meta = META("st2.execution", "delete")
                    process_execution(execution_api, meta)
                elif index == 3:
                    meta = META("st2.liveaction", "create")
                    process_liveaction(liveaction_api, meta)
                elif index == 4:
                    meta = META("st2.liveaction", "create")
                    process_liveaction(liveaction_api, meta)
                elif index == 5:
                    meta = META("st2.liveaction", "delete")
                    process_liveaction(liveaction_api, meta)
                elif index == 6:
                    meta = META("st2.liveaction", "delete")
                    process_liveaction(liveaction_api, meta)
                elif index == 7:
                    meta = META("st2.announcement", "chatops")
                    process_no_api_model({}, meta)
                elif index == 8:
                    meta = META("st2.execution.output", "create")
                    process_output(output_api_stdout, meta)
                elif index == 9:
                    meta = META("st2.execution.output", "create")
                    process_output(output_api_stderr, meta)
                elif index == 10:
                    meta = META("st2.announcement", "errbot")
                    process_no_api_model({}, meta)

                else:
                    break

            received_messages = received_messages_data.split("\n\n")
            received_messages = [message for message in received_messages if message]
            return received_messages

        # 1. Default filter - stdout and stderr messages should be excluded for backward
        # compatibility reasons
        resp = stream.StreamController().get_all()

        received_messages = dispatch_and_handle_mock_data(resp)
        self.assertEqual(len(received_messages), 9)
        self.assertIn("st2.execution__create", received_messages[0])
        self.assertIn("st2.liveaction__delete", received_messages[5])
        self.assertIn("st2.announcement__chatops", received_messages[7])
        self.assertIn("st2.announcement__errbot", received_messages[8])

        # 1. ?events= filter
        # No filter provided - all messages should be received
        stream.DEFAULT_EVENTS_WHITELIST = None
        resp = stream.StreamController().get_all()

        received_messages = dispatch_and_handle_mock_data(resp)
        self.assertEqual(len(received_messages), 11)
        self.assertIn("st2.execution__create", received_messages[0])
        self.assertIn("st2.announcement__chatops", received_messages[7])
        self.assertIn("st2.execution.output__create", received_messages[8])
        self.assertIn("st2.execution.output__create", received_messages[9])
        self.assertIn("st2.announcement__errbot", received_messages[10])

        # Filter provided, only three messages should be received
        events = ["st2.execution__create", "st2.liveaction__delete"]
        resp = stream.StreamController().get_all(events=events)

        received_messages = dispatch_and_handle_mock_data(resp)
        self.assertEqual(len(received_messages), 3)
        self.assertIn("st2.execution__create", received_messages[0])
        self.assertIn("st2.liveaction__delete", received_messages[1])
        self.assertIn("st2.liveaction__delete", received_messages[2])

        # Filter provided, only three messages should be received
        events = ["st2.liveaction__create", "st2.liveaction__delete"]
        resp = stream.StreamController().get_all(events=events)

        received_messages = dispatch_and_handle_mock_data(resp)
        self.assertEqual(len(received_messages), 4)
        self.assertIn("st2.liveaction__create", received_messages[0])
        self.assertIn("st2.liveaction__create", received_messages[1])
        self.assertIn("st2.liveaction__delete", received_messages[2])
        self.assertIn("st2.liveaction__delete", received_messages[3])

        # Glob filter
        events = ["st2.announcement__*"]
        resp = stream.StreamController().get_all(events=events)

        received_messages = dispatch_and_handle_mock_data(resp)
        self.assertEqual(len(received_messages), 2)
        self.assertIn("st2.announcement__chatops", received_messages[0])
        self.assertIn("st2.announcement__errbot", received_messages[1])

        # Filter provided
        events = ["st2.execution.output__create"]
        resp = stream.StreamController().get_all(events=events)

        received_messages = dispatch_and_handle_mock_data(resp)
        self.assertEqual(len(received_messages), 2)
        self.assertIn("st2.execution.output__create", received_messages[0])
        self.assertIn("st2.execution.output__create", received_messages[1])

        # Filter provided, invalid , no message should be received
        events = ["invalid1", "invalid2"]
        resp = stream.StreamController().get_all(events=events)

        received_messages = dispatch_and_handle_mock_data(resp)
        self.assertEqual(len(received_messages), 0)

        # 2. ?action_refs= filter
        action_refs = ["invalid1", "invalid2"]
        resp = stream.StreamController().get_all(action_refs=action_refs)

        received_messages = dispatch_and_handle_mock_data(resp)
        self.assertEqual(len(received_messages), 0)

        action_refs = ["dummy.action1"]
        resp = stream.StreamController().get_all(action_refs=action_refs)

        received_messages = dispatch_and_handle_mock_data(resp)
        self.assertEqual(len(received_messages), 2)

        # 3. ?execution_ids= filter
        execution_ids = ["invalid1", "invalid2"]
        resp = stream.StreamController().get_all(execution_ids=execution_ids)

        received_messages = dispatch_and_handle_mock_data(resp)
        self.assertEqual(len(received_messages), 0)

        execution_ids = [EXECUTION_1["id"]]
        resp = stream.StreamController().get_all(execution_ids=execution_ids)

        received_messages = dispatch_and_handle_mock_data(resp)
        self.assertEqual(len(received_messages), 5)

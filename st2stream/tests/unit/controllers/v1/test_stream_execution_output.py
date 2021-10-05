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

import json

import eventlet

from six.moves import http_client

from st2common.constants import action as action_constants
from st2common.models.db.execution import ActionExecutionDB
from st2common.models.db.execution import ActionExecutionOutputDB
from st2common.persistence.execution import ActionExecution
from st2common.persistence.execution import ActionExecutionOutput
from st2common.util import date as date_utils

from st2common.stream.listener import get_listener

from .base import FunctionalTest

__all__ = ["ActionExecutionOutputStreamControllerTestCase"]


class ActionExecutionOutputStreamControllerTestCase(FunctionalTest):
    def test_get_one_id_last_no_executions_in_the_database(self):
        ActionExecution.query().delete()

        resp = self.app.get("/v1/executions/last/output", expect_errors=True)
        self.assertEqual(resp.status_int, http_client.BAD_REQUEST)
        self.assertEqual(
            resp.json["faultstring"], "No executions found in the database"
        )

    def test_get_output_running_execution(self):
        # Retrieve listener instance to avoid race with listener connection not being established
        # early enough for tests to pass.
        # NOTE: This only affects tests where listeners are not pre-initialized.
        listener = get_listener(name="execution_output")
        eventlet.sleep(0.5)

        # Test the execution output API endpoint for execution which is running (blocking)
        status = action_constants.LIVEACTION_STATUS_RUNNING
        timestamp = date_utils.get_datetime_utc_now()
        action_execution_db = ActionExecutionDB(
            start_timestamp=timestamp,
            end_timestamp=timestamp,
            status=status,
            action={"ref": "core.local"},
            runner={"name": "local-shell-cmd"},
            liveaction={"ref": "foo"},
        )
        action_execution_db = ActionExecution.add_or_update(action_execution_db)

        output_params = dict(
            execution_id=str(action_execution_db.id),
            action_ref="core.local",
            runner_ref="dummy",
            timestamp=timestamp,
            output_type="stdout",
            data="stdout before start\n",
        )

        # Insert mock output object
        output_db = ActionExecutionOutputDB(**output_params)
        ActionExecutionOutput.add_or_update(output_db, publish=False)

        def insert_mock_data():
            output_params["data"] = "stdout mid 1\n"
            output_db = ActionExecutionOutputDB(**output_params)
            ActionExecutionOutput.add_or_update(output_db)

        # Since the API endpoint is blocking (connection is kept open until action finishes), we
        # spawn an eventlet which eventually finishes the action.
        def publish_action_finished(action_execution_db):
            # Insert mock output object
            output_params["data"] = "stdout pre finish 1\n"
            output_db = ActionExecutionOutputDB(**output_params)
            ActionExecutionOutput.add_or_update(output_db)

            eventlet.sleep(0.5)

            # Transition execution to completed state so the connection closes
            action_execution_db.status = action_constants.LIVEACTION_STATUS_SUCCEEDED
            action_execution_db = ActionExecution.add_or_update(action_execution_db)

        eventlet.spawn_after(0.2, insert_mock_data)
        eventlet.spawn_after(1.0, publish_action_finished, action_execution_db)

        # Retrieve data while execution is running - endpoint return new data once it's available
        # and block until the execution finishes
        resp = self.app.get(
            "/v1/executions/%s/output" % (str(action_execution_db.id)),
            expect_errors=False,
        )
        self.assertEqual(resp.status_int, 200)

        events = self._parse_response(resp.text)
        self.assertEqual(len(events), 4)
        self.assertEqual(events[0][1]["data"], "stdout before start\n")
        self.assertEqual(events[1][1]["data"], "stdout mid 1\n")
        self.assertEqual(events[2][1]["data"], "stdout pre finish 1\n")
        self.assertEqual(events[3][0], "EOF")

        # Once the execution is in completed state, existing output should be returned immediately
        resp = self.app.get(
            "/v1/executions/%s/output" % (str(action_execution_db.id)),
            expect_errors=False,
        )
        self.assertEqual(resp.status_int, 200)

        events = self._parse_response(resp.text)
        self.assertEqual(len(events), 4)
        self.assertEqual(events[0][1]["data"], "stdout before start\n")
        self.assertEqual(events[1][1]["data"], "stdout mid 1\n")
        self.assertEqual(events[2][1]["data"], "stdout pre finish 1\n")
        self.assertEqual(events[3][0], "EOF")

        listener.shutdown()

    def test_get_output_finished_execution(self):
        # Test the execution output API endpoint for execution which has finished
        for status in action_constants.LIVEACTION_COMPLETED_STATES:
            # Insert mock execution and output objects
            status = action_constants.LIVEACTION_STATUS_SUCCEEDED
            timestamp = date_utils.get_datetime_utc_now()
            action_execution_db = ActionExecutionDB(
                start_timestamp=timestamp,
                end_timestamp=timestamp,
                status=status,
                action={"ref": "core.local"},
                runner={"name": "local-shell-cmd"},
                liveaction={"ref": "foo"},
            )
            action_execution_db = ActionExecution.add_or_update(action_execution_db)

            for i in range(1, 6):
                stdout_db = ActionExecutionOutputDB(
                    execution_id=str(action_execution_db.id),
                    action_ref="core.local",
                    runner_ref="dummy",
                    timestamp=timestamp,
                    output_type="stdout",
                    data="stdout %s\n" % (i),
                )
                ActionExecutionOutput.add_or_update(stdout_db)

            for i in range(10, 15):
                stderr_db = ActionExecutionOutputDB(
                    execution_id=str(action_execution_db.id),
                    action_ref="core.local",
                    runner_ref="dummy",
                    timestamp=timestamp,
                    output_type="stderr",
                    data="stderr %s\n" % (i),
                )
                ActionExecutionOutput.add_or_update(stderr_db)

            resp = self.app.get(
                "/v1/executions/%s/output" % (str(action_execution_db.id)),
                expect_errors=False,
            )
            self.assertEqual(resp.status_int, 200)

            events = self._parse_response(resp.text)
            self.assertEqual(len(events), 11)
            self.assertEqual(events[0][1]["data"], "stdout 1\n")
            self.assertEqual(events[9][1]["data"], "stderr 14\n")
            self.assertEqual(events[10][0], "EOF")

            # Verify "last" short-hand id works
            resp = self.app.get("/v1/executions/last/output", expect_errors=False)
            self.assertEqual(resp.status_int, 200)

            events = self._parse_response(resp.text)
            self.assertEqual(len(events), 11)
            self.assertEqual(events[10][0], "EOF")

    def _parse_response(self, response):
        """
        Parse event stream response and return a list of events.
        """
        events = []

        lines = response.strip().split("\n")
        for index, line in enumerate(lines):
            if "data:" in line:
                e_line = lines[index - 1]
                event_name = e_line[e_line.find("event: ") + len("event:") :].strip()
                event_data = line[line.find("data: ") + len("data :") :].strip()

                event_data = json.loads(event_data) if len(event_data) > 2 else {}
                events.append((event_name, event_data))

        return events

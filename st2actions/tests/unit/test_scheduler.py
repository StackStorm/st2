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

from __future__ import absolute_import, print_function

from mock import patch, MagicMock

from st2tests import DbTestCase
from st2common.util import date
from st2common.models.db.execution_queue import ActionExecutionSchedulingQueueDB
from st2common.models.db.liveaction import LiveActionDB
from st2common.persistence.execution_queue import ExecutionQueue
from st2common.persistence.liveaction import LiveAction

from st2actions.scheduler import handler, entrypoint


LIVE_ACTION = {
    'parameters': {
        'cmd': 'echo ":dat_face:"',
    },
    'action': 'core.local',
    'status': 'requested'
}


class ActionExecutionSchedulingQueueDBTest(DbTestCase):

    def test_create_from_liveaction(self):
        live_action = LiveAction.add_or_update(
            LiveActionDB(
                parameters=LIVE_ACTION['parameters'],
                action=LIVE_ACTION['action'],
                status=LIVE_ACTION['status']
            )
        )
        delay = 500
        execution_request = entrypoint._create_execution_request_from_liveaction(
            live_action,
            delay,
        )

        delay_date = date.append_milliseconds_to_time(live_action.start_timestamp, delay)

        self.assertIsInstance(execution_request, ActionExecutionSchedulingQueueDB)
        self.assertEqual(execution_request.scheduled_start_timestamp, delay_date)
        self.assertEqual(execution_request.delay, delay)
        self.assertEqual(execution_request.liveaction, str(live_action.id))

    def test_next_execution(self):
        self.reset()
        live_action = LiveAction.add_or_update(
            LiveActionDB(
                parameters=LIVE_ACTION['parameters'],
                action=LIVE_ACTION['action'],
                status=LIVE_ACTION['status']
            )
        )

        executions = [
            {
                "liveaction": live_action,
                "delay": 100,
            },
            {
                "liveaction": live_action,
                "delay": 5000,
            },
            {
                "liveaction": live_action,
                "delay": 1000,
            },
        ]

        execution_requests = []

        for execution in executions:
            execution_requests.append(
                ExecutionQueue.add_or_update(
                    entrypoint._create_execution_request_from_liveaction(
                        execution['liveaction'],
                        execution['delay'],
                    )
                )
            )

        expected_order = [0, 2, 1]

        for index in expected_order:
            delay_date = date.append_milliseconds_to_time(
                live_action.start_timestamp,
                executions[index]['delay']
            )

            date_mock = MagicMock()
            date_mock.get_datetime_utc_now.return_value = delay_date
            date_mock.append_milliseconds_to_time = date.append_milliseconds_to_time

            with patch('st2actions.scheduler.handler.date', date_mock):
                execution_request = handler._next_execution()
                ExecutionQueue.delete(execution_request)

            self.assertIsInstance(execution_request, ActionExecutionSchedulingQueueDB)
            self.assertEqual(execution_request.scheduled_start_timestamp, delay_date)
            self.assertEqual(execution_request.delay, executions[index]['delay'])
            self.assertEqual(execution_request.liveaction, str(executions[index]['liveaction'].id))

    def test_next_executions_empty(self):
        self.reset()
        execution_request = handler._next_execution()
        self.assertEquals(execution_request, None)

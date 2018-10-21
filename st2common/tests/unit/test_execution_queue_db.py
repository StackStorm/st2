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

from st2tests import DbTestCase
from mock import patch, MagicMock
from st2common.util import execution_queue_db as eq_util
from st2common.util import date
from st2common.models.db.execution_queue import ExecutionQueueDB
from st2common.models.db.liveaction import LiveActionDB
from st2common.persistence.execution_queue import ExecutionQueue


LIVE_ACTION = {
    'parameters': {
        'cmd': 'echo ":dat_face:"',
    },
    'action': 'core.local'
}


class ExecutionQueueDBTest(DbTestCase):

    def test_get_execution_request_by_id(self):
        self.reset()
        execution_request = ExecutionQueueDB(
            delay=500,
            priority=12,
            affinity="bob",
            liveaction=LIVE_ACTION
        )
        saved_execution_request = ExecutionQueue.add_or_update(execution_request)
        retrieved_execution_request = eq_util.get_execution_request_by_id(
            saved_execution_request.id
        )
        self.assertEqual(saved_execution_request, retrieved_execution_request)

    def test_create_from_liveaction(self):
        live_action = LiveActionDB(
            parameters=LIVE_ACTION['parameters'],
            action=LIVE_ACTION['action']
        )
        delay = 500
        priority = 10
        affinity = 'angrycoder'
        execution_request = eq_util.create_execution_request_from_liveaction(
            live_action,
            delay,
            priority,
            affinity
        )

        delay_date = date.append_milliseconds_to_time(live_action.start_timestamp, delay)

        self.assertIsInstance(execution_request, ExecutionQueueDB)
        self.assertEqual(execution_request.start_timestamp, delay_date)
        self.assertEqual(execution_request.delay, delay)
        self.assertEqual(execution_request.priority, priority)
        self.assertEqual(execution_request.affinity, affinity)
        self.assertEqual(execution_request.liveaction, live_action.to_serializable_dict())

    def test_pop_next_execution(self):
        self.reset()
        live_action = LiveActionDB(
            parameters=LIVE_ACTION['parameters'],
            action=LIVE_ACTION['action']
        )
        executions = [
            {
                "liveaction": live_action,
                "delay": 100,
                "priority": 100,
                "affinity": "angrycoder",
            },
            {
                "liveaction": live_action,
                "delay": 5000,
                "priority": 200,
                "affinity": "madcoder",
            },
            {
                "liveaction": live_action,
                "delay": 1000,
                "priority": 200,
                "affinity": "m4dcoder",
            },
        ]

        execution_requests = []

        for execution in executions:
            execution_requests.append(
                ExecutionQueue.add_or_update(
                    eq_util.create_execution_request_from_liveaction(
                        execution['liveaction'],
                        execution['delay'],
                        execution['priority'],
                        execution['affinity']
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

            with patch('st2common.util.execution_queue_db.date', date_mock):
                execution_request = eq_util.pop_next_execution()
            self.assertIsInstance(execution_request, ExecutionQueueDB)
            self.assertEqual(execution_request.start_timestamp, delay_date)
            self.assertEqual(execution_request.delay, executions[index]['delay'])
            self.assertEqual(execution_request.priority, executions[index]['priority'])
            self.assertEqual(execution_request.affinity, executions[index]['affinity'])
            self.assertEqual(
                execution_request.liveaction,
                executions[index]['liveaction'].to_serializable_dict()
            )

    def test_pop_next_execution_none(self):
        self.reset()
        execution_request = eq_util.pop_next_execution()
        self.assertIsInstance(execution_request, type(None))

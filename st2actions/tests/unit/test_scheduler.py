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

import datetime
import mock
import eventlet

import st2common
from st2tests import ExecutionDbTestCase
from st2tests.fixturesloader import FixturesLoader
from st2tests.mocks.liveaction import MockLiveActionPublisherSchedulingQueueOnly

from st2actions.scheduler import entrypoint as scheduling
from st2actions.scheduler import handler as scheduling_queue

from st2common.util import date
from st2common.transport.liveaction import LiveActionPublisher
from st2common.constants import action as action_constants
from st2common.bootstrap.policiesregistrar import register_policy_types
from st2common.bootstrap import runnersregistrar as runners_registrar
from st2common.models.db.execution_queue import ActionExecutionSchedulingQueueItemDB
from st2common.models.db.liveaction import LiveActionDB
from st2common.persistence.execution_queue import ActionExecutionSchedulingQueue
from st2common.persistence.liveaction import LiveAction
from st2common.services import executions as execution_service
from st2common.exceptions import db as db_exc

from st2tests import config as test_config
test_config.parse_args()


LIVE_ACTION = {
    'parameters': {
        'cmd': 'echo ":dat_face:"',
    },
    'action': 'core.local',
    'status': 'requested'
}

PACK = 'generic'
TEST_FIXTURES = {
    'actions': [
        'action1.yaml',
        'action2.yaml'
    ],
    'policies': [
        'policy_3.yaml',
        'policy_7.yaml'
    ]
}


@mock.patch.object(
    LiveActionPublisher, 'publish_state',
    mock.MagicMock(side_effect=MockLiveActionPublisherSchedulingQueueOnly.publish_state))
class ActionExecutionSchedulingQueueItemDBTest(ExecutionDbTestCase):

    @classmethod
    def setUpClass(cls):
        ExecutionDbTestCase.setUpClass()

        # Register runners
        runners_registrar.register_runners()

        # Register common policy types
        register_policy_types(st2common)

        loader = FixturesLoader()
        loader.save_fixtures_to_db(fixtures_pack=PACK,
                                   fixtures_dict=TEST_FIXTURES)

    def setUp(self):
        super(ActionExecutionSchedulingQueueItemDBTest, self).setUp()
        self.scheduler = scheduling.get_scheduler_entrypoint()
        self.scheduling_queue = scheduling_queue.get_handler()

    def _create_liveaction_db(self, status=action_constants.LIVEACTION_STATUS_REQUESTED):
        action_ref = 'wolfpack.action-1'
        parameters = {'actionstr': 'fu'}
        liveaction_db = LiveActionDB(action=action_ref, parameters=parameters, status=status)

        liveaction_db = LiveAction.add_or_update(liveaction_db)
        execution_service.create_execution_object(liveaction_db, publish=False)

        return liveaction_db

    def test_create_from_liveaction(self):
        liveaction_db = self._create_liveaction_db()
        delay = 500

        schedule_q_db = self.scheduler._create_execution_queue_item_db_from_liveaction(
            liveaction_db,
            delay,
        )

        delay_date = date.append_milliseconds_to_time(liveaction_db.start_timestamp, delay)

        self.assertIsInstance(schedule_q_db, ActionExecutionSchedulingQueueItemDB)
        self.assertEqual(schedule_q_db.scheduled_start_timestamp, delay_date)
        self.assertEqual(schedule_q_db.delay, delay)
        self.assertEqual(schedule_q_db.liveaction_id, str(liveaction_db.id))

    def test_next_execution(self):
        self.reset()

        schedule_q_dbs = []
        delays = [2000, 5000, 4000]
        expected_order = [0, 2, 1]
        test_cases = []

        for delay in delays:
            liveaction_db = self._create_liveaction_db()
            delayed_start = date.append_milliseconds_to_time(liveaction_db.start_timestamp, delay)

            test_case = {
                'liveaction': liveaction_db,
                'delay': delay,
                'delayed_start': delayed_start
            }

            test_cases.append(test_case)

        for test_case in test_cases:
            schedule_q_dbs.append(
                ActionExecutionSchedulingQueue.add_or_update(
                    self.scheduler._create_execution_queue_item_db_from_liveaction(
                        test_case['liveaction'],
                        test_case['delay'],
                    )
                )
            )

        # Wait maximum delay seconds so the query works as expected
        eventlet.sleep(3.2)

        for index in expected_order:
            test_case = test_cases[index]

            date_mock = mock.MagicMock()
            date_mock.get_datetime_utc_now.return_value = test_case['delayed_start']
            date_mock.append_milliseconds_to_time = date.append_milliseconds_to_time

            with mock.patch('st2actions.scheduler.handler.date', date_mock):
                schedule_q_db = self.scheduling_queue._get_next_execution()
                ActionExecutionSchedulingQueue.delete(schedule_q_db)

            self.assertIsInstance(schedule_q_db, ActionExecutionSchedulingQueueItemDB)
            self.assertEqual(schedule_q_db.delay, test_case['delay'])
            self.assertEqual(schedule_q_db.liveaction_id, str(test_case['liveaction'].id))

            # NOTE: We can't directly assert on the timestamp due to the delays on the code and
            # timing variance
            scheduled_start_timestamp = schedule_q_db.scheduled_start_timestamp
            test_case_start_timestamp = test_case['delayed_start']
            start_timestamp_diff = (scheduled_start_timestamp - test_case_start_timestamp)
            self.assertTrue(start_timestamp_diff <= datetime.timedelta(seconds=1))

    def test_next_executions_empty(self):
        self.reset()

        schedule_q_db = self.scheduling_queue._get_next_execution()

        self.assertEquals(schedule_q_db, None)

    def test_no_double_entries(self):
        self.reset()

        liveaction_db = self._create_liveaction_db()

        LiveAction.publish_status(liveaction_db)
        LiveAction.publish_status(liveaction_db)

        schedule_q_db = self.scheduling_queue._get_next_execution()
        self.assertIsNotNone(schedule_q_db)

        schedule_q_db = self.scheduling_queue._get_next_execution()
        self.assertIsNone(schedule_q_db)

    def test_no_processing_of_non_requested_actions(self):
        self.reset()

        for status in action_constants.LIVEACTION_STATUSES:
            liveaction_db = self._create_liveaction_db(status=status)

            LiveAction.publish_status(liveaction_db)

            schedule_q_db = self.scheduling_queue._get_next_execution()

            if status is action_constants.LIVEACTION_STATUS_REQUESTED:
                self.assertIsNotNone(schedule_q_db)
            else:
                self.assertIsNone(schedule_q_db)

    def test_garbage_collection(self):
        self.reset()

        liveaction_db = self._create_liveaction_db()

        schedule_q_db = self.scheduler._create_execution_queue_item_db_from_liveaction(
            liveaction_db,
            -70000,
        )

        schedule_q_db.handling = True
        schedule_q_db = ActionExecutionSchedulingQueue.add_or_update(schedule_q_db)

        schedule_q_db = self.scheduling_queue._get_next_execution()
        self.assertIsNone(schedule_q_db)

        self.scheduling_queue._handle_garbage_collection()

        schedule_q_db = self.scheduling_queue._get_next_execution()
        self.assertIsNotNone(schedule_q_db)

    @mock.patch('st2actions.scheduler.handler.action_service')
    @mock.patch('st2actions.scheduler.handler.ActionExecutionSchedulingQueue.delete')
    def test_processing_when_task_completed(self, mock_execution_queue_delete, mock_action_service):
        self.reset()

        liveaction_db = self._create_liveaction_db()

        LiveAction.publish_status(liveaction_db)
        liveaction_db.status = action_constants.LIVEACTION_STATUS_CANCELED
        LiveAction.add_or_update(liveaction_db)

        schedule_q_db = self.scheduling_queue._get_next_execution()
        scheduling_queue.get_handler()._handle_execution(schedule_q_db)

        mock_action_service.update_status.assert_not_called()
        mock_execution_queue_delete.assert_called_once()
        ActionExecutionSchedulingQueue.delete(schedule_q_db)

    @mock.patch('st2actions.scheduler.handler.LOG')
    def test_failed_next_item(self, mocked_logger):
        self.reset()

        liveaction_db = self._create_liveaction_db()

        schedule_q_db = self.scheduler._create_execution_queue_item_db_from_liveaction(
            liveaction_db,
        )

        schedule_q_db = ActionExecutionSchedulingQueue.add_or_update(schedule_q_db)

        with mock.patch(
            'st2actions.scheduler.handler.ActionExecutionSchedulingQueue.add_or_update',
            side_effect=db_exc.StackStormDBObjectWriteConflictError(schedule_q_db)
        ):
            schedule_q_db = self.scheduling_queue._get_next_execution()
            self.assertIsNone(schedule_q_db)

        mocked_logger.info.assert_called_once()
        call_args = mocked_logger.info.call_args_list[0][0]
        self.assertEqual(r'Execution queue item handled by another scheduler: %s', call_args[0])

        schedule_q_db = self.scheduling_queue._get_next_execution()
        self.assertIsNotNone(schedule_q_db)
        ActionExecutionSchedulingQueue.delete(schedule_q_db)

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

import st2tests.config as tests_config
tests_config.parse_args()

import mock
from kombu.message import Message

from st2actions import scheduler, worker
from st2actions.container.base import RunnerContainer
from st2common.constants import action as action_constants
from st2common.models.db.liveaction import LiveActionDB
from st2common.models.system.common import ResourceReference
from st2common.persistence import action
from st2common.services import executions
from st2common.transport.publishers import PoolPublisher
from st2common.util import action_db
from st2common.util import date as date_utils
from st2tests.base import DbTestCase


@mock.patch.object(PoolPublisher, 'publish', mock.MagicMock())
@mock.patch.object(executions, 'update_execution', mock.MagicMock())
@mock.patch.object(Message, 'ack', mock.MagicMock())
class QueueConsumerTest(DbTestCase):

    def __init__(self, *args, **kwargs):
        super(QueueConsumerTest, self).__init__(*args, **kwargs)
        self.scheduler = scheduler.get_scheduler()
        self.dispatcher = worker.get_worker()

    def _get_execution_db_model(self, status=action_constants.LIVEACTION_STATUS_REQUESTED):
        live_action_db = LiveActionDB()
        live_action_db.status = status
        live_action_db.start_timestamp = date_utils.get_datetime_utc_now()
        live_action_db.action = ResourceReference(
            name='test_action',
            pack='test_pack').ref
        live_action_db.parameters = None
        return action.LiveAction.add_or_update(live_action_db, publish=False)

    @mock.patch.object(RunnerContainer, 'dispatch', mock.MagicMock(return_value={'key': 'value'}))
    def test_execute(self):
        live_action_db = self._get_execution_db_model(
            status=action_constants.LIVEACTION_STATUS_REQUESTED)

        self.scheduler._queue_consumer._process_message(live_action_db)
        scheduled_live_action_db = action_db.get_liveaction_by_id(live_action_db.id)
        self.assertDictEqual(scheduled_live_action_db.runner_info, {})
        self.assertEqual(scheduled_live_action_db.status,
                         action_constants.LIVEACTION_STATUS_SCHEDULED)

        self.dispatcher._queue_consumer._process_message(scheduled_live_action_db)
        dispatched_live_action_db = action_db.get_liveaction_by_id(live_action_db.id)
        self.assertGreater(len(dispatched_live_action_db.runner_info.keys()), 0)
        self.assertEqual(dispatched_live_action_db.status,
                         action_constants.LIVEACTION_STATUS_RUNNING)

    @mock.patch.object(RunnerContainer, 'dispatch', mock.MagicMock(side_effect=Exception('Boom!')))
    def test_execute_failure(self):
        live_action_db = self._get_execution_db_model(
            status=action_constants.LIVEACTION_STATUS_REQUESTED)

        self.scheduler._queue_consumer._process_message(live_action_db)
        scheduled_live_action_db = action_db.get_liveaction_by_id(live_action_db.id)
        self.assertEqual(scheduled_live_action_db.status,
                         action_constants.LIVEACTION_STATUS_SCHEDULED)

        self.dispatcher._queue_consumer._process_message(scheduled_live_action_db)
        dispatched_live_action_db = action_db.get_liveaction_by_id(live_action_db.id)
        self.assertEqual(dispatched_live_action_db.status,
                         action_constants.LIVEACTION_STATUS_FAILED)

    @mock.patch.object(RunnerContainer, 'dispatch', mock.MagicMock(return_value=None))
    def test_execute_no_result(self):
        live_action_db = self._get_execution_db_model(
            status=action_constants.LIVEACTION_STATUS_REQUESTED)

        self.scheduler._queue_consumer._process_message(live_action_db)
        scheduled_live_action_db = action_db.get_liveaction_by_id(live_action_db.id)
        self.assertEqual(scheduled_live_action_db.status,
                         action_constants.LIVEACTION_STATUS_SCHEDULED)

        self.dispatcher._queue_consumer._process_message(scheduled_live_action_db)
        dispatched_live_action_db = action_db.get_liveaction_by_id(live_action_db.id)
        self.assertEqual(dispatched_live_action_db.status,
                         action_constants.LIVEACTION_STATUS_FAILED)

    @mock.patch.object(RunnerContainer, 'dispatch', mock.MagicMock(return_value=None))
    def test_execute_cancelation(self):
        live_action_db = self._get_execution_db_model(
            status=action_constants.LIVEACTION_STATUS_REQUESTED)

        self.scheduler._queue_consumer._process_message(live_action_db)
        scheduled_live_action_db = action_db.get_liveaction_by_id(live_action_db.id)
        self.assertEqual(scheduled_live_action_db.status,
                         action_constants.LIVEACTION_STATUS_SCHEDULED)

        action_db.update_liveaction_status(status=action_constants.LIVEACTION_STATUS_CANCELED,
                                           liveaction_id=live_action_db.id)
        canceled_live_action_db = action_db.get_liveaction_by_id(live_action_db.id)

        self.dispatcher._queue_consumer._process_message(canceled_live_action_db)
        dispatched_live_action_db = action_db.get_liveaction_by_id(live_action_db.id)
        self.assertEqual(dispatched_live_action_db.status,
                         action_constants.LIVEACTION_STATUS_CANCELED)
        self.assertDictEqual(dispatched_live_action_db.result,
                             {'message': 'Action execution canceled by user.'})

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

import datetime
import mock

from st2actions import worker
from st2actions.container.base import RunnerContainer
from st2common.constants import action as action_constants
from st2common.models.db.action import LiveActionDB
from st2common.models.system.common import ResourceReference
from st2common.persistence import action
from st2common.services import executions
from st2common.transport.publishers import PoolPublisher
from st2common.util.action_db import get_liveaction_by_id
from st2tests.base import DbTestCase


@mock.patch.object(PoolPublisher, 'publish', mock.MagicMock())
@mock.patch.object(executions, 'update_execution', mock.MagicMock())
class TestWorker(DbTestCase):

    @mock.patch.object(RunnerContainer, 'dispatch', mock.MagicMock())
    def test_basic_execution_success(self):
        testworker = worker.Worker(None)
        live_action_db = self._get_execution_db_model(
            status=action_constants.LIVEACTION_STATUS_SUCCEEDED)
        testworker._do_process_task(live_action_db)
        updated_live_action_db = get_liveaction_by_id(live_action_db.id)
        self.assertEqual(updated_live_action_db.status,
                         action_constants.LIVEACTION_STATUS_SUCCEEDED)

    @mock.patch.object(RunnerContainer, 'dispatch', mock.MagicMock())
    def test_basic_execution_fail(self):
        testworker = worker.Worker(None)
        live_action_db = self._get_execution_db_model(
            status=action_constants.LIVEACTION_STATUS_FAILED)
        testworker._do_process_task(live_action_db)
        updated_live_action_db = get_liveaction_by_id(live_action_db.id)
        self.assertEqual(updated_live_action_db.status,
                         action_constants.LIVEACTION_STATUS_FAILED)

    @mock.patch.object(RunnerContainer, 'dispatch', mock.MagicMock())
    def test_basic_execution_canceled(self):
        testworker = worker.Worker(None)
        live_action_db = self._get_execution_db_model(
            status=action_constants.LIVEACTION_STATUS_CANCELED)
        result = getattr(live_action_db, 'result', None)
        self.assertTrue(result == {},
                        getattr(live_action_db, 'result', None))
        testworker._do_process_task(live_action_db)
        updated_live_action_db = get_liveaction_by_id(live_action_db.id)
        self.assertEqual(updated_live_action_db.status,
                         action_constants.LIVEACTION_STATUS_CANCELED)
        result = getattr(updated_live_action_db, 'result', None)
        self.assertTrue(result['message'] is not None)

    @mock.patch.object(RunnerContainer, 'dispatch', mock.MagicMock(return_value=None))
    def test_basic_execution_no_result(self):
        testworker = worker.Worker(None)
        live_action_db = self._get_execution_db_model()
        testworker._do_process_task(live_action_db)
        updated_live_action_db = get_liveaction_by_id(live_action_db.id)
        self.assertEqual(updated_live_action_db.status,
                         action_constants.LIVEACTION_STATUS_FAILED)

    @mock.patch.object(RunnerContainer, 'dispatch', mock.MagicMock(side_effect=Exception('Boom!')))
    def test_failed_execution_handling(self):
        testworker = worker.Worker(None)
        live_action_db = self._get_execution_db_model()
        testworker._do_process_task(live_action_db)
        updated_live_action_db = get_liveaction_by_id(live_action_db.id)
        self.assertEqual(updated_live_action_db.status,
                         action_constants.LIVEACTION_STATUS_FAILED)

    @mock.patch.object(RunnerContainer, 'dispatch', mock.MagicMock(return_value='dont_care'))
    def test_succeeded_execution_handling(self):
        testworker = worker.Worker(None)
        live_action_db = self._get_execution_db_model()
        testworker._do_process_task(live_action_db)
        updated_live_action_db = get_liveaction_by_id(live_action_db.id)
        self.assertEqual(updated_live_action_db.status,
                         action_constants.LIVEACTION_STATUS_RUNNING)

    @mock.patch.object(RunnerContainer, 'dispatch', mock.MagicMock(return_value='dont_care'))
    def test_runner_info(self):
        testworker = worker.Worker(None)
        live_action_db = self._get_execution_db_model()
        testworker._do_process_task(live_action_db)
        updated_live_action_db = get_liveaction_by_id(live_action_db.id)
        self.assertEqual(updated_live_action_db.status,
                         action_constants.LIVEACTION_STATUS_RUNNING)
        self.assertTrue(updated_live_action_db.runner_info, 'runner_info should have value.')

    def _get_execution_db_model(self, status=action_constants.LIVEACTION_STATUS_REQUESTED):
        live_action_db = LiveActionDB()
        live_action_db.status = status
        live_action_db.start_timestamp = datetime.datetime.utcnow()
        live_action_db.action = ResourceReference(
            name='test_action',
            pack='test_pack').ref
        live_action_db.parameters = None
        return action.LiveAction.add_or_update(live_action_db, publish=False)

# Licensed to the StackStorm, Inc ('StackStorm') under one or more
# contributor license agreements.  See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.
# The ASF licenses this file to You under the Apache License, Version 2.0
# (the 'License'); you may not use this file except in compliance with
# the License.  You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an 'AS IS' BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import copy
from datetime import timedelta

import bson

from st2common import log as logging
from st2common.garbage_collection.executions import purge_executions
from st2common.constants import action as action_constants
from st2common.persistence.execution import ActionExecution
from st2common.persistence.liveaction import LiveAction
from st2common.util import date as date_utils
from st2tests.base import CleanDbTestCase
from st2tests.fixturesloader import FixturesLoader

LOG = logging.getLogger(__name__)

TEST_FIXTURES = {
    'executions': [
        'execution1.yaml'
    ],
    'liveactions': [
        'liveaction4.yaml'
    ]
}


class TestPurgeExecutions(CleanDbTestCase):

    @classmethod
    def setUpClass(cls):
        CleanDbTestCase.setUpClass()
        super(TestPurgeExecutions, cls).setUpClass()

    def setUp(self):
        super(TestPurgeExecutions, self).setUp()
        fixtures_loader = FixturesLoader()
        self.models = fixtures_loader.load_models(fixtures_pack='generic',
                                                  fixtures_dict=TEST_FIXTURES)

    def test_no_timestamp_doesnt_delete_things(self):
        now = date_utils.get_datetime_utc_now()
        exec_model = copy.deepcopy(self.models['executions']['execution1.yaml'])
        exec_model['start_timestamp'] = now - timedelta(days=15)
        exec_model['end_timestamp'] = now - timedelta(days=14)
        exec_model['status'] = action_constants.LIVEACTION_STATUS_SUCCEEDED
        exec_model['id'] = bson.ObjectId()
        ActionExecution.add_or_update(exec_model)

        execs = ActionExecution.get_all()
        self.assertEqual(len(execs), 1)

        expected_msg = 'Specify a valid timestamp'
        self.assertRaisesRegexp(ValueError, expected_msg, purge_executions,
                                logger=LOG, timestamp=None)
        execs = ActionExecution.get_all()
        self.assertEqual(len(execs), 1)

    def test_purge_executions_with_action_ref(self):
        now = date_utils.get_datetime_utc_now()
        exec_model = copy.deepcopy(self.models['executions']['execution1.yaml'])
        exec_model['start_timestamp'] = now - timedelta(days=15)
        exec_model['end_timestamp'] = now - timedelta(days=14)
        exec_model['status'] = action_constants.LIVEACTION_STATUS_SUCCEEDED
        exec_model['id'] = bson.ObjectId()
        ActionExecution.add_or_update(exec_model)

        execs = ActionExecution.get_all()
        self.assertEqual(len(execs), 1)
        purge_executions(logger=LOG, action_ref='core.localzzz', timestamp=now - timedelta(days=10))
        execs = ActionExecution.get_all()
        self.assertEqual(len(execs), 1)

        purge_executions(logger=LOG, action_ref='core.local', timestamp=now - timedelta(days=10))
        execs = ActionExecution.get_all()
        self.assertEqual(len(execs), 0)

    def test_purge_executions_with_timestamp(self):
        now = date_utils.get_datetime_utc_now()

        # Write one execution after cut-off threshold
        exec_model = copy.deepcopy(self.models['executions']['execution1.yaml'])
        exec_model['start_timestamp'] = now - timedelta(days=15)
        exec_model['end_timestamp'] = now - timedelta(days=14)
        exec_model['status'] = action_constants.LIVEACTION_STATUS_SUCCEEDED
        exec_model['id'] = bson.ObjectId()
        ActionExecution.add_or_update(exec_model)

        # Write one execution before cut-off threshold
        exec_model = copy.deepcopy(self.models['executions']['execution1.yaml'])
        exec_model['start_timestamp'] = now - timedelta(days=22)
        exec_model['end_timestamp'] = now - timedelta(days=21)
        exec_model['status'] = action_constants.LIVEACTION_STATUS_SUCCEEDED
        exec_model['id'] = bson.ObjectId()
        ActionExecution.add_or_update(exec_model)

        execs = ActionExecution.get_all()
        purge_executions(logger=LOG, timestamp=now - timedelta(days=20))
        execs = ActionExecution.get_all()
        self.assertEqual(len(execs), 1)

    def test_liveaction_gets_deleted(self):
        now = date_utils.get_datetime_utc_now()
        start_ts = now - timedelta(days=15)
        end_ts = now - timedelta(days=14)

        liveaction_model = copy.deepcopy(self.models['liveactions']['liveaction4.yaml'])
        liveaction_model['start_timestamp'] = start_ts
        liveaction_model['end_timestamp'] = end_ts
        liveaction_model['status'] = action_constants.LIVEACTION_STATUS_SUCCEEDED
        liveaction = LiveAction.add_or_update(liveaction_model)

        # Write one execution before cut-off threshold
        exec_model = copy.deepcopy(self.models['executions']['execution1.yaml'])
        exec_model['start_timestamp'] = start_ts
        exec_model['end_timestamp'] = end_ts
        exec_model['status'] = action_constants.LIVEACTION_STATUS_SUCCEEDED
        exec_model['id'] = bson.ObjectId()
        exec_model['liveaction']['id'] = str(liveaction.id)
        ActionExecution.add_or_update(exec_model)

        liveactions = LiveAction.get_all()
        executions = ActionExecution.get_all()
        self.assertEqual(len(liveactions), 1)
        self.assertEqual(len(executions), 1)
        purge_executions(logger=LOG, timestamp=now - timedelta(days=10))
        liveactions = LiveAction.get_all()
        executions = ActionExecution.get_all()
        self.assertEqual(len(executions), 0)
        self.assertEqual(len(liveactions), 0)

    def test_purge_incomplete(self):
        now = date_utils.get_datetime_utc_now()
        start_ts = now - timedelta(days=15)

        # Write executions before cut-off threshold
        exec_model = copy.deepcopy(self.models['executions']['execution1.yaml'])
        exec_model['start_timestamp'] = start_ts
        exec_model['status'] = action_constants.LIVEACTION_STATUS_SCHEDULED
        exec_model['id'] = bson.ObjectId()
        ActionExecution.add_or_update(exec_model)

        exec_model = copy.deepcopy(self.models['executions']['execution1.yaml'])
        exec_model['start_timestamp'] = start_ts
        exec_model['status'] = action_constants.LIVEACTION_STATUS_RUNNING
        exec_model['id'] = bson.ObjectId()
        ActionExecution.add_or_update(exec_model)

        exec_model = copy.deepcopy(self.models['executions']['execution1.yaml'])
        exec_model['start_timestamp'] = start_ts
        exec_model['status'] = action_constants.LIVEACTION_STATUS_DELAYED
        exec_model['id'] = bson.ObjectId()
        ActionExecution.add_or_update(exec_model)

        exec_model = copy.deepcopy(self.models['executions']['execution1.yaml'])
        exec_model['start_timestamp'] = start_ts
        exec_model['status'] = action_constants.LIVEACTION_STATUS_CANCELING
        exec_model['id'] = bson.ObjectId()
        ActionExecution.add_or_update(exec_model)

        exec_model = copy.deepcopy(self.models['executions']['execution1.yaml'])
        exec_model['start_timestamp'] = start_ts
        exec_model['status'] = action_constants.LIVEACTION_STATUS_REQUESTED
        exec_model['id'] = bson.ObjectId()
        ActionExecution.add_or_update(exec_model)

        self.assertEqual(len(ActionExecution.get_all()), 5)
        purge_executions(logger=LOG, timestamp=now - timedelta(days=10), purge_incomplete=False)
        self.assertEqual(len(ActionExecution.get_all()), 5)
        purge_executions(logger=LOG, timestamp=now - timedelta(days=10), purge_incomplete=True)
        self.assertEqual(len(ActionExecution.get_all()), 0)

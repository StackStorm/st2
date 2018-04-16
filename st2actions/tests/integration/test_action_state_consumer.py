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

from __future__ import absolute_import
import mock

from kombu import Connection

from st2common.transport.queues import RESULTSTRACKER_ACTIONSTATE_WORK_QUEUE
from st2actions.resultstracker.resultstracker import ResultsTracker
from st2common.models.db.executionstate import ActionExecutionStateDB
from st2common.persistence.executionstate import ActionExecutionState
from st2common.transport import utils as transport_utils
from st2tests.base import DbTestCase, EventletTestCase
from st2tests.fixturesloader import FixturesLoader
from st2tests.fixtures.packs.runners.test_querymodule.query.test_querymodule import TestQuerier

FIXTURES_PACK = 'generic'
FIXTURES = {'liveactions': ['liveaction1.yaml']}
loader = FixturesLoader()


class ActionStateConsumerTests(EventletTestCase, DbTestCase):
    models = None
    liveactions = None

    @classmethod
    def setUpClass(cls):
        super(ActionStateConsumerTests, cls).setUpClass()
        DbTestCase.setUpClass()
        cls.models = loader.save_fixtures_to_db(fixtures_pack=FIXTURES_PACK,
                                                fixtures_dict=FIXTURES)
        cls.liveactions = cls.models['liveactions']

    @mock.patch.object(TestQuerier, 'query', mock.MagicMock(return_value=(False, {})))
    def test_process_message(self):
        with Connection(transport_utils.get_messaging_urls()) as conn:
            tracker = ResultsTracker(conn, [RESULTSTRACKER_ACTIONSTATE_WORK_QUEUE])
            tracker._bootstrap()
            state = ActionStateConsumerTests.get_state(
                ActionStateConsumerTests.liveactions['liveaction1.yaml'])
            tracker._queue_consumer._process_message(state)
            querier = tracker.get_querier('test_querymodule')
            self.assertEqual(querier._query_contexts.qsize(), 1)

    @classmethod
    def get_state(cls, exec_db):
        state = ActionExecutionStateDB(execution_id=str(exec_db.id), query_context={'id': 'foo'},
                                       query_module='test_querymodule')
        return ActionExecutionState.add_or_update(state)

    @classmethod
    def tearDownClass(cls):
        loader.delete_models_from_db(ActionStateConsumerTests.models)

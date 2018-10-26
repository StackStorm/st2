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

import os
import imp

import eventlet
import mock

from oslo_config import cfg

from st2common.constants import action as action_constants
from st2common.exceptions.db import StackStormDBObjectNotFoundError
from st2common.persistence.action import Action
from st2common.persistence.executionstate import ActionExecutionState
from st2common.persistence.liveaction import LiveAction
from st2common.runners import utils as runners_utils
from st2common.services import executions
from st2common.util import action_db as action_db_utils
from st2tests.base import (DbTestCase, EventletTestCase)
from st2tests.fixturesloader import FixturesLoader

__all__ = [
    'ResultsTrackerTests'
]


FIXTURES_LOADER = FixturesLoader()
FIXTURES_PACK = 'generic'
FIXTURES = {
    'actionstates': ['state1.yaml', 'state2.yaml'],
    'liveactions': ['liveaction1.yaml', 'liveaction2.yaml']
}

CURRENT_DIR = os.path.dirname(__file__)
ST2CONTENT_DIR = os.path.join(CURRENT_DIR, '../../../st2tests/st2tests/fixtures/packs/runners')

MOCK_RUNNER_NAME = 'test_querymodule'

MOCK_QUERIER_PATH = '{0}/{1}/query/{1}.py'.format(ST2CONTENT_DIR, MOCK_RUNNER_NAME)
MOCK_QUERIER_PATH = os.path.abspath(MOCK_QUERIER_PATH)
MOCK_QUERIER_MODULE = imp.load_source(MOCK_RUNNER_NAME + '.query', MOCK_QUERIER_PATH)

MOCK_CALLBACK_PATH = '{0}/{1}/callback/{1}.py'.format(ST2CONTENT_DIR, MOCK_RUNNER_NAME)
MOCK_CALLBACK_PATH = os.path.abspath(MOCK_CALLBACK_PATH)
MOCK_CALLBACK_MODULE = imp.load_source(MOCK_RUNNER_NAME + '.callback', MOCK_CALLBACK_PATH)


@mock.patch.object(
    executions, 'update_execution', mock.MagicMock(return_value=None))
@mock.patch.object(
    LiveAction, 'publish_update', mock.MagicMock(return_value=None))
@mock.patch('st2common.runners.base.get_query_module',
            mock.Mock(return_value=MOCK_QUERIER_MODULE))
@mock.patch('st2actions.resultstracker.resultstracker.get_query_module',
            mock.Mock(return_value=MOCK_QUERIER_MODULE))
class ResultsTrackerTests(EventletTestCase, DbTestCase):
    states = None
    models = None
    liveactions = None

    @classmethod
    def setUpClass(cls):
        super(ResultsTrackerTests, cls).setUpClass()
        cfg.CONF.set_default('empty_q_sleep_time', 0.2, group='resultstracker')
        cfg.CONF.set_default('no_workers_sleep_time', 0.1, group='resultstracker')

    @classmethod
    def tearDownClass(cls):
        cfg.CONF.set_default('empty_q_sleep_time', 1, group='resultstracker')
        cfg.CONF.set_default('no_workers_sleep_time', 1, group='resultstracker')
        super(ResultsTrackerTests, cls).tearDownClass()

    def setUp(self):
        super(ResultsTrackerTests, self).setUp()
        DbTestCase.setUpClass()
        ResultsTrackerTests.models = FIXTURES_LOADER.save_fixtures_to_db(
            fixtures_pack=FIXTURES_PACK, fixtures_dict=FIXTURES)
        ResultsTrackerTests.states = ResultsTrackerTests.models['actionstates']
        ResultsTrackerTests.liveactions = ResultsTrackerTests.models['liveactions']
        ResultsTrackerTests._update_state_models()

    def tearDown(self):
        FIXTURES_LOADER.delete_models_from_db(ResultsTrackerTests.models)
        super(ResultsTrackerTests, self).tearDown()

    @mock.patch.object(
        Action, 'get_by_ref', mock.MagicMock(return_value='foobar'))
    def test_query_process(self):
        tracker = self._get_tracker()
        runners_utils.invoke_post_run = mock.Mock(return_value=None)

        # Ensure state objects are present.
        state1 = ActionExecutionState.get_by_id(ResultsTrackerTests.states['state1.yaml'].id)
        state2 = ActionExecutionState.get_by_id(ResultsTrackerTests.states['state2.yaml'].id)
        self.assertIsNotNone(state1)
        self.assertIsNotNone(state2)

        # Process the state objects.
        tracker._bootstrap()
        eventlet.sleep(1)

        exec_id = str(ResultsTrackerTests.states['state1.yaml'].execution_id)
        exec_db = LiveAction.get_by_id(exec_id)
        self.assertTrue(exec_db.result['called_with'][exec_id] is not None,
                        exec_db.result)

        exec_id = str(ResultsTrackerTests.states['state2.yaml'].execution_id)
        exec_db = LiveAction.get_by_id(exec_id)
        self.assertTrue(exec_db.result['called_with'][exec_id] is not None,
                        exec_db.result)

        tracker.shutdown()

        # Ensure state objects are deleted.
        self.assertRaises(
            StackStormDBObjectNotFoundError,
            ActionExecutionState.get_by_id,
            ResultsTrackerTests.states['state1.yaml'].id
        )

        self.assertRaises(
            StackStormDBObjectNotFoundError,
            ActionExecutionState.get_by_id,
            ResultsTrackerTests.states['state2.yaml'].id
        )

        # Ensure invoke_post_run is called.
        self.assertEqual(2, runners_utils.invoke_post_run.call_count)

    def test_start_shutdown(self):
        tracker = self._get_tracker()
        tracker.start()
        eventlet.sleep(0.1)
        tracker.shutdown()

    def test_get_querier_success(self):
        tracker = self._get_tracker()
        self.assertTrue(tracker.get_querier('test_querymodule') is not None)

    def test_get_querier_not_found(self):
        with mock.patch('st2actions.resultstracker.resultstracker.get_query_module',
                        mock.Mock(side_effect=Exception('Not found'))):
            tracker = self._get_tracker()
            self.assertEqual(tracker.get_querier('this_module_aint_exist'), None)

    def test_querier_started(self):
        tracker = self._get_tracker()
        querier = tracker.get_querier('test_querymodule')
        eventlet.sleep(0.1)
        self.assertTrue(querier.is_started(), 'querier must have been started.')

    def test_delete_state_object_on_error_at_query(self):
        tracker = self._get_tracker()
        querier = tracker.get_querier('test_querymodule')
        querier._delete_state_object = mock.Mock(return_value=None)

        # Ensure state objects are present.
        state1 = ActionExecutionState.get_by_id(ResultsTrackerTests.states['state1.yaml'].id)
        state2 = ActionExecutionState.get_by_id(ResultsTrackerTests.states['state2.yaml'].id)
        self.assertIsNotNone(state1)
        self.assertIsNotNone(state2)

        with mock.patch.object(
                querier.__class__, 'query',
                mock.MagicMock(side_effect=Exception('Mock query exception.'))):
            tracker._bootstrap()
            eventlet.sleep(1)

            exec_id = str(ResultsTrackerTests.states['state1.yaml'].execution_id)
            exec_db = LiveAction.get_by_id(exec_id)
            self.assertDictEqual(exec_db.result, {})

            exec_id = str(ResultsTrackerTests.states['state2.yaml'].execution_id)
            exec_db = LiveAction.get_by_id(exec_id)
            self.assertDictEqual(exec_db.result, {})

            tracker.shutdown()

        # Ensure deletes are called.
        self.assertEqual(2, querier._delete_state_object.call_count)

    def test_keep_state_object_on_error_at_query(self):
        tracker = self._get_tracker()
        querier = tracker.get_querier('test_querymodule')
        querier._delete_state_object = mock.Mock(return_value=None)
        querier.delete_state_object_on_error = False

        # Ensure state objects are present.
        state1 = ActionExecutionState.get_by_id(ResultsTrackerTests.states['state1.yaml'].id)
        state2 = ActionExecutionState.get_by_id(ResultsTrackerTests.states['state2.yaml'].id)
        self.assertIsNotNone(state1)
        self.assertIsNotNone(state2)

        with mock.patch.object(
                querier.__class__, 'query',
                mock.MagicMock(side_effect=Exception('Mock query exception.'))):
            tracker._bootstrap()
            eventlet.sleep(1)

            exec_id = str(ResultsTrackerTests.states['state1.yaml'].execution_id)
            exec_db = LiveAction.get_by_id(exec_id)
            self.assertDictEqual(exec_db.result, {})

            exec_id = str(ResultsTrackerTests.states['state2.yaml'].execution_id)
            exec_db = LiveAction.get_by_id(exec_id)
            self.assertDictEqual(exec_db.result, {})

            tracker.shutdown()

        # Ensure deletes are not called.
        querier._delete_state_object.assert_not_called()

    def test_delete_state_object_on_error_at_update_result(self):
        tracker = self._get_tracker()
        querier = tracker.get_querier('test_querymodule')
        querier._delete_state_object = mock.Mock(return_value=None)

        # Ensure state objects are present.
        state1 = ActionExecutionState.get_by_id(ResultsTrackerTests.states['state1.yaml'].id)
        state2 = ActionExecutionState.get_by_id(ResultsTrackerTests.states['state2.yaml'].id)
        self.assertIsNotNone(state1)
        self.assertIsNotNone(state2)

        with mock.patch.object(
                querier.__class__, '_update_action_results',
                mock.MagicMock(side_effect=Exception('Mock update exception.'))):
            tracker._bootstrap()
            eventlet.sleep(1)

            exec_id = str(ResultsTrackerTests.states['state1.yaml'].execution_id)
            exec_db = LiveAction.get_by_id(exec_id)
            self.assertDictEqual(exec_db.result, {})

            exec_id = str(ResultsTrackerTests.states['state2.yaml'].execution_id)
            exec_db = LiveAction.get_by_id(exec_id)
            self.assertDictEqual(exec_db.result, {})

            tracker.shutdown()

        # Ensure deletes are called.
        self.assertEqual(2, querier._delete_state_object.call_count)

    def test_keep_state_object_on_error_at_update_result(self):
        tracker = self._get_tracker()
        querier = tracker.get_querier('test_querymodule')
        querier._delete_state_object = mock.Mock(return_value=None)
        querier.delete_state_object_on_error = False

        # Ensure state objects are present.
        state1 = ActionExecutionState.get_by_id(ResultsTrackerTests.states['state1.yaml'].id)
        state2 = ActionExecutionState.get_by_id(ResultsTrackerTests.states['state2.yaml'].id)
        self.assertIsNotNone(state1)
        self.assertIsNotNone(state2)

        with mock.patch.object(
                querier.__class__, '_update_action_results',
                mock.MagicMock(side_effect=Exception('Mock update exception.'))):
            tracker._bootstrap()
            eventlet.sleep(1)

            exec_id = str(ResultsTrackerTests.states['state1.yaml'].execution_id)
            exec_db = LiveAction.get_by_id(exec_id)
            self.assertDictEqual(exec_db.result, {})

            exec_id = str(ResultsTrackerTests.states['state2.yaml'].execution_id)
            exec_db = LiveAction.get_by_id(exec_id)
            self.assertDictEqual(exec_db.result, {})

            tracker.shutdown()

        # Ensure deletes are not called.
        querier._delete_state_object.assert_not_called()

    @mock.patch.object(
        Action, 'get_by_ref', mock.MagicMock(return_value='foobar'))
    def test_execution_cancellation(self):
        tracker = self._get_tracker()
        querier = tracker.get_querier('test_querymodule')
        querier._delete_state_object = mock.Mock(return_value=None)
        runners_utils.invoke_post_run = mock.Mock(return_value=None)

        # Ensure state objects are present.
        state1 = ActionExecutionState.get_by_id(ResultsTrackerTests.states['state1.yaml'].id)
        state2 = ActionExecutionState.get_by_id(ResultsTrackerTests.states['state2.yaml'].id)
        self.assertIsNotNone(state1)
        self.assertIsNotNone(state2)

        with mock.patch.object(
                querier.__class__, 'query',
                mock.MagicMock(return_value=(action_constants.LIVEACTION_STATUS_CANCELED, {}))):
            tracker._bootstrap()
            eventlet.sleep(2)

            exec_id = str(ResultsTrackerTests.states['state1.yaml'].execution_id)
            exec_db = LiveAction.get_by_id(exec_id)
            self.assertDictEqual(exec_db.result, {})

            exec_id = str(ResultsTrackerTests.states['state2.yaml'].execution_id)
            exec_db = LiveAction.get_by_id(exec_id)
            self.assertDictEqual(exec_db.result, {})

            tracker.shutdown()

        # Ensure deletes are called.
        self.assertEqual(2, querier._delete_state_object.call_count)

        # Ensure invoke_post_run is called.
        self.assertEqual(2, runners_utils.invoke_post_run.call_count)

    @mock.patch.object(
        Action, 'get_by_ref', mock.MagicMock(return_value=None))
    def test_action_deleted(self):
        tracker = self._get_tracker()
        action_db_utils.get_runnertype_by_name = mock.Mock(return_value=None)

        # Ensure state objects are present.
        state1 = ActionExecutionState.get_by_id(ResultsTrackerTests.states['state1.yaml'].id)
        state2 = ActionExecutionState.get_by_id(ResultsTrackerTests.states['state2.yaml'].id)
        self.assertIsNotNone(state1)
        self.assertIsNotNone(state2)

        # Process the state objects.
        tracker._bootstrap()
        eventlet.sleep(1)

        exec_id = str(ResultsTrackerTests.states['state1.yaml'].execution_id)
        exec_db = LiveAction.get_by_id(exec_id)
        self.assertTrue(exec_db.result['called_with'][exec_id] is not None,
                        exec_db.result)

        exec_id = str(ResultsTrackerTests.states['state2.yaml'].execution_id)
        exec_db = LiveAction.get_by_id(exec_id)
        self.assertTrue(exec_db.result['called_with'][exec_id] is not None,
                        exec_db.result)

        tracker.shutdown()

        # Ensure state objects are deleted.
        self.assertRaises(
            StackStormDBObjectNotFoundError,
            ActionExecutionState.get_by_id,
            ResultsTrackerTests.states['state1.yaml'].id
        )

        self.assertRaises(
            StackStormDBObjectNotFoundError,
            ActionExecutionState.get_by_id,
            ResultsTrackerTests.states['state2.yaml'].id
        )

        # Ensure get_runnertype_by_name in invoke_post_run is not called.
        action_db_utils.get_runnertype_by_name.assert_not_called()

    def _get_tracker(self):
        from st2actions.resultstracker import resultstracker
        tracker = resultstracker.get_tracker()
        return tracker

    @classmethod
    def _update_state_models(cls):
        states = ResultsTrackerTests.states
        state1 = ActionExecutionState.get_by_id(states['state1.yaml'].id)
        state1.execution_id = ResultsTrackerTests.liveactions['liveaction1.yaml'].id
        state2 = ActionExecutionState.get_by_id(states['state2.yaml'].id)
        state2.execution_id = ResultsTrackerTests.liveactions['liveaction2.yaml'].id
        ResultsTrackerTests.states['state1.yaml'] = ActionExecutionState.add_or_update(state1)
        ResultsTrackerTests.states['state2.yaml'] = ActionExecutionState.add_or_update(state2)

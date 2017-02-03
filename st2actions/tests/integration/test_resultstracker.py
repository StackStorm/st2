import eventlet
import mock

import st2actions.resultstracker.resultstracker as results_tracker
from st2common.constants import action as action_constants
from st2common.exceptions.db import StackStormDBObjectNotFoundError
from st2common.persistence.action import Action
from st2common.persistence.executionstate import ActionExecutionState
from st2common.persistence.liveaction import LiveAction
from st2common.services import executions
from st2tests.base import (DbTestCase, EventletTestCase)
from st2tests.fixturesloader import FixturesLoader


FIXTURES_LOADER = FixturesLoader()
FIXTURES_PACK = 'generic'
FIXTURES = {
    'actionstates': ['state1.yaml', 'state2.yaml'],
    'liveactions': ['liveaction1.yaml', 'liveaction2.yaml']
}


@mock.patch.object(
    executions, 'update_execution', mock.MagicMock(return_value=None))
@mock.patch.object(
    LiveAction, 'publish_update', mock.MagicMock(return_value=None))
class ResultsTrackerTests(EventletTestCase, DbTestCase):
    states = None
    models = None
    liveactions = None

    def setUp(self):
        super(ResultsTrackerTests, self).setUp()
        DbTestCase.setUpClass()
        ResultsTrackerTests.models = FIXTURES_LOADER.save_fixtures_to_db(
            fixtures_pack=FIXTURES_PACK, fixtures_dict=FIXTURES)
        ResultsTrackerTests.states = ResultsTrackerTests.models['actionstates']
        ResultsTrackerTests.liveactions = ResultsTrackerTests.models['liveactions']
        ResultsTrackerTests._update_state_models()
        tracker = results_tracker.get_tracker()
        querier = tracker.get_querier('test_querymodule')
        querier.delete_state_object_on_error = True

    def tearDown(self):
        FIXTURES_LOADER.delete_models_from_db(ResultsTrackerTests.models)
        super(ResultsTrackerTests, self).tearDown()

    @classmethod
    def _update_state_models(cls):
        states = ResultsTrackerTests.states
        state1 = ActionExecutionState.get_by_id(states['state1.yaml'].id)
        state1.execution_id = ResultsTrackerTests.liveactions['liveaction1.yaml'].id
        state2 = ActionExecutionState.get_by_id(states['state2.yaml'].id)
        state2.execution_id = ResultsTrackerTests.liveactions['liveaction2.yaml'].id
        ResultsTrackerTests.states['state1.yaml'] = ActionExecutionState.add_or_update(state1)
        ResultsTrackerTests.states['state2.yaml'] = ActionExecutionState.add_or_update(state2)

    @mock.patch.object(
        Action, 'get_by_ref', mock.MagicMock(return_value='foobar'))
    def test_query_process(self):
        tracker = results_tracker.get_tracker()
        querier = tracker.get_querier('test_querymodule')
        querier._invoke_post_run = mock.Mock(return_value=None)

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

        # Ensure state objects are deleted
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
        self.assertEqual(2, querier._invoke_post_run.call_count)

    def test_start_shutdown(self):
        tracker = results_tracker.get_tracker()
        tracker.start()
        eventlet.sleep(0.1)
        tracker.shutdown()

    def test_get_querier(self):
        tracker = results_tracker.get_tracker()
        self.assertEqual(tracker.get_querier('this_module_aint_exist'), None)
        self.assertTrue(tracker.get_querier('test_querymodule') is not None)

    def test_querier_started(self):
        tracker = results_tracker.get_tracker()
        querier = tracker.get_querier('test_querymodule')
        eventlet.sleep(0.1)
        self.assertTrue(querier.is_started(), 'querier must have been started.')

    def test_delete_state_object_on_error_at_query(self):
        tracker = results_tracker.get_tracker()
        querier = tracker.get_querier('test_querymodule')
        querier._delete_state_object = mock.Mock(return_value=None)

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
        tracker = results_tracker.get_tracker()
        querier = tracker.get_querier('test_querymodule')
        querier._delete_state_object = mock.Mock(return_value=None)
        querier.delete_state_object_on_error = False

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
        tracker = results_tracker.get_tracker()
        querier = tracker.get_querier('test_querymodule')
        querier._delete_state_object = mock.Mock(return_value=None)

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
        tracker = results_tracker.get_tracker()
        querier = tracker.get_querier('test_querymodule')
        querier._delete_state_object = mock.Mock(return_value=None)
        querier.delete_state_object_on_error = False

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
        tracker = results_tracker.get_tracker()
        querier = tracker.get_querier('test_querymodule')
        querier._delete_state_object = mock.Mock(return_value=None)
        querier._invoke_post_run = mock.Mock(return_value=None)

        with mock.patch.object(
                querier.__class__, 'query',
                mock.MagicMock(return_value=(action_constants.LIVEACTION_STATUS_CANCELED, {}))):
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

        # Ensure invoke_post_run is not called.
        querier._invoke_post_run.assert_not_called()

    @mock.patch.object(
        Action, 'get_by_ref', mock.MagicMock(return_value=None))
    def test_action_deleted(self):
        tracker = results_tracker.get_tracker()
        querier = tracker.get_querier('test_querymodule')
        querier._invoke_post_run = mock.Mock(return_value=None)

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

        # Ensure state objects are deleted
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

        # Ensure invoke_post_run is not called.
        querier._invoke_post_run.assert_not_called()

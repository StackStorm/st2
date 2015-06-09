import eventlet

import st2actions.resultstracker as results_tracker
from st2common.persistence.executionstate import ActionExecutionState
from st2common.persistence.liveaction import LiveAction
from st2tests.base import (DbTestCase, EventletTestCase)
from st2tests.fixturesloader import FixturesLoader

FIXTURES_PACK = 'generic'
FIXTURES = {'actionstates': ['state1.yaml', 'state2.yaml'],
            'liveactions': ['liveaction1.yaml', 'liveaction2.yaml']}
loader = FixturesLoader()


class ResultsTrackerTests(EventletTestCase, DbTestCase):
    states = None
    models = None
    liveactions = None

    @classmethod
    def setUpClass(cls):
        super(ResultsTrackerTests, cls).setUpClass()
        DbTestCase.setUpClass()
        ResultsTrackerTests.models = loader.save_fixtures_to_db(fixtures_pack=FIXTURES_PACK,
                                                                fixtures_dict=FIXTURES)
        ResultsTrackerTests.states = ResultsTrackerTests.models['actionstates']
        ResultsTrackerTests.liveactions = ResultsTrackerTests.models['liveactions']
        ResultsTrackerTests._update_state_models()

    def test_bootstrap(self):
        tracker = results_tracker.get_tracker()
        tracker._bootstrap()
        eventlet.sleep(0.2)
        exec_id = str(ResultsTrackerTests.states['state1.yaml'].execution_id)
        exec_db = LiveAction.get_by_id(exec_id)
        self.assertTrue(exec_db.result['called_with'][exec_id] is not None,
                        exec_db.result)
        exec_id = str(ResultsTrackerTests.states['state2.yaml'].execution_id)
        exec_db = LiveAction.get_by_id(exec_id)
        self.assertTrue(exec_db.result['called_with'][exec_id] is not None,
                        exec_db.result)
        tracker.shutdown()

    def test_start_shutdown(self):
        tracker = results_tracker.get_tracker()
        tracker.start()
        eventlet.sleep(0.1)
        tracker.shutdown()

    def test_get_querier(self):
        tracker = results_tracker.get_tracker()
        self.assertEqual(tracker.get_querier('this_module_aint_exist'), None)
        self.assertTrue(tracker.get_querier('tests.resources.test_querymodule') is not None)

    def test_querier_started(self):
        tracker = results_tracker.get_tracker()
        querier = tracker.get_querier('tests.resources.test_querymodule')
        eventlet.sleep(0.1)
        self.assertTrue(querier.is_started(), 'querier must have been started.')

    @classmethod
    def tearDownClass(cls):
        loader.delete_models_from_db(ResultsTrackerTests.models)

    @classmethod
    def _update_state_models(cls):
        states = ResultsTrackerTests.states
        state1 = ActionExecutionState.get_by_id(states['state1.yaml'].id)
        state1.execution_id = ResultsTrackerTests.liveactions['liveaction1.yaml'].id
        state2 = ActionExecutionState.get_by_id(states['state2.yaml'].id)
        state2.execution_id = ResultsTrackerTests.liveactions['liveaction2.yaml'].id
        ResultsTrackerTests.states['state1.yaml'] = ActionExecutionState.add_or_update(state1)
        ResultsTrackerTests.states['state2.yaml'] = ActionExecutionState.add_or_update(state2)

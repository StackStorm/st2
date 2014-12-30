import eventlet

from st2actions.resultstracker import ResultsTracker
from st2common.persistence.action import ActionExecution, ActionExecutionState
from st2tests.base import (DbTestCase, EventletTestCase)
from st2tests.fixturesloader import FixturesLoader

FIXTURES_PACK = 'generic'
FIXTURES = {'actionstates': ['state1.json', 'state2.json'],
            'executions': ['execution1.json', 'execution2.json']}
loader = FixturesLoader()


class ResultsTrackerTests(EventletTestCase, DbTestCase):
    states = None
    models = None
    executions = None

    @classmethod
    def setUpClass(cls):
        super(ResultsTrackerTests, cls).setUpClass()
        DbTestCase.setUpClass()
        ResultsTrackerTests.models = loader.save_fixtures_to_db(fixtures_pack=FIXTURES_PACK,
                                                                fixtures_dict=FIXTURES)
        ResultsTrackerTests.states = ResultsTrackerTests.models['actionstates']
        ResultsTrackerTests.executions = ResultsTrackerTests.models['executions']
        ResultsTrackerTests._update_state_models()

    def test_bootstrap(self):
        tracker = ResultsTracker()
        tracker._bootstrap()
        eventlet.sleep(0.2)
        exec_id = str(ResultsTrackerTests.states['state1.json'].execution_id)
        exec_db = ActionExecution.get_by_id(exec_id)
        self.assertTrue(exec_db.result['called_with'][exec_id] is not None,
                        exec_db.result)
        exec_id = str(ResultsTrackerTests.states['state2.json'].execution_id)
        exec_db = ActionExecution.get_by_id(exec_id)
        self.assertTrue(exec_db.result['called_with'][exec_id] is not None,
                        exec_db.result)
        tracker.shutdown()

    @classmethod
    def tearDownClass(cls):
        loader.delete_models_from_db(ResultsTrackerTests.models)

    @classmethod
    def _update_state_models(cls):
        states = ResultsTrackerTests.states
        state1 = ActionExecutionState.get_by_id(states['state1.json'].id)
        state1.execution_id = ResultsTrackerTests.executions['execution1.json'].id
        state2 = ActionExecutionState.get_by_id(states['state2.json'].id)
        state2.execution_id = ResultsTrackerTests.executions['execution2.json'].id
        ResultsTrackerTests.states['state1.json'] = ActionExecutionState.add_or_update(state1)
        ResultsTrackerTests.states['state2.json'] = ActionExecutionState.add_or_update(state2)

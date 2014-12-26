from st2actions.resultstracker import ResultsTracker
from st2tests.base import (DbTestCase, EventletTestCase)
from st2tests.fixturesloader import FixturesLoader

FIXTURES_PACK = 'generic'
FIXTURES = {'actionstates': ['state1.json', 'state2.json']}
loader = FixturesLoader()


class ResultsTrackerTests(EventletTestCase, DbTestCase):
    states = None
    models = None

    @classmethod
    def setUpClass(cls):
        super(ResultsTrackerTests, cls).setUpClass()
        DbTestCase.setUpClass()
        ResultsTrackerTests.models = loader.save_fixtures_to_db(fixtures_pack=FIXTURES_PACK,
                                                                fixtures_dict=FIXTURES)
        ResultsTrackerTests.states = ResultsTrackerTests.models['actionstates']

    def test_bootstrap(self):
        tracker = ResultsTracker()
        tracker._bootstrap()

    @classmethod
    def tearDownClass(cls):
        loader.delete_models_from_db(ResultsTrackerTests.models)

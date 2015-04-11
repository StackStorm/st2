from kombu import Connection
import mock
from oslo.config import cfg

from st2actions.resultstracker import ActionStateQueueConsumer, ResultsTracker
from st2common.models.db.action import ActionExecutionStateDB
from st2common.persistence.action import ActionExecutionState
from st2tests.base import (DbTestCase, EventletTestCase)
from st2tests.fixturesloader import FixturesLoader
from tests.resources.test_querymodule import TestQuerier

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
        ActionStateConsumerTests.models = loader.save_fixtures_to_db(fixtures_pack=FIXTURES_PACK,
                                                                     fixtures_dict=FIXTURES)
        ActionStateConsumerTests.liveactions = ActionStateConsumerTests.models['liveactions']

    @mock.patch.object(TestQuerier, 'query', mock.MagicMock(return_value=(False, {})))
    def test_do_process_task(self):
        conn = None
        with Connection(cfg.CONF.messaging.url) as conn:
            tracker = ResultsTracker(q_connection=conn)
            tracker._bootstrap()
            consumer = ActionStateQueueConsumer(conn, tracker)
            state = ActionStateConsumerTests.get_state(
                ActionStateConsumerTests.liveactions['liveaction1.yaml'])
            consumer._do_process_task(state)
            querier = tracker.get_querier('tests.resources.test_querymodule')
            self.assertEqual(querier._query_contexts.qsize(), 1)

    @classmethod
    def get_state(cls, exec_db):
        state = ActionExecutionStateDB(execution_id=str(exec_db.id), query_context={'id': 'foo'},
                                       query_module='tests.resources.test_querymodule')
        return ActionExecutionState.add_or_update(state)

    @classmethod
    def tearDownClass(cls):
        loader.delete_models_from_db(ActionStateConsumerTests.models)

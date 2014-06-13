import datetime
import mock
import tests
import unittest2

from st2common.models.db.reactor import TriggerDB, TriggerInstanceDB
from st2common.persistence.reactor import Trigger, TriggerInstance
import st2reactor.container.utils as container_utils
from st2reactor.container.triggerdispatcher import TriggerDispatcher

MOCK_TRIGGER = TriggerDB()
MOCK_TRIGGER.id = 'trigger-test.id'
MOCK_TRIGGER.name = 'trigger-test.name'

MOCK_TRIGGER_INSTANCE = TriggerInstanceDB()
MOCK_TRIGGER_INSTANCE.id = 'triggerinstance-test'
MOCK_TRIGGER_INSTANCE.name = 'triggerinstance-test.name'
MOCK_TRIGGER_INSTANCE.trigger = MOCK_TRIGGER
MOCK_TRIGGER_INSTANCE.payload = {}
MOCK_TRIGGER_INSTANCE.occurrence_time = datetime.datetime.now()


class TriggerDispatcherTest(unittest2.TestCase):
    class TestDispatcher(TriggerDispatcher):
        called_dispatch = False

        def dispatch(self, triggers):
            TriggerDispatcherTest.TestDispatcher.called_dispatch = True

    def setUp(self):
        tests.parse_args()

    @mock.patch.object(Trigger, 'query', mock.MagicMock(
        return_value=[MOCK_TRIGGER]))
    @mock.patch.object(TriggerInstance, 'add_or_update', mock.MagicMock(
        return_value=MOCK_TRIGGER_INSTANCE))
    def test_validate_dispatch(self):
        dispatcher = TriggerDispatcherTest.TestDispatcher()
        dispatcher.dispatch([MOCK_TRIGGER_INSTANCE])
        self.assertEquals(TriggerDispatcherTest.TestDispatcher.called_dispatch, True,
                          "dispatch() method should have been called")


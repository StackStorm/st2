import datetime
import mock
import tests
import unittest2
import st2reactor.adapter.containerservice
from st2common.persistence.reactor import Trigger, TriggerInstance
from st2common.models.db.reactor import TriggerDB, TriggerInstanceDB

MOCK_TRIGGER = TriggerDB()
MOCK_TRIGGER.id = 'trigger-test.id'
MOCK_TRIGGER.name = 'trigger-test.name'

MOCK_TRIGGER_INSTANCE = TriggerInstanceDB()
MOCK_TRIGGER_INSTANCE.id = 'triggerinstance-test'
MOCK_TRIGGER_INSTANCE.name = 'triggerinstance-test.name'
MOCK_TRIGGER_INSTANCE.trigger = MOCK_TRIGGER
MOCK_TRIGGER_INSTANCE.payload = {}
MOCK_TRIGGER_INSTANCE.occurrence_time = datetime.datetime.now()


class ContainerServiceTest(unittest2.TestCase):
    def setUp(self):
        tests.parse_args()

    @mock.patch.object(Trigger, 'query', mock.MagicMock(
        return_value=[MOCK_TRIGGER]))
    @mock.patch.object(TriggerInstance, 'add_or_update', mock.MagicMock(
        return_value=MOCK_TRIGGER_INSTANCE))
    @mock.patch('st2reactor.adapter.containerservice.DISPATCH_HANDLER')
    def test_validate_dispatch(self, mock_dispatch_handler):
        st2reactor.adapter.containerservice.dispatch_trigger(
            MOCK_TRIGGER_INSTANCE)
        mock_dispatch_handler.assert_called_once_with([MOCK_TRIGGER_INSTANCE])


    @mock.patch.object(Trigger, 'query', mock.MagicMock(
        return_value=[MOCK_TRIGGER]))
    @mock.patch.object(Trigger, 'add_or_update')
    def test_add_trigger(self, mock_add_handler):
        mock_add_handler.return_value = MOCK_TRIGGER
        st2reactor.adapter.containerservice.add_trigger_type(MOCK_TRIGGER)
        self.assertTrue(mock_add_handler.called, 'trigger not added.')

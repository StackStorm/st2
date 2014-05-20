import datetime
import mock
import tests
import unittest2
import st2reactor.adapter.containerservice
from st2common.persistence.reactor import Trigger, TriggerInstance

MOCK_TRIGGER = {
    'id': 'trigger-test'
}
MOCK_TRIGGER_INSTANCE = {
    'id': 'triggerinstance-test',
    'trigger': MOCK_TRIGGER,
    'payload': {},
    'occurrence_time': datetime.datetime.now()
}


class ContainerServiceTest(unittest2.TestCase):
    def setUp(self):
        tests.parse_args()

    @mock.patch.object(Trigger, 'get_by_id', mock.MagicMock(
        return_value=MOCK_TRIGGER))
    @mock.patch.object(TriggerInstance, 'add_or_update', mock.MagicMock(
        return_value=MOCK_TRIGGER_INSTANCE))
    @mock.patch('st2reactor.adapter.containerservice.DISPATCH_HANDLER')
    def test_validate_dispatch(self, mock_dispatch_handler):
        st2reactor.adapter.containerservice.dispatch_trigger(
            MOCK_TRIGGER_INSTANCE)
        mock_dispatch_handler.assert_called_once_with([MOCK_TRIGGER_INSTANCE])
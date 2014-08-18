import mock
import unittest2

from st2common.persistence.reactor import Trigger, TriggerType
from st2common.models.db.reactor import TriggerDB, TriggerTypeDB
import st2reactor.container.utils as container_utils

MOCK_TRIGGER_TYPE = TriggerTypeDB()
MOCK_TRIGGER_TYPE.id = 'trigger-type-test.id'
MOCK_TRIGGER_TYPE.name = 'trigger-type-test.name'
MOCK_TRIGGER_TYPE.parameters_schema = {}
MOCK_TRIGGER_TYPE.payload_info = {}

MOCK_TRIGGER = TriggerDB()
MOCK_TRIGGER.id = 'trigger-test.id'
MOCK_TRIGGER.name = 'trigger-test.name'
MOCK_TRIGGER.parameters = {}
MOCK_TRIGGER.type = {'name': MOCK_TRIGGER_TYPE.name, 'id': MOCK_TRIGGER_TYPE.id}


class ContainerUtilsTest(unittest2.TestCase):
    @mock.patch.object(TriggerType, 'query', mock.MagicMock(
        return_value=[MOCK_TRIGGER_TYPE]))
    @mock.patch.object(Trigger, 'get_by_name', mock.MagicMock(return_value=MOCK_TRIGGER))
    @mock.patch.object(TriggerType, 'add_or_update')
    def test_add_trigger(self, mock_add_handler):
        mock_add_handler.return_value = MOCK_TRIGGER_TYPE
        container_utils.add_trigger_models([MOCK_TRIGGER_TYPE])
        self.assertTrue(mock_add_handler.called, 'trigger not added.')

    def test_add_trigger_type(self):
        """
        This sensor has misconfigured trigger type. We shouldn't explode.
        """
        class FailTestSensor(object):
            started = False

            def setup(self):
                pass

            def start(self):
                FailTestSensor.started = True

            def stop(self):
                pass

            def get_trigger_types(self):
                return [
                    {'description': 'Ain\'t got no name'}
                ]

        try:
            container_utils.add_trigger_models(FailTestSensor().get_trigger_types())
            self.assertTrue(False, 'Trigger type doesn\'t have \'name\' field. Should have thrown.')
        except Exception:
            self.assertTrue(True)

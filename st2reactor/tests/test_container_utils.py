import mock
import unittest2

from st2common.persistence.reactor import TriggerType
from st2common.models.db.reactor import TriggerTypeDB
import st2reactor.container.utils as container_utils

MOCK_TRIGGER = TriggerTypeDB()
MOCK_TRIGGER.id = 'trigger-test.id'
MOCK_TRIGGER.name = 'trigger-test.name'


class ContainerUtilsTest(unittest2.TestCase):
    @mock.patch.object(TriggerType, 'query', mock.MagicMock(
        return_value=[MOCK_TRIGGER]))
    @mock.patch.object(TriggerType, 'add_or_update')
    def test_add_trigger(self, mock_add_handler):
        mock_add_handler.return_value = MOCK_TRIGGER
        container_utils.add_trigger_types([MOCK_TRIGGER])
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
            container_utils.add_trigger_types(FailTestSensor().get_trigger_types())
            self.assertTrue(False, 'Trigger type doesn\'t have \'name\' field. Should have thrown.')
        except Exception:
            self.assertTrue(True)

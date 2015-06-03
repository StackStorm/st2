import os
import unittest2

import mock

import st2tests.config as tests_config
from st2tests.base import TESTS_CONFIG_PATH
from st2reactor.container.sensor_wrapper import SensorWrapper
from st2reactor.container.sensor_wrapper import SensorService
from st2client.models.keyvalue import KeyValuePair

CURRENT_DIR = os.path.abspath(os.path.dirname(__file__))
RESOURCES_DIR = os.path.abspath(os.path.join(CURRENT_DIR, '../resources'))


class Trigger(object):
    def __init__(self, id, type, data=None):
        self.id = id
        self.type = type
        self.data = data or {}
        self._data = data or {}


class SensorWrapperTestCase(unittest2.TestCase):
    @classmethod
    def setUpClass(cls):
        super(SensorWrapperTestCase, cls).setUpClass()
        tests_config.parse_args()

    def test_trigger_cud_event_handlers(self):
        file_path = os.path.join(RESOURCES_DIR, 'test_sensor.py')
        trigger_types = ['trigger1', 'trigger2']
        parent_args = ['--config-file', TESTS_CONFIG_PATH]

        wrapper = SensorWrapper(pack='core', file_path=file_path,
                                class_name='TestSensor',
                                trigger_types=trigger_types,
                                parent_args=parent_args)

        self.assertEqual(wrapper._trigger_names, {})

        wrapper._sensor_instance.add_trigger = mock.Mock()
        wrapper._sensor_instance.update_trigger = mock.Mock()
        wrapper._sensor_instance.remove_trigger = mock.Mock()

        # Call create handler with a trigger which refers to this sensor
        self.assertEqual(wrapper._sensor_instance.add_trigger.call_count, 0)

        trigger = Trigger(id='2', type=trigger_types[0])
        wrapper._handle_create_trigger(trigger=trigger)
        self.assertEqual(wrapper._trigger_names, {'2': trigger})
        self.assertEqual(wrapper._sensor_instance.add_trigger.call_count, 1)

        # Validate that update handler updates the trigger_names
        self.assertEqual(wrapper._sensor_instance.update_trigger.call_count, 0)

        trigger = Trigger(id='2', type=trigger_types[0])
        wrapper._handle_update_trigger(trigger=trigger)
        self.assertEqual(wrapper._trigger_names, {'2': trigger})
        self.assertEqual(wrapper._sensor_instance.update_trigger.call_count, 1)

        # Validate that delete handler deletes the trigger from trigger_names
        self.assertEqual(wrapper._sensor_instance.remove_trigger.call_count, 0)

        trigger = Trigger(id='2', type=trigger_types[0])
        wrapper._handle_delete_trigger(trigger=trigger)
        self.assertEqual(wrapper._trigger_names, {})
        self.assertEqual(wrapper._sensor_instance.remove_trigger.call_count, 1)


class SensorServiceTestCase(unittest2.TestCase):
    @classmethod
    def setUpClass(cls):
        super(SensorServiceTestCase, cls).setUpClass()
        tests_config.parse_args()

    def setUp(self):
        super(SensorServiceTestCase, self).setUp()

        file_path = os.path.join(RESOURCES_DIR, 'test_sensor.py')
        trigger_types = ['trigger1', 'trigger2']
        parent_args = ['--config-file', TESTS_CONFIG_PATH]
        wrapper = SensorWrapper(pack='core', file_path=file_path,
                                class_name='TestSensor',
                                trigger_types=trigger_types,
                                parent_args=parent_args)
        self._sensor_service = SensorService(sensor_wrapper=wrapper)
        self._sensor_service._get_api_client = mock.Mock()

    def test_datastore_operations_list_values(self):
        # Verify prefix filtering
        mock_api_client = mock.Mock()
        mock_api_client.keys.get_all.return_value = []
        self._set_mock_api_client(mock_api_client)

        self._sensor_service.list_values(local=True, prefix=None)
        mock_api_client.keys.get_all.assert_called_with(prefix='core.TestSensor:')
        self._sensor_service.list_values(local=True, prefix='ponies')
        mock_api_client.keys.get_all.assert_called_with(prefix='core.TestSensor:ponies')

        self._sensor_service.list_values(local=False, prefix=None)
        mock_api_client.keys.get_all.assert_called_with(prefix=None)
        self._sensor_service.list_values(local=False, prefix='ponies')
        mock_api_client.keys.get_all.assert_called_with(prefix='ponies')

        # No values in the datastore
        mock_api_client = mock.Mock()
        mock_api_client.keys.get_all.return_value = []
        self._set_mock_api_client(mock_api_client)

        values = self._sensor_service.list_values(local=True)
        self.assertEqual(values, [])
        values = self._sensor_service.list_values(local=False)
        self.assertEqual(values, [])

        # Values in the datastore
        kvp1 = KeyValuePair()
        kvp1.name = 'test1'
        kvp1.value = 'bar'
        kvp2 = KeyValuePair()
        kvp2.name = 'test2'
        kvp2.value = 'bar'
        mock_return_value = [kvp1, kvp2]
        mock_api_client.keys.get_all.return_value = mock_return_value
        self._set_mock_api_client(mock_api_client)

        values = self._sensor_service.list_values(local=True)
        self.assertEqual(len(values), 2)
        self.assertEqual(values, mock_return_value)

    def test_datastore_operations_get_value(self):
        mock_api_client = mock.Mock()
        kvp1 = KeyValuePair()
        kvp1.name = 'test1'
        kvp1.value = 'bar'
        mock_api_client.keys.get_by_id.return_value = kvp1
        self._set_mock_api_client(mock_api_client)

        value = self._sensor_service.get_value(name='test1', local=False)
        self.assertEqual(value, kvp1.value)

    def test_datastore_operations_set_value(self):
        mock_api_client = mock.Mock()
        mock_api_client.keys.update.return_value = True
        self._set_mock_api_client(mock_api_client)

        value = self._sensor_service.set_value(name='test1', value='foo', local=False)
        self.assertTrue(value)

    def test_datastore_operations_delete_value(self):
        mock_api_client = mock.Mock()
        mock_api_client.keys.delete.return_value = True
        self._set_mock_api_client(mock_api_client)

        value = self._sensor_service.delete_value(name='test', local=False)
        self.assertTrue(value)

    def _set_mock_api_client(self, mock_api_client):
        mock_method = mock.Mock()
        mock_method.return_value = mock_api_client
        self._sensor_service._get_api_client = mock_method

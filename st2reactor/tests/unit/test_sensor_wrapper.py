import os
import unittest2

import mock

import st2tests.config as tests_config
from st2tests.base import TESTS_CONFIG_PATH
from st2common.models.db.trigger import TriggerDB
from st2reactor.container.sensor_wrapper import SensorWrapper
from st2reactor.sensor.base import Sensor, PollingSensor

CURRENT_DIR = os.path.abspath(os.path.dirname(__file__))
RESOURCES_DIR = os.path.abspath(os.path.join(CURRENT_DIR, '../resources'))

__all__ = [
    'SensorWrapperTestCase'
]


class SensorWrapperTestCase(unittest2.TestCase):
    @classmethod
    def setUpClass(cls):
        super(SensorWrapperTestCase, cls).setUpClass()
        tests_config.parse_args()

    def test_sensor_instance_has_sensor_service(self):
        file_path = os.path.join(RESOURCES_DIR, 'test_sensor.py')
        trigger_types = ['trigger1', 'trigger2']
        parent_args = ['--config-file', TESTS_CONFIG_PATH]

        wrapper = SensorWrapper(pack='core', file_path=file_path,
                                class_name='TestSensor',
                                trigger_types=trigger_types,
                                parent_args=parent_args)
        self.assertTrue(getattr(wrapper._sensor_instance, 'sensor_service', None) is not None)
        self.assertTrue(getattr(wrapper._sensor_instance, 'config', None) is not None)

    def test_trigger_cud_event_handlers(self):
        trigger_id = '57861fcb0640fd1524e577c0'
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

        trigger = TriggerDB(id=trigger_id, name='test', pack='dummy', type=trigger_types[0])
        wrapper._handle_create_trigger(trigger=trigger)
        self.assertEqual(wrapper._trigger_names, {trigger_id: trigger})
        self.assertEqual(wrapper._sensor_instance.add_trigger.call_count, 1)

        # Validate that update handler updates the trigger_names
        self.assertEqual(wrapper._sensor_instance.update_trigger.call_count, 0)

        trigger = TriggerDB(id=trigger_id, name='test', pack='dummy', type=trigger_types[0])
        wrapper._handle_update_trigger(trigger=trigger)
        self.assertEqual(wrapper._trigger_names, {trigger_id: trigger})
        self.assertEqual(wrapper._sensor_instance.update_trigger.call_count, 1)

        # Validate that delete handler deletes the trigger from trigger_names
        self.assertEqual(wrapper._sensor_instance.remove_trigger.call_count, 0)

        trigger = TriggerDB(id=trigger_id, name='test', pack='dummy', type=trigger_types[0])
        wrapper._handle_delete_trigger(trigger=trigger)
        self.assertEqual(wrapper._trigger_names, {})
        self.assertEqual(wrapper._sensor_instance.remove_trigger.call_count, 1)

    def test_sensor_creation_passive(self):
        file_path = os.path.join(RESOURCES_DIR, 'test_sensor.py')
        trigger_types = ['trigger1', 'trigger2']
        parent_args = ['--config-file', TESTS_CONFIG_PATH]

        wrapper = SensorWrapper(pack='core', file_path=file_path,
                                class_name='TestSensor',
                                trigger_types=trigger_types,
                                parent_args=parent_args)
        self.assertIsInstance(wrapper._sensor_instance, Sensor)
        self.assertIsNotNone(wrapper._sensor_instance)

    def test_sensor_creation_active(self):
        file_path = os.path.join(RESOURCES_DIR, 'test_sensor.py')
        trigger_types = ['trigger1', 'trigger2']
        parent_args = ['--config-file', TESTS_CONFIG_PATH]
        poll_interval = 10
        wrapper = SensorWrapper(pack='core', file_path=file_path,
                                class_name='TestPollingSensor',
                                trigger_types=trigger_types,
                                parent_args=parent_args,
                                poll_interval=poll_interval)
        self.assertIsNotNone(wrapper._sensor_instance)
        self.assertIsInstance(wrapper._sensor_instance, PollingSensor)
        self.assertEquals(wrapper._sensor_instance._poll_interval, poll_interval)

    def test_sensor_init_fails_file_doesnt_exist(self):
        file_path = os.path.join(RESOURCES_DIR, 'test_sensor_doesnt_exist.py')
        trigger_types = ['trigger1', 'trigger2']
        parent_args = ['--config-file', TESTS_CONFIG_PATH]

        expected_msg = 'Failed to load sensor class from file'
        self.assertRaisesRegexp(ValueError, expected_msg, SensorWrapper,
                                pack='core', file_path=file_path,
                                class_name='TestSensor',
                                trigger_types=trigger_types,
                                parent_args=parent_args)

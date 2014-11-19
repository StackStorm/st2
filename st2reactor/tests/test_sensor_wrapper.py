import os
import unittest2

import mock

from st2reactor.container.sensor_wrapper import SensorWrapper

CURRENT_DIR = os.path.abspath(os.path.dirname(__file__))
RESOURCES_DIR = os.path.join(CURRENT_DIR, 'resources')

class Trigger(object):
    def __init__(self, id, type, data=None):
        self.id = id
        self.type = type
        self.data = data or {}
        self._data = data or {}


class SensorWrapperTestCase(unittest2.TestCase):
    def test_trigger_cud_event_handlers(self):
        file_path = os.path.join(RESOURCES_DIR, 'test_sensor.py')
        trigger_types = ['trigger1', 'trigger2']

        wrapper = SensorWrapper(pack='core', file_path=file_path,
                                class_name='TestSensor',
                                trigger_types=trigger_types)

        self.assertEqual(wrapper._trigger_names, {})

        wrapper._sensor_instance.add_trigger = mock.Mock()
        wrapper._sensor_instance.update_trigger = mock.Mock()
        wrapper._sensor_instance.remove_trigger = mock.Mock()

        # Call create handler with trigger referring to a different sensor
        trigger = Trigger(id='1', type='sometrigger')
        wrapper._handle_create_trigger(trigger=trigger)
        self.assertEqual(wrapper._trigger_names, {})
        self.assertEqual(wrapper._sensor_instance.add_trigger.call_count, 0)

        # Call create handler with a trigger which refers to this sensor
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

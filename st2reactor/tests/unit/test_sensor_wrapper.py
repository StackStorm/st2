# Copyright 2020 The StackStorm Authors.
# Copyright 2019 Extreme Networks, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import absolute_import

from st2common.util.monkey_patch import monkey_patch

monkey_patch()

import os
import unittest

import six
import mock
import eventlet


import st2tests.config as tests_config
from st2tests.base import TESTS_CONFIG_PATH
from st2common.models.db.trigger import TriggerDB
from st2reactor.container.sensor_wrapper import SensorWrapper
from st2reactor.sensor.base import Sensor, PollingSensor

from tests.resources.fixture import FIXTURE_PATH as RESOURCES_DIR

__all__ = ["SensorWrapperTestCase"]


class SensorWrapperTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        super(SensorWrapperTestCase, cls).setUpClass()
        tests_config.parse_args()

    def test_sensor_instance_has_sensor_service(self):
        file_path = os.path.join(RESOURCES_DIR, "test_sensor.py")
        trigger_types = ["trigger1", "trigger2"]
        parent_args = ["--config-file", TESTS_CONFIG_PATH]

        wrapper = SensorWrapper(
            pack="core",
            file_path=file_path,
            class_name="TestSensor",
            trigger_types=trigger_types,
            parent_args=parent_args,
        )
        self.assertIsNotNone(getattr(wrapper._sensor_instance, "sensor_service", None))
        self.assertIsNotNone(getattr(wrapper._sensor_instance, "config", None))

    def test_trigger_cud_event_handlers(self):
        trigger_id = "57861fcb0640fd1524e577c0"
        file_path = os.path.join(RESOURCES_DIR, "test_sensor.py")
        trigger_types = ["trigger1", "trigger2"]
        parent_args = ["--config-file", TESTS_CONFIG_PATH]

        wrapper = SensorWrapper(
            pack="core",
            file_path=file_path,
            class_name="TestSensor",
            trigger_types=trigger_types,
            parent_args=parent_args,
        )

        self.assertEqual(wrapper._trigger_names, {})

        wrapper._sensor_instance.add_trigger = mock.Mock()
        wrapper._sensor_instance.update_trigger = mock.Mock()
        wrapper._sensor_instance.remove_trigger = mock.Mock()

        # Call create handler with a trigger which refers to this sensor
        self.assertEqual(wrapper._sensor_instance.add_trigger.call_count, 0)

        trigger = TriggerDB(
            id=trigger_id, name="test", pack="dummy", type=trigger_types[0]
        )
        wrapper._handle_create_trigger(trigger=trigger)
        self.assertEqual(wrapper._trigger_names, {trigger_id: trigger})
        self.assertEqual(wrapper._sensor_instance.add_trigger.call_count, 1)

        # Validate that update handler updates the trigger_names
        self.assertEqual(wrapper._sensor_instance.update_trigger.call_count, 0)

        trigger = TriggerDB(
            id=trigger_id, name="test", pack="dummy", type=trigger_types[0]
        )
        wrapper._handle_update_trigger(trigger=trigger)
        self.assertEqual(wrapper._trigger_names, {trigger_id: trigger})
        self.assertEqual(wrapper._sensor_instance.update_trigger.call_count, 1)

        # Validate that delete handler deletes the trigger from trigger_names
        self.assertEqual(wrapper._sensor_instance.remove_trigger.call_count, 0)

        trigger = TriggerDB(
            id=trigger_id, name="test", pack="dummy", type=trigger_types[0]
        )
        wrapper._handle_delete_trigger(trigger=trigger)
        self.assertEqual(wrapper._trigger_names, {})
        self.assertEqual(wrapper._sensor_instance.remove_trigger.call_count, 1)

    def test_sensor_creation_passive(self):
        file_path = os.path.join(RESOURCES_DIR, "test_sensor.py")
        trigger_types = ["trigger1", "trigger2"]
        parent_args = ["--config-file", TESTS_CONFIG_PATH]

        wrapper = SensorWrapper(
            pack="core",
            file_path=file_path,
            class_name="TestSensor",
            trigger_types=trigger_types,
            parent_args=parent_args,
            db_ensure_indexes=False,
        )
        self.assertIsInstance(wrapper._sensor_instance, Sensor)
        self.assertIsNotNone(wrapper._sensor_instance)

    def test_sensor_creation_active(self):
        file_path = os.path.join(RESOURCES_DIR, "test_sensor.py")
        trigger_types = ["trigger1", "trigger2"]
        parent_args = ["--config-file", TESTS_CONFIG_PATH]
        poll_interval = 10
        wrapper = SensorWrapper(
            pack="core",
            file_path=file_path,
            class_name="TestPollingSensor",
            trigger_types=trigger_types,
            parent_args=parent_args,
            poll_interval=poll_interval,
            db_ensure_indexes=False,
        )
        self.assertIsNotNone(wrapper._sensor_instance)
        self.assertIsInstance(wrapper._sensor_instance, PollingSensor)
        self.assertEqual(wrapper._sensor_instance._poll_interval, poll_interval)

    def test_sensor_init_fails_file_doesnt_exist(self):
        file_path = os.path.join(RESOURCES_DIR, "test_sensor_doesnt_exist.py")
        trigger_types = ["trigger1", "trigger2"]
        parent_args = ["--config-file", TESTS_CONFIG_PATH]

        expected_msg = (
            "Failed to load sensor class from file.*? No such file or directory"
        )
        self.assertRaisesRegex(
            IOError,
            expected_msg,
            SensorWrapper,
            pack="core",
            file_path=file_path,
            class_name="TestSensor",
            trigger_types=trigger_types,
            parent_args=parent_args,
        )

    def test_sensor_init_fails_sensor_code_contains_typo(self):
        file_path = os.path.join(RESOURCES_DIR, "test_sensor_with_typo.py")
        trigger_types = ["trigger1", "trigger2"]
        parent_args = ["--config-file", TESTS_CONFIG_PATH]

        expected_msg = (
            "Failed to load sensor class from file.*? 'typobar' is not defined"
        )
        self.assertRaisesRegex(
            NameError,
            expected_msg,
            SensorWrapper,
            pack="core",
            file_path=file_path,
            class_name="TestSensor",
            trigger_types=trigger_types,
            parent_args=parent_args,
        )

        # Verify error message also contains traceback
        try:
            SensorWrapper(
                pack="core",
                file_path=file_path,
                class_name="TestSensor",
                trigger_types=trigger_types,
                parent_args=parent_args,
            )
        except NameError as e:
            self.assertIn("Traceback (most recent call last)", six.text_type(e))
            self.assertIn("line 20, in <module>", six.text_type(e))
        else:
            self.fail("NameError not thrown")

    def test_sensor_wrapper_poll_method_still_works(self):
        # Verify that sensor wrapper correctly applied select.poll() eventlet workaround so code
        # which relies on select.poll() such as subprocess.poll() still works
        # Note: If workaround is not applied "AttributeError: 'module' object has no attribute
        # 'poll'" will be thrown
        import select

        self.assertTrue(eventlet.patcher.is_monkey_patched(select))
        self.assertTrue(select != eventlet.patcher.original("select"))
        self.assertTrue(select.poll())

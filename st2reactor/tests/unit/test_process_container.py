# Licensed to the StackStorm, Inc ('StackStorm') under one or more
# contributor license agreements.  See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.
# The ASF licenses this file to You under the Apache License, Version 2.0
# (the "License"); you may not use this file except in compliance with
# the License.  You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import time

import eventlet
from mock import (MagicMock, Mock, patch)
import unittest2

from st2reactor.container.process_container import ProcessSensorContainer

import st2tests.config as tests_config
tests_config.parse_args()


class ProcessContainerTests(unittest2.TestCase):

    def test_no_sensors_dont_quit(self):
        process_container = ProcessSensorContainer(None, poll_interval=0.1)
        process_container_thread = eventlet.spawn(process_container.run)
        eventlet.sleep(0.5)
        self.assertEqual(process_container.running(), 0)
        self.assertEqual(process_container.stopped(), False)
        process_container.shutdown()
        process_container_thread.kill()

    @patch.object(time, 'time', MagicMock(return_value=1439441533))
    def test_dispatch_triggers_on_spawn_exit(self):
        mock_dispatcher = Mock()
        process_container = ProcessSensorContainer(None, poll_interval=0.1,
                                                   dispatcher=mock_dispatcher)
        sensor = {
            'class_name': 'pack.StupidSensor'
        }
        process = Mock()
        process_attrs = {'pid': 1234}
        process.configure_mock(**process_attrs)
        cmd = 'sensor_wrapper.py --class-name pack.StupidSensor'

        process_container._dispatch_trigger_for_sensor_spawn(sensor, process, cmd)
        mock_dispatcher.dispatch.assert_called_with(
            'core.st2.sensor.process_spawn',
            payload={
                'timestamp': 1439441533,
                'cmd': 'sensor_wrapper.py --class-name pack.StupidSensor',
                'pid': 1234,
                'id': 'pack.StupidSensor'})

        process_container._dispatch_trigger_for_sensor_exit(sensor, 1)
        mock_dispatcher.dispatch.assert_called_with(
            'core.st2.sensor.process_exit',
            payload={
                'id': 'pack.StupidSensor',
                'timestamp': 1439441533,
                'exit_code': 1
            })

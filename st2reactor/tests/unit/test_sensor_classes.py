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

import unittest2

from st2reactor.sensor.base import Sensor
from st2reactor.sensor.base import PollingSensor


class TestSensor(Sensor):
    def setup(self):
        pass

    def run(self):
        pass

    def cleanup(self):
        pass

    def add_trigger(self, trigger):
        pass

    def update_trigger(self, trigger):
        pass

    def remove_trigger(self, trigger):
        pass


class TestPollingSensor(TestSensor, PollingSensor):
    def poll(self):
        pass


class SensorClassesTestCase(unittest2.TestCase):
    def test_instance_variables_backward_compatibility(self):
        sensor1 = TestSensor(sensor_service='service', config='config')
        sensor2 = TestPollingSensor(sensor_service='service', config='config')

        # Current way
        self.assertEqual(sensor1.sensor_service, 'service')
        self.assertEqual(sensor1.config, 'config')
        self.assertEqual(sensor2.sensor_service, 'service')
        self.assertEqual(sensor2.config, 'config')

        # Old way (for backward compatibility)
        self.assertEqual(sensor1._sensor_service, 'service')
        self.assertEqual(sensor1._config, 'config')
        self.assertEqual(sensor2._sensor_service, 'service')
        self.assertEqual(sensor2._config, 'config')

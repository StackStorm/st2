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

import copy

import six
import st2common.bootstrap.sensorsregistrar as sensors_registrar
from tests import FunctionalTest

http_client = six.moves.http_client

__all__ = [
    'SensorTypeControllerTestCase'
]


class SensorTypeControllerTestCase(FunctionalTest):
    @classmethod
    def setUpClass(cls):
        super(SensorTypeControllerTestCase, cls).setUpClass()

        # Register local sensor and pack fixtures
        sensors_registrar.register_sensors(use_pack_cache=False)

    def test_get_all(self):
        resp = self.app.get('/v1/sensortypes')
        self.assertEqual(resp.status_int, http_client.OK)
        self.assertEqual(len(resp.json), 1)
        self.assertEqual(resp.json[0]['name'], 'SampleSensor')

    def test_get_one_success(self):
        resp = self.app.get('/v1/sensortypes/dummy_pack_1.SampleSensor')
        self.assertEqual(resp.status_int, http_client.OK)
        self.assertEqual(resp.json['name'], 'SampleSensor')

    def test_get_one_doesnt_exist(self):
        resp = self.app.get('/v1/sensortypes/1', expect_errors=True)
        self.assertEqual(resp.status_int, http_client.NOT_FOUND)

    def test_disable_and_enable_sensor(self):
        # Verify initial state
        resp = self.app.get('/v1/sensortypes/dummy_pack_1.SampleSensor')
        self.assertEqual(resp.status_int, http_client.OK)
        self.assertTrue(resp.json['enabled'])

        sensor_data = resp.json

        # Disable sensor
        data = copy.deepcopy(sensor_data)
        data['enabled'] = False
        put_resp = self.app.put_json('/v1/sensortypes/dummy_pack_1.SampleSensor', data)
        self.assertEqual(put_resp.status_int, http_client.OK)
        self.assertFalse(put_resp.json['enabled'])

        # Verify sensor has been disabled
        resp = self.app.get('/v1/sensortypes/dummy_pack_1.SampleSensor')
        self.assertEqual(resp.status_int, http_client.OK)
        self.assertFalse(resp.json['enabled'])

        # Enable sensor
        data = copy.deepcopy(sensor_data)
        data['enabled'] = True
        put_resp = self.app.put_json('/v1/sensortypes/dummy_pack_1.SampleSensor', data)
        self.assertEqual(put_resp.status_int, http_client.OK)
        self.assertTrue(put_resp.json['enabled'])

        # Verify sensor has been enabled
        resp = self.app.get('/v1/sensortypes/dummy_pack_1.SampleSensor')
        self.assertEqual(resp.status_int, http_client.OK)
        self.assertTrue(resp.json['enabled'])

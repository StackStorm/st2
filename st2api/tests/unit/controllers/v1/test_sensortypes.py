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
from st2api.controllers.v1.sensors import SensorTypeController

from st2tests.api import FunctionalTest
from st2tests.api import APIControllerWithIncludeAndExcludeFilterTestCase

http_client = six.moves.http_client

__all__ = [
    'SensorTypeControllerTestCase'
]


class SensorTypeControllerTestCase(FunctionalTest,
                                   APIControllerWithIncludeAndExcludeFilterTestCase):
    get_all_path = '/v1/sensortypes'
    controller_cls = SensorTypeController
    include_attribute_field_name = 'entry_point'
    exclude_attribute_field_name = 'artifact_uri'
    test_exact_object_count = False

    @classmethod
    def setUpClass(cls):
        super(SensorTypeControllerTestCase, cls).setUpClass()

        # Register local sensor and pack fixtures
        sensors_registrar.register_sensors(use_pack_cache=False)

    def test_get_all_and_minus_one(self):
        resp = self.app.get('/v1/sensortypes')
        self.assertEqual(resp.status_int, http_client.OK)
        self.assertEqual(len(resp.json), 3)
        self.assertEqual(resp.json[0]['name'], 'SampleSensor')

        resp = self.app.get('/v1/sensortypes/?limit=-1')
        self.assertEqual(resp.status_int, http_client.OK)
        self.assertEqual(len(resp.json), 3)
        self.assertEqual(resp.json[0]['name'], 'SampleSensor')

    def test_get_all_negative_limit(self):
        resp = self.app.get('/v1/sensortypes/?limit=-22', expect_errors=True)
        self.assertEqual(resp.status_int, 400)
        self.assertEqual(resp.json['faultstring'],
                         u'Limit, "-22" specified, must be a positive number.')

    def test_get_all_filters(self):
        resp = self.app.get('/v1/sensortypes')
        self.assertEqual(resp.status_int, http_client.OK)
        self.assertEqual(len(resp.json), 3)

        # ?name filter
        resp = self.app.get('/v1/sensortypes?name=foobar')
        self.assertEqual(len(resp.json), 0)

        resp = self.app.get('/v1/sensortypes?name=SampleSensor2')
        self.assertEqual(len(resp.json), 1)
        self.assertEqual(resp.json[0]['name'], 'SampleSensor2')
        self.assertEqual(resp.json[0]['ref'], 'dummy_pack_1.SampleSensor2')

        resp = self.app.get('/v1/sensortypes?name=SampleSensor3')
        self.assertEqual(len(resp.json), 1)
        self.assertEqual(resp.json[0]['name'], 'SampleSensor3')

        # ?pack filter
        resp = self.app.get('/v1/sensortypes?pack=foobar')
        self.assertEqual(len(resp.json), 0)

        resp = self.app.get('/v1/sensortypes?pack=dummy_pack_1')
        self.assertEqual(len(resp.json), 3)

        # ?enabled filter
        resp = self.app.get('/v1/sensortypes?enabled=False')
        self.assertEqual(len(resp.json), 1)
        self.assertEqual(resp.json[0]['enabled'], False)

        resp = self.app.get('/v1/sensortypes?enabled=True')
        self.assertEqual(len(resp.json), 2)
        self.assertEqual(resp.json[0]['enabled'], True)
        self.assertEqual(resp.json[1]['enabled'], True)

        # ?trigger filter
        resp = self.app.get('/v1/sensortypes?trigger=dummy_pack_1.event3')
        self.assertEqual(len(resp.json), 1)
        self.assertEqual(resp.json[0]['trigger_types'], ['dummy_pack_1.event3'])

        resp = self.app.get('/v1/sensortypes?trigger=dummy_pack_1.event')
        self.assertEqual(len(resp.json), 2)
        self.assertEqual(resp.json[0]['trigger_types'], ['dummy_pack_1.event'])
        self.assertEqual(resp.json[1]['trigger_types'], ['dummy_pack_1.event'])

    def test_get_one_success(self):
        resp = self.app.get('/v1/sensortypes/dummy_pack_1.SampleSensor')
        self.assertEqual(resp.status_int, http_client.OK)
        self.assertEqual(resp.json['name'], 'SampleSensor')
        self.assertEqual(resp.json['ref'], 'dummy_pack_1.SampleSensor')

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
        self.assertEqual(put_resp.json['ref'], 'dummy_pack_1.SampleSensor')
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

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

import six
from tests import FunctionalTest

from st2tests.fixturesloader import FixturesLoader

http_client = six.moves.http_client

TEST_FIXTURES = {
    'sensors': ['parameterized_sensor.yaml'],
    'sensorinstances': ['sensor_instance_1.yaml', 'sensor_instance_2.yaml'],
    'sensorexecutions': ['sensor_execution_1.yaml', 'sensor_execution_2.yaml',
                         'sensor_execution_3.yaml']
}

FIXTURES_PACK = 'generic'


class SensorExecutionControllerTestCase(FunctionalTest):

    models = None

    @classmethod
    def setUpClass(cls):
        super(SensorExecutionControllerTestCase, cls).setUpClass()

        fixtures_loader = FixturesLoader()
        cls.models = fixtures_loader.save_fixtures_to_db(
            fixtures_pack=FIXTURES_PACK, fixtures_dict=TEST_FIXTURES)

    def test_get_all(self):
        resp = self.app.get('/v1/sensorexecutions')
        self.assertEqual(resp.status_int, http_client.OK)
        self.assertEqual(len(resp.json), len(self.models['sensorexecutions']))

    def test_get_one(self):
        # By id
        id_ = str(self.models['sensorexecutions']['sensor_execution_1.yaml']['id'])
        resp = self.app.get('/v1/sensorexecutions/%s' % id_)
        self.assertEqual(resp.status_int, http_client.OK)
        self.assertEqual(resp.json['id'], id_)

    def test_get_by_sensor_instace(self):
        sensor_instance_ref = self.models['sensorinstances']['sensor_instance_1.yaml']. \
            get_reference().ref
        resp = self.app.get('/v1/sensorexecutions/?sensor_instance=%s' % sensor_instance_ref)
        self.assertEqual(resp.status_int, http_client.OK)
        self.assertEqual(len(resp.json), 2)

    def test_get_one_doesnt_exist(self):
        resp = self.app.get('/v1/sensorexecutions/1', expect_errors=True)
        self.assertEqual(resp.status_int, http_client.NOT_FOUND)

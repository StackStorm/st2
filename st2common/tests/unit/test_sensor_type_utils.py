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

import mock
import unittest2

from st2common.models.api.sensor import SensorTypeAPI
from st2common.models.utils import sensor_type_utils


class SensorTypeUtilsTestCase(unittest2.TestCase):

    def test_to_sensor_db_model_no_trigger_types(self):
        sensor_meta = {
            'artifact_uri': 'file:///data/st2contrib/packs/jira/sensors/jira_sensor.py',
            'class_name': 'JIRASensor',
            'pack': 'jira'
        }
        sensor_api = SensorTypeAPI(**sensor_meta)
        sensor_model = SensorTypeAPI.to_model(sensor_api)
        self.assertEqual(sensor_model.name, sensor_meta['class_name'])
        self.assertEqual(sensor_model.pack, sensor_meta['pack'])
        self.assertEqual(sensor_model.artifact_uri, sensor_meta['artifact_uri'])
        self.assertListEqual(sensor_model.trigger_types, [])

    @mock.patch.object(sensor_type_utils, 'create_trigger_types', mock.MagicMock(
        return_value=['mock.trigger_ref']))
    def test_to_sensor_db_model_with_trigger_types(self):
        sensor_meta = {
            'artifact_uri': 'file:///data/st2contrib/packs/jira/sensors/jira_sensor.py',
            'class_name': 'JIRASensor',
            'pack': 'jira',
            'trigger_types': [{'pack': 'jira', 'name': 'issue_created', 'parameters': {}}]
        }

        sensor_api = SensorTypeAPI(**sensor_meta)
        sensor_model = SensorTypeAPI.to_model(sensor_api)
        self.assertListEqual(sensor_model.trigger_types, ['mock.trigger_ref'])

    def test_get_sensor_entry_point(self):
        # System packs
        file_path = 'file:///data/st/st2reactor/st2reactor/' + \
                    'contrib/sensors/st2_generic_webhook_sensor.py'
        class_name = 'St2GenericWebhooksSensor'

        sensor = {'artifact_uri': file_path, 'class_name': class_name, 'pack': 'core'}
        sensor_api = SensorTypeAPI(**sensor)

        entry_point = sensor_type_utils.get_sensor_entry_point(sensor_api)
        self.assertEqual(entry_point, class_name)

        # Non system packs
        file_path = 'file:///data/st2contrib/packs/jira/sensors/jira_sensor.py'
        class_name = 'JIRASensor'
        sensor = {'artifact_uri': file_path, 'class_name': class_name, 'pack': 'jira'}
        sensor_api = SensorTypeAPI(**sensor)

        entry_point = sensor_type_utils.get_sensor_entry_point(sensor_api)
        self.assertEqual(entry_point, 'sensors.jira_sensor.JIRASensor')

        file_path = 'file:///data/st2contrib/packs/docker/sensors/docker_container_sensor.py'
        class_name = 'DockerSensor'
        sensor = {'artifact_uri': file_path, 'class_name': class_name, 'pack': 'docker'}
        sensor_api = SensorTypeAPI(**sensor)

        entry_point = sensor_type_utils.get_sensor_entry_point(sensor_api)
        self.assertEqual(entry_point, 'sensors.docker_container_sensor.DockerSensor')

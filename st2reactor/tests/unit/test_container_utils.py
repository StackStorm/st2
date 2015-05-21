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

from st2common.persistence.reactor import (Trigger, TriggerType)
from st2common.models.api.sensor import SensorTypeAPI
from st2common.models.db.reactor import TriggerDB
from st2common.models.utils import sensor_type_utils
import st2common.services.triggers as trigger_services
from st2common.transport.publishers import PoolPublisher
import st2reactor.container.utils as container_utils
from st2tests.base import CleanDbTestCase

MOCK_TRIGGER_TYPE = {}
MOCK_TRIGGER_TYPE['id'] = 'trigger-type-test.id'
MOCK_TRIGGER_TYPE['name'] = 'trigger-type-test.name'
MOCK_TRIGGER_TYPE['pack'] = 'dummy_pack_1'
MOCK_TRIGGER_TYPE['parameters_schema'] = {}
MOCK_TRIGGER_TYPE['payload_schema'] = {}

MOCK_TRIGGER = TriggerDB()
MOCK_TRIGGER.id = 'trigger-test.id'
MOCK_TRIGGER.name = 'trigger-test.name'
MOCK_TRIGGER.pack = 'dummy_pack_1'
MOCK_TRIGGER.parameters = {}
MOCK_TRIGGER.type = 'dummy_pack_1.trigger-type-test.name'


@mock.patch.object(PoolPublisher, 'publish', mock.MagicMock())
class ContainerUtilsTest(CleanDbTestCase):
    def test_add_trigger_type(self):
        """
        This sensor has misconfigured trigger type. We shouldn't explode.
        """
        class FailTestSensor(object):
            started = False

            def setup(self):
                pass

            def start(self):
                FailTestSensor.started = True

            def stop(self):
                pass

            def get_trigger_types(self):
                return [
                    {'description': 'Ain\'t got no name'}
                ]

        try:
            trigger_services.add_trigger_models(FailTestSensor().get_trigger_types())
            self.assertTrue(False, 'Trigger type doesn\'t have \'name\' field. Should have thrown.')
        except Exception:
            self.assertTrue(True)

    def test_create_trigger_instance_invalid_trigger(self):
        trigger_instance = 'dummy_pack.footrigger'
        instance = container_utils.create_trigger_instance(trigger_instance, {}, None)
        self.assertTrue(instance is None)

    def test_add_trigger_type_no_params(self):
        # Trigger type with no params should create a trigger with same name as trigger type.
        trig_type = {
            'name': 'myawesometriggertype',
            'pack': 'dummy_pack_1',
            'description': 'Words cannot describe how awesome I am.',
            'parameters_schema': {},
            'payload_schema': {}
        }
        trigtype_dbs = trigger_services.add_trigger_models(trigger_types=[trig_type])
        trigger_type, trigger = trigtype_dbs[0]

        trigtype_db = TriggerType.get_by_id(trigger_type.id)
        self.assertEqual(trigtype_db.pack, 'dummy_pack_1')
        self.assertEqual(trigtype_db.name, trig_type.get('name'))
        self.assertTrue(trigger is not None)
        self.assertEqual(trigger.name, trigtype_db.name)

        # Add duplicate
        trigtype_dbs = trigger_services.add_trigger_models(trigger_types=[trig_type])
        triggers = Trigger.get_all()
        self.assertTrue(len(triggers) == 1)

    def test_add_trigger_type_with_params(self):
        MOCK_TRIGGER.type = 'system.test'
        # Trigger type with params should not create a trigger.
        PARAMETERS_SCHEMA = {
            "type": "object",
            "properties": {
                "url": {"type": "string"}
            },
            "required": ['url'],
            "additionalProperties": False
        }
        trig_type = {
            'name': 'myawesometriggertype2',
            'pack': 'my_pack_1',
            'description': 'Words cannot describe how awesome I am.',
            'parameters_schema': PARAMETERS_SCHEMA,
            'payload_schema': {}
        }
        trigtype_dbs = trigger_services.add_trigger_models(trigger_types=[trig_type])
        trigger_type, trigger = trigtype_dbs[0]

        trigtype_db = TriggerType.get_by_id(trigger_type.id)
        self.assertEqual(trigtype_db.pack, 'my_pack_1')
        self.assertEqual(trigtype_db.name, trig_type.get('name'))
        self.assertEqual(trigger, None)

    def test_get_sensor_entry_point(self):
        # System packs
        file_path = '/data/st/st2reactor/st2reactor/contrib/sensors/st2_generic_webhook_sensor.py'
        class_name = 'St2GenericWebhooksSensor'

        sensor = {'artifact_uri': file_path, 'class_name': class_name, 'pack': 'core'}
        sensor_api = SensorTypeAPI(**sensor)

        entry_point = sensor_type_utils.get_sensor_entry_point(sensor_api)
        self.assertEqual(entry_point, class_name)

        # Non system packs
        file_path = '/data/st2contrib/packs/jira/sensors/jira_sensor.py'
        class_name = 'JIRASensor'
        sensor = {'artifact_uri': file_path, 'class_name': class_name, 'pack': 'jira'}
        sensor_api = SensorTypeAPI(**sensor)

        entry_point = sensor_type_utils.get_sensor_entry_point(sensor_api)
        self.assertEqual(entry_point, 'sensors.jira_sensor.JIRASensor')

        file_path = '/data/st2contrib/packs/docker/sensors/docker_container_sensor.py'
        class_name = 'DockerSensor'
        sensor = {'artifact_uri': file_path, 'class_name': class_name, 'pack': 'docker'}
        sensor_api = SensorTypeAPI(**sensor)

        entry_point = sensor_type_utils.get_sensor_entry_point(sensor_api)
        self.assertEqual(entry_point, 'sensors.docker_container_sensor.DockerSensor')

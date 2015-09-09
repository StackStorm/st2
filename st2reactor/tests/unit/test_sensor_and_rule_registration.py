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

import os

import mock

from st2tests import DbTestCase
from st2common.persistence.rule import Rule
from st2common.persistence.sensor import SensorType
from st2common.persistence.trigger import Trigger
from st2common.persistence.trigger import TriggerType
from st2common.transport.publishers import PoolPublisher
from st2common.bootstrap.sensorsregistrar import SensorsRegistrar
from st2common.bootstrap.rulesregistrar import RulesRegistrar

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PACKS_DIR = os.path.join(CURRENT_DIR, '../fixtures/packs')


class SensorRegistrationTestCase(DbTestCase):

    @mock.patch.object(PoolPublisher, 'publish', mock.MagicMock())
    def test_register_sensors(self):
        # Verify DB is empty at the beginning
        self.assertEqual(len(SensorType.get_all()), 0)
        self.assertEqual(len(TriggerType.get_all()), 0)
        self.assertEqual(len(Trigger.get_all()), 0)

        registrar = SensorsRegistrar()
        registrar.register_sensors_from_packs(base_dirs=[PACKS_DIR])

        # Verify objects have been created
        sensor_dbs = SensorType.get_all()
        trigger_type_dbs = TriggerType.get_all()
        trigger_dbs = Trigger.get_all()

        self.assertEqual(len(sensor_dbs), 2)
        self.assertEqual(len(trigger_type_dbs), 2)
        self.assertEqual(len(trigger_dbs), 2)

        self.assertEqual(sensor_dbs[0].name, 'TestSensor')
        self.assertEqual(sensor_dbs[0].poll_interval, 10)
        self.assertTrue(sensor_dbs[0].enabled)

        self.assertEqual(sensor_dbs[1].name, 'TestSensorDisabled')
        self.assertEqual(sensor_dbs[1].poll_interval, 10)
        self.assertFalse(sensor_dbs[1].enabled)

        self.assertEqual(trigger_type_dbs[0].name, 'trigger_type_1')
        self.assertEqual(trigger_type_dbs[0].pack, 'pack_with_sensor')
        self.assertEqual(trigger_type_dbs[1].name, 'trigger_type_2')
        self.assertEqual(trigger_type_dbs[1].pack, 'pack_with_sensor')

        # Verify second call to registration doesn't create a duplicate objects
        registrar.register_sensors_from_packs(base_dirs=[PACKS_DIR])

        sensor_dbs = SensorType.get_all()
        trigger_type_dbs = TriggerType.get_all()
        trigger_dbs = Trigger.get_all()

        self.assertEqual(len(sensor_dbs), 2)
        self.assertEqual(len(trigger_type_dbs), 2)
        self.assertEqual(len(trigger_dbs), 2)

        self.assertEqual(sensor_dbs[0].name, 'TestSensor')
        self.assertEqual(sensor_dbs[0].poll_interval, 10)

        self.assertEqual(trigger_type_dbs[0].name, 'trigger_type_1')
        self.assertEqual(trigger_type_dbs[0].pack, 'pack_with_sensor')
        self.assertEqual(trigger_type_dbs[1].name, 'trigger_type_2')
        self.assertEqual(trigger_type_dbs[1].pack, 'pack_with_sensor')

        # Verify sensor and trigger data is updated on registration
        original_load = registrar._meta_loader.load

        def mock_load(*args, **kwargs):
            # Update poll_interval and trigger_type_2 description
            data = original_load(*args, **kwargs)
            data['poll_interval'] = 50
            data['trigger_types'][1]['description'] = 'test 2'
            return data
        registrar._meta_loader.load = mock_load

        registrar.register_sensors_from_packs(base_dirs=[PACKS_DIR])

        sensor_dbs = SensorType.get_all()
        trigger_type_dbs = TriggerType.get_all()
        trigger_dbs = Trigger.get_all()

        self.assertEqual(len(sensor_dbs), 2)
        self.assertEqual(len(trigger_type_dbs), 2)
        self.assertEqual(len(trigger_dbs), 2)

        self.assertEqual(sensor_dbs[0].name, 'TestSensor')
        self.assertEqual(sensor_dbs[0].poll_interval, 50)

        self.assertEqual(trigger_type_dbs[0].name, 'trigger_type_1')
        self.assertEqual(trigger_type_dbs[0].pack, 'pack_with_sensor')
        self.assertEqual(trigger_type_dbs[1].name, 'trigger_type_2')
        self.assertEqual(trigger_type_dbs[1].pack, 'pack_with_sensor')
        self.assertEqual(trigger_type_dbs[1].description, 'test 2')


class RuleRegistrationTestCase(DbTestCase):
    def test_register_rules(self):
        # Verify DB is empty at the beginning
        self.assertEqual(len(Rule.get_all()), 0)
        self.assertEqual(len(Trigger.get_all()), 0)

        registrar = RulesRegistrar()
        registrar.register_rules_from_packs(base_dirs=[PACKS_DIR])

        # Verify modeles are created
        rule_dbs = Rule.get_all()
        trigger_dbs = Trigger.get_all()
        self.assertEqual(len(rule_dbs), 2)
        self.assertEqual(len(trigger_dbs), 1)

        self.assertEqual(rule_dbs[0].name, 'sample.with_the_same_timer')
        self.assertEqual(rule_dbs[1].name, 'sample.with_timer')
        self.assertTrue(trigger_dbs[0].name is not None)

        # Verify second register call updates existing models
        registrar.register_rules_from_packs(base_dirs=[PACKS_DIR])

        rule_dbs = Rule.get_all()
        trigger_dbs = Trigger.get_all()
        self.assertEqual(len(rule_dbs), 2)
        self.assertEqual(len(trigger_dbs), 1)

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

from st2tests import CleanDbTestCase
from st2common.persistence.sensor import SensorType, SensorInstance
from st2common.transport.publishers import PoolPublisher
from st2reactor.bootstrap.sensorsregistrar import SensorsRegistrar
from st2reactor.bootstrap.sensorinstancesregistrar import SensorInstancesRegistrar

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PACKS_DIR = os.path.join(CURRENT_DIR, '../fixtures/packs')


@mock.patch.object(PoolPublisher, 'publish', mock.MagicMock())
class SensorInstanceRegistrationTestCase(CleanDbTestCase):

    def test_register_sensor_instances(self):
        # Verify DB is empty at the beginning
        self.assertEqual(len(SensorInstance.get_all()), 0)
        self.assertEqual(len(SensorType.get_all()), 0)

        st_registrar = SensorsRegistrar()
        st_registrar.register_sensors_from_packs(base_dirs=[PACKS_DIR])

        si_registrar = SensorInstancesRegistrar()
        si_registrar.register_sensor_instances_from_packs(base_dirs=[PACKS_DIR])

        # Verify objects have been created
        sensor_dbs = SensorType.get_all()
        self.assertEqual(len(sensor_dbs), 3)

        self._validate_sensor(sensor_dbs, sensor_name='ParameterizedSensor')

        sensor_instance_dbs = SensorInstance.get_all()
        self.assertEqual(len(sensor_instance_dbs), 2)

        self._validate_sensor_instance(sensor_instance_dbs,
                                       sensor_instance_name='sensor_instance_1',
                                       sensor_instance_pack='pack_with_sensor_instances',
                                       sensor_type='pack_with_sensor_instances.ParameterizedSensor')

    def test_register_sensor_instances_from_pack(self):
        # Verify DB is empty at the beginning
        self.assertEqual(len(SensorInstance.get_all()), 0)
        self.assertEqual(len(SensorType.get_all()), 0)

        pack_dir = os.path.join(PACKS_DIR, 'pack_with_sensor_instances')

        st_registrar = SensorsRegistrar()
        st_registrar.register_sensors_from_pack(pack_dir=pack_dir)

        si_registrar = SensorInstancesRegistrar()
        si_registrar.register_sensor_instances_from_pack(pack_dir=pack_dir)

        # Verify objects have been created
        sensor_dbs = SensorType.get_all()
        self.assertEqual(len(sensor_dbs), 1)

        self._validate_sensor(sensor_dbs, sensor_name='ParameterizedSensor')

        sensor_instance_dbs = SensorInstance.get_all()
        self.assertEqual(len(sensor_instance_dbs), 2)

        self._validate_sensor_instance(sensor_instance_dbs,
                                       sensor_instance_name='sensor_instance_1',
                                       sensor_instance_pack='pack_with_sensor_instances',
                                       sensor_type='pack_with_sensor_instances.ParameterizedSensor')

    def _validate_sensor(self, sensor_dbs, sensor_name, poll_interval=10, enabled=True):
        found = False
        for sensor_db in sensor_dbs:
            if sensor_db.name == sensor_name:
                self.assertEqual(sensor_db.name, sensor_name)
                self.assertEqual(sensor_db.poll_interval, poll_interval)
                self.assertEqual(sensor_db.enabled, enabled)
                found = True
                break
        if not found:
            self.assertTrue(False, 'sensor with name %s not found.' % sensor_name)

    def _validate_sensor_instance(self, sensor_instance_dbs, sensor_instance_name,
                                  sensor_instance_pack, sensor_type):
        found = False
        for sensor_instance_db in sensor_instance_dbs:
            if sensor_instance_db.name == sensor_instance_name:
                self.assertEqual(sensor_instance_db.name, sensor_instance_name)
                self.assertEqual(sensor_instance_db.pack, sensor_instance_pack)
                self.assertEqual(sensor_instance_db.sensor_type, sensor_type)
                found = True
                break
        if not found:
            self.assertTrue(False, 'sensor with name %s not found.' % sensor_instance_name)

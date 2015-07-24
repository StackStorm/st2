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
from st2common.persistence.sensor import SensorType, SensorInstance
from st2common.transport.publishers import PoolPublisher
from st2reactor.bootstrap.sensorsregistrar import SensorsRegistrar
from st2reactor.bootstrap.sensorinstancesregistrar import SensorInstancesRegistrar

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PACKS_DIR = os.path.join(CURRENT_DIR, '../fixtures/packs')


@mock.patch.object(PoolPublisher, 'publish', mock.MagicMock())
class SensorInstanceRegistrationTestCase(DbTestCase):

    def test_register_sensor_instances(self):
        # Verify DB is empty at the beginning
        self.assertEqual(len(SensorInstance.get_all()), 0)
        self.assertEqual(len(SensorType.get_all()), 0)

        st_registrar = SensorsRegistrar()
        st_registrar.register_sensors_from_packs(base_dirs=[PACKS_DIR])

        si_registrar = SensorInstancesRegistrar()
        si_registrar.register_sensor_instances_from_packs(base_dirs=[PACKS_DIR])

        # Verify objects have been created
        sensors_db = SensorType.get_all()
        self.assertEqual(len(sensors_db), 3)

        sensor_instances_db = SensorInstance.get_all()
        self.assertEqual(len(sensor_instances_db), 2)

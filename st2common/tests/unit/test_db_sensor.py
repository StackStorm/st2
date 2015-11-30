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

from st2common.transport.publishers import PoolPublisher
from st2tests import DbTestCase
from st2common.models.db.sensor import SensorTypeDB, SensorInstanceDB, SensorExecutionDB
from st2common.persistence.sensor import SensorType, SensorInstance, SensorExecution

DUMMY_DESCRIPTION = 'Dummy description'


@mock.patch.object(PoolPublisher, 'publish', mock.MagicMock())
class SensorModelTest(DbTestCase):

    def test_sensor_type_cud(self):
        saved = SensorModelTest._create_save_sensor_type()
        retrieved = SensorType.get_by_id(saved.id)
        self.assertEqual(saved.name, retrieved.name,
                         'Same sensortype was not returned.')
        # test update
        self.assertEqual(retrieved.description, '')
        retrieved.description = DUMMY_DESCRIPTION
        saved = SensorType.add_or_update(retrieved)
        retrieved = SensorType.get_by_id(saved.id)
        self.assertEqual(retrieved.description, DUMMY_DESCRIPTION, 'Update to sensortype failed.')
        # cleanup
        SensorModelTest._delete(SensorType, [retrieved])
        try:
            retrieved = SensorType.get_by_id(saved.id)
        except ValueError:
            retrieved = None
        self.assertIsNone(retrieved, 'managed to retrieve after delete.')

    def test_sensor_instance_cud(self):
        sensor_type = SensorModelTest._create_save_sensor_type()
        saved = SensorModelTest._create_save_sensor_instance(
            sensor_type_ref=sensor_type.get_reference().ref)
        retrieved = SensorInstance.get_by_id(saved.id)
        self.assertEqual(saved.name, retrieved.name,
                         'Same sensortype was not returned.')
        # test update
        self.assertEqual(retrieved.enabled, True)
        retrieved.enabled = False
        saved = SensorInstance.add_or_update(retrieved)
        retrieved = SensorInstance.get_by_id(saved.id)
        self.assertEqual(retrieved.enabled, False, 'Update to sensorinstance failed.')
        # cleanup
        SensorModelTest._delete(SensorInstance, [retrieved])
        SensorModelTest._delete(SensorType, [sensor_type])
        try:
            retrieved = SensorInstance.get_by_id(saved.id)
        except ValueError:
            retrieved = None
        self.assertIsNone(retrieved, 'managed to retrieve after delete.')

    def test_sensor_execution_cud(self):
        sensor_type = SensorModelTest._create_save_sensor_type()
        sensor_instance = SensorModelTest._create_save_sensor_instance(
            sensor_type_ref=sensor_type.get_reference().ref)
        saved = SensorModelTest._create_save_sensor_execution(
            sensor_instance_ref=sensor_instance.get_reference().ref)
        retrieved = SensorExecution.get_by_id(saved.id)
        self.assertEqual(saved.sensor_instance, retrieved.sensor_instance,
                         'Same sensorinstance was not returned.')
        # test update
        self.assertEqual(retrieved.sensor_node, 'sensor_node_1')
        retrieved.sensor_node = 'sensor_node_2'
        saved = SensorExecution.add_or_update(retrieved)
        retrieved = SensorExecution.get_by_id(saved.id)
        self.assertEqual(retrieved.sensor_node, 'sensor_node_2',
                         'Update to sensorexecution failed.')
        # cleanup
        SensorModelTest._delete(SensorExecution, [retrieved])
        SensorModelTest._delete(SensorInstance, [sensor_instance])
        SensorModelTest._delete(SensorType, [sensor_type])
        try:
            retrieved = SensorExecution.get_by_id(saved.id)
        except ValueError:
            retrieved = None
        self.assertIsNone(retrieved, 'managed to retrieve after delete.')

    @staticmethod
    def _create_save_sensor_type():
        created = SensorTypeDB(name='sensor_type-1', pack='test_pack', description='',
                               artifact_uri='file://sensortype.yaml',
                               entry_point='module.foo.ClassSensor', trigger_types=[],
                               parameters_schema={})
        return SensorType.add_or_update(created)

    @staticmethod
    def _create_save_sensor_instance(sensor_type_ref):
        created = SensorInstanceDB(name='sensor_instance-1', pack='test_pack',
                                   sensor_type=sensor_type_ref, parameters={})
        return SensorInstance.add_or_update(created)

    @staticmethod
    def _create_save_sensor_execution(sensor_instance_ref):
        created = SensorExecutionDB(status='RUNNING', sensor_node='sensor_node_1',
                                    sensor_instance=sensor_instance_ref)
        return SensorExecution.add_or_update(created)

    @staticmethod
    def _delete(access, db_objects):
        for db_object in db_objects:
            access.delete(db_object)

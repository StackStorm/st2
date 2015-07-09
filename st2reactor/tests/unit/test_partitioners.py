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

from oslo_config import cfg

from st2common.constants.sensors import KVSTORE_PARTITION_LOADER, FILE_PARTITION_LOADER, \
    HASH_PARTITION_LOADER
from st2common.models.db.keyvalue import KeyValuePairDB
from st2common.persistence.keyvalue import KeyValuePair
from st2reactor.container.partitioner_lookup import get_sensors_partitioner
from st2reactor.container.hash_partitioner import Range
from st2tests import config
from st2tests import DbTestCase
from st2tests.fixturesloader import FixturesLoader

PACK = 'generic'
FIXTURES_1 = {
    'sensors': ['sensor1.yaml', 'sensor2.yaml', 'sensor3.yaml']
}


class PartitionerTest(DbTestCase):

    models = None

    @classmethod
    def setUpClass(cls):
        super(PartitionerTest, cls).setUpClass()
        # Create TriggerTypes before creation of Rule to avoid failure. Rule requires the
        # Trigger and therefore TriggerType to be created prior to rule creation.
        cls.models = FixturesLoader().save_fixtures_to_db(
            fixtures_pack=PACK, fixtures_dict=FIXTURES_1)
        config.parse_args()

    def test_default_partitioner(self):
        provider = get_sensors_partitioner()
        sensors = provider.get_sensors()

        self.assertEqual(len(sensors), len(FIXTURES_1['sensors']),
                         'Failed to provider all sensors')

        sensor1 = self.models['sensors']['sensor1.yaml']
        self.assertTrue(provider.is_sensor_owner(sensor1))

    def test_kvstore_partitioner(self):
        cfg.CONF.set_override(name='partition_provider',
                              override={'name': KVSTORE_PARTITION_LOADER},
                              group='sensorcontainer')
        kvp = KeyValuePairDB(**{'name': 'sensornode1.sensor_partition',
                                'value': 'generic.Sensor1, generic.Sensor2'})
        KeyValuePair.add_or_update(kvp, publish=False, dispatch_trigger=False)

        provider = get_sensors_partitioner()
        sensors = provider.get_sensors()

        self.assertEqual(len(sensors), len(kvp.value.split(',')))

        sensor1 = self.models['sensors']['sensor1.yaml']
        self.assertTrue(provider.is_sensor_owner(sensor1))

        sensor3 = self.models['sensors']['sensor3.yaml']
        self.assertFalse(provider.is_sensor_owner(sensor3))

    def test_file_partitioner(self):
        partition_file = FixturesLoader().get_fixture_file_path_abs(
            fixtures_pack=PACK, fixtures_type='sensors', fixture_name='partition_file.yaml')
        cfg.CONF.set_override(name='partition_provider',
                              override={'name': FILE_PARTITION_LOADER,
                                        'partition_file': partition_file},
                              group='sensorcontainer')

        provider = get_sensors_partitioner()
        sensors = provider.get_sensors()

        self.assertEqual(len(sensors), 2)

        sensor1 = self.models['sensors']['sensor1.yaml']
        self.assertTrue(provider.is_sensor_owner(sensor1))

        sensor3 = self.models['sensors']['sensor3.yaml']
        self.assertFalse(provider.is_sensor_owner(sensor3))

    def test_hash_partitioner(self):
        # no specific partitioner testing here for that see test_hash_partitioner.py
        # This test is to make sure the wiring and some basics work
        cfg.CONF.set_override(name='partition_provider',
                              override={'name': HASH_PARTITION_LOADER,
                                        'hash_ranges': '%s..%s' % (Range.RANGE_MIN_ENUM,
                                                                   Range.RANGE_MAX_ENUM)},
                              group='sensorcontainer')

        provider = get_sensors_partitioner()
        sensors = provider.get_sensors()

        self.assertEqual(len(sensors), 3)

        sensor1 = self.models['sensors']['sensor1.yaml']
        self.assertTrue(provider.is_sensor_owner(sensor1))

        sensor2 = self.models['sensors']['sensor2.yaml']
        self.assertTrue(provider.is_sensor_owner(sensor2))

        sensor3 = self.models['sensors']['sensor3.yaml']
        self.assertTrue(provider.is_sensor_owner(sensor3))

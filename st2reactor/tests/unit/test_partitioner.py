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

from st2common.constants.sensors import KVSTORE_PARTITION_LOADER, FILE_PARTITION_LOADER
from st2common.models.db.keyvalue import KeyValuePairDB
from st2common.persistence.keyvalue import KeyValuePair
from st2reactor.container import partitioner
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
        sensors = partitioner.get_sensors()
        self.assertEqual(len(sensors), len(FIXTURES_1['sensors']),
                         'Failed to provider all sensors')

    def test_kvstore__partitioner(self):
        cfg.CONF.set_override(name='partition_provider',
                              override={'name': KVSTORE_PARTITION_LOADER},
                              group='sensorcontainer')
        kvp = KeyValuePairDB(**{'name': 'sensornode1.sensor_partition',
                                'value': 'generic.Sensor1, generic.Sensor2'})
        KeyValuePair.add_or_update(kvp, publish=False, dispatch_trigger=False)
        sensors = partitioner.get_sensors()
        self.assertEqual(len(sensors), len(kvp.value.split(',')))

    def test_file__partitioner(self):
        partition_file = FixturesLoader().get_fixture_file_path_abs(
            fixtures_pack=PACK, fixtures_type='sensors', fixture_name='partition_file.yaml')
        cfg.CONF.set_override(name='partition_provider',
                              override={'name': FILE_PARTITION_LOADER,
                                        'partition_file': partition_file},
                              group='sensorcontainer')
        sensors = partitioner.get_sensors()
        self.assertEqual(len(sensors), 2)

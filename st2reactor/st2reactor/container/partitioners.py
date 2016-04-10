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

import sets
import yaml

from st2common import log as logging
from st2common.exceptions.sensors import SensorNotFoundException, \
    SensorPartitionMapMissingException
from st2common.persistence.keyvalue import KeyValuePair
from st2common.persistence.sensor import SensorType


__all__ = [
    'get_all_enabled_sensors',
    'DefaultPartitioner',
    'KVStorePartitioner',
    'FileBasedPartitioner',
    'SingleSensorPartitioner'
]

LOG = logging.getLogger(__name__)


def get_all_enabled_sensors():
    # only query for enabled sensors.
    sensors = SensorType.query(enabled=True)
    LOG.info('Found %d registered sensors in db scan.', len(sensors))
    return sensors


class DefaultPartitioner(object):

    def __init__(self, sensor_node_name):
        self.sensor_node_name = sensor_node_name

    def is_sensor_owner(self, sensor_db):
        """
        All sensors are supported
        """
        # No enabled check here as this could also be due to a delete or update
        return sensor_db is not None

    def get_sensors(self):
        all_enabled_sensors = get_all_enabled_sensors()

        sensor_refs = self.get_required_sensor_refs()

        # None has special meaning and is different from empty array.
        if sensor_refs is None:
            return all_enabled_sensors

        partition_members = []

        for sensor in all_enabled_sensors:
            # pylint: disable=unsupported-membership-test
            sensor_ref = sensor.get_reference()
            if sensor_ref.ref in sensor_refs:
                partition_members.append(sensor)

        return partition_members

    def get_required_sensor_refs(self):
        return None


class KVStorePartitioner(DefaultPartitioner):

    def __init__(self, sensor_node_name):
        super(KVStorePartitioner, self).__init__(sensor_node_name=sensor_node_name)
        self._supported_sensor_refs = None

    def is_sensor_owner(self, sensor_db):
        return sensor_db.get_reference().ref in self._supported_sensor_refs

    def get_required_sensor_refs(self):
        partition_lookup_key = self._get_partition_lookup_key(self.sensor_node_name)

        kvp = KeyValuePair.get_by_name(partition_lookup_key)
        sensor_refs_str = kvp.value if kvp.value else ''
        self._supported_sensor_refs = sets.Set([
            sensor_ref.strip() for sensor_ref in sensor_refs_str.split(',')])
        return self._supported_sensor_refs

    def _get_partition_lookup_key(self, sensor_node_name):
        return '{}.sensor_partition'.format(sensor_node_name)


class FileBasedPartitioner(DefaultPartitioner):

    def __init__(self, sensor_node_name, partition_file):
        super(FileBasedPartitioner, self).__init__(sensor_node_name=sensor_node_name)
        self.partition_file = partition_file
        self._supported_sensor_refs = None

    def is_sensor_owner(self, sensor_db):
        return sensor_db.get_reference().ref in self._supported_sensor_refs and sensor_db.enabled

    def get_required_sensor_refs(self):
        with open(self.partition_file, 'r') as f:
            partition_map = yaml.safe_load(f)
            sensor_refs = partition_map.get(self.sensor_node_name, None)
            if sensor_refs is None:
                raise SensorPartitionMapMissingException('Sensor partition not found for %s in %s.',
                                                         self.sensor_node_name, self.partition_file)
            self._supported_sensor_refs = sets.Set(sensor_refs)
            return self._supported_sensor_refs


class SingleSensorPartitioner(object):

    def __init__(self, sensor_ref):
        self._sensor_ref = sensor_ref

    def get_sensors(self):
        sensor = SensorType.get_by_ref(self._sensor_ref)
        if not sensor:
            raise SensorNotFoundException('Sensor %s not found in db.' % self._sensor_ref)
        return [sensor]

    def is_sensor_owner(self, sensor_db):
        """
        No other sensor supported just the single sensor which was previously loaded.
        """
        return False

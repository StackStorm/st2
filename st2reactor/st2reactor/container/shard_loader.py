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

import copy
import sets
import yaml

from oslo_config import cfg

from st2common import log as logging
from st2common.exceptions.sensors import SensorNotFoundException, \
    SensorShardProviderNotSupportedException, SensorPartitionMapMissingException
from st2common.persistence.keyvalue import KeyValuePair
from st2common.persistence.sensor import SensorType
from st2common.constants.sensors import DEFAULT_SHARD_LOADER, KVSTORE_SHARD_LOADER, FILE_SHARD_LOADER

__all__ = [
    'get_sensors'
]

LOG = logging.getLogger(__name__)


def _get_all_enabled_sensors():
    # only query for enabled sensors.
    sensors = SensorType.query(enabled=True)
    LOG.info('Found %d registered sensors in db scan.', len(sensors))
    return sensors


class DefaultShardProvider(object):

    def __init__(self, sensor_node_name):
        self.sensor_node_name = sensor_node_name

    def get_sensors(self):
        all_enabled_sensors = _get_all_enabled_sensors()

        sensor_refs = self.get_required_sensor_refs()

        # None has special meaning and is different from empty array.
        if sensor_refs is None:
            return all_enabled_sensors

        shard_members = []

        for sensor in all_enabled_sensors:
            sensor_ref = sensor.get_reference()
            if sensor_ref.ref in sensor_refs:
                shard_members.append(sensor)

        return shard_members

    def get_required_sensor_refs(self):
        return None


class KVStoreShardProvider(DefaultShardProvider):

    def __init__(self, sensor_node_name):
        self.sensor_node_name = sensor_node_name

    def get_required_sensor_refs(self):
        shard_lookup_key = self._get_shard_lookup_key(self.sensor_node_name)

        kvp = KeyValuePair.get_by_name(shard_lookup_key)
        sensor_refs_str = kvp.value if kvp.value else ''
        return sets.Set([sensor_ref.strip() for sensor_ref in sensor_refs_str.split(',')])

    def _get_shard_lookup_key(self, sensor_node_name):
        return '{}.shard'.format(sensor_node_name)


class FileBasedShardProvider(DefaultShardProvider):

    def __init__(self, sensor_node_name, shard_file):
        self.sensor_node_name = sensor_node_name
        self.shard_file = shard_file

    def get_required_sensor_refs(self):
        with open(self.shard_file, 'r') as f:
            shard_map = yaml.safe_load(f)
            sensor_refs = shard_map.get(self.sensor_node_name, None)
            if sensor_refs is None:
                raise SensorPartitionMapMissingException('Sensor partition not found for %s in %s.',
                                                         self.sensor_node_name, self.shard_file)
            return sets.Set(sensor_refs)


class SingleSensorProvider(object):

    def get_sensors(self, sensor_ref):
        sensor = SensorType.get_by_ref(sensor_ref)
        if not sensor:
            raise SensorNotFoundException('Sensor %s not found in db.' % sensor_ref)
        return [sensor]


PROVIDERS = {
    DEFAULT_SHARD_LOADER: DefaultShardProvider,
    KVSTORE_SHARD_LOADER: KVStoreShardProvider,
    FILE_SHARD_LOADER: FileBasedShardProvider
}


def get_sensors():
    if cfg.CONF.sensor_ref:
        return SingleSensorProvider().get_sensors(sensor_ref=cfg.CONF.sensor_ref)
    LOG.info('shard_provider [%s]%s', type(cfg.CONF.sensorcontainer.shard_provider),
             cfg.CONF.sensorcontainer.shard_provider)
    shard_provider_config = copy.copy(cfg.CONF.sensorcontainer.shard_provider)
    shard_provider = shard_provider_config.pop('name')
    sensor_node_name = cfg.CONF.sensorcontainer.sensor_node_name

    provider = PROVIDERS.get(shard_provider.lower(), None)
    if not provider:
        raise SensorShardProviderNotSupportedException(
            'Shard provider %s not found.' % shard_provider)

    # pass in extra config with no analysis
    return provider(sensor_node_name=sensor_node_name, **shard_provider_config).get_sensors()

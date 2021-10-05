# Copyright 2020 The StackStorm Authors.
# Copyright 2019 Extreme Networks, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import absolute_import
import copy
from oslo_config import cfg

from st2common import log as logging
from st2common.constants.sensors import (
    DEFAULT_PARTITION_LOADER,
    KVSTORE_PARTITION_LOADER,
    FILE_PARTITION_LOADER,
    HASH_PARTITION_LOADER,
)
from st2common.exceptions.sensors import SensorPartitionerNotSupportedException
from st2reactor.container.partitioners import (
    DefaultPartitioner,
    KVStorePartitioner,
    FileBasedPartitioner,
    SingleSensorPartitioner,
)
from st2reactor.container.hash_partitioner import HashPartitioner

__all__ = ["get_sensors_partitioner"]

LOG = logging.getLogger(__name__)

PROVIDERS = {
    DEFAULT_PARTITION_LOADER: DefaultPartitioner,
    KVSTORE_PARTITION_LOADER: KVStorePartitioner,
    FILE_PARTITION_LOADER: FileBasedPartitioner,
    HASH_PARTITION_LOADER: HashPartitioner,
}


def get_sensors_partitioner():
    if cfg.CONF.sensor_ref:
        LOG.info("Running in single sensor mode, using a single sensor partitioner...")
        return SingleSensorPartitioner(sensor_ref=cfg.CONF.sensor_ref)

    partition_provider_config = copy.copy(cfg.CONF.sensorcontainer.partition_provider)
    partition_provider = partition_provider_config.pop("name")
    sensor_node_name = cfg.CONF.sensorcontainer.sensor_node_name

    provider = PROVIDERS.get(partition_provider.lower(), None)
    if not provider:
        raise SensorPartitionerNotSupportedException(
            "Partition provider %s not found." % (partition_provider)
        )

    LOG.info(
        "Using partitioner %s with sensornode %s.", partition_provider, sensor_node_name
    )

    # pass in extra config with no analysis
    return provider(sensor_node_name=sensor_node_name, **partition_provider_config)

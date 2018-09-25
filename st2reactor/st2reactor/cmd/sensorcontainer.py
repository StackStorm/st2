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

from __future__ import absolute_import

import sys

from oslo_config import cfg

from st2common import log as logging
from st2common.logging.misc import get_logger_name_for_module
from st2common.service import PassiveService
from st2common.service import run_service
from st2common.util.monkey_patch import monkey_patch
from st2reactor.sensor import config
from st2reactor.container.manager import SensorContainerManager
from st2reactor.container.partitioner_lookup import get_sensors_partitioner

__all__ = [
    'main'
]

monkey_patch()

LOGGER_NAME = get_logger_name_for_module(sys.modules[__name__])
LOG = logging.getLogger(LOGGER_NAME)


class SensorContainerService(PassiveService):
    name = 'sensorcontainer'

    config = config

    setup_db = True
    register_mq_exchanges = True
    register_signal_handlers = True
    run_migrations = True

    def start(self):
        single_sensor_mode = (cfg.CONF.single_sensor_mode or
                              cfg.CONF.sensorcontainer.single_sensor_mode)

        if single_sensor_mode and not cfg.CONF.sensor_ref:
            raise ValueError('--sensor-ref argument must be provided when running in single '
                             'sensor mode')

        sensors_partitioner = get_sensors_partitioner()
        container_manager = SensorContainerManager(sensors_partitioner=sensors_partitioner,
                                                   single_sensor_mode=single_sensor_mode)
        return container_manager.run_sensors()


def main():
    service = SensorContainerService(logger=LOG)
    exit_code = run_service(service=service)
    return exit_code

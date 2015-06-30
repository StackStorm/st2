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
import sys

import eventlet

from st2common import log as logging
from st2common.service_setup import setup as common_setup
from st2common.service_setup import teardown as common_teardown
from st2common.exceptions.sensors import SensorNotFoundException
from st2common.persistence.sensor import SensorType
from st2reactor.sensor import config
from st2reactor.container.manager import SensorContainerManager
from st2reactor.container.shard_loader import get_sensors

eventlet.monkey_patch(
    os=True,
    select=True,
    socket=True,
    thread=False if '--use-debugger' in sys.argv else True,
    time=True)


LOG = logging.getLogger('st2reactor.bin.sensors_manager')


def _setup():
    common_setup(service='sensorcontainer', config=config, setup_db=True,
                 register_mq_exchanges=True, register_signal_handlers=True)


def _teardown():
    common_teardown()


def _get_all_enabled_sensors():
    # only query for enabled sensors.
    sensors = SensorType.query(enabled=True)
    LOG.info('Found %d registered sensors in db scan.', len(sensors))
    return sensors


def main():
    try:
        _setup()
        container_manager = SensorContainerManager()
        sensors = get_sensors()
        if not sensors:
            msg = 'No sensors configured to run. See http://docs.stackstorm.com/sensors.html. ' + \
                  'Register some sensors and a container will pick them to run.'
            LOG.info(msg)

        return container_manager.run_sensors(sensors=sensors)
    except SystemExit as exit_code:
        return exit_code
    except SensorNotFoundException as e:
        LOG.exception(e)
        return 1
    except:
        LOG.exception('(PID:%s) SensorContainer quit due to exception.', os.getpid())
        return 2
    finally:
        _teardown()

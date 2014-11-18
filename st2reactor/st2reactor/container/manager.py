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

from oslo.config import cfg

from st2common import log as logging
from st2common.persistence.reactor import Trigger
from st2common.transport.reactor import TriggerCUDPublisher
from st2reactor.container.process_container import ProcessSensorContainer

LOG = logging.getLogger(__name__)


class SensorContainerManager(object):
    # TODO: Load balancing for sensors.
    def __init__(self, max_containers=10):
        self._max_containers = max_containers

    def run_sensors(self, sensors):
        """
        :param sensors: A list of DB models of sensors to run.
        :type sensors: ``list``
        """
        LOG.info('Setting up container to run %d sensors.', len(sensors))

        sensors_to_run = []
        for sensor in sensors:
            # TODO: Directly pass DB object to the ProcessContainer
            file_path = sensor.artifact_uri.replace('file://', '')
            class_name = sensor.entry_point.split('.')[-1]

            sensor_obj = {
                'pack': sensor.pack,
                'file_path': file_path,
                'class_name': class_name,
                'trigger_types': sensor.trigger_types,
                'poll_interval': sensor.poll_interval
            }
            sensors_to_run.append(sensor_obj)

        trigger_cud_publisher = TriggerCUDPublisher(url=cfg.CONF.messaging.url)
        for trigger in Trigger.get_all():
            # Dispatch create Trigger CUD events for all the existing Triggers
            # in the DB. Those events are consumer by the sensor wrapper
            trigger_cud_publisher.publish_create(payload=trigger)

        LOG.info('(PID:%s) SensorContainer started.', os.getpid())
        sensor_container = ProcessSensorContainer(sensors=sensors_to_run)
        try:
            exit_code = sensor_container.run()
            LOG.info('(PID:%s) SensorContainer stopped. Reason - run ended.', os.getpid())
            return exit_code
        except (KeyboardInterrupt, SystemExit):
            LOG.info('(PID:%s) SensorContainer stopped. Reason - %s', os.getpid(),
                     sys.exc_info()[0].__name__)
            return 0

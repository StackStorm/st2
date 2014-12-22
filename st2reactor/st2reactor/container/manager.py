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
import signal

from st2common import log as logging
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

        LOG.info('(PID:%s) SensorContainer started.', os.getpid())
        sensor_container = ProcessSensorContainer(sensors=sensors_to_run)

        def sigterm_handler(signum=None, frame=None):
            # This will cause SystemExit to be throw and we call sensor_container.shutdown()
            # there which cleans things up.
            sys.exit(0)

        # Register a SIGTERM signal handler which calls sys.exit which causes SystemExit to
        # be thrown. We catch SystemExit and handle cleanup there.
        signal.signal(signal.SIGTERM, sigterm_handler)

        try:
            exit_code = sensor_container.run()
            LOG.info('(PID:%s) SensorContainer stopped. Reason - run ended.', os.getpid())
            return exit_code
        except (KeyboardInterrupt, SystemExit):
            sensor_container.shutdown()

            LOG.info('(PID:%s) SensorContainer stopped. Reason - %s', os.getpid(),
                     sys.exc_info()[0].__name__)
            return 0

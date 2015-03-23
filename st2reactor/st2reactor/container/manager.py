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
from st2common.services.sensor_watcher import SensorWatcher
LOG = logging.getLogger(__name__)


class SensorContainerManager(object):
    # TODO: Load balancing for sensors.
    def __init__(self, max_containers=10):
        self._max_containers = max_containers
        self._sensor_container = None
        self._sensors_watcher = SensorWatcher(create_handler=self._handle_create_sensor,
                                              update_handler=self._handle_update_sensor,
                                              delete_handler=self._handle_delete_sensor,
                                              queue_suffix='sensors')
        self._sensors_watcher.start()

    def run_sensors(self, sensors):
        """
        :param sensors: A list of DB models of sensors to run.
        :type sensors: ``list``
        """
        LOG.info('Setting up container to run %d sensors.', len(sensors))

        sensors_to_run = []
        for sensor in sensors:
            # TODO: Directly pass DB object to the ProcessContainer
            sensors_to_run.append(self._to_sensor_object(sensor))

        LOG.info('(PID:%s) SensorContainer started.', os.getpid())
        self._sensor_container = ProcessSensorContainer(sensors=sensors_to_run)

        def sigterm_handler(signum=None, frame=None):
            # This will cause SystemExit to be throw and we call sensor_container.shutdown()
            # there which cleans things up.
            sys.exit(0)

        # Register a SIGTERM signal handler which calls sys.exit which causes SystemExit to
        # be thrown. We catch SystemExit and handle cleanup there.
        signal.signal(signal.SIGTERM, sigterm_handler)

        try:
            exit_code = self._sensor_container.run()
            LOG.info('(PID:%s) SensorContainer stopped. Reason - run ended.', os.getpid())
            return exit_code
        except (KeyboardInterrupt, SystemExit):
            self._sensor_container.shutdown()

            # XXX: kill sensor watcher thread.
            self._sensors_watcher.shutdown()

            LOG.info('(PID:%s) SensorContainer stopped. Reason - %s', os.getpid(),
                     sys.exc_info()[0].__name__)
            return 0

    def _to_sensor_object(self, sensor_db):
        file_path = sensor_db.artifact_uri.replace('file://', '')
        class_name = sensor_db.entry_point.split('.')[-1]

        sensor_obj = {
            'pack': sensor_db.pack,
            'file_path': file_path,
            'class_name': class_name,
            'trigger_types': sensor_db.trigger_types,
            'poll_interval': sensor_db.poll_interval
        }

        return sensor_obj
    #################################################
    # Event handler methods for the sensor CUD events
    #################################################

    def _handle_create_sensor(self, sensor):
        LOG.debug('Calling "add_sensor" method (sensor.type=%s)' % (sensor.type))
        sensor = self._sanitize_sensor(sensor=sensor)
        self._sensor_container.add_sensor(sensor=self._to_sensor_object(sensor))

    def _handle_update_sensor(self, sensor):
        LOG.debug('Calling "update_sensor" method (sensor.type=%s)' % (sensor.type))
        sensor = self._sanitize_sensor(sensor=sensor)
        LOG.warning('Sensor %s updated. Not doing anything.', sensor)

    def _handle_delete_sensor(self, sensor):
        LOG.debug('Calling "remove_sensor" method (sensor.type=%s)' % (sensor.type))
        sensor = self._sanitize_sensor(sensor=sensor)
        self._sensor_container.remove_sensor(sensor=self._to_sensor_object(sensor))

    def _sanitize_sensor(self, sensor):
        sanitized = sensor._data
        if 'id' in sanitized:
            # Friendly objectid rather than the MongoEngine representation.
            sanitized['id'] = str(sanitized['id'])
        return sanitized

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
import atexit
import imp
import sys
import logging
import httplib
import argparse
import json

import requests

import logging as slogging

from st2common import config
from st2common import log as logging
from st2common.util.config_parser import ContentPackConfigParser
from st2reactor.container.triggerwatcher import TriggerWatcher

__all__ = [
    'SensorWrapper'
]

# TODO: Implement trigger API endpoint authentication with per-sensor secret key


class SensorWrapper(object):
    def __init__(self, sensor_file_path, sensor_class_name, sensor_config_path,
                 trigger_types):
        """
        :param sensor_file_path: Path to the sensor module file.
        :type sensor_file_path: ``str``

        :param sensor_class_name: Sensor class name.
        :type sensor_class_name: ``str``

        :param trigger_types: A list of references to trigger types which
                                  belong to this sensor.
        :type trigger_types: ``list`` of ``str``
        """
        self._sensor_file_path = sensor_file_path
        self._sensor_class_name = sensor_class_name
        self._sensor_config_path = sensor_config_path
        self._trigger_types = trigger_types or []

        # TODO: Inherit args from the parent
        config.parse_args(args={})

        # TODO: Use per sensor queue so we don't only get events for this
        # particular sensor
        self._trigger_watcher = TriggerWatcher(create_handler=self._handle_create_trigger,
                                               update_handler=self._handle_update_trigger,
                                               delete_handler=self._handle_delete_trigger)

        self._sensor_instance = self._get_sensor_instance()
        self._logger = logging.getLogger('SensorWrapper.%s' %
                                         (self._sensor_class_name))
        self._logger.setLevel(slogging.DEBUG)
        ch = slogging.StreamHandler(sys.stdout)
        ch.setLevel(slogging.DEBUG)
        formatter = slogging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        ch.setFormatter(formatter)
        self._logger.addHandler(ch)

    ##############################################
    # Event handler methods for the trigger events
    ##############################################

    def _handle_create_trigger(self, trigger):
        # TODO: Only handle it if the trigger refers to the current sensor
        trigger = self._sanitize_trigger(trigger=trigger)
        self._sensor_instance.add_trigger(trigger=trigger)
        pass

    def _handle_update_trigger(self, trigger):
        # TODO: Only handle it if the trigger refers to the current sensor
        trigger = self._sanitize_trigger(trigger=trigger)
        self._sensor_instance.update_trigger(trigger=trigger)
        pass

    def _handle_delete_trigger(self, trigger):
        # TODO: Only handle it if the trigger refers to the current sensor
        trigger = self._sanitize_trigger(trigger=trigger)
        self._sensor_instance.remove_trigger(trigger=trigger)

    def dispatch(self, trigger, payload=None):
        """
        Method which sends trigger to the API and is called by the sensor
        class.

        :param trigger: Full name / reference of the trigger.
        :type trigger: ``str``

        :param payload: Trigger payload.
        :type payload: ``dict``
        """
        assert(isinstance(trigger, (str, unicode)))
        assert(isinstance(payload, (type(None), dict)))

        self._logger.debug('Dispatching trigger (trigger=%s,payload=%s)', trigger, payload)
        data = json.dumps(payload)
        # TODO: Send trigger via API
        response = requests.post(url=self._api_endpoint, data=data)

        if response.status_code == httplib.OK:
            self._logger.debug('Sucessfully sent trigger to the API')
        else:
            self._logger.debug('Failed to send trigger to the API: %s',
                               response.text)

    def run(self):
        atexit.register(self.stop)

        self._logger.debug('Running sensor initialization code')
        self._sensor_instance.setup()

        self._trigger_watcher.start()
        self._logger.debug('Watcher started')

        self._logger.debug('Running sensor')

        try:
            self._sensor_instance.start()
        except Exception as e:
            self._logger.exception('Failed to start the sensor: %s' % (str(e)))
            sys.exit(1)

    def stop(self):
        # Stop watcher
        self._logger.debug('Stopping trigger watcher')
        self._trigger_watcher.start()

        # Run sensor cleanup code
        self._logger.debug('Invoking cleanup on sensor')
        self._sensor_instance.stop()

    def _get_sensor_instance(self):
        """
        Retrieve instance of a sensor class.
        """
        _, filename = os.path.split(self._sensor_file_path)
        module_name, _ = os.path.splitext(filename)

        sensor_module = imp.load_source(module_name, self._sensor_file_path)
        sensor_class = getattr(sensor_module, self._sensor_class_name, None)

        if not sensor_class:
            raise ValueError('Sensor module is missing a class with name "%s"' %
                             (self._sensor_class_name))

        sensor_config = self._get_sensor_config()
        sensor_instance = sensor_class(container_service=self,
                                       config=sensor_config)

        return sensor_instance

    def _get_sensor_config(self):
        if not self._sensor_config_path or not os.path.isfile(self._sensor_config_path):
            return {}

        config_path = self._sensor_config_path
        config = ContentPackConfigParser.get_and_parse_config(config_path=config_path)

        if config:
            return config.config
        else:
            return {}

    def _sanitize_trigger(self, trigger):
        sanitized = trigger._data
        if 'id' in sanitized:
            # Friendly objectid rather than the MongoEngine representation.
            sanitized['id'] = str(sanitized['id'])
        return sanitized


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Sensor runner wrapper')
    parser.add_argument('--sensor-file-path', required=True,
                        help='Path to the sensor module')
    parser.add_argument('--sensor-class-name', required=True,
                        help='Name of the sensor class')
    parser.add_argument('--sensor-config-path', required=False,
                        help='Path to the pack config')
    parser.add_argument('--trigger-type-refs', required=False,
                        help='Comma delimited string of trigger type references')
    args = parser.parse_args()

    trigger_types = args.trigger_types
    trigger_types = trigger_types.split(',') if trigger_types else []

    obj = SensorWrapper(sensor_file_path=args.sensor_file_path,
                        sensor_class_name=args.sensor_class_name,
                        sensor_config_path=args.sensor_config_path,
                        trigger_types=trigger_types)
    obj.run()

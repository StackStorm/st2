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

import eventlet
import logging as slogging

from st2common import config
from st2common import log as logging
from st2common.util.config_parser import ContentPackConfigParser
from st2reactor.container.triggerwatcher import TriggerWatcher
from st2common.constants.pack import SYSTEM_PACK_NAMES

__all__ = [
    'SensorWrapper'
]


class SensorWrapper(object):
    def __init__(self, pack, file_path, class_name, trigger_types,
                 poll_interval=5):
        """
        :param pack: Name of the pack this sensor belongs to.
        :type pack: ``str``

        :param file_path: Path to the sensor module file.
        :type file_path: ``str``

        :param class_name: Sensor class name.
        :type class_name: ``str``

        :param trigger_types: A list of references to trigger types which
                                  belong to this sensor.
        :type trigger_types: ``list`` of ``str``

        :param poll_interval: Sensor poll interval (in seconds).
        :type poll_interval: ``int``
        """
        self._pack = pack
        self._file_path = file_path
        self._class_name = class_name
        self._trigger_types = trigger_types or []
        self._poll_interval = poll_interval
        self._trigger_names = {}

        # TODO: Inherit args from the parent
        config.parse_args(args={})

        # TODO: Use per sensor queue so we don't only get events for this
        # particular sensor
        self._trigger_watcher = TriggerWatcher(create_handler=self._handle_create_trigger,
                                               update_handler=self._handle_update_trigger,
                                               delete_handler=self._handle_delete_trigger)

        self._logger = logging.getLogger('SensorWrapper.%s' %
                                         (self._class_name))
        self._sensor_instance = self._get_sensor_instance()
        self._logger.setLevel(slogging.DEBUG)
        ch = slogging.StreamHandler(sys.stdout)
        ch.setLevel(slogging.DEBUG)
        formatter = slogging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        ch.setFormatter(formatter)
        self._logger.addHandler(ch)

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
        # TODO: Dispatch event via queue

    def run(self):
        atexit.register(self.stop)

        self._logger.debug('Running sensor initialization code')
        self._sensor_instance.setup()

        self._trigger_watcher.start()
        self._logger.debug('Watcher started')

        self._logger.debug('Starting sensor poll loop (interval=%s)',
                           self._poll_interval)

        while True:
            try:
                self._sensor_instance.poll()
            except Exception as e:
                self._logger.exception('Sensor raised an exception during poll: %s', (str(e)))
            eventlet.sleep(self._poll_interval)

    def stop(self):
        # Stop watcher
        self._logger.debug('Stopping trigger watcher')
        self._trigger_watcher.start()

        # Run sensor cleanup code
        self._logger.debug('Invoking cleanup on sensor')
        self._sensor_instance.stop()

    ##############################################
    # Event handler methods for the trigger events
    ##############################################

    def _handle_create_trigger(self, trigger):
        trigger_type_ref = trigger.type
        if trigger_type_ref not in self._trigger_type_refs:
            # This trigger doesn't belong to this sensor
            return

        self._trigger_names[str(trigger.id)] = trigger

        trigger = self._sanitize_trigger(trigger=trigger)
        self._sensor_instance.add_trigger(trigger=trigger)

    def _handle_update_trigger(self, trigger):
        trigger_type_ref = trigger.type
        if trigger_type_ref not in self._trigger_type_refs:
            # This trigger doesn't belong to this sensor
            return

        self._trigger_names[str(trigger.id)] = trigger

        trigger = self._sanitize_trigger(trigger=trigger)
        self._sensor_instance.update_trigger(trigger=trigger)

    def _handle_delete_trigger(self, trigger):
        trigger_type_ref = trigger.type
        if trigger_type_ref not in self._trigger_type_refs:
            # This trigger doesn't belong to this sensor
            return

        trigger_id = str(trigger.id)
        if trigger_id not in self._trigger_names:
            return

        del self._trigger_names[trigger_id]

        trigger = self._sanitize_trigger(trigger=trigger)
        self._sensor_instance.remove_trigger(trigger=trigger)

    def _call_sensor_method(self, method_name, args, kwargs):
        """
        Call the provided sensor method (if exists) with the provided args and
        kwargs.
        """
        pass

    def _get_sensor_instance(self):
        """
        Retrieve instance of a sensor class.
        """
        _, filename = os.path.split(self._file_path)
        module_name, _ = os.path.splitext(filename)

        sensor_module = imp.load_source(module_name, self._file_path)
        sensor_class = getattr(sensor_module, self._class_name, None)

        if not sensor_class:
            raise ValueError('Sensor module is missing a class with name "%s"' %
                             (self._class_name))

        sensor_class_kwargs = {
            'container_service': self
        }
        sensor_config = self._get_sensor_config()

        if self._pack not in SYSTEM_PACK_NAMES:
            sensor_class_kwargs['config'] = sensor_config

        sensor_instance = sensor_class(**sensor_class_kwargs)

        return sensor_instance

    def _get_sensor_config(self):
        config_parser = ContentPackConfigParser(pack_name=self._pack)
        config = config_parser.get_sensor_config(sensor_file_path=self._file_path)

        if config:
            self._logger.info('Using config "%s" for sensor "%s"' % (config.file_path,
                                                                     self._class_name))
            return config.config
        else:
            self._logger.info('No config found for sensor "%s"' % (self._class_name))
            return {}

    def _sanitize_trigger(self, trigger):
        sanitized = trigger._data
        if 'id' in sanitized:
            # Friendly objectid rather than the MongoEngine representation.
            sanitized['id'] = str(sanitized['id'])
        return sanitized


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Sensor runner wrapper')
    parser.add_argument('--pack', required=True,
                        help='Name of the pack this sensor belongs to')
    parser.add_argument('--file-path', required=True,
                        help='Path to the sensor module')
    parser.add_argument('--class-name', required=True,
                        help='Name of the sensor class')
    parser.add_argument('--trigger-type-refs', required=False,
                        help='Comma delimited string of trigger type references')
    parser.add_argument('--poll-interval', type=int, default=10, required=False,
                        help='Sensor poll interval')
    args = parser.parse_args()

    trigger_types = args.trigger_type_refs
    trigger_types = trigger_types.split(',') if trigger_types else []

    obj = SensorWrapper(pack=args.pack,
                        file_path=args.file_path,
                        class_name=args.class_name,
                        trigger_types=trigger_types,
                        poll_interval=args.poll_interval)
    obj.run()

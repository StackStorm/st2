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
import time
import json
import subprocess

from st2common import log as logging
from st2common.constants.error_messages import PACK_VIRTUALENV_DOESNT_EXIST
from st2common.util.sandboxing import get_sandbox_python_path
from st2common.util.sandboxing import get_sandbox_python_binary_path
from st2common.util.sandboxing import get_sandbox_virtualenv_path

__all__ = [
    'ProcessSensorContainer'
]

LOG = logging.getLogger('st2reactor.process_sensor_container')

PROCESS_EXIT_TIMEOUT = 5  # how long to wait for process to exit after sending SIGKILL (in seconds)
SUCCESS_EXIT_CODE = 0

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
WRAPPER_SCRIPT_NAME = 'sensor_wrapper.py'
WRAPPER_SCRIPT_PATH = os.path.join(BASE_DIR, WRAPPER_SCRIPT_NAME)

# TODO: Allow multiple instances of the same sensor with different configuration
# options - we need to update sensors for that and add "get_id" or similar
# method to the sensor class


class ProcessSensorContainer(object):
    """
    Sensor container which runs sensors in a separate process.
    """

    def __init__(self, sensors):
        """
        :param sensors: A list of sensor dicts.
        :type sensors: ``list`` of ``dict``
        """
        self._sensors = {}  # maps sensor_id -> sensor object
        self._processes = {}  # maps sensor_id -> sensor process

        for sensor_obj in sensors:
            sensor_id = self._get_sensor_id(sensor=sensor_obj)
            self._sensors[sensor_id] = sensor_obj

    def run(self):
        self._run_all_sensors()

        # Poll for all running processes
        sensor_ids = self._sensors.keys()
        poll_interval = 5

        while len(sensor_ids) >= 1:
            for sensor_id in sensor_ids:
                process = self._processes[sensor_id]
                status = process.poll()

                if status is not None:
                    # Dead process detected
                    LOG.info('Process for sensor %s has exited with code %s',
                             sensor_id, status)

                    del self._processes[sensor_id]
                    del self._sensors[sensor_id]

            sensor_ids = self._sensors.keys()
            time.sleep(poll_interval)

        LOG.info('Container has no active sensors running.')
        return SUCCESS_EXIT_CODE

    def running(self):
        return len(self._processes)

    def shutdown(self):
        LOG.info('Container shutting down. Invoking cleanup on sensors.')

        for sensor_id in self._sensors:
            self._stop_sensor_process(sensor_id=sensor_id)

        LOG.info('All sensors are shut down.')

        self._sensors = {}
        self._processes = {}

    def add_sensor(self, sensor):
        """
        Add a new sensor to the container.

        :type sensor: ``dict``
        """
        sensor_id = self._get_sensor_id(sensor=sensor)

        if sensor_id in self._sensors:
            LOG.warning('Sensor %s already exists and running.', sensor_id)
            return False

        self._spawn_sensor_process(sensor=sensor)
        self._sensors[sensor_id] = sensor
        return True

    def remove_sensor(self, sensor):
        """
        Remove an existing sensor from the container.

        :type sensor: ``dict``
        """
        sensor_id = self._get_sensor_id(sensor=sensor)

        if sensor_id not in self._sensors:
            LOG.warning('Sensor %s isn\'t running in this container.', sensor_id)
            return False

        self._stop_sensor_process(sensor_id=sensor_id)
        return True

    def _run_all_sensors(self):
        sensor_ids = self._sensors.keys()

        for sensor_id in sensor_ids:
            sensor_obj = self._sensors[sensor_id]
            LOG.info('Running sensor %s' % sensor_id)

            try:
                self._spawn_sensor_process(sensor=sensor_obj)
            except Exception as e:
                LOG.warning(e.message, exc_info=True)

                # Disable sensor which we are unable to start
                del self._sensors[sensor_id]
                continue

            LOG.info('Sensor %s started' % sensor_id)

    def _spawn_sensor_process(self, sensor):
        """
        Spawn a new process for the provided sensor.

        New process uses isolated Python binary from a virtual environment
        belonging to the sensor pack.
        """
        sensor_id = self._get_sensor_id(sensor=sensor)
        virtualenv_path = get_sandbox_virtualenv_path(pack=sensor['pack'])
        python_path = get_sandbox_python_binary_path(pack=sensor['pack'])

        if virtualenv_path and not os.path.isdir(virtualenv_path):
            msg = PACK_VIRTUALENV_DOESNT_EXIST % (sensor['pack'], sensor['pack'])
            raise Exception(msg)

        trigger_type_refs = sensor['trigger_types'] or []
        trigger_type_refs = ','.join(trigger_type_refs)

        parent_args = json.dumps(sys.argv[1:])

        args = [
            python_path,
            WRAPPER_SCRIPT_PATH,
            '--pack=%s' % (sensor['pack']),
            '--file-path=%s' % (sensor['file_path']),
            '--class-name=%s' % (sensor['class_name']),
            '--trigger-type-refs=%s' % (trigger_type_refs),
            '--parent-args=%s' % (parent_args)
        ]

        if sensor['poll_interval']:
            args.append('--poll-interval=%s' % (sensor['poll_interval']))

        env = os.environ.copy()
        env['PYTHONPATH'] = get_sandbox_python_path(inherit_from_parent=True,
                                                    inherit_parent_virtualenv=True)

        LOG.debug('Running sensor subprocess (cmd="%s")', ' '.join(args))

        # TODO: Intercept stdout and stderr for aggregated logging purposes
        try:
            process = subprocess.Popen(args=args, stdin=None, stdout=None,
                                       stderr=None, shell=False, env=env)
        except Exception as e:
            cmd = ' '.join(args)
            message = ('Failed to spawn process for sensor %s ("%s"): %s' %
                       (sensor_id, cmd, str(e)))
            raise Exception(message)

        self._processes[sensor_id] = process
        return process

    def _stop_sensor_process(self, sensor_id, exit_timeout=5):
        """
        Stop a sensor process for the provided sensor.

        :param sensor_id: Sensor ID.
        :type sensor_id: ``str``

        :param exit_timeout: How long to wait for process to exit after
                             sending SIGTERM signal. If the process doesn't
                             exit in this amount of seconds, SIGTERM signal
                             will be sent to the process.
        :type exit__timeout: ``int``
        """
        process = self._processes[sensor_id]

        # Terminate the process and wait for up to stop_timeout seconds for the
        # process to exit
        process.terminate()

        timeout = 0
        sleep_delay = 1
        while timeout < exit_timeout:
            status = process.poll()

            if status is not None:
                # Process has exited
                break

            timeout += sleep_delay
            time.sleep(sleep_delay)

        if status is None:
            # Process hasn't exited yet, forcefully kill it
            process.kill()

        del self._processes[sensor_id]
        del self._sensors[sensor_id]

    def _get_sensor_id(self, sensor):
        """
        Return unique identifier for the provider sensor dict.

        :type sensor: ``dict``
        """
        sensor_id = sensor['class_name']
        return sensor_id

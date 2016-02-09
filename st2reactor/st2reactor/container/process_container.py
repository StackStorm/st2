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

from collections import defaultdict

import eventlet
from eventlet.support import greenlets as greenlet

from st2common import log as logging
from st2common.constants.error_messages import PACK_VIRTUALENV_DOESNT_EXIST
from st2common.constants.system import API_URL_ENV_VARIABLE_NAME
from st2common.constants.system import AUTH_TOKEN_ENV_VARIABLE_NAME
from st2common.constants.triggers import (SENSOR_SPAWN_TRIGGER, SENSOR_EXIT_TRIGGER)
from st2common.constants.exit_codes import SUCCESS_EXIT_CODE
from st2common.constants.exit_codes import FAILURE_EXIT_CODE
from st2common.models.system.common import ResourceReference
from st2common.services.access import create_token
from st2common.transport.reactor import TriggerDispatcher
from st2common.util.api import get_full_public_api_url
from st2common.util.shell import on_parent_exit
from st2common.util.sandboxing import get_sandbox_python_path
from st2common.util.sandboxing import get_sandbox_python_binary_path
from st2common.util.sandboxing import get_sandbox_virtualenv_path

__all__ = [
    'ProcessSensorContainer'
]

LOG = logging.getLogger('st2reactor.process_sensor_container')

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
WRAPPER_SCRIPT_NAME = 'sensor_wrapper.py'
WRAPPER_SCRIPT_PATH = os.path.join(BASE_DIR, WRAPPER_SCRIPT_NAME)

# How many times to try to subsequently respawn a sensor after a non-zero exit before giving up
SENSOR_MAX_RESPAWN_COUNTS = 2

# How many seconds after the sensor has been started we should wait before considering sensor as
# being started and running successfully
SENSOR_SUCCESSFUL_START_THRESHOLD = 10

# How long to wait (in seconds) before respawning a dead process
SENSOR_RESPAWN_DELAY = 2.5

# How long to wait for process to exit after sending SIGTERM signal. If the process doesn't
# exit in this amount of seconds, SIGKILL signal will be sent to the process.
PROCESS_EXIT_TIMEOUT = 5

# TODO: Allow multiple instances of the same sensor with different configuration
# options - we need to update sensors for that and add "get_id" or similar
# method to the sensor class


class ProcessSensorContainer(object):
    """
    Sensor container which runs sensors in a separate process.
    """

    def __init__(self, sensors, poll_interval=5, dispatcher=None):
        """
        :param sensors: A list of sensor dicts.
        :type sensors: ``list`` of ``dict``

        :param poll_interval: How long to sleep between each poll for running / dead sensors.
        :type poll_interval: ``float``
        """
        self._poll_interval = poll_interval

        self._sensors = {}  # maps sensor_id -> sensor object
        self._processes = {}  # maps sensor_id -> sensor process

        if not dispatcher:
            dispatcher = TriggerDispatcher(LOG)
        self._dispatcher = dispatcher

        self._stopped = False

        sensors = sensors or []
        for sensor_obj in sensors:
            sensor_id = self._get_sensor_id(sensor=sensor_obj)
            self._sensors[sensor_id] = sensor_obj

        # Stores information needed for respawning dead sensors
        self._sensor_start_times = {}  # maps sensor_id -> sensor start time
        self._sensor_respawn_counts = defaultdict(int)  # maps sensor_id -> number of respawns

        # A list of all the instance variables which hold internal state information about a
        # particular_sensor
        # Note: We don't clear respawn counts since we want to track this through the whole life
        # cycle of the container manager
        self._internal_sensor_state_variables = [
            self._processes,
            self._sensors,
            self._sensor_start_times,
        ]

    def run(self):
        self._run_all_sensors()

        try:
            while not self._stopped:
                # Poll for all running processes
                sensor_ids = self._sensors.keys()

                if len(sensor_ids) >= 1:
                    LOG.debug('%d active sensor(s)' % (len(sensor_ids)))
                    self._poll_sensors_for_results(sensor_ids)
                else:
                    LOG.debug('No active sensors')

                eventlet.sleep(self._poll_interval)
        except greenlet.GreenletExit:
            # This exception is thrown when sensor container manager
            # kills the thread which runs process container. Not sure
            # if this is the best thing to do.
            self._stopped = True
            return SUCCESS_EXIT_CODE
        except:
            LOG.exception('Container failed to run sensors.')
            self._stopped = True
            return FAILURE_EXIT_CODE

        self._stopped = True
        LOG.error('Process container quit. It shouldn\'t.')
        return SUCCESS_EXIT_CODE

    def _poll_sensors_for_results(self, sensor_ids):
        """
        Main loop which polls sensor for results and detects dead sensors.
        """
        for sensor_id in sensor_ids:
            now = int(time.time())

            process = self._processes[sensor_id]
            status = process.poll()

            if status is not None:
                # Dead process detected
                LOG.info('Process for sensor %s has exited with code %s', sensor_id, status)

                sensor = self._sensors[sensor_id]
                self._delete_sensor(sensor_id)

                self._dispatch_trigger_for_sensor_exit(sensor=sensor,
                                                       exit_code=status)

                # Try to respawn a dead process (maybe it was a simple failure which can be
                # resolved with a restart)
                eventlet.spawn_n(self._respawn_sensor, sensor_id=sensor_id, sensor=sensor,
                                 exit_code=status)
            else:
                sensor_start_time = self._sensor_start_times[sensor_id]
                sensor_respawn_count = self._sensor_respawn_counts[sensor_id]
                successfuly_started = (now - sensor_start_time) >= SENSOR_SUCCESSFUL_START_THRESHOLD

                if successfuly_started and sensor_respawn_count >= 1:
                    # Sensor has been successfully running more than threshold seconds, clear the
                    # respawn counter so we can try to restart the sensor if it dies later on
                    self._sensor_respawn_counts[sensor_id] = 0

    def running(self):
        return len(self._processes)

    def stopped(self):
        return self._stopped

    def shutdown(self, force=False):
        LOG.info('Container shutting down. Invoking cleanup on sensors.')
        self._stopped = True

        if force:
            exit_timeout = 0
        else:
            exit_timeout = PROCESS_EXIT_TIMEOUT

        sensor_ids = self._sensors.keys()
        for sensor_id in sensor_ids:
            self._stop_sensor_process(sensor_id=sensor_id, exit_timeout=exit_timeout)

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
        LOG.debug('Sensor %s started.', sensor_id)
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
        LOG.debug('Sensor %s stopped.', sensor_id)
        return True

    def _run_all_sensors(self):
        sensor_ids = self._sensors.keys()

        for sensor_id in sensor_ids:
            sensor_obj = self._sensors[sensor_id]
            LOG.info('Running sensor %s', sensor_id)

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
            format_values = {'pack': sensor['pack'], 'virtualenv_path': virtualenv_path}
            msg = PACK_VIRTUALENV_DOESNT_EXIST % format_values
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

        # Include full api URL and API token specific to that sensor
        ttl = (24 * 60 * 60)
        temporary_token = create_token(username='sensors_container', ttl=ttl)

        env[API_URL_ENV_VARIABLE_NAME] = get_full_public_api_url()
        env[AUTH_TOKEN_ENV_VARIABLE_NAME] = temporary_token.token

        # TODO 1: Purge temporary token when service stops or sensor process dies
        # TODO 2: Store metadata (wrapper process id) with the token and delete
        # tokens for old, dead processes on startup
        cmd = ' '.join(args)
        LOG.debug('Running sensor subprocess (cmd="%s")', cmd)

        # TODO: Intercept stdout and stderr for aggregated logging purposes
        try:
            process = subprocess.Popen(args=args, stdin=None, stdout=None,
                                       stderr=None, shell=False, env=env,
                                       preexec_fn=on_parent_exit('SIGTERM'))
        except Exception as e:
            cmd = ' '.join(args)
            message = ('Failed to spawn process for sensor %s ("%s"): %s' %
                       (sensor_id, cmd, str(e)))
            raise Exception(message)

        self._processes[sensor_id] = process
        self._sensors[sensor_id] = sensor
        self._sensor_start_times[sensor_id] = int(time.time())

        self._dispatch_trigger_for_sensor_spawn(sensor=sensor, process=process, cmd=cmd)

        return process

    def _stop_sensor_process(self, sensor_id, exit_timeout=PROCESS_EXIT_TIMEOUT):
        """
        Stop a sensor process for the provided sensor.

        :param sensor_id: Sensor ID.
        :type sensor_id: ``str``

        :param exit_timeout: How long to wait for process to exit after
                             sending SIGTERM signal. If the process doesn't
                             exit in this amount of seconds, SIGKILL signal
                             will be sent to the process.
        :type exit__timeout: ``int``
        """
        process = self._processes[sensor_id]

        # Delete sensor before terminating process so that it will not be
        # respawned during termination
        self._delete_sensor(sensor_id)

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

    def _respawn_sensor(self, sensor_id, sensor, exit_code):
        """
        Method for respawning a sensor which died with a non-zero exit code.
        """
        extra = {'sensor_id': sensor_id, 'sensor': sensor}

        if self._stopped:
            LOG.debug('Stopped, not respawning a dead sensor', extra=extra)
            return

        should_respawn = self._should_respawn_sensor(sensor_id=sensor_id, sensor=sensor,
                                                     exit_code=exit_code)

        if not should_respawn:
            LOG.debug('Not respawning a dead sensor', extra=extra)
            return

        LOG.debug('Respawning dead sensor', extra=extra)

        self._sensor_respawn_counts[sensor_id] += 1
        sleep_delay = (SENSOR_RESPAWN_DELAY * self._sensor_respawn_counts[sensor_id])
        eventlet.sleep(sleep_delay)

        try:
            self._spawn_sensor_process(sensor=sensor)
        except Exception as e:
            LOG.warning(e.message, exc_info=True)

            # Disable sensor which we are unable to start
            del self._sensors[sensor_id]

    def _should_respawn_sensor(self, sensor_id, sensor, exit_code):
        """
        Return True if the provided sensor should be respawned, False otherwise.
        """
        if exit_code == 0:
            # We only try to respawn sensors which exited with non-zero status code
            return False

        respawn_count = self._sensor_respawn_counts[sensor_id]
        if respawn_count >= SENSOR_MAX_RESPAWN_COUNTS:
            LOG.debug('Sensor has already been respawned max times, giving up')
            return False

        return True

    def _get_sensor_id(self, sensor):
        """
        Return unique identifier for the provider sensor dict.

        :type sensor: ``dict``
        """
        sensor_id = sensor['ref']
        return sensor_id

    def _dispatch_trigger_for_sensor_spawn(self, sensor, process, cmd):
        trigger = ResourceReference.to_string_reference(
            name=SENSOR_SPAWN_TRIGGER['name'],
            pack=SENSOR_SPAWN_TRIGGER['pack'])
        now = int(time.time())
        payload = {
            'id': sensor['class_name'],
            'timestamp': now,
            'pid': process.pid,
            'cmd': cmd
        }
        self._dispatcher.dispatch(trigger, payload=payload)

    def _dispatch_trigger_for_sensor_exit(self, sensor, exit_code):
        trigger = ResourceReference.to_string_reference(
            name=SENSOR_EXIT_TRIGGER['name'],
            pack=SENSOR_EXIT_TRIGGER['pack'])
        now = int(time.time())
        payload = {
            'id': sensor['class_name'],
            'timestamp': now,
            'exit_code': exit_code
        }
        self._dispatcher.dispatch(trigger, payload=payload)

    def _delete_sensor(self, sensor_id):
        """
        Delete / reset all the internal state about a particular sensor.
        """
        for var in self._internal_sensor_state_variables:
            if sensor_id in var:
                del var[sensor_id]

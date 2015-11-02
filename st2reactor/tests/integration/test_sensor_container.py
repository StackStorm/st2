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

import os
import signal

import psutil
import eventlet
from eventlet.green import subprocess
from oslo_config import cfg

import st2tests.config
from st2common.models.db import db_setup
from st2common.util.green.shell import run_command
from st2common.bootstrap.sensorsregistrar import register_sensors
from st2tests.base import IntegrationTestCase

__all__ = [
    'SensorContainerTestCase'
]

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ST2_CONFIG_PATH = os.path.join(BASE_DIR, '../../../conf/st2.tests.conf')
ST2_CONFIG_PATH = os.path.abspath(ST2_CONFIG_PATH)
BINARY = os.path.join(BASE_DIR, '../../../st2reactor/bin/st2sensorcontainer')
BINARY = os.path.abspath(BINARY)
CMD = [BINARY, '--config-file', ST2_CONFIG_PATH, '--sensor-ref=examples.SamplePollingSensor']


class SensorContainerTestCase(IntegrationTestCase):
    """
    Note: For those tests MongoDB must be running, virtualenv must exist for
    examples pack and sensors from the example pack must be registered.
    """

    print_stdout_stderr_on_teardown = True

    @classmethod
    def setUpClass(cls):
        super(SensorContainerTestCase, cls).setUpClass()

        st2tests.config.parse_args()

        username = cfg.CONF.database.username if hasattr(cfg.CONF.database, 'username') else None
        password = cfg.CONF.database.password if hasattr(cfg.CONF.database, 'password') else None
        cls.db_connection = db_setup(
            cfg.CONF.database.db_name, cfg.CONF.database.host, cfg.CONF.database.port,
            username=username, password=password, ensure_indexes=False)

        # Register sensors
        register_sensors(packs_base_paths=['/opt/stackstorm/packs'], use_pack_cache=False)

        # Create virtualenv for examples pack
        virtualenv_path = '/opt/stackstorm/virtualenvs/examples'
        cmd = ['virtualenv', '--system-site-packages', virtualenv_path]
        run_command(cmd=cmd)

    def test_child_processes_are_killed_on_sigint(self):
        process = self._start_sensor_container()

        # Give it some time to start up
        eventlet.sleep(5)

        # Assert process has started and is running
        self.assertProcessIsRunning(process=process)

        # Verify container process and children sensor / wrapper processes are running
        pp = psutil.Process(process.pid)
        children_pp = pp.children()
        self.assertEqual(pp.cmdline()[1:], CMD)
        self.assertEqual(len(children_pp), 1)

        # Send SIGINT
        process.send_signal(signal.SIGINT)

        # SIGINT causes graceful shutdown so give it some time to gracefuly shut down the sensor
        # child processes
        eventlet.sleep(8)

        # Verify parent and children processes have exited
        self.assertProcessExited(proc=pp)
        self.assertProcessExited(proc=children_pp[0])

        self.remove_process(process=process)

    def test_child_processes_are_killed_on_sigterm(self):
        process = self._start_sensor_container()

        # Give it some time to start up
        eventlet.sleep(5)

        # Verify container process and children sensor / wrapper processes are running
        pp = psutil.Process(process.pid)
        children_pp = pp.children()
        self.assertEqual(pp.cmdline()[1:], CMD)
        self.assertEqual(len(children_pp), 1)

        # Send SIGTERM
        process.send_signal(signal.SIGTERM)

        # SIGTERM causes graceful shutdown so give it some time to gracefuly shut down the sensor
        # child processes
        eventlet.sleep(8)

        # Verify parent and children processes have exited
        self.assertProcessExited(proc=pp)
        self.assertProcessExited(proc=children_pp[0])

        self.remove_process(process=process)

    def test_child_processes_are_killed_on_sigkill(self):
        process = self._start_sensor_container()

        # Give it some time to start up
        eventlet.sleep(5)

        # Verify container process and children sensor / wrapper processes are running
        pp = psutil.Process(process.pid)
        children_pp = pp.children()
        self.assertEqual(pp.cmdline()[1:], CMD)
        self.assertEqual(len(children_pp), 1)

        # Send SIGKILL
        process.send_signal(signal.SIGKILL)

        # Note: On SIGKILL processes should be killed instantly
        eventlet.sleep(1)

        # Verify parent and children processes have exited
        self.assertProcessExited(proc=pp)
        self.assertProcessExited(proc=children_pp[0])

        self.remove_process(process=process)

    def _start_sensor_container(self):
        process = subprocess.Popen(CMD, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                   shell=False, preexec_fn=os.setsid)
        self.add_process(process=process)
        return process

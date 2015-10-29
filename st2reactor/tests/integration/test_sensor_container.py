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

import unittest2
import psutil
import eventlet
from eventlet.green import subprocess

__all__ = [
    'SensorContainerTestCase'
]

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ST2_CONFIG_PATH = os.path.join(BASE_DIR, '../../../conf/st2.dev.conf')
ST2_CONFIG_PATH = os.path.abspath(ST2_CONFIG_PATH)
BINARY = os.path.join(BASE_DIR, '../../../st2reactor/bin/st2sensorcontainer')
BINARY = os.path.abspath(BINARY)
CMD = [BINARY, '--config-file', ST2_CONFIG_PATH, '--sensor-ref=examples.SamplePollingSensor']


class SensorContainerTestCase(unittest2.TestCase):
    """
    Note: For those tests MongoDB must be running, virtualenv must exist for
    examples pack and sensors from the example pack must be registered.
    """

    processes = {}

    def tearDown(self):
        # Make sure we kill all the processes on teardown so they don't linger around if an
        # exception was thrown.
        for pid, proc in self.processes.items():
            proc.kill()

    @unittest2.skipIf(os.environ.get('TRAVIS'), 'Running on travis')
    def test_child_processes_are_killed_on_sigint(self):
        process = self._start_sensor_container()

        # Give it some time to start up
        eventlet.sleep(5)

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

        del self.processes[process.pid]

    @unittest2.skipIf(os.environ.get('TRAVIS'), 'Running on travis')
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

        del self.processes[process.pid]

    @unittest2.skipIf(os.environ.get('TRAVIS'), 'Running on travis')
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

        del self.processes[process.pid]

    def assertProcessExited(self, proc):
        try:
            status = proc.status()
        except psutil.NoSuchProcess:
            status = 'exited'

        if status not in ['exited', 'zombie']:
            self.fail('Process with pid "%s" is still running' % (proc.pid))

    def _start_sensor_container(self):
        process = subprocess.Popen(CMD, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                   shell=False, preexec_fn=os.setsid)
        self.processes[process.pid] = process
        return process

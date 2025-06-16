# Copyright 2020 The StackStorm Authors.
# Copyright 2019 Extreme Networks, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import absolute_import

import os
import sys
import signal

import psutil
from oslo_config import cfg

import st2tests.config
from st2common.util import concurrency
from st2common.models.db import db_setup
from st2reactor.container.process_container import PROCESS_EXIT_TIMEOUT
from st2common.util.green.shell import run_command
from st2common.util.virtualenvs import inject_st2_pth_into_virtualenv
from st2common.bootstrap.sensorsregistrar import register_sensors
from st2tests.base import IntegrationTestCase

__all__ = ["SensorContainerTestCase"]

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

ST2_CONFIG_PATH = os.path.join(BASE_DIR, "../../../conf/st2.tests.conf")
ST2_CONFIG_PATH = os.path.abspath(ST2_CONFIG_PATH)

PYTHON_BINARY = sys.executable

BINARY = os.path.join(BASE_DIR, "../../../st2reactor/bin/st2sensorcontainer")
BINARY = os.path.abspath(BINARY)

PACKS_BASE_PATH = os.path.abspath(os.path.join(BASE_DIR, "../../../contrib"))

DEFAULT_CMD = [
    PYTHON_BINARY,
    BINARY,
    "--config-file",
    ST2_CONFIG_PATH,
    "--sensor-ref=examples.SamplePollingSensor",
]


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

        username = (
            cfg.CONF.database.username
            if hasattr(cfg.CONF.database, "username")
            else None
        )
        password = (
            cfg.CONF.database.password
            if hasattr(cfg.CONF.database, "password")
            else None
        )
        cls.db_connection = db_setup(
            cfg.CONF.database.db_name,
            cfg.CONF.database.host,
            cfg.CONF.database.port,
            username=username,
            password=password,
            ensure_indexes=False,
        )

        # NOTE: We need to perform this patching because test fixtures are located outside of the
        # packs base paths directory. This will never happen outside the context of test fixtures.
        cfg.CONF.content.packs_base_paths = PACKS_BASE_PATH

        # Register sensors
        register_sensors(packs_base_paths=[PACKS_BASE_PATH], use_pack_cache=False)

        # Create virtualenv for examples pack
        virtualenv_path = "/tmp/virtualenvs/examples"

        run_command(cmd=["rm", "-rf", virtualenv_path])

        cmd = [
            "virtualenv",
            "--system-site-packages",
            "--python",
            PYTHON_BINARY,
            virtualenv_path,
        ]
        run_command(cmd=cmd)
        inject_st2_pth_into_virtualenv(virtualenv_path)

    def test_child_processes_are_killed_on_sigint(self):
        process = self._start_sensor_container()

        # Give it some time to start up
        concurrency.sleep(7)

        # Assert process has started and is running
        self.assertProcessIsRunning(process=process)

        # Verify container process and children sensor / wrapper processes are running
        pp = psutil.Process(process.pid)
        children_pp = pp.children()
        self.assertEqual(pp.cmdline()[1:], DEFAULT_CMD[1:])
        self.assertEqual(len(children_pp), 1)

        # Send SIGINT
        process.send_signal(signal.SIGINT)

        # SIGINT causes graceful shutdown so give it some time to gracefuly shut down the sensor
        # child processes
        concurrency.sleep(PROCESS_EXIT_TIMEOUT + 1)

        # Verify parent and children processes have exited
        self.assertProcessExited(proc=pp)
        self.assertProcessExited(proc=children_pp[0])

        self.remove_process(process=process)

    def test_child_processes_are_killed_on_sigterm(self):
        process = self._start_sensor_container()

        # Give it some time to start up
        concurrency.sleep(5)

        # Verify container process and children sensor / wrapper processes are running
        pp = psutil.Process(process.pid)
        children_pp = pp.children()
        self.assertEqual(pp.cmdline()[1:], DEFAULT_CMD[1:])
        self.assertEqual(len(children_pp), 1)

        # Send SIGTERM
        process.send_signal(signal.SIGTERM)

        # SIGTERM causes graceful shutdown so give it some time to gracefuly shut down the sensor
        # child processes
        concurrency.sleep(PROCESS_EXIT_TIMEOUT + 8)

        # Verify parent and children processes have exited
        self.assertProcessExited(proc=pp)
        self.assertProcessExited(proc=children_pp[0])

        self.remove_process(process=process)

    def test_child_processes_are_killed_on_sigkill(self):
        process = self._start_sensor_container()

        # Give it some time to start up
        concurrency.sleep(5)

        # Verify container process and children sensor / wrapper processes are running
        pp = psutil.Process(process.pid)
        children_pp = pp.children()
        self.assertEqual(pp.cmdline()[1:], DEFAULT_CMD[1:])
        self.assertEqual(len(children_pp), 1)

        # Send SIGKILL
        process.send_signal(signal.SIGKILL)

        # Note: On SIGKILL processes should be killed instantly
        concurrency.sleep(1)

        # Verify parent and children processes have exited
        self.assertProcessExited(proc=pp)
        self.assertProcessExited(proc=children_pp[0])

        self.remove_process(process=process)

    def test_single_sensor_mode(self):
        # 1. --sensor-ref not provided
        cmd = [
            PYTHON_BINARY,
            BINARY,
            "--config-file",
            ST2_CONFIG_PATH,
            "--single-sensor-mode",
        ]

        process = self._start_sensor_container(cmd=cmd)
        pp = psutil.Process(process.pid)

        # Give it some time to start up
        concurrency.sleep(5)

        stdout = process.stdout.read()
        self.assertTrue(
            (
                b"--sensor-ref argument must be provided when running in single sensor "
                b"mode"
            )
            in stdout
        )
        self.assertProcessExited(proc=pp)
        self.remove_process(process=process)

        # 2. sensor ref provided
        cmd = [
            BINARY,
            "--config-file",
            ST2_CONFIG_PATH,
            "--single-sensor-mode",
            "--sensor-ref=examples.SampleSensorExit",
        ]

        process = self._start_sensor_container(cmd=cmd)
        pp = psutil.Process(process.pid)

        # Give it some time to start up
        concurrency.sleep(1)

        # Container should exit and not respawn a sensor in single sensor mode
        stdout = process.stdout.read()

        self.assertTrue(
            b"Process for sensor examples.SampleSensorExit has exited with code 110"
        )
        self.assertTrue(b"Not respawning a sensor since running in single sensor mode")
        self.assertTrue(b"Process container quit with exit_code 110.")

        concurrency.sleep(2)
        self.assertProcessExited(proc=pp)

        self.remove_process(process=process)

    def _start_sensor_container(self, cmd=DEFAULT_CMD):
        subprocess = concurrency.get_subprocess_module()
        env = os.environ.copy()
        env.update(st2tests.config.db_opts_as_env_vars())
        env.update(st2tests.config.mq_opts_as_env_vars())
        env.update(st2tests.config.coord_opts_as_env_vars())
        print("Using command: %s" % (" ".join(cmd)))
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            shell=False,
            preexec_fn=os.setsid,
            env=env,
        )
        self.add_process(process=process)
        return process

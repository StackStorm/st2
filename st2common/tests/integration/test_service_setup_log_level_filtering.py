# Copyright 2021 The StackStorm Authors.
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

import eventlet
from eventlet.green import subprocess

import st2tests.config
from st2tests.base import IntegrationTestCase
from st2tests.fixtures.conf.fixture import FIXTURE_PATH as CONF_FIXTURES_PATH

__all__ = ["ServiceSetupLogLevelFilteringTestCase"]

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

ST2_CONFIG_INFO_LL_PATH = os.path.join(
    CONF_FIXTURES_PATH, "st2.tests.api.info_log_level.conf"
)
ST2_CONFIG_INFO_LL_PATH = os.path.abspath(ST2_CONFIG_INFO_LL_PATH)

ST2_CONFIG_DEBUG_LL_PATH = os.path.join(
    CONF_FIXTURES_PATH, "st2.tests.api.debug_log_level.conf"
)
ST2_CONFIG_DEBUG_LL_PATH = os.path.abspath(ST2_CONFIG_DEBUG_LL_PATH)

ST2_CONFIG_AUDIT_LL_PATH = os.path.join(
    CONF_FIXTURES_PATH, "st2.tests.api.audit_log_level.conf"
)
ST2_CONFIG_AUDIT_LL_PATH = os.path.abspath(ST2_CONFIG_AUDIT_LL_PATH)

ST2_CONFIG_SYSTEM_DEBUG_PATH = os.path.join(
    CONF_FIXTURES_PATH, "st2.tests.api.system_debug_true.conf"
)
ST2_CONFIG_SYSTEM_DEBUG_PATH = os.path.abspath(ST2_CONFIG_SYSTEM_DEBUG_PATH)

ST2_CONFIG_SYSTEM_LL_DEBUG_PATH = os.path.join(
    CONF_FIXTURES_PATH, "st2.tests.api.system_debug_true_logging_debug.conf"
)

PYTHON_BINARY = sys.executable

ST2API_BINARY = os.path.join(BASE_DIR, "../../../st2api/bin/st2api")
ST2API_BINARY = os.path.abspath(ST2API_BINARY)

CMD = [PYTHON_BINARY, ST2API_BINARY, "--config-file"]


class ServiceSetupLogLevelFilteringTestCase(IntegrationTestCase):
    def setUp(self):
        super(ServiceSetupLogLevelFilteringTestCase, self).setUp()
        self._reset_env()

    def tearDown(self):
        super(ServiceSetupLogLevelFilteringTestCase, self).tearDown()
        self._reset_env()

    def _reset_env(self):
        keys_to_delete = ["LC_ALL", "ST2_LOG_PATCH_STDOUT", "PYTHONIOENCODING"]

        for key in keys_to_delete:
            if key in os.environ:
                del os.environ[key]

    def test_system_info_is_logged_on_startup(self):
        # Verify INFO level service start up messages
        process = self._start_process(config_path=ST2_CONFIG_INFO_LL_PATH)
        self.add_process(process=process)

        # Give it some time to start up
        eventlet.sleep(4)
        process.send_signal(signal.SIGKILL)

        # Verify first 4 environment related log messages
        stdout = process.stdout.read().decode("utf-8")
        stderr = process.stderr.read().decode("utf-8")
        print(stdout)
        print(stderr)
        self.assertIn("INFO [-] Using Python:", stdout)
        self.assertIn("INFO [-] Using fs encoding:", stdout)
        self.assertIn("INFO [-] Using config files:", stdout)
        self.assertIn("INFO [-] Using logging config:", stdout)

    def test_warning_is_emitted_on_non_utf8_encoding(self):
        env = os.environ.copy()
        env["LC_ALL"] = "invalid"
        env["ST2_LOG_PATCH_STDOUT"] = "false"
        env["PYTHONIOENCODING"] = "ascii"
        process = self._start_process(config_path=ST2_CONFIG_INFO_LL_PATH, env=env)
        self.add_process(process=process)

        # Give it some time to start up
        eventlet.sleep(4)
        process.send_signal(signal.SIGKILL)

        # Verify first 4 environment related log messages
        stdout = "\n".join(process.stdout.read().decode("utf-8").split("\n"))
        stderr = process.stderr.read().decode("utf-8")
        print(stdout)
        print(stderr)
        self.assertIn("WARNING [-] Detected a non utf-8 locale / encoding", stdout)

        if sys.version_info < (3, 8, 0):
            self.assertIn("fs encoding: ascii", stdout)

        self.assertIn("unknown locale: invalid", stdout)

    def test_audit_log_level_is_filtered_if_log_level_is_not_debug_or_audit(self):
        # 0. Verify INFO level service start up messages
        process = self._start_process(config_path=ST2_CONFIG_INFO_LL_PATH)
        self.add_process(process=process)

        # Give it some time to start up
        eventlet.sleep(4)
        process.send_signal(signal.SIGKILL)

        # Verify first 4 environment related log messages
        stdout = "\n".join(process.stdout.read().decode("utf-8").split("\n")[:6])
        self.assertIn("INFO [-] Using Python:", stdout)
        self.assertIn("INFO [-] Using fs encoding:", stdout)
        self.assertIn("INFO [-] Using config files:", stdout)
        self.assertIn("INFO [-] Using logging config:", stdout)
        self.assertIn("INFO [-] Using coordination driver:", stdout)
        self.assertIn("INFO [-] Using metrics driver:", stdout)

        # 1. INFO log level - audit messages should not be included
        process = self._start_process(config_path=ST2_CONFIG_INFO_LL_PATH)
        self.add_process(process=process)

        # Give it some time to start up
        eventlet.sleep(4)
        process.send_signal(signal.SIGKILL)

        # First 6 log lines are debug messages about the environment which are always logged
        stdout = "\n".join(process.stdout.read().decode("utf-8").split("\n")[6:])

        self.assertIn("INFO [-]", stdout)
        self.assertNotIn("DEBUG [-]", stdout)
        self.assertNotIn("AUDIT [-]", stdout)

        # 2. DEBUG log level - audit messages should be included
        process = self._start_process(config_path=ST2_CONFIG_DEBUG_LL_PATH)
        self.add_process(process=process)

        # Give it some time to start up
        eventlet.sleep(6)
        process.send_signal(signal.SIGKILL)

        # First 6 log lines are debug messages about the environment which are always logged
        stdout = "\n".join(process.stdout.read().decode("utf-8").split("\n")[6:])

        self.assertIn("INFO [-]", stdout)
        self.assertIn("DEBUG [-]", stdout)
        self.assertIn("AUDIT [-]", stdout)

        # 3. AUDIT log level - audit messages should be included
        process = self._start_process(config_path=ST2_CONFIG_AUDIT_LL_PATH)
        self.add_process(process=process)

        # Give it some time to start up
        eventlet.sleep(6)
        process.send_signal(signal.SIGKILL)

        # First 6 log lines are debug messages about the environment which are always logged
        stdout = "\n".join(process.stdout.read().decode("utf-8").split("\n")[6:])

        self.assertNotIn("INFO [-]", stdout)
        self.assertNotIn("DEBUG [-]", stdout)
        self.assertIn("AUDIT [-]", stdout)

        # 2. INFO log level but system.debug set to True
        process = self._start_process(config_path=ST2_CONFIG_SYSTEM_DEBUG_PATH)
        self.add_process(process=process)

        # Give it some time to start up
        eventlet.sleep(6)
        process.send_signal(signal.SIGKILL)

        # First 6 log lines are debug messages about the environment which are always logged
        stdout = "\n".join(process.stdout.read().decode("utf-8").split("\n")[6:])
        stderr = process.stderr.read().decode("utf-8")
        print(stdout)
        print(stderr)

        self.assertIn("INFO [-]", stdout)
        self.assertIn("DEBUG [-]", stdout)
        self.assertIn("AUDIT [-]", stdout)

    def test_kombu_heartbeat_tick_log_messages_are_excluded(self):
        # 1. system.debug = True config option is set, verify heartbeat_tick message is not logged
        process = self._start_process(config_path=ST2_CONFIG_SYSTEM_LL_DEBUG_PATH)
        self.add_process(process=process)

        # Give it some time to start up
        eventlet.sleep(6)
        process.send_signal(signal.SIGKILL)

        stdout = "\n".join(process.stdout.read().decode("utf-8").split("\n"))
        self.assertNotIn("heartbeat_tick", stdout)

        # 2. system.debug = False, log level is set to debug
        process = self._start_process(config_path=ST2_CONFIG_DEBUG_LL_PATH)
        self.add_process(process=process)

        # Give it some time to start up
        eventlet.sleep(6)
        process.send_signal(signal.SIGKILL)

        stdout = "\n".join(process.stdout.read().decode("utf-8").split("\n"))
        self.assertNotIn("heartbeat_tick", stdout)

    @staticmethod
    def _start_process(config_path, env=None):
        cmd = CMD + [config_path]
        cwd = os.path.abspath(os.path.join(BASE_DIR, "../../../"))
        cwd = os.path.abspath(cwd)
        env = env or os.environ.copy()
        env.update(st2tests.config.db_opts_as_env_vars())
        env.update(st2tests.config.mq_opts_as_env_vars())
        env.update(st2tests.config.coord_opts_as_env_vars())
        process = subprocess.Popen(
            cmd,
            env=env,
            cwd=cwd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            shell=False,
            preexec_fn=os.setsid,
        )
        return process

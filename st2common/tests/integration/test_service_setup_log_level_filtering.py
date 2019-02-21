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

from __future__ import absolute_import

import os
import sys
import signal

import eventlet
from eventlet.green import subprocess

from st2tests.base import IntegrationTestCase
from st2tests.fixturesloader import get_fixtures_base_path

__all__ = [
    'ServiceSetupLogLevelFilteringTestCase'
]

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

FIXTURES_DIR = get_fixtures_base_path()

ST2_CONFIG_INFO_LL_PATH = os.path.join(FIXTURES_DIR, 'conf/st2.tests.api.info_log_level.conf')
ST2_CONFIG_INFO_LL_PATH = os.path.abspath(ST2_CONFIG_INFO_LL_PATH)

ST2_CONFIG_DEBUG_LL_PATH = os.path.join(FIXTURES_DIR, 'conf/st2.tests.api.debug_log_level.conf')
ST2_CONFIG_DEBUG_LL_PATH = os.path.abspath(ST2_CONFIG_DEBUG_LL_PATH)

ST2_CONFIG_AUDIT_LL_PATH = os.path.join(FIXTURES_DIR, 'conf/st2.tests.api.audit_log_level.conf')
ST2_CONFIG_AUDIT_LL_PATH = os.path.abspath(ST2_CONFIG_AUDIT_LL_PATH)

ST2_CONFIG_SYSTEM_DEBUG_PATH = os.path.join(FIXTURES_DIR,
                                            'conf/st2.tests.api.system_debug_true.conf')
ST2_CONFIG_SYSTEM_DEBUG_PATH = os.path.abspath(ST2_CONFIG_SYSTEM_DEBUG_PATH)

ST2_CONFIG_SYSTEM_LL_DEBUG_PATH = os.path.join(FIXTURES_DIR,
    'conf/st2.tests.api.system_debug_true_logging_debug.conf')

PYTHON_BINARY = sys.executable

ST2API_BINARY = os.path.join(BASE_DIR, '../../../st2api/bin/st2api')
ST2API_BINARY = os.path.abspath(ST2API_BINARY)

CMD = [PYTHON_BINARY, ST2API_BINARY, '--config-file']


class ServiceSetupLogLevelFilteringTestCase(IntegrationTestCase):
    def test_audit_log_level_is_filtered_if_log_level_is_not_debug_or_audit(self):
        # 1. INFO log level - audit messages should not be included
        process = self._start_process(config_path=ST2_CONFIG_INFO_LL_PATH)
        self.add_process(process=process)

        # Give it some time to start up
        eventlet.sleep(3)
        process.send_signal(signal.SIGKILL)

        # First 3 log lines are debug messages about the environment which are always logged
        stdout = '\n'.join(process.stdout.read().decode('utf-8').split('\n')[3:])

        self.assertTrue('INFO [-]' in stdout)
        self.assertTrue('DEBUG [-]' not in stdout)
        self.assertTrue('AUDIT [-]' not in stdout)

        # 2. DEBUG log level - audit messages should be included
        process = self._start_process(config_path=ST2_CONFIG_DEBUG_LL_PATH)
        self.add_process(process=process)

        # Give it some time to start up
        eventlet.sleep(5)
        process.send_signal(signal.SIGKILL)

        # First 3 log lines are debug messages about the environment which are always logged
        stdout = '\n'.join(process.stdout.read().decode('utf-8').split('\n')[3:])

        self.assertTrue('INFO [-]' in stdout)
        self.assertTrue('DEBUG [-]' in stdout)
        self.assertTrue('AUDIT [-]' in stdout)

        # 3. AUDIT log level - audit messages should be included
        process = self._start_process(config_path=ST2_CONFIG_AUDIT_LL_PATH)
        self.add_process(process=process)

        # Give it some time to start up
        eventlet.sleep(5)
        process.send_signal(signal.SIGKILL)

        # First 3 log lines are debug messages about the environment which are always logged
        stdout = '\n'.join(process.stdout.read().decode('utf-8').split('\n')[3:])

        self.assertTrue('INFO [-]' not in stdout)
        self.assertTrue('DEBUG [-]' not in stdout)
        self.assertTrue('AUDIT [-]' in stdout)

        # 2. INFO log level but system.debug set to True
        process = self._start_process(config_path=ST2_CONFIG_SYSTEM_DEBUG_PATH)
        self.add_process(process=process)

        # Give it some time to start up
        eventlet.sleep(5)
        process.send_signal(signal.SIGKILL)

        # First 3 log lines are debug messages about the environment which are always logged
        stdout = '\n'.join(process.stdout.read().decode('utf-8').split('\n')[3:])

        self.assertTrue('INFO [-]' in stdout)
        self.assertTrue('DEBUG [-]' in stdout)
        self.assertTrue('AUDIT [-]' in stdout)

    def test_kombu_heartbeat_tick_log_messages_are_excluded(self):
        # 1. system.debug = True config option is set, verify heartbeat_tick message is not logged
        process = self._start_process(config_path=ST2_CONFIG_SYSTEM_LL_DEBUG_PATH)
        self.add_process(process=process)

        # Give it some time to start up
        eventlet.sleep(5)
        process.send_signal(signal.SIGKILL)

        stdout = '\n'.join(process.stdout.read().decode('utf-8').split('\n'))
        self.assertTrue('heartbeat_tick' not in stdout)

        # 2. system.debug = False, log level is set to debug
        process = self._start_process(config_path=ST2_CONFIG_DEBUG_LL_PATH)
        self.add_process(process=process)

        # Give it some time to start up
        eventlet.sleep(5)
        process.send_signal(signal.SIGKILL)

        stdout = '\n'.join(process.stdout.read().decode('utf-8').split('\n'))
        self.assertTrue('heartbeat_tick' not in stdout)

    def _start_process(self, config_path):
        cmd = CMD + [config_path]
        cwd = os.path.abspath(os.path.join(BASE_DIR, '../../../'))
        cwd = os.path.abspath(cwd)
        process = subprocess.Popen(cmd, cwd=cwd,
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                   shell=False, preexec_fn=os.setsid)
        return process

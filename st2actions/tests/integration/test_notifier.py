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
import tempfile

from eventlet.green import subprocess

from st2common.constants.scheduler import SCHEDULER_ENABLED_LOG_LINE, SCHEDULER_DISABLED_LOG_LINE
from st2tests.base import IntegrationTestCase
from st2tests.base import CleanDbTestCase

__all__ = [
    'SchedulerEnableDisableTestCase'
]


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ST2_CONFIG_PATH = os.path.join(BASE_DIR, '../../../conf/st2.tests.conf')
ST2_CONFIG_PATH = os.path.abspath(ST2_CONFIG_PATH)
BINARY = os.path.join(BASE_DIR, '../../../st2actions/bin/st2notifier')
BINARY = os.path.abspath(BINARY)
CMD = [BINARY, '--config-file']


class SchedulerEnableDisableTestCase(IntegrationTestCase, CleanDbTestCase):
    @classmethod
    def setUpClass(cls):
        super(SchedulerEnableDisableTestCase, cls).setUpClass()

    def setUp(self):
        super(SchedulerEnableDisableTestCase, self).setUp()
        config_text = open(ST2_CONFIG_PATH).read()
        self.cfg_fd, self.cfg_path = tempfile.mkstemp()
        with open(self.cfg_path, 'w') as f:
            f.write(config_text)
        self.cmd = []
        self.cmd.extend(CMD)
        self.cmd.append(self.cfg_path)

    def tearDown(self):
        self.cmd = None
        self._remove_tempfile(self.cfg_fd, self.cfg_path)
        super(SchedulerEnableDisableTestCase, self).tearDown()

    def test_scheduler_enable_implicit(self):
        process = None
        try:
            process = self._start_notifier(cmd=self.cmd)
            lines = 0
            while lines < 100:
                line = process.stdout.readline()
                lines += 1
                if SCHEDULER_ENABLED_LOG_LINE in line:
                    self.assertTrue(True)
                    break
        finally:
            if process:
                process.send_signal(signal.SIGKILL)
                self.remove_process(process=process)

    def test_scheduler_enable_explicit(self):
        self._append_to_cfg_file(cfg_path=self.cfg_path, content='\n[scheduler]\nenable = True')
        process = None
        try:
            process = self._start_notifier(cmd=self.cmd)
            lines = 0
            while lines < 100:
                line = process.stdout.readline()
                lines += 1
                if SCHEDULER_ENABLED_LOG_LINE in line:
                    self.assertTrue(True)
                    break
        finally:
            if process:
                process.send_signal(signal.SIGKILL)
                self.remove_process(process=process)

    def test_scheduler_disable_explicit(self):
        self._append_to_cfg_file(cfg_path=self.cfg_path, content='\n[scheduler]\nenable = False')
        process = None
        try:
            process = self._start_notifier(cmd=self.cmd)
            lines = 0
            while lines < 100:
                line = process.stdout.readline()
                lines += 1
                if SCHEDULER_DISABLED_LOG_LINE in line:
                    self.assertTrue(True)
                    break
        finally:
            if process:
                process.send_signal(signal.SIGKILL)
                self.remove_process(process=process)

    def _start_notifier(self, cmd):
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                   shell=False, preexec_fn=os.setsid)
        self.add_process(process=process)
        return process

    def _append_to_cfg_file(self, cfg_path, content):
        with open(cfg_path, 'a') as f:
            f.write(content)

    def _remove_tempfile(self, fd, path):
        os.close(fd)
        os.unlink(path)

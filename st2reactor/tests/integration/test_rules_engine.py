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
import tempfile

from st2common.util import concurrency
from st2common.constants.timer import TIMER_ENABLED_LOG_LINE
from st2common.constants.timer import TIMER_DISABLED_LOG_LINE
from st2tests.base import IntegrationTestCase
from st2tests.base import CleanDbTestCase

__all__ = ["TimersEngineServiceEnableDisableTestCase"]


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ST2_CONFIG_PATH = os.path.join(BASE_DIR, "../../../conf/st2.tests.conf")
ST2_CONFIG_PATH = os.path.abspath(ST2_CONFIG_PATH)
PYTHON_BINARY = sys.executable
BINARY = os.path.join(BASE_DIR, "../../../st2reactor/bin/st2timersengine")
BINARY = os.path.abspath(BINARY)
CMD = [PYTHON_BINARY, BINARY, "--config-file"]


class TimersEngineServiceEnableDisableTestCase(IntegrationTestCase, CleanDbTestCase):
    def setUp(self):
        super(TimersEngineServiceEnableDisableTestCase, self).setUp()

        config_text = open(ST2_CONFIG_PATH).read()
        self.cfg_fd, self.cfg_path = tempfile.mkstemp()
        with open(self.cfg_path, "w") as f:
            f.write(config_text)
        self.cmd = []
        self.cmd.extend(CMD)
        self.cmd.append(self.cfg_path)

    def tearDown(self):
        self.cmd = None
        self._remove_tempfile(self.cfg_fd, self.cfg_path)
        super(TimersEngineServiceEnableDisableTestCase, self).tearDown()

    def test_timer_enable_implicit(self):
        process = None
        seen_line = False

        try:
            process = self._start_times_engine(cmd=self.cmd)
            lines = 0
            while lines < 100:
                line = process.stdout.readline().decode("utf-8")
                lines += 1
                sys.stdout.write(line)

                if TIMER_ENABLED_LOG_LINE in line:
                    seen_line = True
                    break
        finally:
            if process:
                process.send_signal(signal.SIGKILL)
                self.remove_process(process=process)

        if not seen_line:
            raise AssertionError(
                'Didn\'t see "%s" log line in timer output' % (TIMER_ENABLED_LOG_LINE)
            )

    def test_timer_enable_explicit(self):
        self._append_to_cfg_file(
            cfg_path=self.cfg_path,
            content="\n[timersengine]\nenable = True\n[timer]\nenable = True",
        )
        process = None
        seen_line = False

        try:
            process = self._start_times_engine(cmd=self.cmd)
            lines = 0
            while lines < 100:
                line = process.stdout.readline().decode("utf-8")
                lines += 1
                sys.stdout.write(line)

                if TIMER_ENABLED_LOG_LINE in line:
                    seen_line = True
                    break
        finally:
            if process:
                process.send_signal(signal.SIGKILL)
                self.remove_process(process=process)

        if not seen_line:
            raise AssertionError(
                'Didn\'t see "%s" log line in timer output' % (TIMER_ENABLED_LOG_LINE)
            )

    def test_timer_disable_explicit(self):
        self._append_to_cfg_file(
            cfg_path=self.cfg_path,
            content="\n[timersengine]\nenable = False\n[timer]\nenable = False",
        )
        process = None
        seen_line = False

        try:
            process = self._start_times_engine(cmd=self.cmd)
            lines = 0
            while lines < 100:
                line = process.stdout.readline().decode("utf-8")
                lines += 1
                sys.stdout.write(line)

                if TIMER_DISABLED_LOG_LINE in line:
                    seen_line = True
                    break
        finally:
            if process:
                process.send_signal(signal.SIGKILL)
                self.remove_process(process=process)

        if not seen_line:
            raise AssertionError(
                'Didn\'t see "%s" log line in timer output' % (TIMER_DISABLED_LOG_LINE)
            )

    def _start_times_engine(self, cmd):
        subprocess = concurrency.get_subprocess_module()
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            shell=False,
            preexec_fn=os.setsid,
        )
        self.add_process(process=process)
        return process

    def _append_to_cfg_file(self, cfg_path, content):
        with open(cfg_path, "a") as f:
            f.write(content)

    def _remove_tempfile(self, fd, path):
        os.close(fd)
        os.unlink(path)

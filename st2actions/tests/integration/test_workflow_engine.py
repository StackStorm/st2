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

import psutil

from st2common.util import concurrency
from st2tests.base import IntegrationTestCase

__all__ = ["WorkflowEngineTestCase"]

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

ST2_CONFIG_PATH = os.path.join(BASE_DIR, "../../../conf/st2.tests.conf")

ST2_CONFIG_PATH = os.path.abspath(ST2_CONFIG_PATH)

PYTHON_BINARY = sys.executable

BINARY = os.path.join(BASE_DIR, "../../../st2actions/bin/st2workflowengine")
BINARY = os.path.abspath(BINARY)

PACKS_BASE_PATH = os.path.abspath(os.path.join(BASE_DIR, "../../../contrib"))

DEFAULT_CMD = [PYTHON_BINARY, BINARY, "--config-file", ST2_CONFIG_PATH]


class WorkflowEngineTestCase(IntegrationTestCase):
    @classmethod
    def setUpClass(cls):
        super(WorkflowEngineTestCase, cls).setUpClass()

    def test_shutdown(self):
        process = self._start_workflow_engine_container()

        # Give it some time to start up
        concurrency.sleep(7)

        # Assert process has started and is running
        self.assertProcessIsRunning(process=process)

        pp = psutil.Process(process.pid)

        # Send SIGTERM
        process.send_signal(signal.SIGTERM)
        concurrency.sleep(1)

        # Assert process is still running after receiving SIGTREM signal.
        self.assertProcessIsRunning(process)

        # Wait for rquest shutdown time.
        concurrency.sleep(15)

        # Verify process has exited.
        self.assertProcessExited(proc=pp)
        self.remove_process(process=process)

    def _start_workflow_engine_container(self):
        subprocess = concurrency.get_subprocess_module()
        print("Using command: %s" % (" ".join(DEFAULT_CMD)))
        process = subprocess.Popen(
            DEFAULT_CMD,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            shell=False,
            preexec_fn=os.setsid,
        )
        self.add_process(process=process)
        return process

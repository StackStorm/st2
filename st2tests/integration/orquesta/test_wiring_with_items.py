# -*- coding: utf-8 -*-

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
import tempfile

from integration.orquesta import base

from st2common.constants import action as ac_const


class WithItemsWiringTest(base.TestWorkflowExecution):

    tempfiles = None

    def tearDown(self):
        if self.tempfiles and isinstance(self.tempfiles, list):
            for f in self.tempfiles:
                if os.path.exists(f):
                    os.remove(f)

        self.tempfiles = None

        super(WithItemsWiringTest, self).tearDown()

    def test_with_items(self):
        wf_name = "examples.orquesta-with-items"

        members = ["Lakshmi", "Lindsay", "Tomaz", "Matt", "Drew"]
        wf_input = {"members": members}

        message = "%s, resistance is futile!"
        expected_output = {"items": [message % i for i in members]}
        expected_result = {"output": expected_output}

        ex = self._execute_workflow(wf_name, wf_input)
        ex = self._wait_for_completion(ex)

        self.assertEqual(ex.status, ac_const.LIVEACTION_STATUS_SUCCEEDED)
        self.assertDictEqual(ex.result, expected_result)

    def test_with_items_failure(self):
        wf_name = "examples.orquesta-test-with-items-failure"

        ex = self._execute_workflow(wf_name)
        ex = self._wait_for_completion(ex)

        self._wait_for_task(ex, "task1", num_task_exs=10)

        self.assertEqual(ex.status, ac_const.LIVEACTION_STATUS_FAILED)

    def test_with_items_concurrency(self):
        wf_name = "examples.orquesta-test-with-items"

        concurrency = 2
        num_items = 5
        self.tempfiles = []

        for i in range(0, num_items):
            _, f = tempfile.mkstemp()
            os.chmod(f, 0o755)  # nosec
            self.tempfiles.append(f)

        wf_input = {"tempfiles": self.tempfiles, "concurrency": concurrency}
        ex = self._execute_workflow(wf_name, wf_input)
        ex = self._wait_for_state(ex, [ac_const.LIVEACTION_STATUS_RUNNING])

        self._wait_for_task(ex, "task1", num_task_exs=2)
        os.remove(self.tempfiles[0])
        os.remove(self.tempfiles[1])

        self._wait_for_task(ex, "task1", num_task_exs=4)
        os.remove(self.tempfiles[2])
        os.remove(self.tempfiles[3])

        self._wait_for_task(ex, "task1", num_task_exs=5)
        os.remove(self.tempfiles[4])

        ex = self._wait_for_completion(ex)

        self.assertEqual(ex.status, ac_const.LIVEACTION_STATUS_SUCCEEDED)

    def test_with_items_cancellation(self):
        wf_name = "examples.orquesta-test-with-items"

        concurrency = 2
        num_items = 2
        self.tempfiles = []

        for i in range(0, num_items):
            _, f = tempfile.mkstemp()
            os.chmod(f, 0o755)  # nosec
            self.tempfiles.append(f)

        wf_input = {"tempfiles": self.tempfiles, "concurrency": concurrency}
        ex = self._execute_workflow(wf_name, wf_input)
        ex = self._wait_for_state(ex, [ac_const.LIVEACTION_STATUS_RUNNING])

        # Wait for action executions to run.
        self._wait_for_task(
            ex, "task1", ac_const.LIVEACTION_STATUS_RUNNING, num_task_exs=concurrency
        )

        # Cancel the workflow execution.
        self.st2client.executions.delete(ex)

        # Expecting the ex to be canceling, waiting for task1 to complete.
        ex = self._wait_for_state(ex, ac_const.LIVEACTION_STATUS_CANCELING)

        # Delete the temporary files.
        for f in self.tempfiles:
            os.remove(f)
            self.assertFalse(os.path.exists(f))

        # Task is completed successfully for graceful exit.
        self._wait_for_task(
            ex, "task1", ac_const.LIVEACTION_STATUS_SUCCEEDED, num_task_exs=concurrency
        )

        # Wait for the ex to be canceled.
        ex = self._wait_for_state(ex, ac_const.LIVEACTION_STATUS_CANCELED)

    def test_with_items_concurrency_cancellation(self):
        wf_name = "examples.orquesta-test-with-items"

        concurrency = 2
        num_items = 4
        self.tempfiles = []

        for i in range(0, num_items):
            _, f = tempfile.mkstemp()
            os.chmod(f, 0o755)  # nosec
            self.tempfiles.append(f)

        wf_input = {"tempfiles": self.tempfiles, "concurrency": concurrency}
        ex = self._execute_workflow(wf_name, wf_input)
        ex = self._wait_for_state(ex, [ac_const.LIVEACTION_STATUS_RUNNING])

        # Wait for action executions to run.
        self._wait_for_task(
            ex, "task1", ac_const.LIVEACTION_STATUS_RUNNING, num_task_exs=concurrency
        )

        # Cancel the workflow execution.
        self.st2client.executions.delete(ex)

        # Expecting the ex to be canceling, waiting for task1 to complete.
        ex = self._wait_for_state(ex, ac_const.LIVEACTION_STATUS_CANCELING)

        # Delete all the temporary files. There could be a race as to which
        # files were picked up in the first batch by with items concurrency.
        for f in self.tempfiles:
            os.remove(f)
            self.assertFalse(os.path.exists(f))

        # Task is completed successfully for graceful exit.
        self._wait_for_task(
            ex, "task1", ac_const.LIVEACTION_STATUS_SUCCEEDED, num_task_exs=concurrency
        )

        # Wait for the ex to be canceled.
        ex = self._wait_for_state(ex, ac_const.LIVEACTION_STATUS_CANCELED)

    def test_with_items_pause_and_resume(self):
        wf_name = "examples.orquesta-test-with-items"

        num_items = 2
        self.tempfiles = []

        for i in range(0, num_items):
            _, f = tempfile.mkstemp()
            os.chmod(f, 0o755)  # nosec
            self.tempfiles.append(f)

        wf_input = {"tempfiles": self.tempfiles}
        ex = self._execute_workflow(wf_name, wf_input)
        ex = self._wait_for_state(ex, [ac_const.LIVEACTION_STATUS_RUNNING])

        # Pause the workflow execution.
        self.st2client.executions.pause(ex.id)

        # Expecting the ex to be pausing, waiting for task1 to complete.
        ex = self._wait_for_state(ex, ac_const.LIVEACTION_STATUS_PAUSING)

        # Delete the first set of temporary files.
        for f in self.tempfiles:
            os.remove(f)
            self.assertFalse(os.path.exists(f))

        # Wait for action executions for task to succeed.
        self._wait_for_task(
            ex, "task1", ac_const.LIVEACTION_STATUS_SUCCEEDED, num_task_exs=num_items
        )

        # Wait for the workflow execution to pause.
        ex = self._wait_for_state(ex, ac_const.LIVEACTION_STATUS_PAUSED)

        # Resume the workflow execution.
        ex = self.st2client.executions.resume(ex.id)

        # Wait for completion.
        ex = self._wait_for_state(ex, ac_const.LIVEACTION_STATUS_SUCCEEDED)

    def test_with_items_concurrency_pause_and_resume(self):
        wf_name = "examples.orquesta-test-with-items"

        concurrency = 2
        num_items = 4
        self.tempfiles = []

        for i in range(0, num_items):
            _, f = tempfile.mkstemp()
            os.chmod(f, 0o755)  # nosec
            self.tempfiles.append(f)

        wf_input = {"tempfiles": self.tempfiles, "concurrency": concurrency}
        ex = self._execute_workflow(wf_name, wf_input)
        ex = self._wait_for_state(ex, [ac_const.LIVEACTION_STATUS_RUNNING])

        # Pause the workflow execution.
        self.st2client.executions.pause(ex.id)

        # Expecting the ex to be pausing, waiting for task1 to complete.
        ex = self._wait_for_state(ex, ac_const.LIVEACTION_STATUS_PAUSING)

        # Delete the first set of temporary files.
        for f in self.tempfiles[0:concurrency]:
            os.remove(f)
            self.assertFalse(os.path.exists(f))

        # Wait for action executions for task to succeed.
        self._wait_for_task(
            ex, "task1", ac_const.LIVEACTION_STATUS_SUCCEEDED, num_task_exs=concurrency
        )

        # Wait for the workflow execution to pause.
        ex = self._wait_for_state(ex, ac_const.LIVEACTION_STATUS_PAUSED)

        # Resume the workflow execution.
        ex = self.st2client.executions.resume(ex.id)

        # Delete the remaining temporary files.
        for f in self.tempfiles[concurrency:]:
            os.remove(f)
            self.assertFalse(os.path.exists(f))

        # Wait for action executions for task to succeed.
        self._wait_for_task(
            ex, "task1", ac_const.LIVEACTION_STATUS_SUCCEEDED, num_task_exs=num_items
        )

        # Wait for completion.
        ex = self._wait_for_state(ex, ac_const.LIVEACTION_STATUS_SUCCEEDED)

    def test_subworkflow_empty_with_items(self):
        wf_name = "examples.orquesta-test-subworkflow-empty-with-items"
        ex = self._execute_workflow(wf_name)
        ex = self._wait_for_completion(ex)

        self.assertEqual(ex.status, ac_const.LIVEACTION_STATUS_SUCCEEDED)

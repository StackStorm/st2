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

from integration.orquesta import base

from st2common.constants import action as ac_const


class TaskDelayWiringTest(base.TestWorkflowExecution):
    def test_task_delay(self):
        wf_name = "examples.orquesta-delay"
        wf_input = {"name": "Thanos", "delay": 1}

        expected_output = {"greeting": "Thanos, All your base are belong to us!"}
        expected_result = {"output": expected_output}

        ex = self._execute_workflow(wf_name, wf_input)
        ex = self._wait_for_completion(ex)

        self.assertEqual(ex.status, ac_const.LIVEACTION_STATUS_SUCCEEDED)
        self.assertDictEqual(ex.result, expected_result)

    def test_task_delay_workflow_cancellation(self):
        wf_name = "examples.orquesta-delay"
        wf_input = {"name": "Thanos", "delay": 300}

        # Launch workflow and task1 should be delayed.
        ex = self._execute_workflow(wf_name, wf_input)
        self._wait_for_task(ex, "task1", ac_const.LIVEACTION_STATUS_DELAYED)

        # Cancel the workflow before the temp file is created. The workflow will be paused
        # but task1 will still be running to allow for graceful exit.
        self.st2client.executions.delete(ex)

        # Wait for the ex to be canceled.
        ex = self._wait_for_state(ex, ac_const.LIVEACTION_STATUS_CANCELED)

        # Task execution should be canceled.
        self._wait_for_task(ex, "task1", ac_const.LIVEACTION_STATUS_CANCELED)

        # Get the updated execution with task result.
        ex = self._wait_for_state(ex, ac_const.LIVEACTION_STATUS_CANCELED)

    def test_task_delay_task_cancellation(self):
        wf_name = "examples.orquesta-delay"
        wf_input = {"name": "Thanos", "delay": 300}

        # Launch workflow and task1 should be delayed.
        ex = self._execute_workflow(wf_name, wf_input)
        task_exs = self._wait_for_task(ex, "task1", ac_const.LIVEACTION_STATUS_DELAYED)

        # Cancel the task execution.
        self.st2client.executions.delete(task_exs[0])

        # Wait for the task and parent workflow to be canceled.
        self._wait_for_task(ex, "task1", ac_const.LIVEACTION_STATUS_CANCELED)

        # Get the updated execution with task result.
        ex = self._wait_for_state(ex, ac_const.LIVEACTION_STATUS_CANCELED)

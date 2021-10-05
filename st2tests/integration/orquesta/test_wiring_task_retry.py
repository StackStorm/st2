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


class TaskRetryWiringTest(base.TestWorkflowExecution):
    def test_task_retry(self):
        wf_name = "examples.orquesta-task-retry"

        ex = self._execute_workflow(wf_name)
        ex = self._wait_for_completion(ex)

        self.assertEqual(ex.status, ac_const.LIVEACTION_STATUS_SUCCEEDED)

        # Assert there are retries for the task.
        task_exs = [
            task_ex
            for task_ex in self._get_children(ex)
            if task_ex.context.get("orquesta", {}).get("task_name", "") == "check"
        ]

        self.assertGreater(len(task_exs), 1)

    def test_task_retry_exhausted(self):
        wf_name = "examples.orquesta-task-retry-exhausted"

        ex = self._execute_workflow(wf_name)
        ex = self._wait_for_completion(ex)

        # Assert the workflow has failed.
        self.assertEqual(ex.status, ac_const.LIVEACTION_STATUS_FAILED)

        # Assert the task has exhausted the number of retries
        task_exs = [
            task_ex
            for task_ex in self._get_children(ex)
            if task_ex.context.get("orquesta", {}).get("task_name", "") == "check"
        ]

        self.assertListEqual(["failed"] * 3, [task_ex.status for task_ex in task_exs])

        # Assert the task following the retry task is not run.
        task_exs = [
            task_ex
            for task_ex in self._get_children(ex)
            if task_ex.context.get("orquesta", {}).get("task_name", "") == "delete"
        ]

        self.assertEqual(len(task_exs), 0)

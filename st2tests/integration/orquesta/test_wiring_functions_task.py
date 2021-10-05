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

from st2common.constants import action as action_constants


class FunctionsWiringTest(base.TestWorkflowExecution):
    def test_task_functions_in_yaql(self):
        wf_name = "examples.orquesta-test-yaql-task-functions"

        expected_output = {
            "last_task4_result": "False",
            "task9__1__parent": "task8__1",
            "task9__2__parent": "task8__2",
            "that_task_by_name": "task1",
            "this_task_by_name": "task1",
            "this_task_no_arg": "task1",
        }

        expected_result = {"output": expected_output}

        self._execute_workflow(
            wf_name, execute_async=False, expected_result=expected_result
        )

    def test_task_functions_in_jinja(self):
        wf_name = "examples.orquesta-test-jinja-task-functions"

        expected_output = {
            "last_task4_result": "False",
            "task9__1__parent": "task8__1",
            "task9__2__parent": "task8__2",
            "that_task_by_name": "task1",
            "this_task_by_name": "task1",
            "this_task_no_arg": "task1",
        }

        expected_result = {"output": expected_output}

        self._execute_workflow(
            wf_name, execute_async=False, expected_result=expected_result
        )

    def test_task_nonexistent_in_yaql(self):
        wf_name = "examples.orquesta-test-yaql-task-nonexistent"

        expected_output = None

        expected_errors = [
            {
                "type": "error",
                "message": (
                    "YaqlEvaluationException: Unable to evaluate expression "
                    "'<% task(\"task0\") %>'. ExpressionEvaluationException: "
                    'Unable to find task execution for "task0".'
                ),
                "task_transition_id": "continue__t0",
                "task_id": "task1",
                "route": 0,
            }
        ]

        expected_result = {"output": expected_output, "errors": expected_errors}

        self._execute_workflow(
            wf_name,
            execute_async=False,
            expected_status=action_constants.LIVEACTION_STATUS_FAILED,
            expected_result=expected_result,
        )

    def test_task_nonexistent_in_jinja(self):
        wf_name = "examples.orquesta-test-jinja-task-nonexistent"

        expected_output = None

        expected_errors = [
            {
                "type": "error",
                "message": (
                    "JinjaEvaluationException: Unable to evaluate expression "
                    "'{{ task(\"task0\") }}'. ExpressionEvaluationException: "
                    'Unable to find task execution for "task0".'
                ),
                "task_transition_id": "continue__t0",
                "task_id": "task1",
                "route": 0,
            }
        ]

        expected_result = {"output": expected_output, "errors": expected_errors}

        self._execute_workflow(
            wf_name,
            execute_async=False,
            expected_status=action_constants.LIVEACTION_STATUS_FAILED,
            expected_result=expected_result,
        )

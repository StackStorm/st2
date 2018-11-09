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

from integration.orquesta import base

from st2common.constants import action as action_constants


class FunctionsWiringTest(base.TestWorkflowExecution):

    def test_task_functions_in_yaql(self):
        wf_name = 'examples.orquesta-test-yaql-task-functions'

        expected_output = {
            'last_task3_result': 'False',
            'task7__1__parent': 'task6__1',
            'task7__2__parent': 'task6__2',
            'that_task_by_name': 'task1',
            'this_task_by_name': 'task1',
            'this_task_no_arg': 'task1'
        }

        expected_result = {'output': expected_output}

        self._execute_workflow(wf_name, execute_async=False, expected_result=expected_result)

    def test_task_functions_in_jinja(self):
        wf_name = 'examples.orquesta-test-jinja-task-functions'

        expected_output = {
            'last_task3_result': 'False',
            'task7__1__parent': 'task6__1',
            'task7__2__parent': 'task6__2',
            'that_task_by_name': 'task1',
            'this_task_by_name': 'task1',
            'this_task_no_arg': 'task1'
        }

        expected_result = {'output': expected_output}

        self._execute_workflow(wf_name, execute_async=False, expected_result=expected_result)

    def test_task_nonexistent_in_yaql(self):
        wf_name = 'examples.orquesta-test-yaql-task-nonexistent'

        expected_output = None

        expected_errors = [
            {
                'message': (
                    'Unable to evaluate expression \'<% task("task0") %>\'. '
                    'ExpressionEvaluationException: Unable to find task execution for "task0".'
                ),
                'task_transition_id': 'noop__0',
                'task_id': 'task1'
            }
        ]

        expected_result = {'output': expected_output, 'errors': expected_errors}

        self._execute_workflow(
            wf_name,
            execute_async=False,
            expected_status=action_constants.LIVEACTION_STATUS_FAILED,
            expected_result=expected_result
        )

    def test_task_nonexistent_in_jinja(self):
        wf_name = 'examples.orquesta-test-jinja-task-nonexistent'

        expected_output = None

        expected_errors = [
            {
                'message': (
                    'Unable to evaluate expression \'{{ task("task0") }}\'. '
                    'ExpressionEvaluationException: Unable to find task execution for "task0".'
                ),
                'task_transition_id': 'noop__0',
                'task_id': 'task1'
            }
        ]

        expected_result = {'output': expected_output, 'errors': expected_errors}

        self._execute_workflow(
            wf_name,
            execute_async=False,
            expected_status=action_constants.LIVEACTION_STATUS_FAILED,
            expected_result=expected_result
        )

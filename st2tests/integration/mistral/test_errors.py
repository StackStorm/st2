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
from integration.mistral import base


class ExceptionHandlingTest(base.TestWorkflowExecution):

    def test_bad_workflow(self):
        with self.assertRaises(Exception) as t:
            self._execute_workflow('examples.mistral-foobar', {})

        self.assertIn('Action "examples.mistral-foobar" cannot be found', t.exception.message)

    def test_bad_action(self):
        execution = self._execute_workflow('examples.mistral-error-bad-action', {})
        execution = self._wait_for_completion(execution)
        self._assert_failure(execution)
        self.assertIn('Failed to find action', execution.result['extra']['state_info'])

    def test_bad_wf_arg(self):
        execution = self._execute_workflow('examples.mistral-error-bad-wf-arg', {})

        execution = self._wait_for_completion(
            execution,
            expect_tasks=False,
            expect_tasks_completed=False
        )

        self._assert_failure(execution, expect_tasks_failure=False)
        self.assertIn('Invalid input', execution.result['extra']['state_info'])

    def test_bad_task_transition(self):
        execution = self._execute_workflow('examples.mistral-error-bad-task-transition', {})

        execution = self._wait_for_completion(
            execution,
            expect_tasks=False,
            expect_tasks_completed=False
        )

        self._assert_failure(execution, expect_tasks_failure=False)
        self.assertIn("Task 'task3' not found", execution.result['error'])

    def test_bad_with_items(self):
        execution = self._execute_workflow('examples.mistral-error-bad-with-items', {})
        execution = self._wait_for_completion(execution, expect_tasks=False)
        self._assert_failure(execution, expect_tasks_failure=False)
        self.assertIn('Wrong input format', execution.result['extra']['state_info'])

    def test_bad_expr_yaql(self):
        execution = self._execute_workflow('examples.mistral-test-yaql-bad-expr', {})
        execution = self._wait_for_completion(execution)
        self._assert_failure(execution, expect_tasks_failure=False)
        self.assertIn('Can not evaluate YAQL expression', execution.result['extra']['state_info'])

    def test_bad_publish_yaql(self):
        execution = self._execute_workflow('examples.mistral-test-yaql-bad-publish', {})
        execution = self._wait_for_completion(execution)
        self._assert_failure(execution, expect_tasks_failure=False)
        self.assertIn('Can not evaluate YAQL expression', execution.result['extra']['state_info'])

    def test_bad_subworkflow_input_yaql(self):
        execution = self._execute_workflow('examples.mistral-test-yaql-bad-subworkflow-input', {})
        execution = self._wait_for_completion(execution)
        self._assert_failure(execution, expect_tasks_failure=False)
        self.assertIn('Can not evaluate YAQL expression', execution.result['extra']['state_info'])

    def test_bad_task_transition_yaql(self):
        execution = self._execute_workflow('examples.mistral-test-yaql-bad-task-transition', {})
        execution = self._wait_for_completion(execution)
        self._assert_failure(execution, expect_tasks_failure=False)
        self.assertIn('Can not evaluate YAQL expression', execution.result['extra']['state_info'])

    def test_bad_with_items_yaql(self):
        execution = self._execute_workflow('examples.mistral-test-yaql-bad-with-items', {})
        execution = self._wait_for_completion(execution, expect_tasks=False)
        self._assert_failure(execution, expect_tasks_failure=False)
        self.assertIn('Can not evaluate YAQL expression', execution.result['extra']['state_info'])

    def test_bad_expr_jinja(self):
        execution = self._execute_workflow('examples.mistral-test-jinja-bad-expr', {})
        execution = self._wait_for_completion(execution, expect_tasks=False)
        self._assert_failure(execution, expect_tasks_failure=False)

        # TODO: Currently, Mistral returns "UndefinedError ContextView object has no attribute".
        # Need to fix Mistral to return "Cannot evaulate Jinja expression."
        # self.assertIn('Can not evaluate Jinja expression',
        # execution.result['extra']['state_info'])

    def test_bad_publish_jinja(self):
        execution = self._execute_workflow('examples.mistral-test-jinja-bad-publish', {})
        execution = self._wait_for_completion(execution)
        self._assert_failure(execution, expect_tasks_failure=False)
        self.assertIn('Can not evaluate Jinja expression', execution.result['extra']['state_info'])

    def test_bad_subworkflow_input_jinja(self):
        execution = self._execute_workflow('examples.mistral-test-jinja-bad-subworkflow-input', {})
        execution = self._wait_for_completion(execution)
        self._assert_failure(execution, expect_tasks_failure=False)
        self.assertIn('Can not evaluate Jinja expression', execution.result['extra']['state_info'])

    def test_bad_task_transition_jinja(self):
        execution = self._execute_workflow('examples.mistral-test-jinja-bad-task-transition', {})
        execution = self._wait_for_completion(execution)
        self._assert_failure(execution, expect_tasks_failure=False)
        self.assertIn('Can not evaluate Jinja expression', execution.result['extra']['state_info'])

    def test_bad_with_items_jinja(self):
        execution = self._execute_workflow('examples.mistral-test-jinja-bad-with-items', {})
        execution = self._wait_for_completion(execution, expect_tasks=False)
        self._assert_failure(execution, expect_tasks_failure=False)
        self.assertIn('Can not evaluate Jinja expression', execution.result['extra']['state_info'])

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

from st2common.constants import action as action_constants


class ExceptionHandlingTest(base.TestWorkflowExecution):

    def test_bad_workflow(self):
        with self.assertRaises(Exception) as t:
            self._execute_workflow('examples.mistral-foobar', {})

        self.assertIn('Action "examples.mistral-foobar" cannot be found', t.exception.message)

    def test_bad_action(self):
        ex = self._execute_workflow('examples.mistral-error-bad-action', {})
        ex = self._wait_for_completion(ex)
        self.assertEqual(ex.status, action_constants.LIVEACTION_STATUS_FAILED)
        self.assertIn('Failed to find action', ex.result['extra']['state_info'])

    def test_bad_wf_arg(self):
        ex = self._execute_workflow('examples.mistral-error-bad-wf-arg', {})
        ex = self._wait_for_completion(ex)
        self.assertEqual(ex.status, action_constants.LIVEACTION_STATUS_FAILED)
        self.assertIn('Invalid input', ex.result['extra']['state_info'])

    def test_bad_task_transition(self):
        ex = self._execute_workflow('examples.mistral-error-bad-task-transition', {})
        ex = self._wait_for_completion(ex)
        self.assertEqual(ex.status, action_constants.LIVEACTION_STATUS_FAILED)
        self.assertIn("Task 'task3' not found", ex.result['error'])

    def test_bad_with_items(self):
        ex = self._execute_workflow('examples.mistral-error-bad-with-items', {})
        ex = self._wait_for_completion(ex)
        self.assertEqual(ex.status, action_constants.LIVEACTION_STATUS_FAILED)
        self.assertIn('Wrong input format', ex.result['extra']['state_info'])

    def test_bad_expr_yaql(self):
        ex = self._execute_workflow('examples.mistral-test-yaql-bad-expr', {})
        ex = self._wait_for_completion(ex)
        self.assertEqual(ex.status, action_constants.LIVEACTION_STATUS_FAILED)
        self.assertIn('Can not evaluate YAQL expression', ex.result['extra']['state_info'])

    def test_bad_publish_yaql(self):
        ex = self._execute_workflow('examples.mistral-test-yaql-bad-publish', {})
        ex = self._wait_for_completion(ex)
        self.assertEqual(ex.status, action_constants.LIVEACTION_STATUS_FAILED)
        self.assertIn('Can not evaluate YAQL expression', ex.result['extra']['state_info'])

    def test_bad_subworkflow_input_yaql(self):
        ex = self._execute_workflow('examples.mistral-test-yaql-bad-subworkflow-input', {})
        ex = self._wait_for_completion(ex)
        self.assertEqual(ex.status, action_constants.LIVEACTION_STATUS_FAILED)
        self.assertIn('Can not evaluate YAQL expression', ex.result['extra']['state_info'])

    def test_bad_task_transition_yaql(self):
        ex = self._execute_workflow('examples.mistral-test-yaql-bad-task-transition', {})
        ex = self._wait_for_completion(ex)
        self.assertEqual(ex.status, action_constants.LIVEACTION_STATUS_FAILED)
        self.assertIn('Can not evaluate YAQL expression', ex.result['extra']['state_info'])

    def test_bad_with_items_yaql(self):
        ex = self._execute_workflow('examples.mistral-test-yaql-bad-with-items', {})
        ex = self._wait_for_completion(ex)
        self.assertEqual(ex.status, action_constants.LIVEACTION_STATUS_FAILED)
        self.assertIn('Can not evaluate YAQL expression', ex.result['extra']['state_info'])

    def test_bad_expr_jinja(self):
        ex = self._execute_workflow('examples.mistral-test-jinja-bad-expr', {})
        ex = self._wait_for_completion(ex)
        self.assertEqual(ex.status, action_constants.LIVEACTION_STATUS_FAILED)

        # TODO: Currently, Mistral returns "UndefinedError ContextView object has no attribute".
        # Need to fix Mistral to return "Cannot evaulate Jinja expression."
        # self.assertIn('Can not evaluate Jinja expression',
        # ex.result['extra']['state_info'])

    def test_bad_publish_jinja(self):
        ex = self._execute_workflow('examples.mistral-test-jinja-bad-publish', {})
        ex = self._wait_for_completion(ex)
        self.assertEqual(ex.status, action_constants.LIVEACTION_STATUS_FAILED)
        self.assertIn('Can not evaluate Jinja expression', ex.result['extra']['state_info'])

    def test_bad_subworkflow_input_jinja(self):
        ex = self._execute_workflow('examples.mistral-test-jinja-bad-subworkflow-input', {})
        ex = self._wait_for_completion(ex)
        self.assertEqual(ex.status, action_constants.LIVEACTION_STATUS_FAILED)
        self.assertIn('Can not evaluate Jinja expression', ex.result['extra']['state_info'])

    def test_bad_task_transition_jinja(self):
        ex = self._execute_workflow('examples.mistral-test-jinja-bad-task-transition', {})
        ex = self._wait_for_completion(ex)
        self.assertEqual(ex.status, action_constants.LIVEACTION_STATUS_FAILED)
        self.assertIn('Can not evaluate Jinja expression', ex.result['extra']['state_info'])

    def test_bad_with_items_jinja(self):
        ex = self._execute_workflow('examples.mistral-test-jinja-bad-with-items', {})
        ex = self._wait_for_completion(ex)
        self.assertEqual(ex.status, action_constants.LIVEACTION_STATUS_FAILED)
        self.assertIn('Can not evaluate Jinja expression', ex.result['extra']['state_info'])

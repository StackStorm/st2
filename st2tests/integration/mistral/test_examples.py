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

from integration.mistral import base


class ExamplesTest(base.TestWorkflowExecution):

    def test_workbook_multiple_subflows(self):
        execution = self._execute_workflow('examples.mistral-workbook-multiple-subflows')
        execution = self._wait_for_completion(execution)
        self.assertEqual(execution.status, 'succeeded')

    def test_handle_error(self):
        execution = self._execute_workflow('examples.mistral-handle-error')
        execution = self._wait_for_completion(execution)
        self.assertEqual(execution.status, 'failed')
        tasks = {t['name']: t for t in execution.result['tasks']}
        self.assertEqual(tasks['task1']['state'], 'ERROR')
        self.assertIn(tasks['notify_on_error']['state'], ['RUNNING', 'SUCCESS'])

    def test_handle_retry(self):
        execution = self._execute_workflow('examples.mistral-handle-retry')
        execution = self._wait_for_completion(execution)
        self.assertEqual(execution.status, 'succeeded')

    def test_repeat(self):
        inputs = {'cmd': 'echo "Yo!"'}
        execution = self._execute_workflow('examples.mistral-repeat', parameters=inputs)
        execution = self._wait_for_completion(execution)
        self.assertEqual(execution.status, 'succeeded')
        self.assertEqual(len(execution.result['result']), 3)
        self.assertListEqual(execution.result['result'], ['Yo!\n', 'Yo!\n', 'Yo!\n'])

    def test_repeat_with_items(self):
        inputs = {'cmds': ['echo "a"', 'echo "b"', 'echo "c"']}
        execution = self._execute_workflow('examples.mistral-repeat-with-items', parameters=inputs)
        execution = self._wait_for_completion(execution)
        self.assertEqual(execution.status, 'succeeded')
        self.assertEqual(len(execution.result['result']), 3)
        self.assertListEqual(sorted(execution.result['result']), ['a\n', 'b\n', 'c\n'])

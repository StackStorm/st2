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

import six

from integration.mistral import base


class ExamplesTest(base.TestWorkflowExecution):

    def test_environment(self):
        execution = self._execute_workflow('examples.mistral-env-var')
        execution = self._wait_for_completion(execution)
        self._assert_success(execution, num_tasks=1)
        tasks = {t['name']: t for t in execution.result['tasks']}
        self.assertEqual(tasks['task1']['result']['stdout'], execution.id)

    def test_branching(self):
        # Execute with path a.
        inputs = {'which': 'a'}
        execution = self._execute_workflow('examples.mistral-branching', parameters=inputs)
        execution = self._wait_for_completion(execution)
        self._assert_success(execution, num_tasks=2)
        tasks = {t['name']: t for t in execution.result['tasks']}
        self.assertEqual(tasks['a']['state'], 'SUCCESS')
        self.assertEqual(tasks['a']['result']['stdout'], 'Took path A.')

        # Execute with path b.
        inputs = {'which': 'b'}
        execution = self._execute_workflow('examples.mistral-branching', parameters=inputs)
        execution = self._wait_for_completion(execution)
        self._assert_success(execution, num_tasks=2)
        tasks = {t['name']: t for t in execution.result['tasks']}
        self.assertEqual(tasks['b']['state'], 'SUCCESS')
        self.assertEqual(tasks['b']['result']['stdout'], 'Took path B.')

        # Execute with path c.
        inputs = {'which': 'c'}
        execution = self._execute_workflow('examples.mistral-branching', parameters=inputs)
        execution = self._wait_for_completion(execution)
        self._assert_success(execution, num_tasks=2)
        tasks = {t['name']: t for t in execution.result['tasks']}
        self.assertEqual(tasks['c']['state'], 'SUCCESS')
        self.assertEqual(tasks['c']['result']['stdout'], 'Took path C.')

    def test_join(self):
        execution = self._execute_workflow('examples.mistral-join')
        execution = self._wait_for_completion(execution)
        self._assert_success(execution, num_tasks=5)
        tasks = {t['name']: t for t in execution.result['tasks']}
        for task_name, task_result in six.iteritems(tasks):
            self.assertEqual(task_result['result']['stdout'], task_name)

    def test_handle_error(self):
        execution = self._execute_workflow('examples.mistral-handle-error')
        execution = self._wait_for_completion(execution, expect_tasks_completed=False)
        self.assertEqual(execution.status, 'failed')
        self.assertIn('tasks', execution.result)
        self.assertEqual(2, len(execution.result['tasks']))
        tasks = {t['name']: t for t in execution.result['tasks']}
        self.assertEqual(tasks['task1']['state'], 'ERROR')
        self.assertIn(tasks['notify_on_error']['state'], ['RUNNING', 'SUCCESS'])

    def test_handle_error_task_default(self):
        execution = self._execute_workflow('examples.mistral-handle-error-task-default')
        execution = self._wait_for_completion(execution, expect_tasks_completed=False)
        self.assertEqual(execution.status, 'failed')
        self.assertIn('tasks', execution.result)
        self.assertEqual(2, len(execution.result['tasks']))
        tasks = {t['name']: t for t in execution.result['tasks']}
        self.assertEqual(tasks['task1']['state'], 'ERROR')
        self.assertIn(tasks['notify_on_error']['state'], ['RUNNING', 'SUCCESS'])

    def test_handle_retry(self):
        execution = self._execute_workflow('examples.mistral-handle-retry')
        execution = self._wait_for_completion(execution)
        self._assert_success(execution, num_tasks=4)

    def test_repeat(self):
        inputs = {'cmd': 'echo "Yo!"', 'count': 3}
        execution = self._execute_workflow('examples.mistral-repeat', parameters=inputs)
        execution = self._wait_for_completion(execution)
        self._assert_success(execution, num_tasks=1)
        self.assertEqual(len(execution.result['result']), inputs['count'])
        self.assertListEqual(execution.result['result'], ['Yo!'] * inputs['count'])

    def test_repeat_with_items(self):
        inputs = {'cmds': ['echo "a"', 'echo "b"', 'echo "c"']}
        execution = self._execute_workflow('examples.mistral-repeat-with-items', parameters=inputs)
        execution = self._wait_for_completion(execution)
        self._assert_success(execution, num_tasks=1)
        self.assertEqual(len(execution.result['result']), len(inputs['cmds']))
        self.assertListEqual(sorted(execution.result['result']), ['a', 'b', 'c'])

    def test_with_items_batch_processing(self):
        inputs = {'cmd': 'date +%s', 'count': 4}
        execution = self._execute_workflow('examples.mistral-with-items-concurrency',
                                           parameters=inputs)

        execution = self._wait_for_completion(execution)
        self._assert_success(execution, num_tasks=1)
        self.assertEqual(len(execution.result['result']), inputs['count'])

        timestamps = [int(dt) for dt in execution.result['result']]
        self.assertTrue(timestamps[1] - timestamps[0] <= 1)
        self.assertTrue(timestamps[3] - timestamps[2] <= 1)
        self.assertTrue(timestamps[2] - timestamps[1] >= 2)

    def test_workbook_multiple_subflows(self):
        execution = self._execute_workflow('examples.mistral-workbook-multiple-subflows')
        execution = self._wait_for_completion(execution)
        self._assert_success(execution, num_tasks=4)

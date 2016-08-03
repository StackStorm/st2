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

import ast
import os
import shutil
import tempfile

import eventlet

from integration.mistral import base


class WiringTest(base.TestWorkflowExecution):

    temp_dir_path = None

    def setUp(self):
        super(WiringTest, self).setUp()

        # Create temporary directory used by the tests
        _, self.temp_dir_path = tempfile.mkstemp()
        os.chmod(self.temp_dir_path, 0666)   # nosec

    def tearDown(self):
        if self.temp_dir_path and os.path.exists(self.temp_dir_path):
            if os.path.isdir(self.temp_dir_path):
                shutil.rmtree(self.temp_dir_path)
            else:
                os.remove(self.temp_dir_path)

    def test_basic_workflow(self):
        execution = self._execute_workflow('examples.mistral-basic', {'cmd': 'date'})
        execution = self._wait_for_completion(execution)
        self._assert_success(execution, num_tasks=1)
        self.assertIn('stdout', execution.result)

    def test_basic_workbook(self):
        execution = self._execute_workflow('examples.mistral-workbook-basic', {'cmd': 'date'})
        execution = self._wait_for_completion(execution)
        self._assert_success(execution, num_tasks=1)
        self.assertIn('stdout', execution.result)

    def test_complex_workbook(self):
        execution = self._execute_workflow(
            'examples.mistral-workbook-complex', {'vm_name': 'demo1'})
        execution = self._wait_for_completion(execution)
        self._assert_success(execution, num_tasks=8)
        self.assertIn('vm_id', execution.result)

    def test_complex_workbook_subflow_actions(self):
        execution = self._execute_workflow(
            'examples.mistral-workbook-subflows', {'subject': 'st2', 'adjective': 'cool'})
        execution = self._wait_for_completion(execution)
        self._assert_success(execution, num_tasks=2)
        self.assertIn('tagline', execution.result)
        self.assertEqual(execution.result['tagline'], 'st2 is cool!')

    def test_with_items(self):
        params = {'cmd': 'date', 'count': 8}
        execution = self._execute_workflow('examples.mistral-repeat', params)
        execution = self._wait_for_completion(execution)
        self._assert_success(execution, num_tasks=1)
        self.assertEqual(len(execution.result['result']), params['count'])

    def test_concurrent_load(self):
        wf_name = 'examples.mistral-workbook-complex'
        wf_params = {'vm_name': 'demo1'}
        executions = [self._execute_workflow(wf_name, wf_params) for i in range(3)]

        eventlet.sleep(30)

        for execution in executions:
            e = self._wait_for_completion(execution)
            self._assert_success(e, num_tasks=8)
            self.assertIn('vm_id', e.result)

    def test_execution_failure(self):
        execution = self._execute_workflow('examples.mistral-basic', {'cmd': 'foo'})
        execution = self._wait_for_completion(execution)
        self._assert_failure(execution)

    def test_cancellation(self):
        execution = self._execute_workflow('examples.mistral-test-cancel', {'sleep': 10})
        execution = self._wait_for_state(execution, ['running'])
        self.st2client.liveactions.delete(execution)
        execution = self._wait_for_completion(execution, expect_tasks_completed=False)
        self._assert_canceled(execution, are_tasks_completed=False)

    def test_task_cancellation(self):
        execution = self._execute_workflow('examples.mistral-test-cancel', {'sleep': 30})
        execution = self._wait_for_state(execution, ['running'])

        task_executions = [e for e in self.st2client.liveactions.get_all()
                           if e.context.get('parent', {}).get('execution_id') == execution.id]

        self.assertGreater(len(task_executions), 0)

        self.st2client.liveactions.delete(task_executions[0])
        execution = self._wait_for_completion(execution, expect_tasks_completed=True)
        self._assert_failure(execution)

        task_results = execution.result.get('tasks', [])
        self.assertGreater(len(task_results), 0)
        expected_state_info = {'error': 'Execution canceled by user.'}
        self.assertDictEqual(ast.literal_eval(task_results[0]['state_info']), expected_state_info)

    def test_basic_rerun(self):
        path = self.temp_dir_path

        with open(path, 'w') as f:
            f.write('1')

        execution = self._execute_workflow('examples.mistral-test-rerun', {'tempfile': path})
        execution = self._wait_for_completion(execution)
        self._assert_failure(execution)
        orig_st2_ex_id = execution.id
        orig_wf_ex_id = execution.context['mistral']['execution_id']

        with open(path, 'w') as f:
            f.write('0')

        execution = self.st2client.liveactions.re_run(orig_st2_ex_id)
        self.assertNotEqual(execution.id, orig_st2_ex_id)
        execution = self._wait_for_completion(execution)
        self._assert_success(execution, num_tasks=1)
        self.assertNotEqual(execution.context['mistral']['execution_id'], orig_wf_ex_id)

    def test_basic_rerun_task(self):
        path = self.temp_dir_path

        with open(path, 'w') as f:
            f.write('1')

        execution = self._execute_workflow('examples.mistral-test-rerun', {'tempfile': path})
        execution = self._wait_for_completion(execution)
        self._assert_failure(execution)
        orig_st2_ex_id = execution.id
        orig_wf_ex_id = execution.context['mistral']['execution_id']

        with open(path, 'w') as f:
            f.write('0')

        execution = self.st2client.liveactions.re_run(orig_st2_ex_id, tasks=['task1'])
        self.assertNotEqual(execution.id, orig_st2_ex_id)
        execution = self._wait_for_completion(execution)
        self._assert_success(execution, num_tasks=1)
        self.assertEqual(execution.context['mistral']['execution_id'], orig_wf_ex_id)

    def test_rerun_subflow_task(self):
        path = self.temp_dir_path

        with open(path, 'w') as f:
            f.write('1')

        workflow_name = 'examples.mistral-test-rerun-subflow'
        execution = self._execute_workflow(workflow_name, {'tempfile': path})
        execution = self._wait_for_completion(execution)
        self._assert_failure(execution)
        orig_st2_ex_id = execution.id
        orig_wf_ex_id = execution.context['mistral']['execution_id']

        with open(path, 'w') as f:
            f.write('0')

        execution = self.st2client.liveactions.re_run(orig_st2_ex_id, tasks=['task1.task1'])
        self.assertNotEqual(execution.id, orig_st2_ex_id)
        execution = self._wait_for_completion(execution)
        self._assert_success(execution, num_tasks=1)
        self.assertEqual(execution.context['mistral']['execution_id'], orig_wf_ex_id)

    def test_basic_rerun_and_reset_with_items_task(self):
        path = self.temp_dir_path

        with open(path, 'w') as f:
            f.write('1')

        execution = self._execute_workflow(
            'examples.mistral-test-rerun-with-items',
            {'tempfile': path}
        )

        execution = self._wait_for_completion(execution)
        self._assert_failure(execution)
        orig_st2_ex_id = execution.id
        orig_wf_ex_id = execution.context['mistral']['execution_id']

        with open(path, 'w') as f:
            f.write('0')

        execution = self.st2client.liveactions.re_run(orig_st2_ex_id, tasks=['task1'])
        self.assertNotEqual(execution.id, orig_st2_ex_id)

        execution = self._wait_for_completion(execution)
        self._assert_success(execution, num_tasks=1)
        self.assertEqual(execution.context['mistral']['execution_id'], orig_wf_ex_id)

        children = self.st2client.liveactions.get_property(execution.id, 'children')
        self.assertEqual(len(children), 4)

    def test_basic_rerun_and_resume_with_items_task(self):
        path = self.temp_dir_path

        with open(path, 'w') as f:
            f.write('1')

        execution = self._execute_workflow(
            'examples.mistral-test-rerun-with-items',
            {'tempfile': path}
        )

        execution = self._wait_for_completion(execution)
        self._assert_failure(execution)
        orig_st2_ex_id = execution.id
        orig_wf_ex_id = execution.context['mistral']['execution_id']

        with open(path, 'w') as f:
            f.write('0')

        execution = self.st2client.liveactions.re_run(
            orig_st2_ex_id,
            tasks=['task1'],
            no_reset=['task1']
        )

        self.assertNotEqual(execution.id, orig_st2_ex_id)

        execution = self._wait_for_completion(execution)
        self._assert_success(execution, num_tasks=1)
        self.assertEqual(execution.context['mistral']['execution_id'], orig_wf_ex_id)

        children = self.st2client.liveactions.get_property(execution.id, 'children')
        self.assertEqual(len(children), 2)

    def test_rerun_subflow_and_reset_with_items_task(self):
        path = self.temp_dir_path

        with open(path, 'w') as f:
            f.write('1')

        execution = self._execute_workflow(
            'examples.mistral-test-rerun-subflow-with-items',
            {'tempfile': path}
        )

        execution = self._wait_for_completion(execution)
        self._assert_failure(execution)
        orig_st2_ex_id = execution.id
        orig_wf_ex_id = execution.context['mistral']['execution_id']

        with open(path, 'w') as f:
            f.write('0')

        execution = self.st2client.liveactions.re_run(orig_st2_ex_id, tasks=['task1.task1'])
        self.assertNotEqual(execution.id, orig_st2_ex_id)

        execution = self._wait_for_completion(execution)
        self._assert_success(execution, num_tasks=1)
        self.assertEqual(execution.context['mistral']['execution_id'], orig_wf_ex_id)

        children = self.st2client.liveactions.get_property(execution.id, 'children')
        self.assertEqual(len(children), 4)

    def test_rerun_subflow_and_resume_with_items_task(self):
        path = self.temp_dir_path

        with open(path, 'w') as f:
            f.write('1')

        execution = self._execute_workflow(
            'examples.mistral-test-rerun-subflow-with-items',
            {'tempfile': path}
        )

        execution = self._wait_for_completion(execution)
        self._assert_failure(execution)
        orig_st2_ex_id = execution.id
        orig_wf_ex_id = execution.context['mistral']['execution_id']

        with open(path, 'w') as f:
            f.write('0')

        execution = self.st2client.liveactions.re_run(
            orig_st2_ex_id,
            tasks=['task1.task1'],
            no_reset=['task1.task1']
        )

        self.assertNotEqual(execution.id, orig_st2_ex_id)

        execution = self._wait_for_completion(execution)
        self._assert_success(execution, num_tasks=1)
        self.assertEqual(execution.context['mistral']['execution_id'], orig_wf_ex_id)

        children = self.st2client.liveactions.get_property(execution.id, 'children')
        self.assertEqual(len(children), 2)

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
        os.chmod(self.temp_dir_path, 0755)   # nosec

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

    def test_complex_workbook_with_yaql(self):
        execution = self._execute_workflow(
            'examples.mistral-workbook-complex', {'vm_name': 'demo1'})
        execution = self._wait_for_completion(execution)
        self._assert_success(execution, num_tasks=8)
        self.assertIn('vm_id', execution.result)

    def test_complex_workbook_with_jinja(self):
        execution = self._execute_workflow(
            'examples.mistral-jinja-workbook-complex', {'vm_name': 'demo2'})
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

        execution = self._wait_for_completion(
            execution,
            expect_tasks=False,
            expect_tasks_completed=False
        )

        self._assert_canceled(execution, are_tasks_completed=False)

    def test_cancellation_cascade_subworkflow_action(self):
        execution = self._execute_workflow(
            'examples.mistral-test-cancel-subworkflow-action',
            {'sleep': 30}
        )

        execution = self._wait_for_state(execution, ['running'])
        self.st2client.liveactions.delete(execution)

        execution = self._wait_for_completion(
            execution,
            expect_tasks=False,
            expect_tasks_completed=False
        )

        self.assertEqual(execution.status, 'canceled')

        task_executions = [e for e in self.st2client.liveactions.get_all()
                           if e.context.get('parent', {}).get('execution_id') == execution.id]

        subworkflow_execution = self.st2client.liveactions.get_by_id(task_executions[0].id)

        subworkflow_execution = self._wait_for_completion(
            subworkflow_execution,
            expect_tasks=False,
            expect_tasks_completed=False
        )

        self.assertEqual(execution.status, 'canceled')

    def test_task_cancellation(self):
        execution = self._execute_workflow('examples.mistral-test-cancel', {'sleep': 30})
        execution = self._wait_for_state(execution, ['running'])

        task_executions = [e for e in self.st2client.liveactions.get_all()
                           if e.context.get('parent', {}).get('execution_id') == execution.id]

        self.assertGreater(len(task_executions), 0)

        self.st2client.liveactions.delete(task_executions[0])
        execution = self._wait_for_completion(execution, expect_tasks_completed=True)
        self._assert_canceled(execution, are_tasks_completed=True)

        task_results = execution.result.get('tasks', [])
        self.assertGreater(len(task_results), 0)
        self.assertEqual(task_results[0]['state'], 'CANCELLED')

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

    def test_invoke_from_action_chain(self):
        execution = self._execute_workflow('examples.invoke-mistral-with-jinja', {'cmd': 'date'})
        execution = self._wait_for_state(execution, ['succeeded'])

    def test_pause_resume(self):
        # A temp file is created during test setup. Ensure the temp file exists.
        path = self.temp_dir_path
        self.assertTrue(os.path.exists(path))

        # Launch the workflow. The workflow will wait for the temp file to be deleted.
        params = {'tempfile': path, 'message': 'foobar'}
        execution = self._execute_workflow('examples.mistral-test-pause-resume', params)
        execution = self._wait_for_task(execution, 'task1', 'RUNNING')

        # Pause the workflow before the temp file is created. The workflow will be paused
        # but task1 will still be running to allow for graceful exit.
        execution = self.st2client.liveactions.pause(execution.id)

        # Expecting the execution to be pausing, waiting for task1 to be completed.
        execution = self._wait_for_state(execution, ['pausing'])

        # Delete the temporary file.
        os.remove(path)
        self.assertFalse(os.path.exists(path))

        # Wait for the execution to be paused.
        execution = self._wait_for_state(execution, ['paused'])

        # Resume the execution.
        execution = self.st2client.liveactions.resume(execution.id)

        # Wait for completion.
        execution = self._wait_for_completion(execution)
        self._assert_success(execution, num_tasks=2)

    def test_resume_auto_pause(self):
        # Launch the workflow. The workflow will pause automatically after the first task.
        params = {'message': 'foobar'}
        execution = self._execute_workflow('examples.mistral-test-pause-before-task', params)
        execution = self._wait_for_task(execution, 'task1', 'SUCCESS')
        execution = self._wait_for_state(execution, ['paused'])

        # Resume the execution.
        execution = self.st2client.liveactions.resume(execution.id)

        # Wait for completion.
        execution = self._wait_for_completion(execution)
        self._assert_success(execution, num_tasks=2)

    def test_resume_auto_pause_cascade_subworkflow_action(self):
        # Launch the workflow. The workflow will pause automatically after the first task.
        workflow = 'examples.mistral-test-pause-before-task-subworkflow-action'
        params = {'message': 'foobar'}
        execution = self._execute_workflow(workflow, params)
        execution = self._wait_for_task(execution, 'task1', 'PAUSED')
        execution = self._wait_for_state(execution, ['paused'])

        # Resume the execution.
        execution = self.st2client.liveactions.resume(execution.id)

        # Wait for completion.
        execution = self._wait_for_completion(execution)
        self._assert_success(execution, num_tasks=2)

    def test_resume_auto_pause_cascade_workbook_subworkflow(self):
        # Launch the workflow. The workflow will pause automatically after the first task.
        workflow = 'examples.mistral-test-pause-before-task-subworkflow-workbook'
        params = {'message': 'foobar'}
        execution = self._execute_workflow(workflow, params)
        execution = self._wait_for_task(execution, 'task1', 'PAUSED')
        execution = self._wait_for_state(execution, ['paused'])

        # Resume the execution.
        execution = self.st2client.liveactions.resume(execution.id)

        # Wait for completion.
        execution = self._wait_for_completion(execution)
        self._assert_success(execution, num_tasks=2)

    def test_pause_resume_cascade_subworkflow_action(self):
        # A temp file is created during test setup. Ensure the temp file exists.
        path = self.temp_dir_path
        self.assertTrue(os.path.exists(path))

        # Launch the workflow. The workflow will wait for the temp file to be deleted.
        params = {'tempfile': path, 'message': 'foobar'}
        action_ref = 'examples.mistral-test-pause-resume-subworkflow-action'
        execution = self._execute_workflow(action_ref, params)
        execution = self._wait_for_task(execution, 'task1', 'RUNNING')

        # Pause the workflow before the temp file is created. The workflow will be paused
        # but task1 will still be running to allow for graceful exit.
        execution = self.st2client.liveactions.pause(execution.id)

        # Expecting the execution to be pausing, waiting for task1 to be completed.
        execution = self._wait_for_state(execution, ['pausing'])

        # Get the subworkflow execution.
        task_executions = [e for e in self.st2client.liveactions.get_all()
                           if e.context.get('parent', {}).get('execution_id') == execution.id]

        subworkflow_execution = self.st2client.liveactions.get_by_id(task_executions[0].id)
        subworkflow_execution = self._wait_for_state(subworkflow_execution, ['pausing'])

        # Delete the temporary file.
        os.remove(path)
        self.assertFalse(os.path.exists(path))

        # Wait for the executions to be paused.
        subworkflow_execution = self._wait_for_state(subworkflow_execution, ['paused'])
        execution = self._wait_for_state(execution, ['paused'])

        # Resume the parent execution.
        execution = self.st2client.liveactions.resume(execution.id)

        # Wait for completion.
        subworkflow_execution = self._wait_for_completion(subworkflow_execution)
        self._assert_success(subworkflow_execution, num_tasks=2)

        execution = self._wait_for_completion(execution)
        self._assert_success(execution, num_tasks=2)

    def test_pause_resume_cascade_workbook_subworkflow(self):
        # A temp file is created during test setup. Ensure the temp file exists.
        path = self.temp_dir_path
        self.assertTrue(os.path.exists(path))

        # Launch the workflow. The workflow will wait for the temp file to be deleted.
        params = {'tempfile': path, 'message': 'foobar'}
        action_ref = 'examples.mistral-test-pause-resume-subworkflow-workbook'
        execution = self._execute_workflow(action_ref, params)
        execution = self._wait_for_task(execution, 'task1', 'RUNNING')

        # Pause the main workflow before the temp file is created.
        # The subworkflow will also pause.
        execution = self.st2client.liveactions.pause(execution.id)

        # Expecting the execution to be pausing, waiting for task1 to be completed.
        execution = self._wait_for_state(execution, ['pausing'])
        execution = self._wait_for_task(execution, 'task1', 'PAUSED')

        # Get the task execution (since subworkflow is in a workbook, st2 has no visibility).
        task_executions = [e for e in self.st2client.liveactions.get_all()
                           if e.context.get('parent', {}).get('execution_id') == execution.id]

        task1_execution = self.st2client.liveactions.get_by_id(task_executions[0].id)
        task1_execution = self._wait_for_state(task1_execution, ['running'])

        # Delete the temporary file.
        os.remove(path)
        self.assertFalse(os.path.exists(path))

        # Wait for the main workflow to be paused.
        task1_execution = self._wait_for_state(task1_execution, ['succeeded'])
        execution = self._wait_for_state(execution, ['paused'])

        # Resume the parent execution.
        execution = self.st2client.liveactions.resume(execution.id)

        # Wait for completion.
        execution = self._wait_for_completion(execution)
        self._assert_success(execution, num_tasks=2)

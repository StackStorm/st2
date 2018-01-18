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
import os
import shutil
import tempfile

from integration.mistral import base


class PauseResumeWiringTest(base.TestWorkflowExecution):

    temp_dir_path = None

    def setUp(self):
        super(PauseResumeWiringTest, self).setUp()

        # Create temporary directory used by the tests
        _, self.temp_dir_path = tempfile.mkstemp()
        os.chmod(self.temp_dir_path, 0o755)   # nosec

    def tearDown(self):
        if self.temp_dir_path and os.path.exists(self.temp_dir_path):
            if os.path.isdir(self.temp_dir_path):
                shutil.rmtree(self.temp_dir_path)
            else:
                os.remove(self.temp_dir_path)

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

    def test_pause_resume_cascade_to_subchain(self):
        # A temp file is created during test setup. Ensure the temp file exists.
        path = self.temp_dir_path
        self.assertTrue(os.path.exists(path))

        # Launch the workflow. The workflow will wait for the temp file to be deleted.
        params = {'tempfile': path, 'message': 'foobar'}
        action_ref = 'examples.mistral-test-pause-resume-subworkflow-chain'
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

    def test_pause_resume_cascade_subworkflow_from_chain(self):
        # A temp file is created during test setup. Ensure the temp file exists.
        path = self.temp_dir_path
        self.assertTrue(os.path.exists(path))

        # Launch the workflow. The workflow will wait for the temp file to be deleted.
        params = {'tempfile': path, 'message': 'foobar'}
        action_ref = 'examples.chain-test-pause-resume-with-subworkflow'
        execution = self._execute_workflow(action_ref, params)

        # Expecting the execution to be running.
        execution = self._wait_for_state(execution, ['running'])

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

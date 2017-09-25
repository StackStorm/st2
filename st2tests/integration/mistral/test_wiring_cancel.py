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

from integration.mistral import base


class CancellationWiringTest(base.TestWorkflowExecution):

    temp_dir_path = None

    def setUp(self):
        super(CancellationWiringTest, self).setUp()

        # Create temporary directory used by the tests
        _, self.temp_dir_path = tempfile.mkstemp()
        os.chmod(self.temp_dir_path, 0755)   # nosec

    def tearDown(self):
        if self.temp_dir_path and os.path.exists(self.temp_dir_path):
            if os.path.isdir(self.temp_dir_path):
                shutil.rmtree(self.temp_dir_path)
            else:
                os.remove(self.temp_dir_path)

    def test_cancellation(self):
        # A temp file is created during test setup. Ensure the temp file exists.
        path = self.temp_dir_path
        self.assertTrue(os.path.exists(path))

        # Launch the workflow. The workflow will wait for the temp file to be deleted.
        params = {'tempfile': path, 'message': 'foobar'}
        execution = self._execute_workflow('examples.mistral-test-cancel', params)
        execution = self._wait_for_task(execution, 'task1', 'RUNNING')

        # Cancel the workflow before the temp file is created. The workflow will be paused
        # but task1 will still be running to allow for graceful exit.
        self.st2client.liveactions.delete(execution)

        # Expecting the execution to be canceling, waiting for task1 to be completed.
        execution = self._wait_for_state(execution, ['canceling'])

        # Delete the temporary file.
        os.remove(path)
        self.assertFalse(os.path.exists(path))

        # Wait for the execution to be canceled.
        execution = self._wait_for_state(execution, ['canceled'])

        # Task is completed successfully for graceful exit.
        self.assertEqual(len(execution.result.get('tasks', [])), 1)
        self.assertEqual(execution.result['tasks'][0]['state'], 'SUCCESS')

    def test_task_cancellation(self):
        # A temp file is created during test setup. Ensure the temp file exists.
        path = self.temp_dir_path
        self.assertTrue(os.path.exists(path))

        # Launch the workflow. The workflow will wait for the temp file to be deleted.
        params = {'tempfile': path, 'message': 'foobar'}
        execution = self._execute_workflow('examples.mistral-test-cancel', params)
        execution = self._wait_for_task(execution, 'task1', 'RUNNING')

        # Identify and cancel the task execution.
        task_executions = [e for e in self.st2client.liveactions.get_all()
                           if e.context.get('parent', {}).get('execution_id') == execution.id]

        self.assertGreater(len(task_executions), 0)

        self.st2client.liveactions.delete(task_executions[0])

        # Wait for the execution and task to be canceled.
        execution = self._wait_for_state(execution, ['canceled'])
        self.assertEqual(len(execution.result.get('tasks', [])), 1)
        self.assertEqual(execution.result['tasks'][0]['state'], 'CANCELLED')

    def test_cancellation_cascade_to_subworkflow_action(self):
        # A temp file is created during test setup. Ensure the temp file exists.
        path = self.temp_dir_path
        self.assertTrue(os.path.exists(path))

        # Launch the workflow. The workflow will wait for the temp file to be deleted.
        params = {'tempfile': path, 'message': 'foobar'}
        action_ref = 'examples.mistral-test-cancel-subworkflow-action'
        execution = self._execute_workflow(action_ref, params)
        execution = self._wait_for_task(execution, 'task1', 'RUNNING')

        # Cancel the workflow before the temp file is created. The workflow will be canceled
        # but task1 will still be running to allow for graceful exit.
        self.st2client.liveactions.delete(execution)

        # Expecting the execution to be canceling, waiting for task1 to be completed.
        execution = self._wait_for_state(execution, ['canceling'])

        # Get the subworkflow execution.
        task_executions = [e for e in self.st2client.liveactions.get_all()
                           if e.context.get('parent', {}).get('execution_id') == execution.id]

        subworkflow_execution = self.st2client.liveactions.get_by_id(task_executions[0].id)
        subworkflow_execution = self._wait_for_state(subworkflow_execution, ['canceling'])

        # Delete the temporary file.
        os.remove(path)
        self.assertFalse(os.path.exists(path))

        # Wait for the executions to be canceled.
        subworkflow_execution = self._wait_for_state(subworkflow_execution, ['canceled'])
        execution = self._wait_for_state(execution, ['canceled'])

        # Task is canceled in the execution result.
        self.assertEqual(len(execution.result.get('tasks', [])), 1)
        self.assertEqual(execution.result['tasks'][0]['state'], 'CANCELLED')

    def test_cancellation_cascade_to_subchain(self):
        # A temp file is created during test setup. Ensure the temp file exists.
        path = self.temp_dir_path
        self.assertTrue(os.path.exists(path))

        # Launch the workflow. The workflow will wait for the temp file to be deleted.
        params = {'tempfile': path, 'message': 'foobar'}
        action_ref = 'examples.mistral-test-cancel-subworkflow-chain'
        execution = self._execute_workflow(action_ref, params)
        execution = self._wait_for_task(execution, 'task1', 'RUNNING')

        # Cancel the workflow before the temp file is created. The workflow will be canceled
        # but task1 will still be running to allow for graceful exit.
        self.st2client.liveactions.delete(execution)

        # Expecting the execution to be canceling, waiting for task1 to be completed.
        execution = self._wait_for_state(execution, ['canceling'])

        # Get the subworkflow execution.
        task_executions = [e for e in self.st2client.liveactions.get_all()
                           if e.context.get('parent', {}).get('execution_id') == execution.id]

        subworkflow_execution = self.st2client.liveactions.get_by_id(task_executions[0].id)
        subworkflow_execution = self._wait_for_state(subworkflow_execution, ['canceling'])

        # Delete the temporary file.
        os.remove(path)
        self.assertFalse(os.path.exists(path))

        # Wait for the executions to be canceled.
        subworkflow_execution = self._wait_for_state(subworkflow_execution, ['canceled'])
        execution = self._wait_for_state(execution, ['canceled'])

        # Task is canceled in the execution result.
        self.assertEqual(len(execution.result.get('tasks', [])), 1)
        self.assertEqual(execution.result['tasks'][0]['state'], 'CANCELLED')

    def test_cancellation_cascade_from_subworkflow_action(self):
        # A temp file is created during test setup. Ensure the temp file exists.
        path = self.temp_dir_path
        self.assertTrue(os.path.exists(path))

        # Launch the workflow. The workflow will wait for the temp file to be deleted.
        params = {'tempfile': path, 'message': 'foobar'}
        action_ref = 'examples.mistral-test-cancel-subworkflow-action'
        execution = self._execute_workflow(action_ref, params)
        execution = self._wait_for_task(execution, 'task1', 'RUNNING')

        # Identify and cancel the task execution.
        task_executions = [e for e in self.st2client.liveactions.get_all()
                           if e.context.get('parent', {}).get('execution_id') == execution.id]

        self.assertGreater(len(task_executions), 0)

        self.st2client.liveactions.delete(task_executions[0])
        subworkflow_execution = self.st2client.liveactions.get_by_id(task_executions[0].id)

        # Expecting task1 and main workflow execution to be canceling.
        subworkflow_execution = self._wait_for_state(subworkflow_execution, ['canceling'])
        execution = self._wait_for_state(execution, ['canceling'])

        # Delete the temporary file.
        os.remove(path)
        self.assertFalse(os.path.exists(path))

        # Wait for the executions to be canceled.
        subworkflow_execution = self._wait_for_state(subworkflow_execution, ['canceled'])
        execution = self._wait_for_state(execution, ['canceled'])

        # Task is canceled in the execution result.
        self.assertEqual(len(execution.result.get('tasks', [])), 1)
        self.assertEqual(execution.result['tasks'][0]['state'], 'CANCELLED')

    def test_cancellation_cascade_from_subchain(self):
        # A temp file is created during test setup. Ensure the temp file exists.
        path = self.temp_dir_path
        self.assertTrue(os.path.exists(path))

        # Launch the workflow. The workflow will wait for the temp file to be deleted.
        params = {'tempfile': path, 'message': 'foobar'}
        action_ref = 'examples.mistral-test-cancel-subworkflow-chain'
        execution = self._execute_workflow(action_ref, params)
        execution = self._wait_for_task(execution, 'task1', 'RUNNING')

        # Identify and cancel the task execution.
        task_executions = [e for e in self.st2client.liveactions.get_all()
                           if e.context.get('parent', {}).get('execution_id') == execution.id]

        self.assertGreater(len(task_executions), 0)

        self.st2client.liveactions.delete(task_executions[0])
        subworkflow_execution = self.st2client.liveactions.get_by_id(task_executions[0].id)

        # Expecting task1 to be canceling. Main workflow execution is still running.
        subworkflow_execution = self._wait_for_state(subworkflow_execution, ['canceling'])
        execution = self._wait_for_state(execution, ['running'])

        # Delete the temporary file.
        os.remove(path)
        self.assertFalse(os.path.exists(path))

        # Wait for the executions to be canceled.
        subworkflow_execution = self._wait_for_state(subworkflow_execution, ['canceled'])
        execution = self._wait_for_state(execution, ['canceled'])

        # Task is canceled in the execution result.
        self.assertEqual(len(execution.result.get('tasks', [])), 1)
        self.assertEqual(execution.result['tasks'][0]['state'], 'CANCELLED')

    def test_cancellation_chain_cascade_to_subworkflow(self):
        # A temp file is created during test setup. Ensure the temp file exists.
        path = self.temp_dir_path
        self.assertTrue(os.path.exists(path))

        # Launch the workflow. The workflow will wait for the temp file to be deleted.
        params = {'tempfile': path, 'message': 'foobar'}
        action_ref = 'examples.chain-test-cancel-with-subworkflow'
        execution = self._execute_workflow(action_ref, params)

        # Expecting the execution to be running.
        execution = self._wait_for_state(execution, ['running'])

        # Cancel the workflow before the temp file is created. The workflow will be canceled
        # but task1 will still be running to allow for graceful exit.
        self.st2client.liveactions.delete(execution)

        # Expecting the execution to be cancelinging, waiting for task1 to be completed.
        execution = self._wait_for_state(execution, ['canceling'])

        # Get the subworkflow execution.
        task_executions = [e for e in self.st2client.liveactions.get_all()
                           if e.context.get('parent', {}).get('execution_id') == execution.id]

        subworkflow_execution = self.st2client.liveactions.get_by_id(task_executions[0].id)
        subworkflow_execution = self._wait_for_state(subworkflow_execution, ['canceling'])

        # Delete the temporary file.
        os.remove(path)
        self.assertFalse(os.path.exists(path))

        # Wait for the executions to be paused.
        subworkflow_execution = self._wait_for_state(subworkflow_execution, ['canceled'])
        execution = self._wait_for_state(execution, ['canceled'])

    def test_cancellation_chain_cascade_from_subworkflow(self):
        # A temp file is created during test setup. Ensure the temp file exists.
        path = self.temp_dir_path
        self.assertTrue(os.path.exists(path))

        # Launch the workflow. The workflow will wait for the temp file to be deleted.
        params = {'tempfile': path, 'message': 'foobar'}
        action_ref = 'examples.chain-test-cancel-with-subworkflow'
        execution = self._execute_workflow(action_ref, params)

        # Expecting the execution to be running.
        execution = self._wait_for_state(execution, ['running'])

        # Identify and cancel the task execution.
        task_executions = [e for e in self.st2client.liveactions.get_all()
                           if e.context.get('parent', {}).get('execution_id') == execution.id]

        self.assertGreater(len(task_executions), 0)

        self.st2client.liveactions.delete(task_executions[0])
        subworkflow_execution = self.st2client.liveactions.get_by_id(task_executions[0].id)

        # Expecting task1 and main workflow execution to be canceling.
        subworkflow_execution = self._wait_for_state(subworkflow_execution, ['canceling'])
        execution = self._wait_for_state(execution, ['running'])

        # Delete the temporary file.
        os.remove(path)
        self.assertFalse(os.path.exists(path))

        # Wait for the executions to be paused.
        subworkflow_execution = self._wait_for_state(subworkflow_execution, ['canceled'])
        execution = self._wait_for_state(execution, ['canceled'])

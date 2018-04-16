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

from st2common.constants import action as action_constants


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
        ex = self._execute_workflow('examples.mistral-test-pause-resume', params)
        ex = self._wait_for_state(ex, action_constants.LIVEACTION_STATUS_RUNNING)
        self._wait_for_task(ex, 'task1', action_constants.LIVEACTION_STATUS_RUNNING)

        # Pause the workflow before the temp file is created. The workflow will be paused
        # but task1 will still be running to allow for graceful exit.
        ex = self.st2client.liveactions.pause(ex.id)

        # Expecting the ex to be pausing, waiting for task1 to be completed.
        ex = self._wait_for_state(ex, action_constants.LIVEACTION_STATUS_PAUSING)

        # Delete the temporary file.
        os.remove(path)
        self.assertFalse(os.path.exists(path))

        # Wait for the ex to be paused.
        ex = self._wait_for_state(ex, action_constants.LIVEACTION_STATUS_PAUSED)

        # Resume the ex.
        ex = self.st2client.liveactions.resume(ex.id)

        # Wait for completion.
        ex = self._wait_for_state(ex, action_constants.LIVEACTION_STATUS_SUCCEEDED)
        self.assertEqual(len(ex.result.get('tasks', [])), 2)

    def test_resume_auto_pause(self):
        # Launch the workflow. The workflow will pause automatically after the first task.
        params = {'message': 'foobar'}
        ex = self._execute_workflow('examples.mistral-test-pause-before-task', params)
        self._wait_for_task(ex, 'task1', action_constants.LIVEACTION_STATUS_SUCCEEDED)
        ex = self._wait_for_state(ex, action_constants.LIVEACTION_STATUS_PAUSED)

        # Resume the ex.
        ex = self.st2client.liveactions.resume(ex.id)

        # Wait for completion.
        ex = self._wait_for_state(ex, action_constants.LIVEACTION_STATUS_SUCCEEDED)
        self.assertEqual(len(ex.result.get('tasks', [])), 2)

    def test_resume_auto_pause_cascade_subworkflow_action(self):
        # Launch the workflow. The workflow will pause automatically after the first task.
        workflow = 'examples.mistral-test-pause-before-task-subworkflow-action'
        params = {'message': 'foobar'}
        ex = self._execute_workflow(workflow, params)
        self._wait_for_task(ex, 'task1', action_constants.LIVEACTION_STATUS_PAUSED)
        ex = self._wait_for_state(ex, action_constants.LIVEACTION_STATUS_PAUSED)

        # Resume the ex.
        ex = self.st2client.liveactions.resume(ex.id)

        # Wait for completion.
        ex = self._wait_for_state(ex, action_constants.LIVEACTION_STATUS_SUCCEEDED)
        self.assertEqual(len(ex.result.get('tasks', [])), 2)

    def test_resume_auto_pause_cascade_workbook_subworkflow(self):
        # Launch the workflow. The workflow will pause automatically after the first task.
        workflow = 'examples.mistral-test-pause-before-task-subworkflow-workbook'
        params = {'message': 'foobar'}
        ex = self._execute_workflow(workflow, params)
        ex = self._wait_for_state(ex, action_constants.LIVEACTION_STATUS_PAUSED)

        # Ensure only task1 is executed and task2 is not present.
        self._wait_for_task(ex, 'task1', action_constants.LIVEACTION_STATUS_SUCCEEDED)
        task_exs = self._get_children(ex)
        self.assertEqual(len(task_exs), 1)

        # Resume the ex.
        ex = self.st2client.liveactions.resume(ex.id)

        # Wait for completion.
        ex = self._wait_for_state(ex, action_constants.LIVEACTION_STATUS_SUCCEEDED)
        self.assertEqual(len(ex.result.get('tasks', [])), 2)
        task_exs = self._get_children(ex)
        self.assertEqual(len(task_exs), 3)

    def test_pause_resume_cascade_subworkflow_action(self):
        # A temp file is created during test setup. Ensure the temp file exists.
        path = self.temp_dir_path
        self.assertTrue(os.path.exists(path))

        # Launch the workflow. The workflow will wait for the temp file to be deleted.
        params = {'tempfile': path, 'message': 'foobar'}
        action_ref = 'examples.mistral-test-pause-resume-subworkflow-action'
        ex = self._execute_workflow(action_ref, params)
        ex = self._wait_for_state(ex, action_constants.LIVEACTION_STATUS_RUNNING)
        task_exs = self._wait_for_task(ex, 'task1', action_constants.LIVEACTION_STATUS_RUNNING)

        # Pause the workflow before the temp file is created. The workflow will be paused
        # but task1 will still be running to allow for graceful exit.
        ex = self.st2client.liveactions.pause(ex.id)

        # Expecting the ex to be pausing, waiting for task1 to be completed.
        ex = self._wait_for_state(ex, action_constants.LIVEACTION_STATUS_PAUSING)
        subwf_ex = self._wait_for_state(task_exs[0], action_constants.LIVEACTION_STATUS_PAUSING)

        # Delete the temporary file.
        os.remove(path)
        self.assertFalse(os.path.exists(path))

        # Wait for the exs to be paused.
        subwf_ex = self._wait_for_state(subwf_ex, action_constants.LIVEACTION_STATUS_PAUSED)
        ex = self._wait_for_state(ex, action_constants.LIVEACTION_STATUS_PAUSED)

        # Resume the parent ex.
        ex = self.st2client.liveactions.resume(ex.id)

        # Wait for completion.
        subwf_ex = self._wait_for_state(subwf_ex, action_constants.LIVEACTION_STATUS_SUCCEEDED)
        ex = self._wait_for_state(ex, action_constants.LIVEACTION_STATUS_SUCCEEDED)
        self.assertEqual(len(ex.result.get('tasks', [])), 2)

    def test_pause_resume_cascade_workbook_subworkflow(self):
        # A temp file is created during test setup. Ensure the temp file exists.
        path = self.temp_dir_path
        self.assertTrue(os.path.exists(path))

        # Launch the workflow. The workflow will wait for the temp file to be deleted.
        params = {'tempfile': path, 'message': 'foobar'}
        action_ref = 'examples.mistral-test-pause-resume-subworkflow-workbook'
        ex = self._execute_workflow(action_ref, params)
        ex = self._wait_for_state(ex, action_constants.LIVEACTION_STATUS_RUNNING)

        # Get the task execution for the workbook subworkflow.
        task_exs = self._get_children(ex)
        self.assertEqual(len(task_exs), 1)
        self._wait_for_state(task_exs[0], action_constants.LIVEACTION_STATUS_RUNNING)

        # Pause the main workflow before the temp file is created.
        # The subworkflow will also pause.
        ex = self.st2client.liveactions.pause(ex.id)

        # Expecting the ex to be pausing, waiting for task1 to be completed.
        ex = self._wait_for_state(ex, action_constants.LIVEACTION_STATUS_PAUSING)

        # Delete the temporary file.
        os.remove(path)
        self.assertFalse(os.path.exists(path))

        # Wait for the main workflow to be paused.
        self._wait_for_state(task_exs[0], action_constants.LIVEACTION_STATUS_SUCCEEDED)
        ex = self._wait_for_state(ex, action_constants.LIVEACTION_STATUS_PAUSED)

        # Resume the parent ex.
        ex = self.st2client.liveactions.resume(ex.id)

        # Wait for completion.
        ex = self._wait_for_state(ex, action_constants.LIVEACTION_STATUS_SUCCEEDED)
        self.assertEqual(len(ex.result.get('tasks', [])), 2)

    def test_pause_resume_cascade_to_subchain(self):
        # A temp file is created during test setup. Ensure the temp file exists.
        path = self.temp_dir_path
        self.assertTrue(os.path.exists(path))

        # Launch the workflow. The workflow will wait for the temp file to be deleted.
        params = {'tempfile': path, 'message': 'foobar'}
        action_ref = 'examples.mistral-test-pause-resume-subworkflow-chain'
        ex = self._execute_workflow(action_ref, params)
        ex = self._wait_for_state(ex, action_constants.LIVEACTION_STATUS_RUNNING)
        task_exs = self._wait_for_task(ex, 'task1', action_constants.LIVEACTION_STATUS_RUNNING)

        # Pause the workflow before the temp file is created. The workflow will be paused
        # but task1 will still be running to allow for graceful exit.
        ex = self.st2client.liveactions.pause(ex.id)

        # Expecting the ex to be pausing, waiting for task1 to be completed.
        ex = self._wait_for_state(ex, action_constants.LIVEACTION_STATUS_PAUSING)
        subwf_ex = self._wait_for_state(task_exs[0], action_constants.LIVEACTION_STATUS_PAUSING)

        # Delete the temporary file.
        os.remove(path)
        self.assertFalse(os.path.exists(path))

        # Wait for the exs to be paused.
        subwf_ex = self._wait_for_state(subwf_ex, action_constants.LIVEACTION_STATUS_PAUSED)
        ex = self._wait_for_state(ex, action_constants.LIVEACTION_STATUS_PAUSED)

        # Resume the parent ex.
        ex = self.st2client.liveactions.resume(ex.id)

        # Wait for completion.
        subwf_ex = self._wait_for_state(subwf_ex, action_constants.LIVEACTION_STATUS_SUCCEEDED)
        ex = self._wait_for_state(ex, action_constants.LIVEACTION_STATUS_SUCCEEDED)
        self.assertEqual(len(ex.result.get('tasks', [])), 2)

    def test_pause_resume_cascade_subworkflow_from_chain(self):
        # A temp file is created during test setup. Ensure the temp file exists.
        path = self.temp_dir_path
        self.assertTrue(os.path.exists(path))

        # Launch the workflow. The workflow will wait for the temp file to be deleted.
        params = {'tempfile': path, 'message': 'foobar'}
        action_ref = 'examples.chain-test-pause-resume-with-subworkflow'
        ex = self._execute_workflow(action_ref, params)
        ex = self._wait_for_state(ex, action_constants.LIVEACTION_STATUS_RUNNING)

        # Get the execution for the subworkflow in the action chain.
        task_exs = self._get_children(ex)
        self.assertEqual(len(task_exs), 1)
        subwf_ex = self._wait_for_state(task_exs[0], action_constants.LIVEACTION_STATUS_RUNNING)

        # Pause the workflow before the temp file is created. The workflow will be paused
        # but task1 will still be running to allow for graceful exit.
        ex = self.st2client.liveactions.pause(ex.id)

        # Expecting the ex to be pausing, waiting for task1 to be completed.
        subwf_ex = self._wait_for_state(subwf_ex, action_constants.LIVEACTION_STATUS_PAUSING)
        ex = self._wait_for_state(ex, action_constants.LIVEACTION_STATUS_PAUSING)

        # Delete the temporary file.
        os.remove(path)
        self.assertFalse(os.path.exists(path))

        # Wait for the exs to be paused.
        subwf_ex = self._wait_for_state(subwf_ex, action_constants.LIVEACTION_STATUS_PAUSED)
        ex = self._wait_for_state(ex, action_constants.LIVEACTION_STATUS_PAUSED)

        # Resume the parent ex.
        ex = self.st2client.liveactions.resume(ex.id)

        # Wait for completion.
        subwf_ex = self._wait_for_state(subwf_ex, action_constants.LIVEACTION_STATUS_SUCCEEDED)
        ex = self._wait_for_state(ex, action_constants.LIVEACTION_STATUS_SUCCEEDED)
        self.assertEqual(len(ex.result.get('tasks', [])), 2)

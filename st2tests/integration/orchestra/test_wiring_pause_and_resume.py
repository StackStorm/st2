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

from integration.orchestra import base

from st2common.constants import action as ac_const


class PauseResumeWiringTest(base.TestWorkflowExecution, base.WorkflowControlTestCaseMixin):

    temp_file_path_x = None
    temp_file_path_y = None

    def setUp(self):
        super(PauseResumeWiringTest, self).setUp()

        # Create temporary files used by the tests
        self.temp_file_path_x = self._create_temp_file()
        self.temp_file_path_y = self._create_temp_file()

    def tearDown(self):
        # Delete temporary files.
        self._delete_temp_file(self.temp_file_path_x)
        self._delete_temp_file(self.temp_file_path_y)

        super(PauseResumeWiringTest, self).tearDown()

    def test_pause_and_resume(self):
        # A temp file is created during test setup. Ensure the temp file exists.
        path = self.temp_file_path_x
        self.assertTrue(os.path.exists(path))

        # Launch the workflow. The workflow will wait for the temp file to be deleted.
        params = {'tempfile': path}
        ex = self._execute_workflow('examples.orchestra-test-pause', params)
        self._wait_for_task(ex, 'task1', ac_const.LIVEACTION_STATUS_RUNNING)

        # Cancel the workflow before the temp file is deleted. The workflow will be paused
        # but task1 will still be running to allow for graceful exit.
        self.st2client.liveactions.pause(ex.id)

        # Expecting the ex to be canceling, waiting for task1 to be completed.
        ex = self._wait_for_state(ex, ac_const.LIVEACTION_STATUS_PAUSING)

        # Delete the temporary file.
        os.remove(path)
        self.assertFalse(os.path.exists(path))

        # Wait for the ex to be canceled.
        ex = self._wait_for_state(ex, ac_const.LIVEACTION_STATUS_PAUSED)

        # Resume the ex.
        ex = self.st2client.liveactions.resume(ex.id)

        # Wait for completion.
        ex = self._wait_for_state(ex, ac_const.LIVEACTION_STATUS_SUCCEEDED)

    def test_pause_and_resume_cascade_to_subworkflow(self):
        # A temp file is created during test setup. Ensure the temp file exists.
        path = self.temp_file_path_x
        self.assertTrue(os.path.exists(path))

        # Launch the workflow. The workflow will wait for the temp file to be deleted.
        params = {'tempfile': path}
        ex = self._execute_workflow('examples.orchestra-test-pause-subworkflow', params)
        ex = self._wait_for_state(ex, ac_const.LIVEACTION_STATUS_RUNNING)
        tk_exs = self._wait_for_task(ex, 'task1', ac_const.LIVEACTION_STATUS_RUNNING)

        # Pause the workflow before the temp file is deleted. The workflow will be paused
        # but task1 will still be running to allow for graceful exit.
        ex = self.st2client.liveactions.pause(ex.id)

        # Expecting the ex to be pausing, waiting for task1 to be completed.
        ex = self._wait_for_state(ex, ac_const.LIVEACTION_STATUS_PAUSING)
        tk_ac_ex = self._wait_for_state(tk_exs[0], ac_const.LIVEACTION_STATUS_PAUSING)

        # Delete the temporary file.
        os.remove(path)
        self.assertFalse(os.path.exists(path))

        # Wait for the exs to be paused.
        tk_ac_ex = self._wait_for_state(tk_ac_ex, ac_const.LIVEACTION_STATUS_PAUSED)
        ex = self._wait_for_state(ex, ac_const.LIVEACTION_STATUS_PAUSED)

        # Resume the parent ex.
        ex = self.st2client.liveactions.resume(ex.id)

        # Wait for completion.
        tk_ac_ex = self._wait_for_state(tk_ac_ex, ac_const.LIVEACTION_STATUS_SUCCEEDED)
        ex = self._wait_for_state(ex, ac_const.LIVEACTION_STATUS_SUCCEEDED)

    def test_pause_and_resume_cascade_to_subworkflows(self):
        # Temp files are created during test setup. Ensure the temp files exist.
        path1 = self.temp_file_path_x
        self.assertTrue(os.path.exists(path1))
        path2 = self.temp_file_path_y
        self.assertTrue(os.path.exists(path2))

        # Launch the workflow. The workflow will wait for the temp file to be deleted.
        params = {'file1': path1, 'file2': path2}
        ex = self._execute_workflow('examples.orchestra-test-pause-subworkflows', params)
        ex = self._wait_for_state(ex, ac_const.LIVEACTION_STATUS_RUNNING)
        tk1_exs = self._wait_for_task(ex, 'task1', ac_const.LIVEACTION_STATUS_RUNNING)
        tk2_exs = self._wait_for_task(ex, 'task2', ac_const.LIVEACTION_STATUS_RUNNING)

        # Pause the workflow before the temp files are deleted. The workflow will be paused
        # but task1 will still be running to allow for graceful exit.
        ex = self.st2client.liveactions.pause(ex.id)

        # Expecting the ex to be pausing, waiting for task1 to be completed.
        ex = self._wait_for_state(ex, ac_const.LIVEACTION_STATUS_PAUSING)
        tk1_ac_ex = self._wait_for_state(tk1_exs[0], ac_const.LIVEACTION_STATUS_PAUSING)
        tk2_ac_ex = self._wait_for_state(tk2_exs[0], ac_const.LIVEACTION_STATUS_PAUSING)

        # Delete the temporary file for one of the subworkflow.
        os.remove(path1)
        self.assertFalse(os.path.exists(path1))

        # Check the workflow and subworkflow status.
        tk1_ac_ex = self._wait_for_state(tk1_ac_ex, ac_const.LIVEACTION_STATUS_PAUSED)
        tk1_ac_ex = self._wait_for_state(tk2_ac_ex, ac_const.LIVEACTION_STATUS_PAUSING)
        ex = self._wait_for_state(ex, ac_const.LIVEACTION_STATUS_PAUSING)

        # Delete the temporary file for the other subworkflow.
        os.remove(path2)
        self.assertFalse(os.path.exists(path2))

        # Check the workflow and subworkflow status.
        tk1_ac_ex = self._wait_for_state(tk1_ac_ex, ac_const.LIVEACTION_STATUS_PAUSED)
        tk1_ac_ex = self._wait_for_state(tk2_ac_ex, ac_const.LIVEACTION_STATUS_PAUSED)
        ex = self._wait_for_state(ex, ac_const.LIVEACTION_STATUS_PAUSED)

        # Resume the parent ex.
        ex = self.st2client.liveactions.resume(ex.id)

        # Wait for completion.
        tk1_ac_ex = self._wait_for_state(tk1_ac_ex, ac_const.LIVEACTION_STATUS_SUCCEEDED)
        tk2_ac_ex = self._wait_for_state(tk2_ac_ex, ac_const.LIVEACTION_STATUS_SUCCEEDED)
        ex = self._wait_for_state(ex, ac_const.LIVEACTION_STATUS_SUCCEEDED)

    def test_pause_and_resume_cascade_from_subworkflow(self):
        # A temp file is created during test setup. Ensure the temp file exists.
        path = self.temp_file_path_x
        self.assertTrue(os.path.exists(path))

        # Launch the workflow. The workflow will wait for the temp file to be deleted.
        params = {'tempfile': path}
        ex = self._execute_workflow('examples.orchestra-test-pause-subworkflow', params)
        ex = self._wait_for_state(ex, ac_const.LIVEACTION_STATUS_RUNNING)
        tk_exs = self._wait_for_task(ex, 'task1', ac_const.LIVEACTION_STATUS_RUNNING)

        # Pause the subworkflow before the temp file is deleted. The task will be
        # paused but workflow will still be running.
        tk_ac_ex = self.st2client.liveactions.pause(tk_exs[0].id)

        # Expecting the workflow is still running and task1 is pausing.
        ex = self._wait_for_state(ex, ac_const.LIVEACTION_STATUS_RUNNING)
        tk_ac_ex = self._wait_for_state(tk_ac_ex, ac_const.LIVEACTION_STATUS_PAUSING)

        # Delete the temporary file.
        os.remove(path)
        self.assertFalse(os.path.exists(path))

        # Wait for the workflow and task to be paused.
        tk_ac_ex = self._wait_for_state(tk_ac_ex, ac_const.LIVEACTION_STATUS_PAUSED)
        ex = self._wait_for_state(ex, ac_const.LIVEACTION_STATUS_PAUSED)

        # Resume the task.
        tk_ac_ex = self.st2client.liveactions.resume(tk_ac_ex.id)

        # Wait for completion.
        tk_ac_ex = self._wait_for_state(tk_ac_ex, ac_const.LIVEACTION_STATUS_SUCCEEDED)
        ex = self._wait_for_state(ex, ac_const.LIVEACTION_STATUS_SUCCEEDED)

    def test_pause_from_1_of_2_subworkflows_and_resume_subworkflow_when_workflow_paused(self):
        # Temp files are created during test setup. Ensure the temp files exist.
        path1 = self.temp_file_path_x
        self.assertTrue(os.path.exists(path1))
        path2 = self.temp_file_path_y
        self.assertTrue(os.path.exists(path2))

        # Launch the workflow. The workflow will wait for the temp file to be deleted.
        params = {'file1': path1, 'file2': path2}
        ex = self._execute_workflow('examples.orchestra-test-pause-subworkflows', params)
        ex = self._wait_for_state(ex, ac_const.LIVEACTION_STATUS_RUNNING)
        tk1_exs = self._wait_for_task(ex, 'task1', ac_const.LIVEACTION_STATUS_RUNNING)
        tk2_exs = self._wait_for_task(ex, 'task2', ac_const.LIVEACTION_STATUS_RUNNING)

        # Pause the subworkflow before the temp file is deleted. The task will be
        # paused but workflow and the other subworkflow will still be running.
        tk1_ac_ex = self.st2client.liveactions.pause(tk1_exs[0].id)

        # Expecting the workflow is still running and task1 is pausing.
        ex = self._wait_for_state(ex, ac_const.LIVEACTION_STATUS_RUNNING)
        tk1_ac_ex = self._wait_for_state(tk1_ac_ex, ac_const.LIVEACTION_STATUS_PAUSING)
        tk2_ac_ex = self._wait_for_state(tk2_exs[0], ac_const.LIVEACTION_STATUS_RUNNING)

        # Delete the temporary file for the subworkflow.
        os.remove(path1)
        self.assertFalse(os.path.exists(path1))

        # Wait for the subworkflow to pause while the workflow
        # and the other subworkflow will still be running.
        ex = self._wait_for_state(ex, ac_const.LIVEACTION_STATUS_RUNNING)
        tk1_ac_ex = self._wait_for_state(tk1_ac_ex, ac_const.LIVEACTION_STATUS_PAUSED)
        tk2_ac_ex = self._wait_for_state(tk2_ac_ex, ac_const.LIVEACTION_STATUS_RUNNING)

        # Delete the temporary file for the other subworkflow.
        os.remove(path2)
        self.assertFalse(os.path.exists(path2))

        # The workflow will now be paused because no other task is running.
        ex = self._wait_for_state(ex, ac_const.LIVEACTION_STATUS_PAUSED)
        tk1_ac_ex = self._wait_for_state(tk1_ac_ex, ac_const.LIVEACTION_STATUS_PAUSED)
        tk2_ac_ex = self._wait_for_state(tk2_ac_ex, ac_const.LIVEACTION_STATUS_SUCCEEDED)

        # Resume the subworkflow.
        tk1_ac_ex = self.st2client.liveactions.resume(tk1_ac_ex.id)

        # Wait for completion.
        tk1_ac_ex = self._wait_for_state(tk1_ac_ex, ac_const.LIVEACTION_STATUS_SUCCEEDED)
        tk2_ac_ex = self._wait_for_state(tk2_ac_ex, ac_const.LIVEACTION_STATUS_SUCCEEDED)
        ex = self._wait_for_state(ex, ac_const.LIVEACTION_STATUS_SUCCEEDED)

    def test_pause_from_1_of_2_subworkflows_and_resume_subworkflow_while_workflow_running(self):
        # Temp files are created during test setup. Ensure the temp files exist.
        path1 = self.temp_file_path_x
        self.assertTrue(os.path.exists(path1))
        path2 = self.temp_file_path_y
        self.assertTrue(os.path.exists(path2))

        # Launch the workflow. The workflow will wait for the temp file to be deleted.
        params = {'file1': path1, 'file2': path2}
        ex = self._execute_workflow('examples.orchestra-test-pause-subworkflows', params)
        ex = self._wait_for_state(ex, ac_const.LIVEACTION_STATUS_RUNNING)
        tk1_exs = self._wait_for_task(ex, 'task1', ac_const.LIVEACTION_STATUS_RUNNING)
        tk2_exs = self._wait_for_task(ex, 'task2', ac_const.LIVEACTION_STATUS_RUNNING)

        # Pause the subworkflow before the temp file is deleted. The task will be
        # paused but workflow and the other subworkflow will still be running.
        tk1_ac_ex = self.st2client.liveactions.pause(tk1_exs[0].id)

        # Expecting the workflow is still running and task1 is pausing.
        ex = self._wait_for_state(ex, ac_const.LIVEACTION_STATUS_RUNNING)
        tk1_ac_ex = self._wait_for_state(tk1_ac_ex, ac_const.LIVEACTION_STATUS_PAUSING)
        tk2_ac_ex = self._wait_for_state(tk2_exs[0], ac_const.LIVEACTION_STATUS_RUNNING)

        # Delete the temporary file for the subworkflow.
        os.remove(path1)
        self.assertFalse(os.path.exists(path1))

        # Wait for the subworkflow to pause while the workflow
        # and the other subworkflow will still be running.
        ex = self._wait_for_state(ex, ac_const.LIVEACTION_STATUS_RUNNING)
        tk1_ac_ex = self._wait_for_state(tk1_ac_ex, ac_const.LIVEACTION_STATUS_PAUSED)
        tk2_ac_ex = self._wait_for_state(tk2_ac_ex, ac_const.LIVEACTION_STATUS_RUNNING)

        # Resume the subworkflow.
        tk1_ac_ex = self.st2client.liveactions.resume(tk1_ac_ex.id)

        # The subworkflow will succeed while the other subworkflow is still running.
        ex = self._wait_for_state(ex, ac_const.LIVEACTION_STATUS_RUNNING)
        tk1_ac_ex = self._wait_for_state(tk1_ac_ex, ac_const.LIVEACTION_STATUS_SUCCEEDED)
        tk2_ac_ex = self._wait_for_state(tk2_ac_ex, ac_const.LIVEACTION_STATUS_RUNNING)

        # Delete the temporary file for the other subworkflow.
        os.remove(path2)
        self.assertFalse(os.path.exists(path2))

        # Wait for completion.
        tk1_ac_ex = self._wait_for_state(tk1_ac_ex, ac_const.LIVEACTION_STATUS_SUCCEEDED)
        tk2_ac_ex = self._wait_for_state(tk2_ac_ex, ac_const.LIVEACTION_STATUS_SUCCEEDED)
        ex = self._wait_for_state(ex, ac_const.LIVEACTION_STATUS_SUCCEEDED)

    def test_pause_from_all_subworkflows_and_resume_from_subworkflows(self):
        # Temp files are created during test setup. Ensure the temp files exist.
        path1 = self.temp_file_path_x
        self.assertTrue(os.path.exists(path1))
        path2 = self.temp_file_path_y
        self.assertTrue(os.path.exists(path2))

        # Launch the workflow. The workflow will wait for the temp file to be deleted.
        params = {'file1': path1, 'file2': path2}
        ex = self._execute_workflow('examples.orchestra-test-pause-subworkflows', params)
        ex = self._wait_for_state(ex, ac_const.LIVEACTION_STATUS_RUNNING)
        tk1_exs = self._wait_for_task(ex, 'task1', ac_const.LIVEACTION_STATUS_RUNNING)
        tk2_exs = self._wait_for_task(ex, 'task2', ac_const.LIVEACTION_STATUS_RUNNING)

        # Pause the subworkflow before the temp file is deleted. The task will be
        # paused but workflow and the other subworkflow will still be running.
        tk1_ac_ex = self.st2client.liveactions.pause(tk1_exs[0].id)

        # Expecting the workflow is still running and task1 is pausing.
        ex = self._wait_for_state(ex, ac_const.LIVEACTION_STATUS_RUNNING)
        tk1_ac_ex = self._wait_for_state(tk1_ac_ex, ac_const.LIVEACTION_STATUS_PAUSING)
        tk2_ac_ex = self._wait_for_state(tk2_exs[0], ac_const.LIVEACTION_STATUS_RUNNING)

        # Pause the other subworkflow before the temp file is deleted. The main
        # workflow will still running because pause is initiated downstream.
        tk2_ac_ex = self.st2client.liveactions.pause(tk2_exs[0].id)

        # Expecting workflow and subworkflows are pausing.
        ex = self._wait_for_state(ex, ac_const.LIVEACTION_STATUS_RUNNING)
        tk1_ac_ex = self._wait_for_state(tk1_ac_ex, ac_const.LIVEACTION_STATUS_PAUSING)
        tk2_ac_ex = self._wait_for_state(tk2_exs[0], ac_const.LIVEACTION_STATUS_PAUSING)

        # Delete the temporary files for the subworkflows.
        os.remove(path1)
        self.assertFalse(os.path.exists(path1))
        os.remove(path2)
        self.assertFalse(os.path.exists(path2))

        # Wait for subworkflows to pause. The main workflow will also
        # pause now because no other task is running.
        tk1_ac_ex = self._wait_for_state(tk1_ac_ex, ac_const.LIVEACTION_STATUS_PAUSED)
        tk2_ac_ex = self._wait_for_state(tk2_ac_ex, ac_const.LIVEACTION_STATUS_PAUSED)
        ex = self._wait_for_state(ex, ac_const.LIVEACTION_STATUS_PAUSED)

        # Resume the subworkflow.
        tk1_ac_ex = self.st2client.liveactions.resume(tk1_ac_ex.id)

        # The subworkflow will succeed while the other subworkflow is still running.
        tk1_ac_ex = self._wait_for_state(tk1_ac_ex, ac_const.LIVEACTION_STATUS_SUCCEEDED)
        tk2_ac_ex = self._wait_for_state(tk2_ac_ex, ac_const.LIVEACTION_STATUS_PAUSED)
        ex = self._wait_for_state(ex, ac_const.LIVEACTION_STATUS_PAUSED)

        # Resume the other subworkflow.
        tk2_ac_ex = self.st2client.liveactions.resume(tk2_ac_ex.id)

        # Wait for completion.
        tk1_ac_ex = self._wait_for_state(tk1_ac_ex, ac_const.LIVEACTION_STATUS_SUCCEEDED)
        tk2_ac_ex = self._wait_for_state(tk2_ac_ex, ac_const.LIVEACTION_STATUS_SUCCEEDED)
        ex = self._wait_for_state(ex, ac_const.LIVEACTION_STATUS_SUCCEEDED)

    def test_pause_from_all_subworkflows_and_resume_from_parent_workflow(self):
        # Temp files are created during test setup. Ensure the temp files exist.
        path1 = self.temp_file_path_x
        self.assertTrue(os.path.exists(path1))
        path2 = self.temp_file_path_y
        self.assertTrue(os.path.exists(path2))

        # Launch the workflow. The workflow will wait for the temp file to be deleted.
        params = {'file1': path1, 'file2': path2}
        ex = self._execute_workflow('examples.orchestra-test-pause-subworkflows', params)
        ex = self._wait_for_state(ex, ac_const.LIVEACTION_STATUS_RUNNING)
        tk1_exs = self._wait_for_task(ex, 'task1', ac_const.LIVEACTION_STATUS_RUNNING)
        tk2_exs = self._wait_for_task(ex, 'task2', ac_const.LIVEACTION_STATUS_RUNNING)

        # Pause the subworkflow before the temp file is deleted. The task will be
        # paused but workflow and the other subworkflow will still be running.
        tk1_ac_ex = self.st2client.liveactions.pause(tk1_exs[0].id)

        # Expecting the workflow is still running and task1 is pausing.
        ex = self._wait_for_state(ex, ac_const.LIVEACTION_STATUS_RUNNING)
        tk1_ac_ex = self._wait_for_state(tk1_ac_ex, ac_const.LIVEACTION_STATUS_PAUSING)
        tk2_ac_ex = self._wait_for_state(tk2_exs[0], ac_const.LIVEACTION_STATUS_RUNNING)

        # Pause the other subworkflow before the temp file is deleted. The main
        # workflow will still running because pause is initiated downstream.
        tk2_ac_ex = self.st2client.liveactions.pause(tk2_exs[0].id)

        # Expecting workflow and subworkflows are pausing.
        ex = self._wait_for_state(ex, ac_const.LIVEACTION_STATUS_RUNNING)
        tk1_ac_ex = self._wait_for_state(tk1_ac_ex, ac_const.LIVEACTION_STATUS_PAUSING)
        tk2_ac_ex = self._wait_for_state(tk2_exs[0], ac_const.LIVEACTION_STATUS_PAUSING)

        # Delete the temporary files for the subworkflows.
        os.remove(path1)
        self.assertFalse(os.path.exists(path1))
        os.remove(path2)
        self.assertFalse(os.path.exists(path2))

        # Wait for subworkflows to pause. The main workflow will also
        # pause now because no other task is running.
        tk1_ac_ex = self._wait_for_state(tk1_ac_ex, ac_const.LIVEACTION_STATUS_PAUSED)
        tk2_ac_ex = self._wait_for_state(tk2_ac_ex, ac_const.LIVEACTION_STATUS_PAUSED)
        ex = self._wait_for_state(ex, ac_const.LIVEACTION_STATUS_PAUSED)

        # Resume the parent workflow.
        ex = self.st2client.liveactions.resume(ex.id)

        # Wait for completion.
        tk1_ac_ex = self._wait_for_state(tk1_ac_ex, ac_const.LIVEACTION_STATUS_SUCCEEDED)
        tk2_ac_ex = self._wait_for_state(tk2_ac_ex, ac_const.LIVEACTION_STATUS_SUCCEEDED)
        ex = self._wait_for_state(ex, ac_const.LIVEACTION_STATUS_SUCCEEDED)

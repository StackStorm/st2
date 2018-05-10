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

from integration.orchestra import base

from st2common.constants import action as ac_const


class CancellationWiringTest(base.TestWorkflowExecution):

    temp_file_path = None

    def setUp(self):
        super(CancellationWiringTest, self).setUp()

        # Create temporary directory used by the tests
        _, self.temp_file_path = tempfile.mkstemp()
        os.chmod(self.temp_file_path, 0o755)   # nosec

    def tearDown(self):
        if self.temp_file_path and os.path.exists(self.temp_file_path):
            if os.path.isdir(self.temp_file_path):
                shutil.rmtree(self.temp_file_path)
            else:
                os.remove(self.temp_file_path)

    def test_cancellation(self):
        # A temp file is created during test setup. Ensure the temp file exists.
        path = self.temp_file_path
        self.assertTrue(os.path.exists(path))

        # Launch the workflow. The workflow will wait for the temp file to be deleted.
        params = {'tempfile': path, 'message': 'foobar'}
        ex = self._execute_workflow('examples.orchestra-test-cancel', params)
        self._wait_for_task(ex, 'task1', ac_const.LIVEACTION_STATUS_RUNNING)

        # Cancel the workflow before the temp file is created. The workflow will be paused
        # but task1 will still be running to allow for graceful exit.
        self.st2client.liveactions.delete(ex)

        # Expecting the ex to be canceling, waiting for task1 to be completed.
        ex = self._wait_for_state(ex, ac_const.LIVEACTION_STATUS_CANCELING)

        # Delete the temporary file.
        os.remove(path)
        self.assertFalse(os.path.exists(path))

        # Wait for the ex to be canceled.
        ex = self._wait_for_state(ex, ac_const.LIVEACTION_STATUS_CANCELED)

        # Task is completed successfully for graceful exit.
        self._wait_for_task(ex, 'task1', ac_const.LIVEACTION_STATUS_SUCCEEDED)

        # Get the updated execution with task result.
        ex = self._wait_for_state(ex, ac_const.LIVEACTION_STATUS_CANCELED)

    def test_task_cancellation(self):
        # A temp file is created during test setup. Ensure the temp file exists.
        path = self.temp_file_path
        self.assertTrue(os.path.exists(path))

        # Launch the workflow. The workflow will wait for the temp file to be deleted.
        params = {'tempfile': path, 'message': 'foobar'}
        ex = self._execute_workflow('examples.orchestra-test-cancel', params)
        task_exs = self._wait_for_task(ex, 'task1', ac_const.LIVEACTION_STATUS_RUNNING)

        # Cancel the task execution.
        self.st2client.liveactions.delete(task_exs[0])

        # Wait for the task and parent workflow to be canceled.
        self._wait_for_task(ex, 'task1', ac_const.LIVEACTION_STATUS_CANCELED)

        # Get the updated execution with task result.
        ex = self._wait_for_state(ex, ac_const.LIVEACTION_STATUS_CANCELED)

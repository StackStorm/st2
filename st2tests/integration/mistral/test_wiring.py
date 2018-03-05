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

import eventlet

from integration.mistral import base
from six.moves import range

from st2common.constants import action as action_constants


class WiringTest(base.TestWorkflowExecution):

    temp_dir_path = None

    def setUp(self):
        super(WiringTest, self).setUp()

        # Create temporary directory used by the tests
        _, self.temp_dir_path = tempfile.mkstemp()
        os.chmod(self.temp_dir_path, 0o755)   # nosec

    def tearDown(self):
        if self.temp_dir_path and os.path.exists(self.temp_dir_path):
            if os.path.isdir(self.temp_dir_path):
                shutil.rmtree(self.temp_dir_path)
            else:
                os.remove(self.temp_dir_path)

    def test_basic_workflow(self):
        ex = self._execute_workflow('examples.mistral-basic', {'cmd': 'date'})
        ex = self._wait_for_completion(ex)
        self.assertEqual(ex.status, action_constants.LIVEACTION_STATUS_SUCCEEDED)
        self.assertIn('stdout', ex.result)
        self.assertEqual(len(ex.result.get('tasks', [])), 1)

    def test_basic_workbook(self):
        ex = self._execute_workflow('examples.mistral-workbook-basic', {'cmd': 'date'})
        ex = self._wait_for_completion(ex)
        self.assertEqual(ex.status, action_constants.LIVEACTION_STATUS_SUCCEEDED)
        self.assertIn('stdout', ex.result)
        self.assertEqual(len(ex.result.get('tasks', [])), 1)

    def test_complex_workbook_with_yaql(self):
        params = {'vm_name': 'demo1'}
        ex = self._execute_workflow('examples.mistral-workbook-complex', params)
        ex = self._wait_for_completion(ex)
        self.assertEqual(ex.status, action_constants.LIVEACTION_STATUS_SUCCEEDED)
        self.assertIn('vm_id', ex.result)
        self.assertEqual(len(ex.result.get('tasks', [])), 8)

    def test_complex_workbook_with_jinja(self):
        params = {'vm_name': 'demo2'}
        ex = self._execute_workflow('examples.mistral-jinja-workbook-complex', params)
        ex = self._wait_for_completion(ex)
        self.assertEqual(ex.status, action_constants.LIVEACTION_STATUS_SUCCEEDED)
        self.assertIn('vm_id', ex.result)
        self.assertEqual(len(ex.result.get('tasks', [])), 8)

    def test_complex_workbook_subflow_actions(self):
        params = {'subject': 'st2', 'adjective': 'cool'}
        ex = self._execute_workflow('examples.mistral-workbook-subflows', params)
        ex = self._wait_for_completion(ex)
        self.assertEqual(ex.status, action_constants.LIVEACTION_STATUS_SUCCEEDED)
        self.assertIn('tagline', ex.result)
        self.assertEqual(ex.result['tagline'], 'st2 is cool!')
        self.assertEqual(len(ex.result.get('tasks', [])), 2)

    def test_with_items(self):
        params = {'cmd': 'date', 'count': 8}
        ex = self._execute_workflow('examples.mistral-repeat', params)
        ex = self._wait_for_completion(ex)
        self.assertEqual(ex.status, action_constants.LIVEACTION_STATUS_SUCCEEDED)
        self.assertEqual(len(ex.result['result']), params['count'])
        self.assertEqual(len(ex.result.get('tasks', [])), 1)

    def test_concurrent_load(self):
        wf_name = 'examples.mistral-workbook-complex'
        wf_params = {'vm_name': 'demo1'}
        exs = [self._execute_workflow(wf_name, wf_params) for i in range(3)]

        eventlet.sleep(20)

        for ex in exs:
            e = self._wait_for_completion(ex)
            self.assertEqual(e.status, action_constants.LIVEACTION_STATUS_SUCCEEDED)
            self.assertIn('vm_id', e.result)
            self.assertEqual(len(e.result.get('tasks', [])), 8)

    def test_execution_failure(self):
        ex = self._execute_workflow('examples.mistral-basic', {'cmd': 'foo'})
        ex = self._wait_for_completion(ex)
        self.assertEqual(ex.status, action_constants.LIVEACTION_STATUS_FAILED)

    def test_invoke_from_action_chain(self):
        ex = self._execute_workflow('examples.invoke-mistral-with-jinja', {'cmd': 'date'})
        ex = self._wait_for_completion(ex)
        self.assertEqual(ex.status, action_constants.LIVEACTION_STATUS_SUCCEEDED)

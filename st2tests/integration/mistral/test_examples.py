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

from integration.mistral import base

from st2common.constants import action as action_constants


class ExamplesTest(base.TestWorkflowExecution):

    def test_environment(self):
        ex = self._execute_workflow('examples.mistral-env-var')
        ex = self._wait_for_completion(ex)
        self.assertEqual(ex.status, action_constants.LIVEACTION_STATUS_SUCCEEDED)
        expected_output = 'http://127.0.0.1:9101/executions/' + ex.id
        self.assertEqual(ex.result['url'], expected_output)

    def test_branching(self):
        # Execute with path a.
        params = {'which': 'a'}
        ex = self._execute_workflow('examples.mistral-branching', params)
        ex = self._wait_for_completion(ex)
        self.assertEqual(ex.status, action_constants.LIVEACTION_STATUS_SUCCEEDED)
        self.assertEqual(ex.result['stdout'], 'Took path A.')

        # Execute with path b.
        params = {'which': 'b'}
        ex = self._execute_workflow('examples.mistral-branching', params)
        ex = self._wait_for_completion(ex)
        self.assertEqual(ex.status, action_constants.LIVEACTION_STATUS_SUCCEEDED)
        self.assertEqual(ex.result['stdout'], 'Took path B.')

        # Execute with path c.
        params = {'which': 'c'}
        ex = self._execute_workflow('examples.mistral-branching', params)
        ex = self._wait_for_completion(ex)
        self.assertEqual(ex.status, action_constants.LIVEACTION_STATUS_SUCCEEDED)
        self.assertEqual(ex.result['stdout'], 'Took path C.')

    def test_join(self):
        ex = self._execute_workflow('examples.mistral-join')
        ex = self._wait_for_completion(ex)
        self.assertEqual(ex.status, action_constants.LIVEACTION_STATUS_SUCCEEDED)

    def test_handle_error(self):
        ex = self._execute_workflow('examples.mistral-handle-error')
        ex = self._wait_for_completion(ex)
        self.assertEqual(ex.status, action_constants.LIVEACTION_STATUS_FAILED)
        self.assertTrue(ex.result['error_handled'])

    def test_handle_error_task_default(self):
        ex = self._execute_workflow('examples.mistral-handle-error-task-default')
        ex = self._wait_for_completion(ex)
        self.assertEqual(ex.status, action_constants.LIVEACTION_STATUS_FAILED)
        self.assertTrue(ex.result['error_handled'])

    def test_handle_retry(self):
        ex = self._execute_workflow('examples.mistral-handle-retry')
        ex = self._wait_for_completion(ex)
        self.assertEqual(ex.status, action_constants.LIVEACTION_STATUS_SUCCEEDED)

    def test_repeat(self):
        params = {'cmd': 'echo "Yo!"', 'count': 3}
        ex = self._execute_workflow('examples.mistral-repeat', params)
        ex = self._wait_for_completion(ex)
        self.assertEqual(ex.status, action_constants.LIVEACTION_STATUS_SUCCEEDED)
        self.assertEqual(len(ex.result['result']), params['count'])
        self.assertListEqual(ex.result['result'], ['Yo!'] * params['count'])

    def test_repeat_with_items(self):
        params = {'cmds': ['echo "a"', 'echo "b"', 'echo "c"']}
        ex = self._execute_workflow('examples.mistral-repeat-with-items', params)
        ex = self._wait_for_completion(ex)
        self.assertEqual(ex.status, action_constants.LIVEACTION_STATUS_SUCCEEDED)
        self.assertEqual(len(ex.result['result']), len(params['cmds']))
        self.assertListEqual(sorted(ex.result['result']), ['a', 'b', 'c'])

    def test_with_items_batch_processing(self):
        params = {'cmd': 'date +%s', 'count': 4}
        ex = self._execute_workflow('examples.mistral-with-items-concurrency', params)
        ex = self._wait_for_completion(ex)
        self.assertEqual(ex.status, action_constants.LIVEACTION_STATUS_SUCCEEDED)
        self.assertEqual(len(ex.result['result']), params['count'])

        timestamps = [int(dt) for dt in ex.result['result']]
        self.assertTrue(timestamps[1] - timestamps[0] < 3)
        self.assertTrue(timestamps[3] - timestamps[2] < 3)
        self.assertTrue(timestamps[2] - timestamps[1] >= 3)

    def test_workbook_multiple_subflows(self):
        ex = self._execute_workflow('examples.mistral-workbook-multiple-subflows')
        ex = self._wait_for_completion(ex)
        self.assertEqual(ex.status, action_constants.LIVEACTION_STATUS_SUCCEEDED)

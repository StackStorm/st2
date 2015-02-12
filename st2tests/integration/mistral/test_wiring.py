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

import eventlet
import unittest2
import multiprocessing

from st2client import client as st2
from st2client import models


class TestWorkflowExecution(unittest2.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.st2client = st2.Client(base_url='http://localhost')

    def test_cpu_count(self):
        # Ensure tests are run on multi-processor system to catch race conditions
        self.assertGreaterEqual(multiprocessing.cpu_count(), 2)

    def _execute_workflow(self, action, parameters):
        execution = models.ActionExecution(action=action, parameters=parameters)
        execution = self.st2client.executions.create(execution)
        self.assertIsNotNone(execution.id)
        self.assertEqual(execution.action, action)
        self.assertIn(execution.status, ['scheduled', 'running'])
        return execution

    def _wait_for_completion(self, execution, wait=20):
        for i in range(wait):
            eventlet.sleep(1)
            execution = self.st2client.executions.get_by_id(execution.id)
            if execution.status in ['succeeded', 'failed']:
                break
        return execution

    def _assert_success(self, execution):
        self.assertEqual(execution.status, 'succeeded')
        tasks = execution.result['tasks']
        for task in tasks:
            self.assertIn('state', task)
            self.assertEqual(task['state'], 'SUCCESS')

    def _assert_failure(self, execution):
        self.assertEqual(execution.status, 'failed')
        tasks = execution.result['tasks']
        for task in tasks:
            self.assertIn('state', task)
            self.assertEqual(task['state'], 'ERROR')

    def test_basic_workflow(self):
        execution = self._execute_workflow('examples.mistral-basic', {'cmd': 'date'})
        execution = self._wait_for_completion(execution)
        self._assert_success(execution)
        self.assertIn('stdout', execution.result)

    def test_basic_workbook(self):
        execution = self._execute_workflow('examples.mistral-workbook-basic', {'cmd': 'date'})
        execution = self._wait_for_completion(execution)
        self._assert_success(execution)
        self.assertIn('stdout', execution.result)

    def test_complex_workbook(self):
        execution = self._execute_workflow(
            'examples.mistral-workbook-complex', {'vm_name': 'demo1'})
        execution = self._wait_for_completion(execution)
        self._assert_success(execution)
        self.assertIn('vm_id', execution.result)
        self.assertIn('vm_state', execution.result)

    def test_complex_workbook_subflow_actions(self):
        execution = self._execute_workflow(
            'examples.mistral-workbook-subflows', {'subject': 'st2', 'adjective': 'cool'})
        execution = self._wait_for_completion(execution)
        self._assert_success(execution)
        self.assertIn('tagline', execution.result)
        self.assertEqual(execution.result['tagline'], 'st2 is cool!')

    def test_execution_failure(self):
        execution = self._execute_workflow('examples.mistral-basic', {'cmd': 'foo'})
        execution = self._wait_for_completion(execution)
        self._assert_failure(execution)

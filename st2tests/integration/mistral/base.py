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

import retrying
import unittest2

from st2client import client as st2
from st2client import models


class TestWorkflowExecution(unittest2.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.st2client = st2.Client(base_url='http://127.0.0.1')

    def _execute_workflow(self, action, parameters=None):
        if parameters is None:
            parameters = {}

        execution = models.LiveAction(action=action, parameters=parameters)
        execution = self.st2client.liveactions.create(execution)
        self.assertIsNotNone(execution.id)
        self.assertEqual(execution.action['ref'], action)
        self.assertIn(execution.status, ['requested', 'scheduled', 'running'])

        return execution

    @retrying.retry(wait_fixed=3000, stop_max_delay=900000)
    def _wait_for_state(self, execution, states):
        execution = self.st2client.liveactions.get_by_id(execution.id)
        self.assertIn(execution.status, states)
        return execution

    @retrying.retry(wait_fixed=3000, stop_max_delay=900000)
    def _wait_for_completion(self, execution, expect_tasks=True, expect_tasks_completed=True):
        execution = self._wait_for_state(execution, ['succeeded', 'failed', 'canceled'])
        self.assertTrue(hasattr(execution, 'result'))

        if expect_tasks:
            self.assertIn('tasks', execution.result)
            self.assertGreater(len(execution.result['tasks']), 0)

        if expect_tasks_completed:
            tasks = execution.result['tasks']
            self.assertTrue(all([t['state'] in ['SUCCESS', 'ERROR'] for t in tasks]))

        return execution

    def _assert_success(self, execution, num_tasks=0):
        self.assertEqual(execution.status, 'succeeded')
        tasks = execution.result.get('tasks', [])
        self.assertEqual(num_tasks, len(tasks))
        self.assertTrue(all([task['state'] == 'SUCCESS' for task in tasks]))

    def _assert_failure(self, execution, expect_tasks_failure=True):
        self.assertEqual(execution.status, 'failed')
        tasks = execution.result.get('tasks', [])

        if expect_tasks_failure:
            self.assertTrue(any([task['state'] == 'ERROR' for task in tasks]))

    def _assert_canceled(self, execution, are_tasks_completed=False):
        self.assertEqual(execution.status, 'canceled')
        tasks = execution.result.get('tasks', [])

        if are_tasks_completed:
            self.assertTrue(all([t['state'] in ['SUCCESS', 'ERROR'] for t in tasks]))
        else:
            self.assertTrue(any([t['state'] == 'RUNNING' for t in tasks]))

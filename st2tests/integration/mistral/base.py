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

from st2client import client as st2
from st2client import models


class TestWorkflowExecution(unittest2.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.st2client = st2.Client(base_url='http://localhost')

    def _execute_workflow(self, action, parameters=None):
        if parameters is None:
            parameters = {}

        execution = models.LiveAction(action=action, parameters=parameters)
        execution = self.st2client.liveactions.create(execution)
        self.assertIsNotNone(execution.id)
        self.assertEqual(execution.action['ref'], action)
        self.assertIn(execution.status, ['requested', 'scheduled', 'running'])

        return execution

    def _wait_for_completion(self, execution, wait=300):
        for i in range(wait):
            eventlet.sleep(3)
            execution = self.st2client.liveactions.get_by_id(execution.id)

            if execution.status in ['succeeded', 'failed']:
                if hasattr(execution, 'result') and 'tasks' in execution.result:
                    if ([task for task in execution.result['tasks']
                         if task['state'] in ['SUCCESS', 'ERROR']]):
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

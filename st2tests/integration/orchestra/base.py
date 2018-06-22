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
import retrying
import shutil
import six
import tempfile
import unittest2

from st2client import client as st2
from st2client import models
from st2common.constants import action as action_constants


LIVEACTION_LAUNCHED_STATUSES = [
    action_constants.LIVEACTION_STATUS_REQUESTED,
    action_constants.LIVEACTION_STATUS_SCHEDULED,
    action_constants.LIVEACTION_STATUS_RUNNING
]


def retry_on_exceptions(exc):
    return isinstance(exc, AssertionError)


class WorkflowControlTestCaseMixin(object):

    def _create_temp_file(self):
        _, temp_file_path = tempfile.mkstemp()
        os.chmod(temp_file_path, 0o755)     # nosec
        return temp_file_path

    def _delete_temp_file(self, temp_file_path):
        if temp_file_path and os.path.exists(temp_file_path):
            if os.path.isdir(temp_file_path):
                shutil.rmtree(temp_file_path)
            else:
                os.remove(temp_file_path)


class TestWorkflowExecution(unittest2.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.st2client = st2.Client(base_url='http://127.0.0.1')

    def _execute_workflow(self, action, parameters=None):
        ex = models.LiveAction(action=action, parameters=(parameters or {}))
        ex = self.st2client.liveactions.create(ex)
        self.assertIsNotNone(ex.id)
        self.assertEqual(ex.action['ref'], action)
        self.assertIn(ex.status, LIVEACTION_LAUNCHED_STATUSES)

        return ex

    @retrying.retry(
        retry_on_exception=retry_on_exceptions,
        wait_fixed=3000, stop_max_delay=900000)
    def _wait_for_state(self, ex, states):
        if isinstance(states, six.string_types):
            states = [states]

        for state in states:
            if state not in action_constants.LIVEACTION_STATUSES:
                raise ValueError('Status %s is not valid.' % state)

        try:
            ex = self.st2client.liveactions.get_by_id(ex.id)
            self.assertIn(ex.status, states)
        except:
            if ex.status in action_constants.LIVEACTION_COMPLETED_STATES:
                raise Exception(
                    'Execution is in completed state and does not '
                    'match expected state(s).'
                )
            else:
                raise

        return ex

    def _get_children(self, ex):
        return self.st2client.liveactions.query(parent=ex.id)

    @retrying.retry(
        retry_on_exception=retry_on_exceptions,
        wait_fixed=3000, stop_max_delay=900000)
    def _wait_for_task(self, ex, task, status, num_task_exs=1):
        ex = self.st2client.liveactions.get_by_id(ex.id)

        task_exs = [
            task_ex for task_ex in self._get_children(ex)
            if (task_ex.context.get('orchestra', {}).get('task_name', '') == task and
                task_ex.status == status)
        ]

        try:
            self.assertEqual(len(task_exs), num_task_exs)
            self.assertTrue(all([task_ex.status == status for task_ex in task_exs]))
        except:
            if ex.status in action_constants.LIVEACTION_COMPLETED_STATES:
                raise Exception(
                    'Execution is in completed state and does not '
                    'match expected task.'
                )
            else:
                raise

        return task_exs

    @retrying.retry(
        retry_on_exception=retry_on_exceptions,
        wait_fixed=3000, stop_max_delay=900000)
    def _wait_for_completion(self, ex):
        ex = self._wait_for_state(ex, action_constants.LIVEACTION_COMPLETED_STATES)

        try:
            self.assertTrue(hasattr(ex, 'result'))
        except:
            if ex.status in action_constants.LIVEACTION_COMPLETED_STATES:
                raise Exception(
                    'Execution is in completed state and does not '
                    'contain expected result.'
                )
            else:
                raise

        return ex

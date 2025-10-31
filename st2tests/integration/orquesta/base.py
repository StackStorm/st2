# Copyright 2020 The StackStorm Authors.
# Copyright 2019 Extreme Networks, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import absolute_import

from st2common.util.monkey_patch import monkey_patch

monkey_patch()

import os
import retrying
import shutil
import six
import tempfile
import unittest

from st2client import client as st2
from st2client import models
from st2common.constants import action as action_constants


LIVEACTION_LAUNCHED_STATUSES = [
    action_constants.LIVEACTION_STATUS_REQUESTED,
    action_constants.LIVEACTION_STATUS_SCHEDULED,
    action_constants.LIVEACTION_STATUS_RUNNING,
]

DEFAULT_WAIT_FIXED = 500
DEFAULT_STOP_MAX_DELAY = 900000


def retry_on_exceptions(exc):
    return isinstance(exc, AssertionError)


class WorkflowControlTestCaseMixin(object):
    def _create_temp_file(self):
        _, temp_file_path = tempfile.mkstemp()
        os.chmod(temp_file_path, 0o755)  # nosec
        return temp_file_path

    def _delete_temp_file(self, temp_file_path):
        if temp_file_path and os.path.exists(temp_file_path):
            if os.path.isdir(temp_file_path):
                shutil.rmtree(temp_file_path)
            else:
                os.remove(temp_file_path)


class TestWorkflowExecution(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.st2client = st2.Client(base_url="http://127.0.0.1")

    def _execute_workflow(
        self,
        action,
        parameters=None,
        execute_async=True,
        expected_status=None,
        expected_result=None,
    ):

        ex = models.LiveAction(action=action, parameters=(parameters or {}))
        ex = self.st2client.executions.create(ex)
        self.assertIsNotNone(ex.id)
        self.assertEqual(ex.action["ref"], action)
        self.assertIn(ex.status, LIVEACTION_LAUNCHED_STATUSES)

        if execute_async:
            return ex

        if expected_status is None:
            expected_status = action_constants.LIVEACTION_STATUS_SUCCEEDED

        self.assertIn(expected_status, action_constants.LIVEACTION_STATUSES)

        ex = self._wait_for_completion(ex)

        self.assertEqual(ex.status, expected_status)
        self.assertDictEqual(ex.result, expected_result)

        return ex

    @retrying.retry(
        retry_on_exception=retry_on_exceptions,
        wait_fixed=DEFAULT_WAIT_FIXED,
        stop_max_delay=DEFAULT_STOP_MAX_DELAY,
    )
    def _wait_for_state(self, ex, states):
        if isinstance(states, six.string_types):
            states = [states]

        for state in states:
            if state not in action_constants.LIVEACTION_STATUSES:
                raise ValueError("Status %s is not valid." % state)

        try:
            ex = self.st2client.executions.get_by_id(ex.id)
            self.assertIn(ex.status, states)
        except:
            if ex.status in action_constants.LIVEACTION_COMPLETED_STATES:
                raise Exception(
                    'Execution is in completed state "%s" and '
                    "does not match expected state(s). %s" % (ex.status, ex.result)
                )
            else:
                raise

        return ex

    def _get_children(self, ex):
        return self.st2client.executions.query(parent=ex.id)

    @retrying.retry(
        retry_on_exception=retry_on_exceptions,
        wait_fixed=DEFAULT_WAIT_FIXED,
        stop_max_delay=DEFAULT_STOP_MAX_DELAY,
    )
    def _wait_for_task(self, ex, task, status=None, num_task_exs=1):
        ex = self.st2client.executions.get_by_id(ex.id)

        task_exs = [
            task_ex
            for task_ex in self._get_children(ex)
            if task_ex.context.get("orquesta", {}).get("task_name", "") == task
        ]

        try:
            self.assertEqual(len(task_exs), num_task_exs)
        except:
            if ex.status in action_constants.LIVEACTION_COMPLETED_STATES:
                raise Exception(
                    "Execution is in completed state and does not match expected number of "
                    "tasks. Expected: %s Actual: %s"
                    % (str(num_task_exs), str(len(task_exs)))
                )
            else:
                raise

        if status is not None:
            try:
                self.assertTrue(all([task_ex.status == status for task_ex in task_exs]))
            except:
                if ex.status in action_constants.LIVEACTION_COMPLETED_STATES:
                    raise Exception(
                        "Execution is in completed state and not all tasks "
                        'match expected status "%s".' % status
                    )
                else:
                    raise

        return task_exs

    @retrying.retry(
        retry_on_exception=retry_on_exceptions,
        wait_fixed=DEFAULT_WAIT_FIXED,
        stop_max_delay=DEFAULT_STOP_MAX_DELAY,
    )
    def _wait_for_completion(self, ex):
        ex = self._wait_for_state(ex, action_constants.LIVEACTION_COMPLETED_STATES)

        try:
            self.assertTrue(hasattr(ex, "result"))
        except:
            if ex.status in action_constants.LIVEACTION_COMPLETED_STATES:
                raise Exception(
                    "Execution is in completed state and does not "
                    "contain expected result."
                )
            else:
                raise

        return ex

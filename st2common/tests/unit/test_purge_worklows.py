# Copyright 2022 The StackStorm Authors.
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

# pytest: make sure monkey_patching happens before importing mongoengine
from st2common.util.monkey_patch import monkey_patch

monkey_patch()

from datetime import timedelta

from st2common import log as logging
from st2common.garbage_collection.workflows import purge_workflow_executions
from st2common.models.db.workflow import WorkflowExecutionDB
from st2common.persistence.workflow import WorkflowExecution
from st2common.util import date as date_utils
from st2tests.base import CleanDbTestCase

LOG = logging.getLogger(__name__)


class TestPurgeWorkflowExecutionInstances(CleanDbTestCase):
    @classmethod
    def setUpClass(cls):
        CleanDbTestCase.setUpClass()
        super(TestPurgeWorkflowExecutionInstances, cls).setUpClass()

    def setUp(self):
        super(TestPurgeWorkflowExecutionInstances, self).setUp()

    def test_no_timestamp_doesnt_delete(self):
        now = date_utils.get_datetime_utc_now()

        instance_db = WorkflowExecutionDB(
            start_timestamp=now - timedelta(days=20),
            end_timestamp=now - timedelta(days=20),
            status="running",
        )
        WorkflowExecution.add_or_update(instance_db)

        self.assertEqual(len(WorkflowExecution.get_all()), 1)
        expected_msg = "Specify a valid timestamp"
        self.assertRaisesRegex(
            ValueError,
            expected_msg,
            purge_workflow_executions,
            logger=LOG,
            timestamp=None,
        )
        self.assertEqual(len(WorkflowExecution.get_all()), 1)

    def test_purge(self):
        now = date_utils.get_datetime_utc_now()

        instance_db = WorkflowExecutionDB(
            start_timestamp=now - timedelta(days=20),
            end_timestamp=now - timedelta(days=20),
            status="failed",
        )
        WorkflowExecution.add_or_update(instance_db)

        instance_db = WorkflowExecutionDB(
            start_timestamp=now - timedelta(days=20),
            status="running",
        )
        WorkflowExecution.add_or_update(instance_db)

        instance_db = WorkflowExecutionDB(
            start_timestamp=now - timedelta(days=5),
            end_timestamp=now - timedelta(days=5),
            status="succeeded",
        )
        WorkflowExecution.add_or_update(instance_db)

        self.assertEqual(len(WorkflowExecution.get_all()), 3)
        purge_workflow_executions(logger=LOG, timestamp=now - timedelta(days=10))
        self.assertEqual(len(WorkflowExecution.get_all()), 2)

    def test_purge_incomplete(self):
        now = date_utils.get_datetime_utc_now()

        instance_db = WorkflowExecutionDB(
            start_timestamp=now - timedelta(days=20),
            end_timestamp=now - timedelta(days=20),
            status="cancelled",
        )
        WorkflowExecution.add_or_update(instance_db)

        instance_db = WorkflowExecutionDB(
            start_timestamp=now - timedelta(days=20),
            status="running",
        )
        WorkflowExecution.add_or_update(instance_db)

        instance_db = WorkflowExecutionDB(
            start_timestamp=now - timedelta(days=5),
            end_timestamp=now - timedelta(days=5),
            status="succeeded",
        )
        WorkflowExecution.add_or_update(instance_db)

        self.assertEqual(len(WorkflowExecution.get_all()), 3)
        purge_workflow_executions(
            logger=LOG, timestamp=now - timedelta(days=10), purge_incomplete=True
        )
        self.assertEqual(len(WorkflowExecution.get_all()), 1)

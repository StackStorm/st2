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
from st2common.garbage_collection.workflows import purge_task_executions
from st2common.models.db.workflow import TaskExecutionDB
from st2common.models.db.workflow import TaskItemStateDB
from st2common.persistence.workflow import TaskExecution
from st2common.persistence.workflow import TaskItemState
from st2common.util import date as date_utils
from st2tests.base import CleanDbTestCase

LOG = logging.getLogger(__name__)


class TestPurgeTaskExecutionInstances(CleanDbTestCase):
    @classmethod
    def setUpClass(cls):
        CleanDbTestCase.setUpClass()
        super(TestPurgeTaskExecutionInstances, cls).setUpClass()

    def setUp(self):
        super(TestPurgeTaskExecutionInstances, self).setUp()

    def test_no_timestamp_doesnt_delete(self):
        now = date_utils.get_datetime_utc_now()

        instance_db = TaskExecutionDB(
            start_timestamp=now - timedelta(days=20),
            end_timestamp=now - timedelta(days=20),
            status="succeeded",
        )
        TaskExecution.add_or_update(instance_db)

        self.assertEqual(len(TaskExecution.get_all()), 1)
        expected_msg = "Specify a valid timestamp"
        self.assertRaisesRegex(
            ValueError, expected_msg, purge_task_executions, logger=LOG, timestamp=None
        )
        self.assertEqual(len(TaskExecution.get_all()), 1)

    def test_purge(self):
        now = date_utils.get_datetime_utc_now()

        instance_db = TaskExecutionDB(
            start_timestamp=now - timedelta(days=20),
            end_timestamp=now - timedelta(days=20),
            status="failed",
        )
        TaskExecution.add_or_update(instance_db)

        # Addn incomplete
        instance_db = TaskExecutionDB(
            start_timestamp=now - timedelta(days=20),
            status="running",
        )
        TaskExecution.add_or_update(instance_db)

        instance_db = TaskExecutionDB(
            start_timestamp=now - timedelta(days=5),
            end_timestamp=now - timedelta(days=5),
            status="canceled",
        )
        TaskExecution.add_or_update(instance_db)

        self.assertEqual(len(TaskExecution.get_all()), 3)
        purge_task_executions(logger=LOG, timestamp=now - timedelta(days=10))
        self.assertEqual(len(TaskExecution.get_all()), 2)

    def test_purge_incomplete(self):
        now = date_utils.get_datetime_utc_now()

        instance_db = TaskExecutionDB(
            start_timestamp=now - timedelta(days=20),
            end_timestamp=now - timedelta(days=20),
            status="failed",
        )
        TaskExecution.add_or_update(instance_db)

        # Addn incomplete
        instance_db = TaskExecutionDB(
            start_timestamp=now - timedelta(days=20),
            status="running",
        )
        TaskExecution.add_or_update(instance_db)

        instance_db = TaskExecutionDB(
            start_timestamp=now - timedelta(days=5),
            end_timestamp=now - timedelta(days=5),
            status="canceled",
        )
        TaskExecution.add_or_update(instance_db)

        self.assertEqual(len(TaskExecution.get_all()), 3)
        purge_task_executions(
            logger=LOG, timestamp=now - timedelta(days=10), purge_incomplete=True
        )
        self.assertEqual(len(TaskExecution.get_all()), 1)

    def test_purge_deletes_associated_task_item_states(self):
        now = date_utils.get_datetime_utc_now()

        # Old task execution that will be purged, with two item state records.
        old_task_db = TaskExecutionDB(
            start_timestamp=now - timedelta(days=20),
            end_timestamp=now - timedelta(days=20),
            status="succeeded",
        )
        old_task_db = TaskExecution.add_or_update(old_task_db)

        for item_id in range(2):
            item_state_db = TaskItemStateDB(
                task_execution=str(old_task_db.id),
                item_id=item_id,
                status="succeeded",
            )
            TaskItemState.add_or_update(item_state_db)

        # Recent task execution that will be retained, with one item state record.
        recent_task_db = TaskExecutionDB(
            start_timestamp=now - timedelta(days=5),
            end_timestamp=now - timedelta(days=5),
            status="succeeded",
        )
        recent_task_db = TaskExecution.add_or_update(recent_task_db)

        item_state_db = TaskItemStateDB(
            task_execution=str(recent_task_db.id),
            item_id=0,
            status="succeeded",
        )
        TaskItemState.add_or_update(item_state_db)

        self.assertEqual(len(TaskExecution.get_all()), 2)
        self.assertEqual(len(TaskItemState.get_all()), 3)

        purge_task_executions(logger=LOG, timestamp=now - timedelta(days=10))

        # Only the recent task execution and its single item state record remain.
        self.assertEqual(len(TaskExecution.get_all()), 1)

        remaining_item_states = TaskItemState.get_all()
        self.assertEqual(len(remaining_item_states), 1)
        self.assertEqual(
            remaining_item_states[0].task_execution, str(recent_task_db.id)
        )

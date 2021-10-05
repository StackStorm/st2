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

import mock
import uuid

import st2tests

from st2common.exceptions import db as db_exc
from st2common.models.db import workflow as wf_db_models
from st2common.persistence import workflow as wf_db_access
from st2common.transport import publishers
from st2common.util import date as date_utils


@mock.patch.object(publishers.PoolPublisher, "publish", mock.MagicMock())
class TaskExecutionModelTest(st2tests.DbTestCase):
    def test_task_execution_crud(self):
        initial = wf_db_models.TaskExecutionDB()
        initial.workflow_execution = uuid.uuid4().hex
        initial.task_name = "t1"
        initial.task_id = "t1"
        initial.task_route = 0
        initial.task_spec = {"tasks": {"t1": "some task"}}
        initial.delay = 180
        initial.status = "requested"
        initial.context = {"var1": "foobar"}

        # Test create
        created = wf_db_access.TaskExecution.add_or_update(initial)
        self.assertEqual(initial.rev, 1)
        doc_id = created.id

        # Test read
        retrieved = wf_db_access.TaskExecution.get_by_id(doc_id)
        self.assertEqual(created.workflow_execution, retrieved.workflow_execution)
        self.assertEqual(created.task_name, retrieved.task_name)
        self.assertEqual(created.task_id, retrieved.task_id)
        self.assertEqual(created.task_route, retrieved.task_route)
        self.assertDictEqual(created.task_spec, retrieved.task_spec)
        self.assertEqual(created.delay, retrieved.delay)
        self.assertFalse(created.itemized)
        self.assertEqual(created.status, retrieved.status)
        self.assertIsNotNone(created.start_timestamp)
        self.assertIsNone(created.end_timestamp)
        self.assertDictEqual(created.context, retrieved.context)

        # Test update
        status = "running"
        retrieved = wf_db_access.TaskExecution.update(retrieved, status=status)
        updated = wf_db_access.TaskExecution.get_by_id(doc_id)
        self.assertNotEqual(created.rev, updated.rev)
        self.assertEqual(retrieved.rev, updated.rev)
        self.assertEqual(updated.workflow_execution, retrieved.workflow_execution)
        self.assertEqual(updated.task_name, retrieved.task_name)
        self.assertEqual(updated.task_id, retrieved.task_id)
        self.assertEqual(updated.task_route, retrieved.task_route)
        self.assertDictEqual(updated.task_spec, retrieved.task_spec)
        self.assertEqual(updated.delay, retrieved.delay)
        self.assertEqual(updated.itemized, retrieved.itemized)
        self.assertEqual(updated.status, retrieved.status)
        self.assertIsNotNone(updated.start_timestamp)
        self.assertIsNone(updated.end_timestamp)
        self.assertDictEqual(updated.context, retrieved.context)

        # Test add or update
        retrieved.result = {"output": "fubar"}
        retrieved.status = "succeeded"
        retrieved.end_timestamp = date_utils.get_datetime_utc_now()
        retrieved = wf_db_access.TaskExecution.add_or_update(retrieved)
        updated = wf_db_access.TaskExecution.get_by_id(doc_id)
        self.assertNotEqual(created.rev, updated.rev)
        self.assertEqual(retrieved.rev, updated.rev)
        self.assertEqual(updated.workflow_execution, retrieved.workflow_execution)
        self.assertEqual(updated.task_name, retrieved.task_name)
        self.assertEqual(updated.task_id, retrieved.task_id)
        self.assertEqual(updated.task_route, retrieved.task_route)
        self.assertDictEqual(updated.task_spec, retrieved.task_spec)
        self.assertEqual(updated.delay, retrieved.delay)
        self.assertEqual(updated.itemized, retrieved.itemized)
        self.assertEqual(updated.status, retrieved.status)
        self.assertIsNotNone(updated.start_timestamp)
        self.assertIsNotNone(updated.end_timestamp)
        self.assertDictEqual(updated.context, retrieved.context)
        self.assertDictEqual(updated.result, retrieved.result)

        # Test delete
        created.delete()

        self.assertRaises(
            db_exc.StackStormDBObjectNotFoundError,
            wf_db_access.TaskExecution.get_by_id,
            doc_id,
        )

    def test_task_execution_crud_set_itemized_true(self):
        initial = wf_db_models.TaskExecutionDB()
        initial.workflow_execution = uuid.uuid4().hex
        initial.task_name = "t1"
        initial.task_id = "t1"
        initial.task_route = 0
        initial.task_spec = {"tasks": {"t1": "some task"}}
        initial.delay = 180
        initial.itemized = True
        initial.status = "requested"
        initial.context = {"var1": "foobar"}

        # Test create
        created = wf_db_access.TaskExecution.add_or_update(initial)
        self.assertEqual(initial.rev, 1)
        doc_id = created.id

        # Test read
        retrieved = wf_db_access.TaskExecution.get_by_id(doc_id)
        self.assertEqual(created.workflow_execution, retrieved.workflow_execution)
        self.assertEqual(created.task_name, retrieved.task_name)
        self.assertEqual(created.task_id, retrieved.task_id)
        self.assertEqual(created.task_route, retrieved.task_route)
        self.assertDictEqual(created.task_spec, retrieved.task_spec)
        self.assertEqual(created.delay, retrieved.delay)
        self.assertTrue(created.itemized)
        self.assertEqual(created.status, retrieved.status)
        self.assertIsNotNone(created.start_timestamp)
        self.assertIsNone(created.end_timestamp)
        self.assertDictEqual(created.context, retrieved.context)

        # Test update
        status = "running"
        retrieved = wf_db_access.TaskExecution.update(retrieved, status=status)
        updated = wf_db_access.TaskExecution.get_by_id(doc_id)
        self.assertNotEqual(created.rev, updated.rev)
        self.assertEqual(retrieved.rev, updated.rev)
        self.assertEqual(updated.workflow_execution, retrieved.workflow_execution)
        self.assertEqual(updated.task_name, retrieved.task_name)
        self.assertEqual(updated.task_id, retrieved.task_id)
        self.assertEqual(updated.task_route, retrieved.task_route)
        self.assertDictEqual(updated.task_spec, retrieved.task_spec)
        self.assertEqual(updated.delay, retrieved.delay)
        self.assertEqual(updated.itemized, retrieved.itemized)
        self.assertEqual(updated.status, retrieved.status)
        self.assertIsNotNone(updated.start_timestamp)
        self.assertIsNone(updated.end_timestamp)
        self.assertDictEqual(updated.context, retrieved.context)

        # Test add or update
        retrieved.result = {"output": "fubar"}
        retrieved.status = "succeeded"
        retrieved.end_timestamp = date_utils.get_datetime_utc_now()
        retrieved = wf_db_access.TaskExecution.add_or_update(retrieved)
        updated = wf_db_access.TaskExecution.get_by_id(doc_id)
        self.assertNotEqual(created.rev, updated.rev)
        self.assertEqual(retrieved.rev, updated.rev)
        self.assertEqual(updated.workflow_execution, retrieved.workflow_execution)
        self.assertEqual(updated.task_name, retrieved.task_name)
        self.assertEqual(updated.task_id, retrieved.task_id)
        self.assertEqual(updated.task_route, retrieved.task_route)
        self.assertDictEqual(updated.task_spec, retrieved.task_spec)
        self.assertEqual(updated.delay, retrieved.delay)
        self.assertEqual(updated.itemized, retrieved.itemized)
        self.assertEqual(updated.status, retrieved.status)
        self.assertIsNotNone(updated.start_timestamp)
        self.assertIsNotNone(updated.end_timestamp)
        self.assertDictEqual(updated.context, retrieved.context)
        self.assertDictEqual(updated.result, retrieved.result)

        # Test delete
        created.delete()

        self.assertRaises(
            db_exc.StackStormDBObjectNotFoundError,
            wf_db_access.TaskExecution.get_by_id,
            doc_id,
        )

    def test_task_execution_write_conflict(self):
        initial = wf_db_models.TaskExecutionDB()
        initial.workflow_execution = uuid.uuid4().hex
        initial.task_name = "t1"
        initial.task_id = "t1"
        initial.task_route = 0
        initial.task_spec = {"tasks": {"t1": "some task"}}
        initial.delay = 180
        initial.status = "requested"
        initial.context = {"var1": "foobar"}

        # Prep record
        created = wf_db_access.TaskExecution.add_or_update(initial)
        self.assertEqual(initial.rev, 1)
        doc_id = created.id

        # Get two separate instances of the document.
        retrieved1 = wf_db_access.TaskExecution.get_by_id(doc_id)
        retrieved2 = wf_db_access.TaskExecution.get_by_id(doc_id)

        # Test update on instance 1, expect success
        status = "running"
        retrieved1 = wf_db_access.TaskExecution.update(retrieved1, status=status)
        updated = wf_db_access.TaskExecution.get_by_id(doc_id)
        self.assertNotEqual(created.rev, updated.rev)
        self.assertEqual(retrieved1.rev, updated.rev)
        self.assertEqual(updated.workflow_execution, retrieved1.workflow_execution)
        self.assertEqual(updated.task_name, retrieved1.task_name)
        self.assertEqual(updated.task_id, retrieved1.task_id)
        self.assertEqual(updated.task_route, retrieved1.task_route)
        self.assertDictEqual(updated.task_spec, retrieved1.task_spec)
        self.assertEqual(updated.delay, retrieved1.delay)
        self.assertEqual(updated.itemized, retrieved1.itemized)
        self.assertEqual(updated.status, retrieved1.status)
        self.assertIsNotNone(updated.start_timestamp)
        self.assertIsNone(updated.end_timestamp)
        self.assertDictEqual(updated.context, retrieved1.context)

        # Test update on instance 2, expect race error
        self.assertRaises(
            db_exc.StackStormDBObjectWriteConflictError,
            wf_db_access.TaskExecution.update,
            retrieved2,
            status="pausing",
        )

        # Test delete
        created.delete()

        self.assertRaises(
            db_exc.StackStormDBObjectNotFoundError,
            wf_db_access.TaskExecution.get_by_id,
            doc_id,
        )

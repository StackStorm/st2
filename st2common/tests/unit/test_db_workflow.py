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

import mock
import uuid

import st2tests

from st2common.models.db import workflow as wf_db_models
from st2common.persistence import workflow as wf_db_access
from st2common.transport import publishers
from st2common.exceptions import db as db_exc


@mock.patch.object(publishers.PoolPublisher, 'publish', mock.MagicMock())
class WorkflowExecutionModelTest(st2tests.DbTestCase):

    def test_workflow_execution_crud(self):
        initial = wf_db_models.WorkflowExecutionDB()
        initial.action_execution = uuid.uuid4().hex
        initial.graph = {'var1': 'foobar'}
        initial.status = 'requested'

        # Test create
        created = wf_db_access.WorkflowExecution.add_or_update(initial)
        self.assertEqual(initial.rev, 1)
        doc_id = created.id

        # Test read
        retrieved = wf_db_access.WorkflowExecution.get_by_id(doc_id)
        self.assertEqual(created.action_execution, retrieved.action_execution)
        self.assertDictEqual(created.graph, retrieved.graph)
        self.assertEqual(created.status, retrieved.status)

        # Test update
        graph = {'var1': 'fubar'}
        status = 'running'
        retrieved = wf_db_access.WorkflowExecution.update(retrieved, graph=graph, status=status)
        updated = wf_db_access.WorkflowExecution.get_by_id(doc_id)
        self.assertNotEqual(created.rev, updated.rev)
        self.assertEqual(retrieved.rev, updated.rev)
        self.assertEqual(retrieved.action_execution, updated.action_execution)
        self.assertDictEqual(retrieved.graph, updated.graph)
        self.assertEqual(retrieved.status, updated.status)

        # Test add or update
        retrieved.graph = {'var2': 'fubar'}
        retrieved = wf_db_access.WorkflowExecution.add_or_update(retrieved)
        updated = wf_db_access.WorkflowExecution.get_by_id(doc_id)
        self.assertNotEqual(created.rev, updated.rev)
        self.assertEqual(retrieved.rev, updated.rev)
        self.assertEqual(retrieved.action_execution, updated.action_execution)
        self.assertDictEqual(retrieved.graph, updated.graph)
        self.assertEqual(retrieved.status, updated.status)

        # Test delete
        created.delete()

        self.assertRaises(
            db_exc.StackStormDBObjectNotFoundError,
            wf_db_access.WorkflowExecution.get_by_id,
            doc_id
        )

    def test_workflow_execution_write_conflict(self):
        initial = wf_db_models.WorkflowExecutionDB()
        initial.action_execution = uuid.uuid4().hex
        initial.graph = {'var1': 'foobar'}
        initial.status = 'requested'

        # Prep record
        created = wf_db_access.WorkflowExecution.add_or_update(initial)
        self.assertEqual(initial.rev, 1)
        doc_id = created.id

        # Get two separate instances of the document.
        retrieved1 = wf_db_access.WorkflowExecution.get_by_id(doc_id)
        retrieved2 = wf_db_access.WorkflowExecution.get_by_id(doc_id)

        # Test update on instance 1, expect success
        graph = {'var1': 'fubar'}
        status = 'running'
        retrieved1 = wf_db_access.WorkflowExecution.update(retrieved1, graph=graph, status=status)
        updated = wf_db_access.WorkflowExecution.get_by_id(doc_id)
        self.assertNotEqual(created.rev, updated.rev)
        self.assertEqual(retrieved1.rev, updated.rev)
        self.assertEqual(retrieved1.action_execution, updated.action_execution)
        self.assertDictEqual(retrieved1.graph, updated.graph)
        self.assertEqual(retrieved1.status, updated.status)

        # Test update on instance 2, expect race error
        self.assertRaises(
            db_exc.StackStormDBObjectWriteConflictError,
            wf_db_access.WorkflowExecution.update,
            retrieved2,
            graph={'var2': 'fubar'}
        )

        # Test delete
        created.delete()

        self.assertRaises(
            db_exc.StackStormDBObjectNotFoundError,
            wf_db_access.WorkflowExecution.get_by_id,
            doc_id
        )

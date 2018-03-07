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

from st2common.models.db.workflow import WorkflowExecutionDB
from st2common.persistence.workflow import WorkflowExecution
from st2common.transport.publishers import PoolPublisher
from st2common.exceptions import db as db_exc

from st2tests import DbTestCase


@mock.patch.object(PoolPublisher, 'publish', mock.MagicMock())
class WorkflowExecutionModelTest(DbTestCase):

    def test_workflow_execution_crud(self):
        initial = WorkflowExecutionDB()
        initial.graph = {'var1': 'foobar'}

        # Test create
        created = WorkflowExecution.add_or_update(initial)
        self.assertEqual(initial.rev, 1)
        doc_id = created.id

        # Test read
        retrieved = WorkflowExecution.get_by_id(doc_id)
        self.assertDictEqual(created.graph, retrieved.graph)

        # Test update
        retrieved = WorkflowExecution.update(retrieved, graph={'var1': 'fubar'})
        updated = WorkflowExecution.get_by_id(doc_id)
        self.assertNotEqual(created.rev, updated.rev)
        self.assertEqual(retrieved.rev, updated.rev)
        self.assertDictEqual(retrieved.graph, updated.graph)

        # Test add or update
        retrieved.graph = {'var2': 'fubar'}
        retrieved = WorkflowExecution.add_or_update(retrieved)
        updated = WorkflowExecution.get_by_id(doc_id)
        self.assertNotEqual(created.rev, updated.rev)
        self.assertEqual(retrieved.rev, updated.rev)
        self.assertDictEqual(retrieved.graph, updated.graph)

        # Test delete
        created.delete()

        self.assertRaises(
            db_exc.StackStormDBObjectNotFoundError,
            WorkflowExecution.get_by_id,
            doc_id
        )

    def test_workflow_execution_write_conflict(self):
        initial = WorkflowExecutionDB()
        initial.graph = {'var1': 'foobar'}

        # Prep record
        created = WorkflowExecution.add_or_update(initial)
        self.assertEqual(initial.rev, 1)
        doc_id = created.id

        # Get two separate instances of the document.
        retrieved1 = WorkflowExecution.get_by_id(doc_id)
        retrieved2 = WorkflowExecution.get_by_id(doc_id)

        # Test update on instance 1, expect success
        retrieved1 = WorkflowExecution.update(retrieved1, graph={'var1': 'fubar'})
        updated = WorkflowExecution.get_by_id(doc_id)
        self.assertNotEqual(created.rev, updated.rev)
        self.assertEqual(retrieved1.rev, updated.rev)
        self.assertDictEqual(retrieved1.graph, updated.graph)

        # Test update on instance 2, expect race error
        self.assertRaises(
            db_exc.StackStormDBObjectWriteConflictError,
            WorkflowExecution.update,
            retrieved2,
            graph={'var2': 'fubar'}
        )

        # Test delete
        created.delete()

        self.assertRaises(
            db_exc.StackStormDBObjectNotFoundError,
            WorkflowExecution.get_by_id,
            doc_id
        )

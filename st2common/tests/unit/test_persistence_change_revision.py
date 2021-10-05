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

import uuid

from st2common.exceptions import db as db_exc
from st2tests import DbTestCase

from tests.unit.base import ChangeRevFakeModel, ChangeRevFakeModelDB


class TestChangeRevision(DbTestCase):
    @classmethod
    def setUpClass(cls):
        super(TestChangeRevision, cls).setUpClass()
        cls.access = ChangeRevFakeModel()

    def tearDown(self):
        ChangeRevFakeModelDB.drop_collection()
        super(TestChangeRevision, self).tearDown()

    def test_crud(self):
        initial = ChangeRevFakeModelDB(name=uuid.uuid4().hex, context={"a": 1})

        # Test create
        created = self.access.add_or_update(initial)
        self.assertEqual(initial.rev, 1)
        doc_id = created.id

        # Test read
        retrieved = self.access.get_by_id(doc_id)
        self.assertDictEqual(created.context, retrieved.context)

        # Test update
        retrieved = self.access.update(retrieved, context={"a": 2})
        updated = self.access.get_by_id(doc_id)
        self.assertNotEqual(created.rev, updated.rev)
        self.assertEqual(retrieved.rev, updated.rev)
        self.assertDictEqual(retrieved.context, updated.context)

        # Test add or update
        retrieved.context = {"a": 1, "b": 2}
        retrieved = self.access.add_or_update(retrieved)
        updated = self.access.get_by_id(doc_id)
        self.assertNotEqual(created.rev, updated.rev)
        self.assertEqual(retrieved.rev, updated.rev)
        self.assertDictEqual(retrieved.context, updated.context)

        # Test delete
        created.delete()

        self.assertRaises(
            db_exc.StackStormDBObjectNotFoundError, self.access.get_by_id, doc_id
        )

    def test_write_conflict(self):
        initial = ChangeRevFakeModelDB(name=uuid.uuid4().hex, context={"a": 1})

        # Prep record
        created = self.access.add_or_update(initial)
        self.assertEqual(initial.rev, 1)
        doc_id = created.id

        # Get two separate instances of the document.
        retrieved1 = self.access.get_by_id(doc_id)
        retrieved2 = self.access.get_by_id(doc_id)

        # Test update on instance 1, expect success
        retrieved1 = self.access.update(retrieved1, context={"a": 2})
        updated = self.access.get_by_id(doc_id)
        self.assertNotEqual(created.rev, updated.rev)
        self.assertEqual(retrieved1.rev, updated.rev)
        self.assertDictEqual(retrieved1.context, updated.context)

        # Test update on instance 2, expect race error
        self.assertRaises(
            db_exc.StackStormDBObjectWriteConflictError,
            self.access.update,
            retrieved2,
            context={"a": 1, "b": 2},
        )

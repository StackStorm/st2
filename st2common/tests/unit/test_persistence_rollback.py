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

"""
Tests for rollback behavior in persistence layer when RabbitMQ publishing fails.
"""

from __future__ import absolute_import
import uuid
from unittest import mock

from kombu import exceptions as kombu_exceptions

from st2tests import DbTestCase
from tests.unit.base import FakeModel, FakeModelDB


class TestPersistenceRollback(DbTestCase):
    """Test rollback behavior when publishing fails in update() method"""

    @classmethod
    def setUpClass(cls):
        super(TestPersistenceRollback, cls).setUpClass()
        cls.access = FakeModel()

    def tearDown(self):
        FakeModelDB.drop_collection()
        super(TestPersistenceRollback, self).tearDown()

    def test_update_rollback_on_kombu_error(self):
        """Test that update() rolls back DB changes when KombuError occurs"""
        # Create initial object
        obj = FakeModelDB(name=uuid.uuid4().hex, context={"value": "original"})
        obj = self.access.add_or_update(obj, publish=False)
        original_name = obj.name
        # Mock publish_update at class level to raise KombuError
        with mock.patch.object(
            FakeModel,
            "publish_update",
            side_effect=kombu_exceptions.KombuError("Connection failed"),
        ):
            # Try to update with a new name
            new_name = uuid.uuid4().hex
            obj.name = new_name

            # Update should raise the exception
            with self.assertRaises(kombu_exceptions.KombuError):
                self.access.update(obj, publish=True, set__name=new_name)

            # Verify the database was rolled back to original state
            retrieved = self.access.get_by_id(str(obj.id))
            self.assertEqual(retrieved.name, original_name)
            self.assertNotEqual(retrieved.name, new_name)

    def test_update_success_no_rollback(self):
        """Test that successful update() with publish does not trigger rollback"""
        # Create initial object
        obj = FakeModelDB(name=uuid.uuid4().hex, context={"value": "original"})
        obj = self.access.add_or_update(obj, publish=False)

        # Update with a new name and publish=True (mocked to succeed)
        new_name = uuid.uuid4().hex
        obj.name = new_name

        with mock.patch.object(FakeModel, "publish_update", return_value=None):
            result = self.access.update(obj, publish=True, set__name=new_name)

            # Verify the update succeeded
            self.assertEqual(result.name, new_name)
            retrieved = self.access.get_by_id(str(obj.id))
            self.assertEqual(retrieved.name, new_name)

    def test_update_without_publish_no_rollback_needed(self):
        """Test that update() without publish=True doesn't save original state"""
        # Create initial object
        obj = FakeModelDB(name=uuid.uuid4().hex, context={"value": "original"})
        obj = self.access.add_or_update(obj, publish=False)

        # Update with publish=False
        new_name = uuid.uuid4().hex
        obj.name = new_name
        result = self.access.update(
            obj, publish=False, dispatch_trigger=False, set__name=new_name
        )

        # Verify the update succeeded
        self.assertEqual(result.name, new_name)
        retrieved = self.access.get_by_id(str(obj.id))
        self.assertEqual(retrieved.name, new_name)

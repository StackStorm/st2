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

import time

import mongoengine

from st2common.models import db
from st2common.models.db import stormbase
from st2common.persistence.base import Access
from st2common.exceptions.db import StackStormDBObjectNotFoundError

__all__ = [
    "BaseDBModelCRUDTestCase",
    "FakeModel",
    "FakeModelDB",
    "ChangeRevFakeModel",
    "ChangeRevFakeModelDB",
]


class BaseDBModelCRUDTestCase(object):
    model_class = None
    persistance_class = None
    model_class_kwargs = {}
    update_attribute_name = None
    skip_check_attribute_names = []

    def test_crud_operations(self):
        # 1. Test create
        model_db = self.model_class(**self.model_class_kwargs)
        saved_db = self.persistance_class.add_or_update(model_db)

        retrieved_db = self.persistance_class.get_by_id(saved_db.id)
        self.assertEqual(saved_db.id, retrieved_db.id)

        for attribute_name, attribute_value in self.model_class_kwargs.items():
            if attribute_name in self.skip_check_attribute_names:
                continue

            self.assertEqual(getattr(saved_db, attribute_name), attribute_value)
            self.assertEqual(getattr(retrieved_db, attribute_name), attribute_value)

        # 2. Test update
        updated_attribute_value = "updated-%s" % (str(time.time()))
        setattr(model_db, self.update_attribute_name, updated_attribute_value)
        saved_db = self.persistance_class.add_or_update(model_db)
        self.assertEqual(
            getattr(saved_db, self.update_attribute_name), updated_attribute_value
        )

        retrieved_db = self.persistance_class.get_by_id(saved_db.id)
        self.assertEqual(saved_db.id, retrieved_db.id)
        self.assertEqual(
            getattr(retrieved_db, self.update_attribute_name), updated_attribute_value
        )

        # 3. Test delete
        self.persistance_class.delete(model_db)
        self.assertRaises(
            StackStormDBObjectNotFoundError,
            self.persistance_class.get_by_id,
            model_db.id,
        )


class FakeModelDB(stormbase.StormBaseDB):
    context = stormbase.EscapedDictField()
    index = mongoengine.IntField(min_value=0)
    category = mongoengine.StringField()
    timestamp = mongoengine.DateTimeField()

    meta = {
        "indexes": [
            {"fields": ["index"]},
            {"fields": ["category"]},
            {"fields": ["timestamp"]},
            {"fields": ["context.user"]},
        ]
    }


class FakeModel(Access):
    impl = db.MongoDBAccess(FakeModelDB)

    @classmethod
    def _get_impl(cls):
        return cls.impl

    @classmethod
    def _get_by_object(cls, object):
        return None

    @classmethod
    def _get_publisher(cls):
        return None


class ChangeRevFakeModelDB(stormbase.StormBaseDB, stormbase.ChangeRevisionFieldMixin):
    context = stormbase.EscapedDictField()


class ChangeRevFakeModel(Access):
    impl = db.ChangeRevisionMongoDBAccess(ChangeRevFakeModelDB)

    @classmethod
    def _get_impl(cls):
        return cls.impl

    @classmethod
    def _get_by_object(cls, object):
        return None

    @classmethod
    def _get_publisher(cls):
        return None

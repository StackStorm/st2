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

import uuid
import datetime

import bson

from st2tests import DbTestCase
from st2common.util import date as date_utils
from st2common.exceptions.db import StackStormDBObjectNotFoundError
from tests.unit.base import FakeModel, FakeModelDB


class TestPersistence(DbTestCase):

    @classmethod
    def setUpClass(cls):
        super(TestPersistence, cls).setUpClass()
        cls.access = FakeModel()

    def tearDown(self):
        FakeModelDB.drop_collection()
        super(TestPersistence, self).tearDown()

    def test_crud(self):
        obj1 = FakeModelDB(name=uuid.uuid4().hex, context={'a': 1})
        obj1 = self.access.add_or_update(obj1)
        obj2 = self.access.get(name=obj1.name)
        self.assertIsNotNone(obj2)
        self.assertEqual(obj1.id, obj2.id)
        self.assertEqual(obj1.name, obj2.name)
        self.assertDictEqual(obj1.context, obj2.context)

        obj1.name = uuid.uuid4().hex
        obj1 = self.access.add_or_update(obj1)
        obj2 = self.access.get(name=obj1.name)
        self.assertIsNotNone(obj2)
        self.assertEqual(obj1.id, obj2.id)
        self.assertEqual(obj1.name, obj2.name)
        self.assertDictEqual(obj1.context, obj2.context)

        self.access.delete(obj1)
        obj2 = self.access.get(name=obj1.name)
        self.assertIsNone(obj2)

    def test_count(self):
        obj1 = FakeModelDB(name=uuid.uuid4().hex, context={'user': 'system'})
        obj1 = self.access.add_or_update(obj1)
        obj2 = FakeModelDB(name=uuid.uuid4().hex, context={'user': 'stanley'})
        obj2 = self.access.add_or_update(obj2)
        self.assertEqual(self.access.count(), 2)

    def test_get_all(self):
        obj1 = FakeModelDB(name=uuid.uuid4().hex, context={'user': 'system'})
        obj1 = self.access.add_or_update(obj1)
        obj2 = FakeModelDB(name=uuid.uuid4().hex, context={'user': 'stanley'})
        obj2 = self.access.add_or_update(obj2)
        objs = self.access.get_all()
        self.assertIsNotNone(objs)
        self.assertEqual(len(objs), 2)
        self.assertListEqual(list(objs), [obj1, obj2])

    def test_query_by_id(self):
        obj1 = FakeModelDB(name=uuid.uuid4().hex, context={'user': 'system'})
        obj1 = self.access.add_or_update(obj1)
        obj2 = self.access.get_by_id(str(obj1.id))
        self.assertIsNotNone(obj2)
        self.assertEqual(obj1.id, obj2.id)
        self.assertEqual(obj1.name, obj2.name)
        self.assertDictEqual(obj1.context, obj2.context)
        self.assertRaises(StackStormDBObjectNotFoundError,
                          self.access.get_by_id, str(bson.ObjectId()))

    def test_query_by_name(self):
        obj1 = FakeModelDB(name=uuid.uuid4().hex, context={'user': 'system'})
        obj1 = self.access.add_or_update(obj1)
        obj2 = self.access.get_by_name(obj1.name)
        self.assertIsNotNone(obj2)
        self.assertEqual(obj1.id, obj2.id)
        self.assertEqual(obj1.name, obj2.name)
        self.assertDictEqual(obj1.context, obj2.context)
        self.assertRaises(StackStormDBObjectNotFoundError, self.access.get_by_name,
                          uuid.uuid4().hex)

    def test_query_filter(self):
        obj1 = FakeModelDB(name=uuid.uuid4().hex, context={'user': 'system'})
        obj1 = self.access.add_or_update(obj1)
        obj2 = FakeModelDB(name=uuid.uuid4().hex, context={'user': 'stanley'})
        obj2 = self.access.add_or_update(obj2)
        objs = self.access.query(context__user='system')
        self.assertIsNotNone(objs)
        self.assertGreater(len(objs), 0)
        self.assertEqual(obj1.id, objs[0].id)
        self.assertEqual(obj1.name, objs[0].name)
        self.assertDictEqual(obj1.context, objs[0].context)

    def test_null_filter(self):
        obj1 = FakeModelDB(name=uuid.uuid4().hex)
        obj1 = self.access.add_or_update(obj1)

        objs = self.access.query(index='null')
        self.assertEqual(len(objs), 1)
        self.assertEqual(obj1.id, objs[0].id)
        self.assertEqual(obj1.name, objs[0].name)
        self.assertIsNone(getattr(obj1, 'index', None))

        objs = self.access.query(index=None)
        self.assertEqual(len(objs), 1)
        self.assertEqual(obj1.id, objs[0].id)
        self.assertEqual(obj1.name, objs[0].name)
        self.assertIsNone(getattr(obj1, 'index', None))

    def test_datetime_range(self):
        base = date_utils.add_utc_tz(datetime.datetime(2014, 12, 25, 0, 0, 0))
        for i in range(60):
            timestamp = base + datetime.timedelta(seconds=i)
            obj = FakeModelDB(name=uuid.uuid4().hex, timestamp=timestamp)
            self.access.add_or_update(obj)

        dt_range = '2014-12-25T00:00:10Z..2014-12-25T00:00:19Z'
        objs = self.access.query(timestamp=dt_range)
        self.assertEqual(len(objs), 10)
        self.assertLess(objs[0].timestamp, objs[9].timestamp)

        dt_range = '2014-12-25T00:00:19Z..2014-12-25T00:00:10Z'
        objs = self.access.query(timestamp=dt_range)
        self.assertEqual(len(objs), 10)
        self.assertLess(objs[9].timestamp, objs[0].timestamp)

    def test_pagination(self):
        count = 100
        page_size = 25
        pages = count / page_size
        users = ['Peter', 'Susan', 'Edmund', 'Lucy']

        for user in users:
            context = {'user': user}
            for i in range(count):
                self.access.add_or_update(FakeModelDB(name=uuid.uuid4().hex,
                                                      context=context, index=i))

        self.assertEqual(self.access.count(), len(users) * count)

        for user in users:
            for i in range(pages):
                offset = i * page_size
                objs = self.access.query(context__user=user, order_by=['index'],
                                         offset=offset, limit=page_size)
                self.assertEqual(len(objs), page_size)
                for j in range(page_size):
                    self.assertEqual(objs[j].context['user'], user)
                    self.assertEqual(objs[j].index, (i * page_size) + j)

    def test_sort_multiple(self):
        count = 60
        base = date_utils.add_utc_tz(datetime.datetime(2014, 12, 25, 0, 0, 0))
        for i in range(count):
            category = 'type1' if i % 2 else 'type2'
            timestamp = base + datetime.timedelta(seconds=i)
            obj = FakeModelDB(name=uuid.uuid4().hex, timestamp=timestamp, category=category)
            self.access.add_or_update(obj)

        objs = self.access.query(order_by=['category', 'timestamp'])
        self.assertEqual(len(objs), count)
        for i in range(count):
            category = 'type1' if i < count / 2 else 'type2'
            self.assertEqual(objs[i].category, category)
        self.assertLess(objs[0].timestamp, objs[(count / 2) - 1].timestamp)
        self.assertLess(objs[count / 2].timestamp, objs[(count / 2) - 1].timestamp)
        self.assertLess(objs[count / 2].timestamp, objs[count - 1].timestamp)

    def test_escaped_field(self):
        context = {'a.b.c': 'abc'}
        obj1 = FakeModelDB(name=uuid.uuid4().hex, context=context)
        obj2 = self.access.add_or_update(obj1)

        # Check that the original dict has not been altered.
        self.assertIn('a.b.c', context.keys())
        self.assertNotIn('a\uff0eb\uff0ec', context.keys())

        # Check to_python has run and context is not left escaped.
        self.assertDictEqual(obj2.context, context)

        # Check field is not escaped when retrieving from persistence.
        obj3 = self.access.get(name=obj2.name)
        self.assertIsNotNone(obj3)
        self.assertEqual(obj3.id, obj2.id)
        self.assertDictEqual(obj3.context, context)

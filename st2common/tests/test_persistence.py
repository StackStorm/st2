import uuid
import datetime

import bson
import mongoengine

from st2tests import DbTestCase
from st2common.models import db
from st2common import persistence
from st2common.models.db import stormbase


class FakeModelDB(stormbase.StormBaseDB):
    context = stormbase.EscapedDictField()
    index = mongoengine.IntField(min_value=0)
    timestamp = mongoengine.DateTimeField()


class FakeModel(persistence.Access):
    impl = db.MongoDBAccess(FakeModelDB)

    @classmethod
    def _get_impl(cls):
        return cls.impl


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
        self.assertRaises(ValueError, self.access.get_by_id, str(bson.ObjectId()))

    def test_query_by_name(self):
        obj1 = FakeModelDB(name=uuid.uuid4().hex, context={'user': 'system'})
        obj1 = self.access.add_or_update(obj1)
        obj2 = self.access.get_by_name(obj1.name)
        self.assertIsNotNone(obj2)
        self.assertEqual(obj1.id, obj2.id)
        self.assertEqual(obj1.name, obj2.name)
        self.assertDictEqual(obj1.context, obj2.context)
        self.assertRaises(ValueError, self.access.get_by_name, uuid.uuid4().hex)

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
        base = datetime.datetime(2014, 12, 25, 0, 0, 0)
        for i in range(60):
            timestamp = base + datetime.timedelta(seconds=i)
            obj = FakeModelDB(name=uuid.uuid4().hex, timestamp=timestamp)
            self.access.add_or_update(obj)

        dt_range = '20141225T000010..20141225T000019'
        objs = self.access.query(timestamp=dt_range)
        self.assertEqual(len(objs), 10)

        dt_range = '20141225T000019..20141225T000010'
        objs = self.access.query(timestamp=dt_range)
        self.assertEqual(len(objs), 10)

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

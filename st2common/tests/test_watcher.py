import bson
import eventlet
import mock
import mongoengine as me
from oslo.config import cfg

from st2tests import DbTestCase
from st2common.models.db import MongoDBAccess
from st2common.persistence import Access
from st2common.util import watch


class TestDB(me.Document):
    name = me.StringField()


class Test(Access):
    IMPL = MongoDBAccess(TestDB)

    @classmethod
    def _get_impl(kls):
        return kls.IMPL


class WatcherTest(DbTestCase):

    def tearDown(self):
        watch._clear_watcher()
        super(WatcherTest, self).tearDown()

    def test_watcher_started(self):
        watcher = watch.get_watcher()
        self.assertTrue(watcher.status())

    def test_watcher_no_auto_start(self):
        watcher = watch.get_watcher(False)
        self.assertFalse(watcher.status())

    def test_watcher_stop(self):
        watcher = watch.get_watcher()

        watcher.stop()

        self.assertFalse(watcher.status())

    def test_watcher_start_running(self):
        watcher = watch.get_watcher()

        self.assertRaises(Exception, watcher.start)

    def test_watcher_stop_not_running(self):
        watcher = watch.get_watcher()
        watcher.stop()

        self.assertRaises(Exception, watcher.stop)

    def test_watcher_watches_default(self):
        watcher = watch.get_watcher()
        func = mock.MagicMock()

        watcher.watch(func, TestDB)

        eventlet.sleep(0)

        doc = self._create_and_save_test_document()
        self._delete_test_document(doc)

        eventlet.sleep(1)

        self.assertEqual(2, func.call_count)
        self._assert_call_args(func.call_args_list[0][0], dict(doc.to_mongo()), watch.INSERT)
        self._assert_call_args(func.call_args_list[1][0], {'_id': doc.id}, watch.DELETE)

    def test_watcher_watches_operation(self):
        watcher = watch.get_watcher()
        func = mock.MagicMock()

        watcher.watch(func, TestDB, watch.INSERT)

        eventlet.sleep(0)

        doc = self._create_and_save_test_document()
        self._delete_test_document(doc)

        eventlet.sleep(1)

        self.assertEqual(1, func.call_count)
        self._assert_call_args(func.call_args_list[0][0], dict(doc.to_mongo()), watch.INSERT)

    @staticmethod
    def _create_and_save_test_document():
        return Test.add_or_update(TestDB(name='test'))

    @staticmethod
    def _delete_test_document(doc):
        return Test.delete(doc)

    def _assert_call_args(self, args, doc, operation):
        self.assertEqual(args[0], 'st2-test.test_d_b')
        self.assertIsInstance(args[1], bson.Timestamp)
        self.assertEqual(args[2], operation)
        self.assertEqual(args[3], doc['_id'])
        self.assertEqual(args[4], doc)


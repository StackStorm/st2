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

try:
    import simplejson as json
except ImportError:
    import json
import os
import sys
import shutil
import st2tests.config

import eventlet
from unittest2 import TestCase
from oslo.config import cfg

from st2common.models.db import db_setup, db_teardown
import st2common.models.db.reactor as reactor_model
import st2common.models.db.action as action_model
import st2common.models.db.datastore as datastore_model
import st2common.models.db.actionrunner as actionrunner_model
import st2common.models.db.execution as execution_model

__all__ = [
    'EventletTestCase',
    'DbTestCase',
    'CleanDbTestCase',
    'CleanFilesTestCase'
]


ALL_MODELS = []
ALL_MODELS.extend(reactor_model.MODELS)
ALL_MODELS.extend(action_model.MODELS)
ALL_MODELS.extend(datastore_model.MODELS)
ALL_MODELS.extend(actionrunner_model.MODELS)
ALL_MODELS.extend(execution_model.MODELS)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TESTS_CONFIG_PATH = os.path.join(BASE_DIR, '../conf/st2.conf')


class EventletTestCase(TestCase):
    """
    Base test class which performs eventlet monkey patching before the tests run
    and un-patching after the tests have finished running.
    """

    @classmethod
    def setUpClass(cls):
        eventlet.monkey_patch(
            os=True,
            select=True,
            socket=True,
            thread=False if '--use-debugger' in sys.argv else True,
            time=True
        )

    @classmethod
    def tearDownClass(cls):
        eventlet.monkey_patch(
            os=False,
            select=False,
            socket=False,
            thread=False,
            time=False
        )


class BaseDbTestCase(TestCase):
    @classmethod
    def setUpClass(cls):
        st2tests.config.parse_args()

    @classmethod
    def _establish_connection_and_re_create_db(cls):
        username = cfg.CONF.database.username if hasattr(cfg.CONF.database, 'username') else None
        password = cfg.CONF.database.password if hasattr(cfg.CONF.database, 'password') else None
        cls.db_connection = db_setup(
            cfg.CONF.database.db_name, cfg.CONF.database.host, cfg.CONF.database.port,
            username=username, password=password)
        cls._drop_collections()
        cls.db_connection.drop_database(cfg.CONF.database.db_name)

    @classmethod
    def _drop_db(cls):
        cls._drop_collections()
        if cls.db_connection is not None:
            cls.db_connection.drop_database(cfg.CONF.database.db_name)
        db_teardown()
        cls.db_connection = None

    @classmethod
    def _drop_collections(cls):
        # XXX: Explicitly drop all the collection. Otherwise, artifacts are left over in
        # subsequent tests.
        # See: https://github.com/MongoEngine/mongoengine/issues/566
        # See: https://github.com/MongoEngine/mongoengine/issues/565
        global ALL_MODELS
        for model in ALL_MODELS:
            model.drop_collection()


class DbTestCase(BaseDbTestCase):
    """
    This class drops and re-creates the database once per TestCase run.

    This means database is only dropped once before all the tests from this class run. This means
    data is persited between different tests in this class.
    """

    db_connection = None
    current_result = None

    @classmethod
    def setUpClass(cls):
        BaseDbTestCase.setUpClass()
        cls._establish_connection_and_re_create_db()

    @classmethod
    def tearDownClass(cls):
        drop_db = True

        if cls.current_result.errors or cls.current_result.failures:
            # Don't drop DB on test failure
            drop_db = False

        if drop_db:
            cls._drop_db()

    def run(self, result=None):
        # Remember result for use in tearDown and tearDownClass
        self.current_result = result
        self.__class__.current_result = result
        super(DbTestCase, self).run(result=result)


class CleanDbTestCase(BaseDbTestCase):
    """
    Class which ensures database is re-created before running each test method.

    This means each test inside this class is self-sustained and starts with a clean (empty)
    database.
    """

    def setUp(self):
        self._establish_connection_and_re_create_db()


class CleanFilesTestCase(TestCase):
    """
    Base test class which deletes specified files and directories on tearDown.
    """
    to_delete_files = []
    to_delete_directories = []

    def tearDown(self):
        for file_path in self.to_delete_files:
            try:
                os.remove(file_path)
            except Exception:
                pass

        for file_path in self.to_delete_directories:
            try:
                shutil.rmtree(file_path)
            except Exception:
                pass


class FakeResponse(object):

    def __init__(self, text, status_code, reason):
        self.text = text
        self.status_code = status_code
        self.reason = reason

    def json(self):
        return json.loads(self.text)

    def raise_for_status(self):
        raise Exception(self.reason)


def get_fixtures_path():
    return os.path.join(os.path.dirname(__file__), 'fixtures')


def get_resources_path():
    return os.path.join(os.path.dirname(__file__), 'resources')

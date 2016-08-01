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
import os.path
import sys
import shutil
import logging

import six
import eventlet
import psutil
from oslo_config import cfg
from unittest2 import TestCase

from st2common.exceptions.db import StackStormDBObjectConflictError
from st2common.models.db import db_setup, db_teardown, db_ensure_indexes
from st2common.bootstrap.base import ResourceRegistrar
from st2common.bootstrap.configsregistrar import ConfigsRegistrar
from st2common.content.utils import get_packs_base_paths
from st2common.exceptions.db import StackStormDBObjectNotFoundError
import st2common.models.db.rule as rule_model
import st2common.models.db.rule_enforcement as rule_enforcement_model
import st2common.models.db.sensor as sensor_model
import st2common.models.db.trigger as trigger_model
import st2common.models.db.action as action_model
import st2common.models.db.keyvalue as keyvalue_model
import st2common.models.db.runner as runner_model
import st2common.models.db.execution as execution_model
import st2common.models.db.executionstate as executionstate_model
import st2common.models.db.liveaction as liveaction_model
import st2common.models.db.actionalias as actionalias_model
import st2common.models.db.policy as policy_model
import st2tests.config

# Imports for backward compatibility (those classes have been moved to standalone modules)
from st2tests.actions import BaseActionTestCase
from st2tests.sensors import BaseSensorTestCase
from st2tests.action_aliases import BaseActionAliasTestCase


__all__ = [
    'EventletTestCase',
    'DbTestCase',
    'DbModelTestCase',
    'CleanDbTestCase',
    'CleanFilesTestCase',
    'IntegrationTestCase',

    # Pack test classes
    'BaseSensorTestCase',
    'BaseActionTestCase',
    'BaseActionAliasTestCase'
]

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

ALL_MODELS = []
ALL_MODELS.extend(rule_model.MODELS)
ALL_MODELS.extend(sensor_model.MODELS)
ALL_MODELS.extend(trigger_model.MODELS)
ALL_MODELS.extend(action_model.MODELS)
ALL_MODELS.extend(keyvalue_model.MODELS)
ALL_MODELS.extend(runner_model.MODELS)
ALL_MODELS.extend(execution_model.MODELS)
ALL_MODELS.extend(executionstate_model.MODELS)
ALL_MODELS.extend(liveaction_model.MODELS)
ALL_MODELS.extend(actionalias_model.MODELS)
ALL_MODELS.extend(policy_model.MODELS)
ALL_MODELS.extend(rule_enforcement_model.MODELS)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TESTS_CONFIG_PATH = os.path.join(BASE_DIR, '../conf/st2.conf')


class BaseTestCase(TestCase):

    @classmethod
    def _register_packs(self):
        """
        Register all the packs inside the fixtures directory.
        """

        registrar = ResourceRegistrar(use_pack_cache=False)
        registrar.register_packs(base_dirs=get_packs_base_paths())

    @classmethod
    def _register_pack_configs(self, validate_configs=False):
        """
        Register all the packs inside the fixtures directory.
        """
        registrar = ConfigsRegistrar(use_pack_cache=False, validate_configs=validate_configs)
        registrar.register_configs_for_all_packs(base_dirs=get_packs_base_paths())


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


class BaseDbTestCase(BaseTestCase):

    # Set to True to enable printing of all the log messages to the console
    DISPLAY_LOG_MESSAGES = False

    @classmethod
    def setUpClass(cls):
        st2tests.config.parse_args()

        if cls.DISPLAY_LOG_MESSAGES:
            config_path = os.path.join(BASE_DIR, '../conf/logging.conf')
            logging.config.fileConfig(config_path,
                                      disable_existing_loggers=False)

    @classmethod
    def _establish_connection_and_re_create_db(cls):
        username = cfg.CONF.database.username if hasattr(cfg.CONF.database, 'username') else None
        password = cfg.CONF.database.password if hasattr(cfg.CONF.database, 'password') else None
        cls.db_connection = db_setup(
            cfg.CONF.database.db_name, cfg.CONF.database.host, cfg.CONF.database.port,
            username=username, password=password, ensure_indexes=False)
        cls._drop_collections()
        cls.db_connection.drop_database(cfg.CONF.database.db_name)

        # Explicity ensure indexes after we re-create the DB otherwise ensure_indexes could failure
        # inside db_setup if test inserted invalid data
        db_ensure_indexes()

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
    register_packs = False
    register_pack_configs = False

    @classmethod
    def setUpClass(cls):
        BaseDbTestCase.setUpClass()
        cls._establish_connection_and_re_create_db()

        if cls.register_packs:
            cls._register_packs()

        if cls.register_pack_configs:
            cls._register_pack_configs()

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


class DbModelTestCase(DbTestCase):
    access_type = None

    @classmethod
    def setUpClass(cls):
        super(DbModelTestCase, cls).setUpClass()
        cls.db_type = cls.access_type.impl.model

    def _assert_fields_equal(self, a, b, exclude=None):
        exclude = exclude or []
        fields = {k: v for k, v in six.iteritems(self.db_type._fields) if k not in exclude}

        assert_funcs = {
            'mongoengine.fields.DictField': self.assertDictEqual,
            'mongoengine.fields.ListField': self.assertListEqual,
            'mongoengine.fields.SortedListField': self.assertListEqual
        }

        for k, v in six.iteritems(fields):
            assert_func = assert_funcs.get(str(v), self.assertEqual)
            assert_func(getattr(a, k, None), getattr(b, k, None))

    def _assert_values_equal(self, a, values=None):
        values = values or {}

        assert_funcs = {
            'dict': self.assertDictEqual,
            'list': self.assertListEqual
        }

        for k, v in six.iteritems(values):
            assert_func = assert_funcs.get(type(v).__name__, self.assertEqual)
            assert_func(getattr(a, k, None), v)

    def _assert_crud(self, instance, defaults=None, updates=None):
        # Assert instance is not already in the database.
        self.assertIsNone(getattr(instance, 'id', None))

        # Assert default values are assigned.
        self._assert_values_equal(instance, values=defaults)

        # Assert instance is created in the datbaase.
        saved = self.access_type.add_or_update(instance)
        self.assertIsNotNone(saved.id)
        self._assert_fields_equal(instance, saved, exclude=['id'])
        retrieved = self.access_type.get_by_id(saved.id)
        self._assert_fields_equal(saved, retrieved)

        # Assert instance is updated in the database.
        for k, v in six.iteritems(updates or {}):
            setattr(instance, k, v)

        updated = self.access_type.add_or_update(instance)
        self._assert_fields_equal(instance, updated)

        # Assert instance is deleted from the database.
        retrieved = self.access_type.get_by_id(instance.id)
        retrieved.delete()
        self.assertRaises(StackStormDBObjectNotFoundError,
                          self.access_type.get_by_id, instance.id)

    def _assert_unique_key_constraint(self, instance):
        # Assert instance is not already in the database.
        self.assertIsNone(getattr(instance, 'id', None))

        # Assert instance is created in the datbaase.
        saved = self.access_type.add_or_update(instance)
        self.assertIsNotNone(saved.id)

        # Assert exception is thrown if try to create same instance again.
        delattr(instance, 'id')
        self.assertRaises(StackStormDBObjectConflictError,
                          self.access_type.add_or_update,
                          instance)


class CleanDbTestCase(BaseDbTestCase):
    """
    Class which ensures database is re-created before running each test method.

    This means each test inside this class is self-sustained and starts with a clean (empty)
    database.
    """

    register_packs = False
    register_pack_configs = False

    def setUp(self):
        self._establish_connection_and_re_create_db()

        if self.register_packs:
            self._register_packs()

        if self.register_pack_configs:
            self._register_pack_configs()


class CleanFilesTestCase(TestCase):
    """
    Base test class which deletes specified files and directories on setUp and `tearDown.
    """
    to_delete_files = []
    to_delete_directories = []

    def setUp(self):
        super(CleanFilesTestCase, self).setUp()
        self._delete_files()

    def tearDown(self):
        super(CleanFilesTestCase, self).tearDown()
        self._delete_files()

    def _delete_files(self):
        for file_path in self.to_delete_files:
            if not os.path.isfile(file_path):
                continue

            try:
                os.remove(file_path)
            except Exception:
                pass

        for file_path in self.to_delete_directories:
            if not os.path.isdir(file_path):
                continue

            try:
                shutil.rmtree(file_path)
            except Exception:
                pass


class IntegrationTestCase(TestCase):
    """
    Base test class for integration tests to inherit from.

    It includes various utility functions and assert methods for working with processes.
    """

    # Set to True to print process stdout and stderr in tearDown after killing the processes
    # which are still alive
    print_stdout_stderr_on_teardown = False

    processes = {}

    def tearDown(self):
        super(IntegrationTestCase, self).tearDown()

        # Make sure we kill all the processes on teardown so they don't linger around if an
        # exception was thrown.
        for pid, process in self.processes.items():

            try:
                process.kill()
            except OSError:
                # Process already exited or similar
                pass

            if self.print_stdout_stderr_on_teardown:
                try:
                    stdout = process.stdout.read()
                except:
                    stdout = None

                try:
                    stderr = process.stderr.read()
                except:
                    stderr = None

                print('Process "%s"' % (process.pid))
                print('Stdout: %s' % (stdout))
                print('Stderr: %s' % (stderr))

    def add_process(self, process):
        """
        Add a process to the local data structure to make sure it will get killed and cleaned up on
        tearDown.
        """
        self.processes[process.pid] = process

    def remove_process(self, process):
        """
        Remove process from a local data structure.
        """
        if process.pid in self.processes:
            del self.processes[process.pid]

    def assertProcessIsRunning(self, process):
        """
        Assert that a long running process provided Process object as returned by subprocess.Popen
        has succesfuly started and is running.
        """
        return_code = process.poll()

        if return_code is not None:
            stdout = process.stdout.read()
            stderr = process.stderr.read()
            msg = ('Process exited with code=%s.\nStdout:\n%s\n\nStderr:\n%s' %
                   (return_code, stdout, stderr))
            self.fail(msg)

    def assertProcessExited(self, proc):
        try:
            status = proc.status()
        except psutil.NoSuchProcess:
            status = 'exited'

        if status not in ['exited', 'zombie']:
            self.fail('Process with pid "%s" is still running' % (proc.pid))


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

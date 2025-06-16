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

import mock
import six
import unittest

import st2tests

# XXX: actionsensor import depends on config being setup.
import st2tests.config as tests_config

tests_config.parse_args()

from orquesta_functions import st2kv
from orquesta import exceptions as exc

from st2common.constants import keyvalue as kvp_const
from st2common.models.api import keyvalue as kvp_api
from st2common.models.db import auth as auth_db
from st2common.models.db import keyvalue as kvp_db
from st2common.persistence import keyvalue as kvp_db_access
from st2common.util import crypto
from st2common.util import keyvalue as kvp_util


MOCK_CTX = {"__vars": {"st2": {"user": "stanley"}}}
MOCK_CTX_NO_USER = {"__vars": {"st2": {}}}


class DatastoreFunctionTest(unittest.TestCase):
    def test_missing_user_context(self):
        self.assertRaises(KeyError, st2kv.st2kv_, MOCK_CTX_NO_USER, "foo")

    def test_invalid_input(self):
        self.assertRaises(TypeError, st2kv.st2kv_, None, 123)
        self.assertRaises(TypeError, st2kv.st2kv_, {}, 123)
        self.assertRaises(TypeError, st2kv.st2kv_, {}, dict())
        self.assertRaises(TypeError, st2kv.st2kv_, {}, object())
        self.assertRaises(TypeError, st2kv.st2kv_, {}, [1, 2])


class UserScopeDatastoreFunctionTest(st2tests.ExecutionDbTestCase):
    @classmethod
    def setUpClass(cls):
        super(UserScopeDatastoreFunctionTest, cls).setUpClass()
        user = auth_db.UserDB(name="stanley")
        user.save()
        scope = kvp_const.FULL_USER_SCOPE
        cls.kvps = {}

        # Plain keys
        keys = {"stanley:foo": "bar", "stanley:foo_empty": "", "stanley:foo_null": None}

        for k, v in six.iteritems(keys):
            instance = kvp_db.KeyValuePairDB(name=k, value=v, scope=scope)
            cls.kvps[k] = kvp_db_access.KeyValuePair.add_or_update(instance)

        # Secret key
        keys = {"stanley:fu": "bar", "stanley:fu_empty": ""}

        for k, v in six.iteritems(keys):
            value = crypto.symmetric_encrypt(kvp_api.KeyValuePairAPI.crypto_key, v)
            instance = kvp_db.KeyValuePairDB(
                name=k, value=value, scope=scope, secret=True
            )
            cls.kvps[k] = kvp_db_access.KeyValuePair.add_or_update(instance)

    @classmethod
    def tearDownClass(cls):
        for k, v in six.iteritems(cls.kvps):
            v.delete()

        super(UserScopeDatastoreFunctionTest, cls).tearDownClass()

    def test_key_exists(self):
        self.assertEqual(st2kv.st2kv_(MOCK_CTX, "foo"), "bar")
        self.assertEqual(st2kv.st2kv_(MOCK_CTX, "foo_empty"), "")
        self.assertIsNone(st2kv.st2kv_(MOCK_CTX, "foo_null"))

    def test_key_does_not_exist(self):
        self.assertRaisesRegex(
            exc.ExpressionEvaluationException,
            'The key ".*" does not exist in the StackStorm datastore.',
            st2kv.st2kv_,
            MOCK_CTX,
            "foobar",
        )

    def test_key_does_not_exist_but_return_default(self):
        self.assertEqual(
            st2kv.st2kv_(MOCK_CTX, "foobar", default="foosball"), "foosball"
        )
        self.assertEqual(st2kv.st2kv_(MOCK_CTX, "foobar", default=""), "")
        self.assertIsNone(st2kv.st2kv_(MOCK_CTX, "foobar", default=None))

    def test_key_decrypt(self):
        self.assertNotEqual(st2kv.st2kv_(MOCK_CTX, "fu"), "bar")
        self.assertNotEqual(st2kv.st2kv_(MOCK_CTX, "fu", decrypt=False), "bar")
        self.assertEqual(st2kv.st2kv_(MOCK_CTX, "fu", decrypt=True), "bar")
        self.assertNotEqual(st2kv.st2kv_(MOCK_CTX, "fu_empty"), "")
        self.assertNotEqual(st2kv.st2kv_(MOCK_CTX, "fu_empty", decrypt=False), "")
        self.assertEqual(st2kv.st2kv_(MOCK_CTX, "fu_empty", decrypt=True), "")

    @mock.patch.object(
        kvp_util, "get_key", mock.MagicMock(side_effect=Exception("Mock failure."))
    )
    def test_get_key_exception(self):
        self.assertRaisesRegex(
            exc.ExpressionEvaluationException,
            "Mock failure.",
            st2kv.st2kv_,
            MOCK_CTX,
            "foo",
        )


class SystemScopeDatastoreFunctionTest(st2tests.ExecutionDbTestCase):
    @classmethod
    def setUpClass(cls):
        super(SystemScopeDatastoreFunctionTest, cls).setUpClass()
        user = auth_db.UserDB(name="stanley")
        user.save()
        scope = kvp_const.FULL_SYSTEM_SCOPE
        cls.kvps = {}

        # Plain key
        keys = {"foo": "bar", "foo_empty": "", "foo_null": None}

        for k, v in six.iteritems(keys):
            instance = kvp_db.KeyValuePairDB(name=k, value=v, scope=scope)
            cls.kvps[k] = kvp_db_access.KeyValuePair.add_or_update(instance)

        # Secret key
        keys = {"fu": "bar", "fu_empty": ""}

        for k, v in six.iteritems(keys):
            value = crypto.symmetric_encrypt(kvp_api.KeyValuePairAPI.crypto_key, v)
            instance = kvp_db.KeyValuePairDB(
                name=k, value=value, scope=scope, secret=True
            )
            cls.kvps[k] = kvp_db_access.KeyValuePair.add_or_update(instance)

    @classmethod
    def tearDownClass(cls):
        for k, v in six.iteritems(cls.kvps):
            v.delete()

        super(SystemScopeDatastoreFunctionTest, cls).tearDownClass()

    def test_key_exists(self):
        self.assertEqual(st2kv.st2kv_(MOCK_CTX, "system.foo"), "bar")
        self.assertEqual(st2kv.st2kv_(MOCK_CTX, "system.foo_empty"), "")
        self.assertIsNone(st2kv.st2kv_(MOCK_CTX, "system.foo_null"))

    def test_key_does_not_exist(self):
        self.assertRaisesRegex(
            exc.ExpressionEvaluationException,
            'The key ".*" does not exist in the StackStorm datastore.',
            st2kv.st2kv_,
            MOCK_CTX,
            "foo",
        )

    def test_key_does_not_exist_but_return_default(self):
        self.assertEqual(
            st2kv.st2kv_(MOCK_CTX, "system.foobar", default="foosball"), "foosball"
        )
        self.assertEqual(st2kv.st2kv_(MOCK_CTX, "system.foobar", default=""), "")
        self.assertIsNone(st2kv.st2kv_(MOCK_CTX, "system.foobar", default=None))

    def test_key_decrypt(self):
        self.assertNotEqual(st2kv.st2kv_(MOCK_CTX, "system.fu"), "bar")
        self.assertNotEqual(st2kv.st2kv_(MOCK_CTX, "system.fu", decrypt=False), "bar")
        self.assertEqual(st2kv.st2kv_(MOCK_CTX, "system.fu", decrypt=True), "bar")
        self.assertNotEqual(st2kv.st2kv_(MOCK_CTX, "system.fu_empty"), "")
        self.assertNotEqual(
            st2kv.st2kv_(MOCK_CTX, "system.fu_empty", decrypt=False), ""
        )
        self.assertEqual(st2kv.st2kv_(MOCK_CTX, "system.fu_empty", decrypt=True), "")

    @mock.patch.object(
        kvp_util, "get_key", mock.MagicMock(side_effect=Exception("Mock failure."))
    )
    def test_get_key_exception(self):
        self.assertRaisesRegex(
            exc.ExpressionEvaluationException,
            "Mock failure.",
            st2kv.st2kv_,
            MOCK_CTX,
            "system.foo",
        )

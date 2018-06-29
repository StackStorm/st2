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

import unittest2

import st2tests

# XXX: actionsensor import depends on config being setup.
import st2tests.config as tests_config
tests_config.parse_args()

from orchestra_functions import st2kv
from orchestra import exceptions as exc

from st2common.constants import keyvalue as kvp_const
from st2common.models.api import keyvalue as kvp_api
from st2common.models.db import auth as auth_db
from st2common.models.db import keyvalue as kvp_db
from st2common.persistence import keyvalue as kvp_db_access
from st2common.util import crypto


MOCK_ORCHESTRA_CTX = {'__vars': {'st2': {'user': 'stanley'}}}
MOCK_ORCHESTRA_CTX_NO_USER = {'__vars': {'st2': {}}}


class DatastoreFunctionTest(unittest2.TestCase):

    def test_missing_user_context(self):
        self.assertRaises(KeyError, st2kv.st2kv_, MOCK_ORCHESTRA_CTX_NO_USER, 'foo')

    def test_invalid_input(self):
        self.assertRaises(TypeError, st2kv.st2kv_, None, 123)
        self.assertRaises(TypeError, st2kv.st2kv_, {}, 123)
        self.assertRaises(TypeError, st2kv.st2kv_, {}, dict())
        self.assertRaises(TypeError, st2kv.st2kv_, {}, object())
        self.assertRaises(TypeError, st2kv.st2kv_, {}, [1, 2])


class UserScopeDatastoreFunctionTest(st2tests.DbTestCase):

    @classmethod
    def setUpClass(cls):
        super(UserScopeDatastoreFunctionTest, cls).setUpClass()
        user = auth_db.UserDB(name='stanley')
        user.save()

    def setUp(self):
        super(UserScopeDatastoreFunctionTest, self).setUp()
        scope = kvp_const.FULL_USER_SCOPE

        # Plain key
        key_id = 'stanley:foo'
        instance = kvp_db.KeyValuePairDB(name=key_id, value='bar', scope=scope)
        self.kvp = kvp_db_access.KeyValuePair.add_or_update(instance)

        # Secret key
        key_id = 'stanley:fu'
        value = crypto.symmetric_encrypt(kvp_api.KeyValuePairAPI.crypto_key, 'bar')
        instance = kvp_db.KeyValuePairDB(name=key_id, value=value, scope=scope, secret=True)
        self.secret_kvp = kvp_db_access.KeyValuePair.add_or_update(instance)

    def tearDown(self):
        if hasattr(self, 'kvp') and self.kvp:
            self.kvp.delete()

        if hasattr(self, 'secret_kvp') and self.secret_kvp:
            self.secret_kvp.delete()

        super(UserScopeDatastoreFunctionTest, self).tearDown()

    def test_key_exists(self):
        self.assertEqual(st2kv.st2kv_(MOCK_ORCHESTRA_CTX, 'foo'), 'bar')

    def test_key_does_not_exist(self):
        self.assertRaises(
            exc.ExpressionEvaluationException,
            st2kv.st2kv_,
            MOCK_ORCHESTRA_CTX,
            'foobar'
        )

    def test_key_decrypt(self):
        self.assertEqual(st2kv.st2kv_(MOCK_ORCHESTRA_CTX, 'fu', decrypt=True), 'bar')


class SystemScopeDatastoreFunctionTest(st2tests.DbTestCase):

    @classmethod
    def setUpClass(cls):
        super(SystemScopeDatastoreFunctionTest, cls).setUpClass()
        user = auth_db.UserDB(name='stanley')
        user.save()

    def setUp(self):
        super(SystemScopeDatastoreFunctionTest, self).setUp()
        scope = kvp_const.FULL_SYSTEM_SCOPE

        # Plain key
        key_id = 'foo'
        instance = kvp_db.KeyValuePairDB(name=key_id, value='bar', scope=scope)
        self.kvp = kvp_db_access.KeyValuePair.add_or_update(instance)

        # Secret key
        key_id = 'fu'
        value = crypto.symmetric_encrypt(kvp_api.KeyValuePairAPI.crypto_key, 'bar')
        instance = kvp_db.KeyValuePairDB(name=key_id, value=value, scope=scope, secret=True)
        self.secret_kvp = kvp_db_access.KeyValuePair.add_or_update(instance)

    def tearDown(self):
        if hasattr(self, 'kvp') and self.kvp:
            self.kvp.delete()

        if hasattr(self, 'secret_kvp') and self.secret_kvp:
            self.secret_kvp.delete()

        super(SystemScopeDatastoreFunctionTest, self).tearDown()

    def test_key_exists(self):
        self.assertEqual(st2kv.st2kv_(MOCK_ORCHESTRA_CTX, 'system.foo'), 'bar')

    def test_key_does_not_exist(self):
        self.assertRaises(
            exc.ExpressionEvaluationException,
            st2kv.st2kv_,
            MOCK_ORCHESTRA_CTX,
            'foo'
        )

    def test_key_decrypt(self):
        self.assertEqual(st2kv.st2kv_(MOCK_ORCHESTRA_CTX, 'system.fu', decrypt=True), 'bar')

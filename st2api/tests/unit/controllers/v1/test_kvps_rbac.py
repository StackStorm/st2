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

import six

from st2common.constants.keyvalue import FULL_SYSTEM_SCOPE
from st2common.constants.keyvalue import FULL_USER_SCOPE
from st2common.services.keyvalues import get_key_reference
from st2common.persistence.auth import User
from st2common.models.db.auth import UserDB
from st2common.models.db.keyvalue import KeyValuePairDB
from st2common.persistence.keyvalue import KeyValuePair
from st2common.models.api.keyvalue import KeyValuePairSetAPI
from st2common.models.api.keyvalue import KeyValuePairAPI
from tests.base import APIControllerWithRBACTestCase

http_client = six.moves.http_client

__all__ = [
    'KeyValuesControllerRBACTestCase'
]


class KeyValuesControllerRBACTestCase(APIControllerWithRBACTestCase):
    def setUp(self):
        super(KeyValuesControllerRBACTestCase, self).setUp()

        self.kvps = {}

        # Insert mock users
        user_1_db = UserDB(name='user1')
        user_1_db = User.add_or_update(user_1_db)
        self.users['user_1'] = user_1_db

        user_2_db = UserDB(name='user2')
        user_2_db = User.add_or_update(user_2_db)
        self.users['user_2'] = user_2_db

        # Insert mock kvp objects
        kvp_api = KeyValuePairSetAPI(name='test_system_scope', value='value1',
                                     scope=FULL_SYSTEM_SCOPE)
        kvp_db = KeyValuePairSetAPI.to_model(kvp_api)
        kvp_db = KeyValuePair.add_or_update(kvp_db)
        kvp_db = KeyValuePairAPI.from_model(kvp_db)
        self.kvps['kvp_1'] = kvp_db

        kvp_api = KeyValuePairSetAPI(name='test_system_scope_secret', value='value_secret',
                                     scope=FULL_SYSTEM_SCOPE, secret=True)
        kvp_db = KeyValuePairSetAPI.to_model(kvp_api)
        kvp_db = KeyValuePair.add_or_update(kvp_db)
        kvp_db = KeyValuePairAPI.from_model(kvp_db)
        self.kvps['kvp_2'] = kvp_db

        name = get_key_reference(scope=FULL_USER_SCOPE, name='test_user_scope_1', user='user1')
        kvp_db = KeyValuePairDB(name=name, value='valueu12', scope=FULL_USER_SCOPE)
        kvp_db = KeyValuePair.add_or_update(kvp_db)
        kvp_db = KeyValuePairAPI.from_model(kvp_db)
        self.kvps['kvp_3'] = kvp_db

        name = get_key_reference(scope=FULL_USER_SCOPE, name='test_user_scope_2', user='user1')
        kvp_api = KeyValuePairSetAPI(name=name, value='user_secret', scope=FULL_USER_SCOPE,
                                     secret=True)
        kvp_db = KeyValuePairSetAPI.to_model(kvp_api)
        kvp_db = KeyValuePair.add_or_update(kvp_db)
        kvp_db = KeyValuePairAPI.from_model(kvp_db)
        self.kvps['kvp_4'] = kvp_db

        name = get_key_reference(scope=FULL_USER_SCOPE, name='test_user_scope_3', user='user2')
        kvp_db = KeyValuePairDB(name=name, value='valueu21', scope=FULL_USER_SCOPE)
        kvp_db = KeyValuePair.add_or_update(kvp_db)
        kvp_db = KeyValuePairAPI.from_model(kvp_db)
        self.kvps['kvp_5'] = kvp_db

        self.system_scoped_items_count = 2
        self.user_scoped_items_count = 3
        self.user_scoped_items_per_user_count = {
            'user1': 2,
            'user2': 1
        }

    def test_get_all_system_scope_success(self):
        # Regular user, should be able to view all the system scoped items
        self.use_user(self.users['user_1'])

        resp = self.app.get('/v1/keys')
        self.assertEqual(resp.status_int, 200)
        self.assertEqual(len(resp.json), self.system_scoped_items_count)
        for item in resp.json:
            self.assertEqual(item['scope'], FULL_SYSTEM_SCOPE)

        # Verify second item is encrypted
        self.assertTrue(resp.json[1]['secret'])
        self.assertTrue(len(resp.json[1]['value']) > 50)

        resp = self.app.get('/v1/keys')
        self.assertEqual(resp.status_int, 200)
        self.assertEqual(len(resp.json), self.system_scoped_items_count)
        for item in resp.json:
            self.assertEqual(item['scope'], FULL_SYSTEM_SCOPE)

        # limit=-1 admin user
        self.use_user(self.users['admin'])
        resp = self.app.get('/v1/keys/?limit=-1')
        self.assertEqual(resp.status_int, 200)
        self.assertEqual(len(resp.json), self.system_scoped_items_count)
        for item in resp.json:
            self.assertEqual(item['scope'], FULL_SYSTEM_SCOPE)

        # Verify second item is encrypted
        self.assertTrue(resp.json[1]['secret'])
        self.assertTrue(len(resp.json[1]['value']) > 50)

    def test_get_all_user_scope_success(self):
        # Regular user should be able to view all the items scoped to themselves
        self.use_user(self.users['user_1'])

        resp = self.app.get('/v1/keys?scope=st2kv.user')
        self.assertEqual(resp.status_int, 200)
        self.assertEqual(len(resp.json), self.user_scoped_items_per_user_count['user1'])
        for item in resp.json:
            self.assertEqual(item['scope'], FULL_USER_SCOPE)
            self.assertEqual(item['user'], 'user1')

        # Verify second item is encrypted
        self.assertTrue(resp.json[1]['secret'])
        self.assertTrue(len(resp.json[1]['value']) > 50)

        resp = self.app.get('/v1/keys?scope=st2kv.user')
        self.assertEqual(resp.status_int, 200)
        self.assertEqual(len(resp.json), self.user_scoped_items_per_user_count['user1'])
        for item in resp.json:
            self.assertEqual(item['scope'], FULL_USER_SCOPE)
            self.assertEqual(item['user'], 'user1')

        # Verify second item is encrypted
        self.assertTrue(resp.json[1]['secret'])
        self.assertTrue(len(resp.json[1]['value']) > 50)

    def test_get_all_scope_system_decrypt_admin_success(self):
        # Admin should be able to view all system scoped decrypted values
        self.use_user(self.users['admin'])

        resp = self.app.get('/v1/keys?decrypt=True')
        self.assertEqual(resp.status_int, 200)
        self.assertEqual(len(resp.json), self.system_scoped_items_count)
        for item in resp.json:
            self.assertEqual(item['scope'], FULL_SYSTEM_SCOPE)

        # Verify second item is decrypted
        self.assertTrue(resp.json[1]['secret'])
        self.assertEqual(resp.json[1]['value'], 'value_secret')
        resp = self.app.get('/v1/keys?decrypt=True&limit=-1')
        self.assertEqual(resp.status_int, 200)
        self.assertEqual(len(resp.json), self.system_scoped_items_count)
        for item in resp.json:
            self.assertEqual(item['scope'], FULL_SYSTEM_SCOPE)

        # Verify second item is decrypted
        self.assertTrue(resp.json[1]['secret'])
        self.assertEqual(resp.json[1]['value'], 'value_secret')

    def test_get_all_scope_all_admin_decrypt_success(self):
        # Admin users should be able to view all items (including user scoped ones) when using
        # ?scope=all
        self.use_user(self.users['admin'])

        resp = self.app.get('/v1/keys?scope=all&decrypt=True')
        self.assertEqual(resp.status_int, 200)
        expected_count = (self.system_scoped_items_count + self.user_scoped_items_count)
        self.assertEqual(len(resp.json), expected_count)

        # Verify second item is decrypted
        self.assertTrue(resp.json[1]['secret'])
        self.assertEqual(resp.json[1]['scope'], FULL_SYSTEM_SCOPE)
        self.assertEqual(resp.json[1]['value'], 'value_secret')

        # Verify user scoped items are available and decrypted
        self.assertTrue(resp.json[3]['secret'])
        self.assertEqual(resp.json[3]['scope'], FULL_USER_SCOPE)
        self.assertEqual(resp.json[3]['user'], 'user1')
        self.assertEqual(resp.json[3]['value'], 'user_secret')

        self.assertEqual(resp.json[4]['scope'], FULL_USER_SCOPE)
        self.assertEqual(resp.json[4]['user'], 'user2')

        resp = self.app.get('/v1/keys?scope=all&decrypt=True&limit=-1')
        self.assertEqual(resp.status_int, 200)
        expected_count = (self.system_scoped_items_count + self.user_scoped_items_count)
        self.assertEqual(len(resp.json), expected_count)

    def test_get_all_non_admin_decrypt_failure(self):
        # Non admin shouldn't be able to view decrypted items
        self.use_user(self.users['user_1'])

        resp = self.app.get('/v1/keys?decrypt=True', expect_errors=True)
        self.assertEqual(resp.status_code, http_client.FORBIDDEN)
        self.assertTrue('Decrypt option requires administrator access' in resp.json['faultstring'])

    def test_get_all_scope_all_non_admin_failure(self):
        # Non admin users can't use scope=all
        self.use_user(self.users['user_1'])

        resp = self.app.get('/v1/keys?scope=all', expect_errors=True)
        self.assertEqual(resp.status_code, http_client.FORBIDDEN)
        self.assertTrue('"all" scope requires administrator access' in resp.json['faultstring'])

    def test_get_one_system_scope_success(self):
        self.use_user(self.users['user_1'])

        resp = self.app.get('/v1/keys/%s' % (self.kvps['kvp_1'].name))
        self.assertEqual(resp.json['scope'], FULL_SYSTEM_SCOPE)

    def test_get_one_user_scope_success(self):
        # Retrieving user scoped variable which is scoped to the authenticated user
        self.use_user(self.users['user_1'])

        resp = self.app.get('/v1/keys/%s?scope=st2kv.user' % (self.kvps['kvp_3'].name))
        self.assertEqual(resp.json['scope'], FULL_USER_SCOPE)
        self.assertEqual(resp.json['user'], 'user1')

    def test_get_one_user_scope_decrypt_success(self):
        # User can request decrypted value of the item scoped to themselves
        self.use_user(self.users['user_1'])

        resp = self.app.get(
            '/v1/keys/%s?scope=st2kv.user&decrypt=True' % (self.kvps['kvp_4'].name)
        )
        self.assertEqual(resp.json['scope'], FULL_USER_SCOPE)
        self.assertEqual(resp.json['user'], 'user1')
        self.assertTrue(resp.json['secret'])
        self.assertEqual(resp.json['value'], 'user_secret')

    def test_get_one_user_scope_non_current_user_failure(self):
        # User should only be able to retrieved user-scoped items which are scoped to themselves
        self.use_user(self.users['user_1'])

        # This item is scoped to user2
        resp = self.app.get('/v1/keys/%s?scope=st2kv.user' % (self.kvps['kvp_5'].name),
                            expect_errors=True)
        self.assertEqual(resp.status_code, http_client.NOT_FOUND)

        # Should work fine for other user
        self.use_user(self.users['user_2'])

        resp = self.app.get('/v1/keys/%s?scope=st2kv.user' % (self.kvps['kvp_5'].name))
        self.assertEqual(resp.json['scope'], FULL_USER_SCOPE)
        self.assertEqual(resp.json['user'], 'user2')

    def test_get_one_system_scope_decrypt_non_admin_user_failure(self):
        # Non-admin user can't access decrypted system scoped items. They can only access decrypted
        # items which are scoped to themselves.
        self.use_user(self.users['user_1'])

        resp = self.app.get('/v1/keys/%s?decrypt=True' % (self.kvps['kvp_1'].name),
                            expect_errors=True)
        self.assertEqual(resp.status_code, http_client.FORBIDDEN)
        self.assertTrue('Decrypt option requires administrator access' in resp.json['faultstring'])

    def test_set_user_scoped_item_arbitrary_user_admin_success(self):
        # Admin user can set user-scoped items for an arbitrary user
        self.use_user(self.users['admin'])

        data = {
            'name': 'test_new_key_1',
            'value': 'testvalue1',
            'scope': FULL_USER_SCOPE,
            'user': 'user2'
        }
        resp = self.app.put_json('/v1/keys/test_new_key_1', data)
        self.assertEqual(resp.status_code, http_client.OK)

        # Verify item has been created
        resp = self.app.get('/v1/keys/test_new_key_1?scope=st2kv.user&user=user2')
        self.assertEqual(resp.status_code, http_client.OK)
        self.assertEqual(resp.json['value'], 'testvalue1')
        self.assertEqual(resp.json['scope'], FULL_USER_SCOPE)
        self.assertEqual(resp.json['user'], 'user2')

    def test_set_user_scoped_item_arbitrary_user_non_admin_failure(self):
        # Non admin user can't set user scoped item for arbitrary user but just for themselves
        self.use_user(self.users['user_1'])

        data = {
            'name': 'test_new_key_2',
            'value': 'testvalue2',
            'scope': FULL_USER_SCOPE,
            'user': 'user2'
        }
        resp = self.app.put_json('/v1/keys/test_new_key_2', data, expect_errors=True)
        self.assertEqual(resp.status_code, http_client.FORBIDDEN)
        self.assertTrue('"user" attribute can only be provided by admins' in
                        resp.json['faultstring'])

        # But setting user scoped item for themselves should work
        data = {
            'name': 'test_new_key_3',
            'value': 'testvalue3',
            'scope': FULL_USER_SCOPE
        }
        resp = self.app.put_json('/v1/keys/test_new_key_3', data)
        self.assertEqual(resp.status_code, http_client.OK)

        resp = self.app.get('/v1/keys/test_new_key_3?scope=st2kv.user')
        self.assertEqual(resp.status_code, http_client.OK)
        self.assertEqual(resp.json['value'], 'testvalue3')
        self.assertEqual(resp.json['scope'], FULL_USER_SCOPE)
        self.assertEqual(resp.json['user'], 'user1')

    def test_delete_system_scoped_item_non_admin_success(self):
        # Non-admin user can delete any system-scoped item
        self.use_user(self.users['user_1'])

        resp = self.app.get('/v1/keys/%s' % (self.kvps['kvp_1'].name))
        self.assertEqual(resp.status_code, http_client.OK)

        resp = self.app.delete('/v1/keys/%s' % (self.kvps['kvp_1'].name))
        self.assertEqual(resp.status_code, http_client.NO_CONTENT)

        # Verify it has been deleted
        resp = self.app.get('/v1/keys/%s' % (self.kvps['kvp_1'].name), expect_errors=True)
        self.assertEqual(resp.status_code, http_client.NOT_FOUND)

    def test_delete_user_scoped_item_non_admin_scoped_to_itself_success(self):
        # Non-admin user can delete user scoped item scoped to themselves
        self.use_user(self.users['user_1'])

        resp = self.app.get('/v1/keys/%s?scope=st2kv.user' % (self.kvps['kvp_3'].name))
        self.assertEqual(resp.status_code, http_client.OK)

        resp = self.app.delete('/v1/keys/%s?scope=st2kv.user' % (self.kvps['kvp_3'].name))
        self.assertEqual(resp.status_code, http_client.NO_CONTENT)

        # But unable to delete item scoped to other user (user2)
        resp = self.app.delete('/v1/keys/%s?scope=st2kv.user' % (self.kvps['kvp_5'].name),
                               expect_errors=True)
        self.assertEqual(resp.status_code, http_client.NOT_FOUND)

    def test_delete_user_scope_item_aribrary_user_admin_success(self):
        # Admin user can delete user-scoped datastore item scoped to arbitrary user
        self.use_user(self.users['admin'])

        resp = self.app.get('/v1/keys/%s?scope=st2kv.user&user=user1' % (self.kvps['kvp_3'].name))
        self.assertEqual(resp.status_code, http_client.OK)
        resp = self.app.get('/v1/keys/%s?scope=st2kv.user&user=user2' % (self.kvps['kvp_5'].name))
        self.assertEqual(resp.status_code, http_client.OK)

        resp = self.app.delete(
            '/v1/keys/%s?scope=st2kv.user&user=user1' % (self.kvps['kvp_3'].name)
        )
        self.assertEqual(resp.status_code, http_client.NO_CONTENT)
        resp = self.app.delete(
            '/v1/keys/%s?scope=st2kv.user&user=user2' % (self.kvps['kvp_5'].name)
        )
        self.assertEqual(resp.status_code, http_client.NO_CONTENT)

        resp = self.app.delete(
            '/v1/keys/%s?scope=st2kv.user&user=user1' % (self.kvps['kvp_3'].name),
            expect_errors=True
        )
        self.assertEqual(resp.status_code, http_client.NOT_FOUND)
        resp = self.app.delete(
            '/v1/keys/%s?scope=st2kv.user&user=user2' % (self.kvps['kvp_5'].name),
            expect_errors=True
        )

    def test_delete_user_scope_item_non_admin_failure(self):
        # Non admin user can't delete user-scoped items which are not scoped to them
        self.use_user(self.users['user_1'])

        resp = self.app.get('/v1/keys/%s?scope=st2kv.user&user=user2' % (self.kvps['kvp_5'].name),
                            expect_errors=True)
        self.assertEqual(resp.status_code, http_client.FORBIDDEN)
        self.assertTrue('"user" attribute can only be provided by admins' in
                        resp.json['faultstring'])

    def test_get_all_limit_minus_one(self):
        user_db = self.users['observer']
        self.use_user(user_db)

        resp = self.app.get('/v1/keys?limit=-1', expect_errors=True)
        self.assertEqual(resp.status_code, http_client.FORBIDDEN)

        user_db = self.users['admin']
        self.use_user(user_db)

        resp = self.app.get('/v1/keys?limit=-1')
        self.assertEqual(resp.status_code, http_client.OK)

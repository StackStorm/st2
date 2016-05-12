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

from tests import FunctionalTest

KVP = {
    'name': 'keystone_endpoint',
    'value': 'http://127.0.0.1:5000/v3'
}

KVP_2 = {
    'name': 'keystone_version',
    'value': 'v3'
}

KVP_2_USER = {
    'name': 'keystone_version',
    'value': 'user_v3',
    'scope': 'user'
}

KVP_3_USER = {
    'name': 'keystone_endpoint',
    'value': 'http://127.0.1.1:5000/v3',
    'scope': 'user'
}

KVP_4_USER = {
    'name': 'customer_ssn',
    'value': '123-456-7890',
    'secret': True,
    'scope': 'user'
}

KVP_WITH_TTL = {
    'name': 'keystone_endpoint',
    'value': 'http://127.0.0.1:5000/v3',
    'ttl': 10
}

SECRET_KVP = {
    'name': 'secret_key1',
    'value': 'secret_value1',
    'secret': True
}


class TestKeyValuePairController(FunctionalTest):

    def test_get_all(self):
        resp = self.app.get('/v2/keys/system')
        self.assertEqual(resp.status_int, 200)

    def test_get_one(self):
        put_resp = self._do_put('system', 'key1', KVP)
        kvp_id = self._get_kvp_name(put_resp)
        get_resp = self._do_get_one('system', kvp_id)
        self.assertEqual(get_resp.status_int, 200)
        self.assertEqual(self._get_kvp_name(get_resp), kvp_id)
        self._do_delete('system', kvp_id)

    def test_get_all_prefix_filtering(self):
        put_resp1 = self._do_put('system', KVP['name'], KVP)
        put_resp2 = self._do_put('system', KVP_2['name'], KVP_2)
        self.assertEqual(put_resp1.status_int, 200)
        self.assertEqual(put_resp2.status_int, 200)

        # No keys with that prefix
        resp = self.app.get('/v2/keys/system?prefix=something')
        self.assertEqual(resp.json, [])

        # Two keys with the provided prefix
        resp = self.app.get('/v2/keys/system?prefix=keystone')
        self.assertEqual(len(resp.json), 2)

        # One key with the provided prefix
        resp = self.app.get('/v2/keys/system?prefix=keystone_endpoint')
        self.assertEqual(len(resp.json), 1)

        self._do_delete('system', self._get_kvp_name(put_resp1))
        self._do_delete('system', self._get_kvp_name(put_resp2))

    def test_get_one_fail(self):
        resp = self.app.get('/v2/system/keys/1', expect_errors=True)
        self.assertEqual(resp.status_int, 404)

    def test_put(self):
        put_resp = self._do_put('system', 'key1', KVP)
        update_input = put_resp.json
        update_input['value'] = 'http://127.0.0.1:35357/v3'
        put_resp = self._do_put('system', self._get_kvp_name(put_resp), update_input)
        self.assertEqual(put_resp.status_int, 200)
        self._do_delete('system', self._get_kvp_name(put_resp))

    def test_put_with_ttl(self):
        put_resp = self._do_put('system', 'key_with_ttl', KVP_WITH_TTL)
        self.assertEqual(put_resp.status_int, 200)
        get_resp = self.app.get('/v2/keys/system')
        self.assertTrue(get_resp.json[0]['expire_timestamp'])
        self._do_delete('system', self._get_kvp_name(put_resp))

    def test_put_secret(self):
        put_resp = self._do_put('system', 'secret_key1', SECRET_KVP)
        kvp_id = self._get_kvp_name(put_resp)
        get_resp = self._do_get_one('system', kvp_id)
        self.assertTrue(get_resp.json['encrypted'])
        crypto_val = get_resp.json['value']
        self.assertNotEqual(SECRET_KVP['value'], crypto_val)
        self._do_delete('system', self._get_kvp_name(put_resp))

    def test_get_one_secret_no_decrypt(self):
        put_resp = self._do_put('system', 'secret_key1', SECRET_KVP)
        kvp_id = self._get_kvp_name(put_resp)
        get_resp = self.app.get('/v2/keys/system/secret_key1')
        self.assertEqual(get_resp.status_int, 200)
        self.assertEqual(self._get_kvp_name(get_resp), kvp_id)
        self.assertTrue(get_resp.json['secret'])
        self.assertTrue(get_resp.json['encrypted'])
        self._do_delete('system', kvp_id)

    def test_get_one_secret_decrypt(self):
        put_resp = self._do_put('system', 'secret_key1', SECRET_KVP)
        kvp_id = self._get_kvp_name(put_resp)
        get_resp = self.app.get('/v2/keys/system/secret_key1?decrypt=true')
        self.assertEqual(get_resp.status_int, 200)
        self.assertEqual(self._get_kvp_name(get_resp), kvp_id)
        self.assertTrue(get_resp.json['secret'])
        self.assertFalse(get_resp.json['encrypted'])
        self.assertEqual(get_resp.json['value'], SECRET_KVP['value'])
        self._do_delete('system', kvp_id)

    def test_get_all_decrypt(self):
        put_resp = self._do_put('system', 'secret_key1', SECRET_KVP)
        kvp_id_1 = self._get_kvp_name(put_resp)
        put_resp = self._do_put('system', 'key1', KVP)
        kvp_id_2 = self._get_kvp_name(put_resp)
        kvps = {'key1': KVP, 'secret_key1': SECRET_KVP}
        stored_kvps = self.app.get('/v2/keys/system?decrypt=true').json
        self.assertTrue(len(stored_kvps), 2)
        for stored_kvp in stored_kvps:
            self.assertFalse(stored_kvp['encrypted'])
            exp_kvp = kvps.get(stored_kvp['name'])
            self.assertTrue(exp_kvp is not None)
            self.assertEqual(exp_kvp['value'], stored_kvp['value'])
        self._do_delete('system', kvp_id_1)
        self._do_delete('system', kvp_id_2)

    def test_put_delete(self):
        put_resp = self._do_put('system', 'key1', KVP)
        self.assertEqual(put_resp.status_int, 200)
        self._do_delete('system', self._get_kvp_name(put_resp))

    def test_delete(self):
        put_resp = self._do_put('system', 'key1', KVP)
        del_resp = self._do_delete('system', self._get_kvp_name(put_resp))
        self.assertEqual(del_resp.status_int, 204)

    def test_delete_fail(self):
        resp = self._do_delete('user', 'inexistentkey', expect_errors=True)
        self.assertEqual(resp.status_int, 404)

    def test_put_user_scope_and_system_scope_dont_overlap(self):
        self._do_put('system', 'keystone_version', KVP_2)
        self._do_put('user', 'keystone_version', KVP_2_USER)

        get_resp = self._do_get_one('system', 'keystone_version')
        self.assertEqual(get_resp.json['value'], KVP_2['value'])

        get_resp = self._do_get_one('user', 'keystone_version')
        self.assertEqual(get_resp.json['value'], KVP_2_USER['value'])
        self._do_delete('system', 'keystone_version')
        self._do_delete('user', 'keystone_version')

    def test_put_invalid_scope(self):
        put_resp = self.app.put_json('/v2/keys/st2/keystone_version', KVP_2,
                                     expect_errors=True)
        self.assertTrue(put_resp.status_int, 400)

    def test_get_all_with_scope(self):
        self._do_put('system', 'keystone_version', KVP_2)
        self._do_put('user', 'keystone_version', KVP_2_USER)

        get_resp_sys = self.app.get('/v2/keys/system')
        self.assertTrue(len(get_resp_sys.json), 1)
        self.assertEqual(get_resp_sys.json[0]['value'], KVP_2['value'])

        get_resp_sys = self.app.get('/v2/keys/user')
        self.assertTrue(len(get_resp_sys.json), 1)
        self.assertEqual(get_resp_sys.json[0]['value'], KVP_2_USER['value'])

        self._do_delete('system', 'keystone_version')
        self._do_delete('user', 'keystone_version')

    def test_get_all_with_scope_and_prefix_filtering(self):
        self._do_put('user', 'keystone_version', KVP_2_USER)
        self._do_put('user', 'keystone_endpoint', KVP_3_USER)
        self._do_put('user', 'customer_ssn', KVP_4_USER)

        get_prefix = self.app.get('/v2/keys/user?prefix=keystone')
        self.assertEqual(len(get_prefix.json), 2)
        self._do_delete('user', 'keystone_version')
        self._do_delete('user', 'keystone_endpoint')
        self._do_delete('user', 'customer_ssn')

    @staticmethod
    def _get_kvp_name(resp):
        return resp.json['name']

    def _do_get_one(self, scope, kvp_id, expect_errors=False):
        return self.app.get('/v2/keys/%s/%s' % (scope, kvp_id), expect_errors=expect_errors)

    def _do_put(self, scope, kvp_id, kvp, expect_errors=False):
        return self.app.put_json('/v2/keys/%s/%s' % (scope, kvp_id), kvp, expect_errors=expect_errors)

    def _do_delete(self, scope, kvp_id, expect_errors=False):
        return self.app.delete('/v2/keys/%s/%s' % (scope, kvp_id), expect_errors=expect_errors)

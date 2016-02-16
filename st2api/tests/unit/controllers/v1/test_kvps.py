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

KVP_WITH_TTL = {
    'name': 'keystone_endpoint',
    'value': 'http://127.0.0.1:5000/v3',
    'ttl': 10
}


class TestKeyValuePairController(FunctionalTest):

    def test_get_all(self):
        resp = self.app.get('/v1/keys')
        self.assertEqual(resp.status_int, 200)

    def test_get_one(self):
        put_resp = self.__do_put('key1', KVP)
        kvp_id = self.__get_kvp_id(put_resp)
        get_resp = self.__do_get_one(kvp_id)
        self.assertEqual(get_resp.status_int, 200)
        self.assertEqual(self.__get_kvp_id(get_resp), kvp_id)
        self.__do_delete(kvp_id)

    def test_get_all_prefix_filtering(self):
        put_resp1 = self.__do_put(KVP['name'], KVP)
        put_resp2 = self.__do_put(KVP_2['name'], KVP_2)
        self.assertEqual(put_resp1.status_int, 200)
        self.assertEqual(put_resp2.status_int, 200)

        # No keys with that prefix
        resp = self.app.get('/v1/keys?prefix=something')
        self.assertEqual(resp.json, [])

        # Two keys with the provided prefix
        resp = self.app.get('/v1/keys?prefix=keystone')
        self.assertEqual(len(resp.json), 2)

        # One key with the provided prefix
        resp = self.app.get('/v1/keys?prefix=keystone_endpoint')
        self.assertEqual(len(resp.json), 1)

        self.__do_delete(self.__get_kvp_id(put_resp1))
        self.__do_delete(self.__get_kvp_id(put_resp2))

    def test_get_one_fail(self):
        resp = self.app.get('/v1/keys/1', expect_errors=True)
        self.assertEqual(resp.status_int, 404)

    def test_put(self):
        put_resp = self.__do_put('key1', KVP)
        update_input = put_resp.json
        update_input['value'] = 'http://127.0.0.1:35357/v3'
        put_resp = self.__do_put(self.__get_kvp_id(put_resp), update_input)
        self.assertEqual(put_resp.status_int, 200)
        self.__do_delete(self.__get_kvp_id(put_resp))

    def test_put_with_ttl(self):
        put_resp = self.__do_put('key_with_ttl', KVP_WITH_TTL)
        self.assertEqual(put_resp.status_int, 200)
        get_resp = self.app.get('/v1/keys')
        self.assertTrue(get_resp.json[0]['expire_timestamp'])
        self.__do_delete(self.__get_kvp_id(put_resp))

    def test_put_delete(self):
        put_resp = self.__do_put('key1', KVP)
        self.assertEqual(put_resp.status_int, 200)
        self.__do_delete(self.__get_kvp_id(put_resp))

    def test_delete(self):
        put_resp = self.__do_put('key1', KVP)
        del_resp = self.__do_delete(self.__get_kvp_id(put_resp))
        self.assertEqual(del_resp.status_int, 204)

    def test_delete_fail(self):
        resp = self.__do_delete('inexistentkey', expect_errors=True)
        self.assertEqual(resp.status_int, 404)

    @staticmethod
    def __get_kvp_id(resp):
        return resp.json['name']

    def __do_get_one(self, kvp_id, expect_errors=False):
        return self.app.get('/v1/keys/%s' % kvp_id, expect_errors=expect_errors)

    def __do_put(self, kvp_id, kvp, expect_errors=False):
        return self.app.put_json('/v1/keys/%s' % kvp_id, kvp, expect_errors=expect_errors)

    def __do_delete(self, kvp_id, expect_errors=False):
        return self.app.delete('/v1/keys/%s' % kvp_id, expect_errors=expect_errors)

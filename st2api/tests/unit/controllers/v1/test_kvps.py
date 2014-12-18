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
    'value': 'http://localhost:5000/v3'
}


class TestKeyValuePairController(FunctionalTest):

    def test_get_all(self):
        resp = self.app.get('/v1/keys')
        self.assertEqual(resp.status_int, 200)

    def test_get_one(self):
        post_resp = self.__do_post(KVP)
        kvp_id = self.__get_kvp_id(post_resp)
        get_resp = self.__do_get_one(kvp_id)
        self.assertEqual(get_resp.status_int, 200)
        self.assertEqual(self.__get_kvp_id(get_resp), kvp_id)
        self.__do_delete(kvp_id)

    def test_get_one_fail(self):
        resp = self.app.get('/v1/keys/1', expect_errors=True)
        self.assertEqual(resp.status_int, 404)

    def test_post_delete(self):
        post_resp = self.__do_post(KVP)
        self.assertEqual(post_resp.status_int, 201)
        self.__do_delete(self.__get_kvp_id(post_resp))

    def test_put(self):
        post_resp = self.__do_post(KVP)
        update_input = post_resp.json
        update_input['value'] = 'http://localhost:35357/v3'
        put_resp = self.__do_put(self.__get_kvp_id(post_resp), update_input)
        self.assertEqual(put_resp.status_int, 200)
        self.__do_delete(self.__get_kvp_id(put_resp))

    def test_put_fail(self):
        post_resp = self.__do_post(KVP)
        update_input = post_resp.json
        put_resp = self.__do_put(1, update_input, expect_errors=True)
        self.assertEqual(put_resp.status_int, 404)
        self.__do_delete(self.__get_kvp_id(post_resp))

    def test_delete(self):
        post_resp = self.__do_post(KVP)
        del_resp = self.__do_delete(self.__get_kvp_id(post_resp))
        self.assertEqual(del_resp.status_int, 204)

    @staticmethod
    def __get_kvp_id(resp):
        return resp.json['id']

    def __do_get_one(self, kvp_id, expect_errors=False):
        return self.app.get('/v1/keys/%s' % kvp_id, expect_errors=expect_errors)

    def __do_post(self, kvp, expect_errors=False):
        return self.app.post_json('/v1/keys', kvp, expect_errors=expect_errors)

    def __do_put(self, kvp_id, kvp, expect_errors=False):
        return self.app.put_json('/v1/keys/%s' % kvp_id, kvp, expect_errors=expect_errors)

    def __do_delete(self, kvp_id, expect_errors=False):
        return self.app.delete('/v1/keys/%s' % kvp_id, expect_errors=expect_errors)

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

from st2api.controllers.v1.triggers import TriggerTypeController

from st2tests.api import FunctionalTest
from st2tests.api import APIControllerWithIncludeAndExcludeFilterTestCase

http_client = six.moves.http_client

TRIGGER_0 = {
    'name': 'st2.test.triggertype0',
    'pack': 'dummy_pack_1',
    'description': 'test trigger',
    'payload_schema': {'tp1': None, 'tp2': None, 'tp3': None},
    'parameters_schema': {}
}
TRIGGER_1 = {
    'name': 'st2.test.triggertype1',
    'pack': 'dummy_pack_2',
    'description': 'test trigger',
    'payload_schema': {'tp1': None, 'tp2': None, 'tp3': None},
}
TRIGGER_2 = {
    'name': 'st2.test.triggertype3',
    'pack': 'dummy_pack_3',
    'description': 'test trigger',
    'payload_schema': {'tp1': None, 'tp2': None, 'tp3': None},
    'parameters_schema': {'param1': {'type': 'object'}}
}


class TriggerTypeControllerTestCase(FunctionalTest,
                                    APIControllerWithIncludeAndExcludeFilterTestCase):
    get_all_path = '/v1/triggertypes'
    controller_cls = TriggerTypeController
    include_attribute_field_name = 'payload_schema'
    exclude_attribute_field_name = 'parameters_schema'

    @classmethod
    def setUpClass(cls):
        # super's setUpClass does the following:
        #  - create DB connections, sets up a fresh DB etc.
        #  - creates all the controllers by instantiating the pecan app.
        # The WebHookController ends up registering a TriggerType in its  __init__
        # which is why when this test is run individually it simply falls apart.
        # When run in a suite the pecan app creation is somehow optimized and since
        # this is not the first test to run its all good as some other test performs
        # the DB cleanup. This is the unfortunate story of why these two lines in this
        # exact order are needed. There are perhaps other ways to fix the problem
        # however this is the most localized solution for now.
        super(TriggerTypeControllerTestCase, cls).setUpClass()
        cls._establish_connection_and_re_create_db()

    def test_get_all(self):
        post_resp = self.__do_post(TRIGGER_0)
        trigger_id_0 = self.__get_trigger_id(post_resp)
        post_resp = self.__do_post(TRIGGER_1)
        trigger_id_1 = self.__get_trigger_id(post_resp)
        resp = self.app.get('/v1/triggertypes')
        self.assertEqual(resp.status_int, http_client.OK)
        self.assertEqual(len(resp.json), 2, 'Get all failure.')

        # ?pack query filter
        resp = self.app.get('/v1/triggertypes?pack=doesnt-exist-invalid')
        self.assertEqual(resp.status_int, http_client.OK)
        self.assertEqual(len(resp.json), 0)

        resp = self.app.get('/v1/triggertypes?pack=%s' % (TRIGGER_0['pack']))
        self.assertEqual(resp.status_int, http_client.OK)
        self.assertEqual(len(resp.json), 1)
        self.assertEqual(resp.json[0]['pack'], TRIGGER_0['pack'])

        self.__do_delete(trigger_id_0)
        self.__do_delete(trigger_id_1)

    def test_get_one(self):
        post_resp = self.__do_post(TRIGGER_1)
        trigger_id = self.__get_trigger_id(post_resp)
        get_resp = self.__do_get_one(trigger_id)
        self.assertEqual(get_resp.status_int, http_client.OK)
        self.assertEqual(self.__get_trigger_id(get_resp), trigger_id)
        self.__do_delete(trigger_id)

    def test_get_one_fail(self):
        resp = self.__do_get_one('1')
        self.assertEqual(resp.status_int, http_client.NOT_FOUND)

    def test_post(self):
        post_resp = self.__do_post(TRIGGER_1)
        self.assertEqual(post_resp.status_int, http_client.CREATED)
        self.__do_delete(self.__get_trigger_id(post_resp))

    def test_post_with_params(self):
        post_resp = self.__do_post(TRIGGER_2)
        self.assertEqual(post_resp.status_int, http_client.CREATED)
        self.__do_delete(self.__get_trigger_id(post_resp))

    def test_post_duplicate(self):
        post_resp = self.__do_post(TRIGGER_1)
        org_id = self.__get_trigger_id(post_resp)
        self.assertEqual(post_resp.status_int, http_client.CREATED)
        post_resp_2 = self.__do_post(TRIGGER_1)
        self.assertEqual(post_resp_2.status_int, http_client.CONFLICT)
        self.assertEqual(post_resp_2.json['conflict-id'], org_id)
        self.__do_delete(org_id)

    def test_put(self):
        post_resp = self.__do_post(TRIGGER_1)
        update_input = post_resp.json
        update_input['description'] = 'updated description.'
        put_resp = self.__do_put(self.__get_trigger_id(post_resp), update_input)
        self.assertEqual(put_resp.status_int, http_client.OK)
        self.__do_delete(self.__get_trigger_id(put_resp))

    def test_put_fail(self):
        post_resp = self.__do_post(TRIGGER_1)
        update_input = post_resp.json
        # If the id in the URL is incorrect the update will fail since id in the body is ignored.
        put_resp = self.__do_put(1, update_input)
        self.assertEqual(put_resp.status_int, http_client.NOT_FOUND)
        self.__do_delete(self.__get_trigger_id(post_resp))

    def test_delete(self):
        post_resp = self.__do_post(TRIGGER_1)
        del_resp = self.__do_delete(self.__get_trigger_id(post_resp))
        self.assertEqual(del_resp.status_int, http_client.NO_CONTENT)

    def _insert_mock_models(self):
        trigger_1_id = self.__get_trigger_id(self.__do_post(TRIGGER_0))
        trigger_2_id = self.__get_trigger_id(self.__do_post(TRIGGER_1))

        return [trigger_1_id, trigger_2_id]

    def _do_delete(self, trigger_id):
        return self.__do_delete(trigger_id=trigger_id)

    @staticmethod
    def __get_trigger_id(resp):
        return resp.json['id']

    def __do_get_one(self, trigger_id):
        return self.app.get('/v1/triggertypes/%s' % trigger_id, expect_errors=True)

    def __do_post(self, trigger):
        return self.app.post_json('/v1/triggertypes', trigger, expect_errors=True)

    def __do_put(self, trigger_id, trigger):
        return self.app.put_json('/v1/triggertypes/%s' % trigger_id, trigger, expect_errors=True)

    def __do_delete(self, trigger_id):
        return self.app.delete('/v1/triggertypes/%s' % trigger_id)

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

import mock
import pecan
import random
import string
import unittest

from oslo_config import cfg

from st2common.constants.secrets import MASKED_ATTRIBUTE_VALUE
from st2common.models.db.auth import UserDB
from st2common.persistence.auth import ApiKey
from st2tests.fixturesloader import FixturesLoader
from tests import FunctionalTest

FIXTURES_PACK = 'generic'

TEST_MODELS = {
    'apikeys': ['apikey1.yaml', 'apikey2.yaml', 'apikey3.yaml']
}


USERNAME = ''.join(random.choice(string.lowercase) for i in range(10))
PECAN_CONTEXT = {
    'auth': {
        'user': UserDB(name=USERNAME)
    }
}

# Hardcoded keys matching the fixtures. Lazy way to workound one-way hash and still use fixtures.
KEY1_KEY = "1234"
KEY2_KEY = "5678"
KEY3_KEY = "9012"


class TestApiKeyController(FunctionalTest):

    apikey1 = None
    apikey2 = None
    apikey3 = None

    @classmethod
    def setUpClass(cls):
        super(TestApiKeyController, cls).setUpClass()

        cfg.CONF.set_override(name='mask_secrets', override=True, group='api')
        cfg.CONF.set_override(name='mask_secrets', override=True, group='log')

        models = FixturesLoader().save_fixtures_to_db(fixtures_pack=FIXTURES_PACK,
                                                      fixtures_dict=TEST_MODELS)
        cls.apikey1 = models['apikeys']['apikey1.yaml']
        cls.apikey2 = models['apikeys']['apikey2.yaml']
        cls.apikey3 = models['apikeys']['apikey3.yaml']

    def test_get_all(self):
        resp = self.app.get('/v1/apikeys')
        self.assertEqual(resp.status_int, 200)
        self.assertEqual(len(resp.json), 3, '/v1/apikeys did not return all apikeys.')

        retrieved_ids = [apikey['id'] for apikey in resp.json]

        self.assertEqual(retrieved_ids,
                         [str(self.apikey1.id), str(self.apikey2.id), str(self.apikey3.id)],
                         'Incorrect api keys retrieved.')

    def test_get_one_by_id(self):
        resp = self.app.get('/v1/apikeys/%s' % self.apikey1.id)
        self.assertEqual(resp.status_int, 200)
        self.assertEqual(resp.json['id'], str(self.apikey1.id),
                         'Incorrect api key retrieved.')
        self.assertEqual(resp.json['key_hash'], MASKED_ATTRIBUTE_VALUE,
                         'Key should be masked.')

    def test_get_one_by_key(self):
        # key1
        resp = self.app.get('/v1/apikeys/%s' % KEY1_KEY)
        self.assertEqual(resp.status_int, 200)
        self.assertEqual(resp.json['id'], str(self.apikey1.id),
                         'Incorrect api key retrieved.')
        self.assertEqual(resp.json['key_hash'], MASKED_ATTRIBUTE_VALUE,
                         'Key should be masked.')
        # key2
        resp = self.app.get('/v1/apikeys/%s' % KEY2_KEY)
        self.assertEqual(resp.status_int, 200)
        self.assertEqual(resp.json['id'], str(self.apikey2.id),
                         'Incorrect api key retrieved.')
        self.assertEqual(resp.json['key_hash'], MASKED_ATTRIBUTE_VALUE,
                         'Key should be masked.')
        # key3
        resp = self.app.get('/v1/apikeys/%s' % KEY3_KEY)
        self.assertEqual(resp.status_int, 200)
        self.assertEqual(resp.json['id'], str(self.apikey3.id),
                         'Incorrect api key retrieved.')
        self.assertEqual(resp.json['key_hash'], MASKED_ATTRIBUTE_VALUE,
                         'Key should be masked.')

    def test_get_show_secrets(self):

        resp = self.app.get('/v1/apikeys/?show_secrets=True')
        self.assertEqual(resp.status_int, 200)
        for key in resp.json:
            self.assertNotEqual(key['key_hash'], MASKED_ATTRIBUTE_VALUE)
            self.assertNotEqual(key['uid'], MASKED_ATTRIBUTE_VALUE)

    def test_post_delete_key(self):
        api_key = {
            'user': 'herge'
        }
        resp1 = self.app.post_json('/v1/apikeys/', api_key)
        self.assertEqual(resp1.status_int, 201)
        self.assertTrue(resp1.json['key'], 'Key should be non-None.')
        self.assertNotEqual(resp1.json['key'], MASKED_ATTRIBUTE_VALUE,
                            'Key should not be masked.')

        # should lead to creation of another key
        resp2 = self.app.post_json('/v1/apikeys/', api_key)
        self.assertEqual(resp2.status_int, 201)
        self.assertTrue(resp2.json['key'], 'Key should be non-None.')
        self.assertNotEqual(resp2.json['key'], MASKED_ATTRIBUTE_VALUE, 'Key should not be masked.')
        self.assertNotEqual(resp1.json['key'], resp2.json['key'], 'Should be different')

        resp = self.app.delete('/v1/apikeys/%s' % resp1.json['id'])
        self.assertEqual(resp.status_int, 204)

        resp = self.app.delete('/v1/apikeys/%s' % resp2.json['key'])
        self.assertEqual(resp.status_int, 204)

    def test_post_delete_same_key_hash(self):
        api_key = {
            'user': 'herge',
            'key_hash': 'ABCDE'
        }
        resp1 = self.app.post_json('/v1/apikeys/', api_key)
        self.assertEqual(resp1.status_int, 201)
        self.assertEqual(resp1.json['key'], None, 'Key should be None.')

        # drop into the DB since API will be masking this value.
        api_key_db = ApiKey.get_by_id(resp1.json['id'])

        self.assertEqual(api_key_db.key_hash, api_key['key_hash'], 'Key_hash should match.')
        self.assertEqual(api_key_db.user, api_key['user'], 'Key_hash should match.')

        resp = self.app.delete('/v1/apikeys/%s' % resp1.json['id'])
        self.assertEqual(resp.status_int, 204)

    def test_put_api_key(self):
        resp = self.app.get('/v1/apikeys/%s' % self.apikey1.id)
        self.assertEqual(resp.status_int, 200)

        update_input = resp.json
        update_input['enabled'] = not update_input['enabled']
        put_resp = self.app.put_json('/v1/apikeys/%s' % self.apikey1.id, update_input,
                                     expect_errors=True)
        self.assertEqual(put_resp.status_int, 200)
        self.assertEqual(put_resp.json['enabled'], not resp.json['enabled'])

        update_input = put_resp.json
        update_input['enabled'] = not update_input['enabled']
        put_resp = self.app.put_json('/v1/apikeys/%s' % self.apikey1.id, update_input,
                                     expect_errors=True)
        self.assertEqual(put_resp.status_int, 200)
        self.assertEqual(put_resp.json['enabled'], resp.json['enabled'])

    def test_put_api_key_fail(self):
        resp = self.app.get('/v1/apikeys/%s' % self.apikey1.id)
        self.assertEqual(resp.status_int, 200)

        update_input = resp.json
        update_input['key_hash'] = '1'
        put_resp = self.app.put_json('/v1/apikeys/%s' % self.apikey1.id, update_input,
                                     expect_errors=True)
        self.assertEqual(put_resp.status_int, 400)
        self.assertTrue(put_resp.json['faultstring'])

    def test_post_no_user_fail(self):
        self.app.post_json('/v1/apikeys/', {}, expect_errors=True)

    @unittest.skip
    def test_post_no_user_success(self):
        type(pecan.request).context = mock.PropertyMock(return_value=PECAN_CONTEXT)
        try:
            resp = self.app.post_json('/v1/apikeys/', {})
            self.assertEqual(resp.status_int, 201)
            self.assertTrue(resp.json['key'], 'Key should be non-None.')
            self.assertEqual(resp.json['user'], USERNAME, 'User should be from auth context.')

            resp = self.app.delete('/v1/apikeys/%s' % resp.json['id'])
            self.assertEqual(resp.status_int, 204)
        finally:
            type(pecan.request).context = {}

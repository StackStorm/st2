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

from st2common.models.db.auth import UserDB
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


class TestApiKeyController(FunctionalTest):

    apikey1 = None
    apikey2 = None
    apikey3 = None

    @classmethod
    def setUpClass(cls):
        super(TestApiKeyController, cls).setUpClass()
        models = FixturesLoader().save_fixtures_to_db(fixtures_pack=FIXTURES_PACK,
                                                      fixtures_dict=TEST_MODELS)
        cls.apikey1 = models['apikeys']['apikey1.yaml']
        cls.apikey2 = models['apikeys']['apikey2.yaml']
        cls.apikey3 = models['apikeys']['apikey3.yaml']

    def test_get_all(self):
        resp = self.app.get('/v1/apikeys')
        self.assertEqual(resp.status_int, 200)
        self.assertEqual(len(resp.json), 3, '/v1/apikeys did not return all apikeys.')

        retrieved_keys = [apikey['key'] for apikey in resp.json]

        self.assertEqual(retrieved_keys,
                         [self.apikey1.key, self.apikey2.key, self.apikey3.key],
                         'Incorrect api keys retrieved.')

    def test_get_one_by_id(self):
        resp = self.app.get('/v1/apikeys/%s' % self.apikey1.id)
        self.assertEqual(resp.status_int, 200)
        self.assertEqual(resp.json['key'], self.apikey1.key,
                         'Incorrect api key retrieved.')

    def test_get_one_by_key(self):
        resp = self.app.get('/v1/apikeys/%s' % self.apikey2.key)
        self.assertEqual(resp.status_int, 200)
        self.assertEqual(resp.json['id'], str(self.apikey2.id),
                         'Incorrect api key retrieved.')

    def test_post_delete_key(self):
        api_key = {
            'user': 'herge'
        }
        resp = self.app.post_json('/v1/apikeys/', api_key)
        self.assertEqual(resp.status_int, 201)
        self.assertTrue(resp.json['key'], 'Key should be non-None.')

        resp = self.app.delete('/v1/apikeys/%s' % resp.json['id'])
        self.assertEqual(resp.status_int, 204)

        resp = self.app.post_json('/v1/apikeys/', api_key)
        self.assertEqual(resp.status_int, 201)
        self.assertTrue(resp.json['key'], 'Key should be non-None.')

        resp = self.app.delete('/v1/apikeys/%s' % resp.json['key'])
        self.assertEqual(resp.status_int, 204)

    def test_post_no_user_fail(self):
        self.app.post_json('/v1/apikeys/', {}, expect_errors=True)

    def test_post_no_user_success(self):
        type(pecan.request).context = mock.PropertyMock(return_value=PECAN_CONTEXT)
        resp = self.app.post_json('/v1/apikeys/', {})
        self.assertEqual(resp.status_int, 201)
        self.assertTrue(resp.json['key'], 'Key should be non-None.')
        self.assertEqual(resp.json['user'], USERNAME, 'User should be from auth context.')

        resp = self.app.delete('/v1/apikeys/%s' % resp.json['id'])
        self.assertEqual(resp.status_int, 204)

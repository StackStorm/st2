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

import uuid
import datetime

import bson
import mock

from st2tests.api import FunctionalTest
from st2common.util import date as date_utils
from st2common.models.db.auth import ApiKeyDB, TokenDB, UserDB
from st2common.persistence.auth import ApiKey, Token, User
from st2common.exceptions.auth import TokenNotFoundError
from st2tests.fixturesloader import FixturesLoader

OBJ_ID = bson.ObjectId()
USER = 'stanley'
USER_DB = UserDB(name=USER)
TOKEN = uuid.uuid4().hex
NOW = date_utils.get_datetime_utc_now()
FUTURE = NOW + datetime.timedelta(seconds=300)
PAST = NOW + datetime.timedelta(seconds=-300)


class TestTokenBasedAuth(FunctionalTest):

    enable_auth = True

    @mock.patch.object(
        Token, 'get',
        mock.Mock(return_value=TokenDB(id=OBJ_ID, user=USER, token=TOKEN, expiry=FUTURE)))
    @mock.patch.object(User, 'get_by_name', mock.Mock(return_value=USER_DB))
    def test_token_validation_token_in_headers(self):
        response = self.app.get('/v1/actions', headers={'X-Auth-Token': TOKEN},
                                expect_errors=False)
        self.assertTrue('application/json' in response.headers['content-type'])
        self.assertEqual(response.status_int, 200)

    @mock.patch.object(
        Token, 'get',
        mock.Mock(return_value=TokenDB(id=OBJ_ID, user=USER, token=TOKEN, expiry=FUTURE)))
    @mock.patch.object(User, 'get_by_name', mock.Mock(return_value=USER_DB))
    def test_token_validation_token_in_query_params(self):
        response = self.app.get('/v1/actions?x-auth-token=%s' % (TOKEN), expect_errors=False)
        self.assertTrue('application/json' in response.headers['content-type'])
        self.assertEqual(response.status_int, 200)

    @mock.patch.object(
        Token, 'get',
        mock.Mock(return_value=TokenDB(id=OBJ_ID, user=USER, token=TOKEN, expiry=FUTURE)))
    @mock.patch.object(User, 'get_by_name', mock.Mock(return_value=USER_DB))
    def test_token_validation_token_in_cookies(self):
        response = self.app.get('/v1/actions', headers={'X-Auth-Token': TOKEN},
                                expect_errors=False)
        self.assertTrue('application/json' in response.headers['content-type'])
        self.assertEqual(response.status_int, 200)

        with mock.patch.object(self.app.cookiejar, 'clear', return_value=None):
            response = self.app.get('/v1/actions', expect_errors=False)
        self.assertTrue('application/json' in response.headers['content-type'])
        self.assertEqual(response.status_int, 200)

    @mock.patch.object(
        Token, 'get',
        mock.Mock(return_value=TokenDB(id=OBJ_ID, user=USER, token=TOKEN, expiry=PAST)))
    def test_token_expired(self):
        response = self.app.get('/v1/actions', headers={'X-Auth-Token': TOKEN},
                                expect_errors=True)
        self.assertTrue('application/json' in response.headers['content-type'])
        self.assertEqual(response.status_int, 401)

    @mock.patch.object(
        Token, 'get', mock.MagicMock(side_effect=TokenNotFoundError()))
    def test_token_not_found(self):
        response = self.app.get('/v1/actions', headers={'X-Auth-Token': TOKEN},
                                expect_errors=True)
        self.assertTrue('application/json' in response.headers['content-type'])
        self.assertEqual(response.status_int, 401)

    def test_token_not_provided(self):
        response = self.app.get('/v1/actions', expect_errors=True)
        self.assertTrue('application/json' in response.headers['content-type'])
        self.assertEqual(response.status_int, 401)


FIXTURES_PACK = 'generic'

TEST_MODELS = {
    'apikeys': ['apikey1.yaml', 'apikey_disabled.yaml']
}

# Hardcoded keys matching the fixtures. Lazy way to workound one-way hash and still use fixtures.
KEY1_KEY = "1234"
DISABLED_KEY = "0000"


class TestApiKeyBasedAuth(FunctionalTest):

    enable_auth = True

    apikey1 = None
    apikey_disabled = None

    @classmethod
    def setUpClass(cls):
        super(TestApiKeyBasedAuth, cls).setUpClass()
        models = FixturesLoader().save_fixtures_to_db(fixtures_pack=FIXTURES_PACK,
                                                      fixtures_dict=TEST_MODELS)
        cls.apikey1 = models['apikeys']['apikey1.yaml']
        cls.apikey_disabled = models['apikeys']['apikey_disabled.yaml']

    @mock.patch.object(User, 'get_by_name', mock.Mock(return_value=UserDB(name='bill')))
    def test_apikey_validation_apikey_in_headers(self):
        response = self.app.get('/v1/actions', headers={'St2-Api-key': KEY1_KEY},
                                expect_errors=False)
        self.assertTrue('application/json' in response.headers['content-type'])
        self.assertEqual(response.status_int, 200)

    @mock.patch.object(User, 'get_by_name', mock.Mock(return_value=UserDB(name='bill')))
    def test_apikey_validation_apikey_in_query_params(self):
        response = self.app.get('/v1/actions?st2-api-key=%s' % (KEY1_KEY), expect_errors=False)
        self.assertTrue('application/json' in response.headers['content-type'])
        self.assertEqual(response.status_int, 200)

    @mock.patch.object(User, 'get_by_name', mock.Mock(return_value=UserDB(name='bill')))
    def test_apikey_validation_apikey_in_cookies(self):
        response = self.app.get('/v1/actions', headers={'St2-Api-key': KEY1_KEY},
                                expect_errors=False)
        self.assertTrue('application/json' in response.headers['content-type'])
        self.assertEqual(response.status_int, 200)

        with mock.patch.object(self.app.cookiejar, 'clear', return_value=None):
            response = self.app.get('/v1/actions', expect_errors=True)
        self.assertEqual(response.status_int, 401)
        self.assertEqual(response.json_body['faultstring'],
                         'Unauthorized - One of Token or API key required.')

    def test_apikey_disabled(self):
        response = self.app.get('/v1/actions', headers={'St2-Api-key': DISABLED_KEY},
                                expect_errors=True)
        self.assertTrue('application/json' in response.headers['content-type'])
        self.assertEqual(response.status_int, 401)
        self.assertEqual(response.json_body['faultstring'], 'Unauthorized - API key is disabled.')

    def test_apikey_not_found(self):
        response = self.app.get('/v1/actions', headers={'St2-Api-key': 'UNKNOWN'},
                                expect_errors=True)
        self.assertTrue('application/json' in response.headers['content-type'])
        self.assertEqual(response.status_int, 401)
        self.assertRegexpMatches(response.json_body['faultstring'],
                                 '^Unauthorized - ApiKey with key_hash=([a-zA-Z0-9]+) not found.$')

    @mock.patch.object(
        Token, 'get',
        mock.Mock(return_value=TokenDB(id=OBJ_ID, user=USER, token=TOKEN, expiry=FUTURE)))
    @mock.patch.object(
        ApiKey, 'get',
        mock.Mock(return_value=ApiKeyDB(user=USER, key_hash=KEY1_KEY, enabled=True)))
    @mock.patch.object(User, 'get_by_name', mock.Mock(return_value=USER_DB))
    def test_multiple_auth_sources(self):
        response = self.app.get('/v1/actions',
                                headers={'X-Auth-Token': TOKEN, 'St2-Api-key': KEY1_KEY},
                                expect_errors=True)
        self.assertTrue('application/json' in response.headers['content-type'])
        self.assertEqual(response.status_int, 200)

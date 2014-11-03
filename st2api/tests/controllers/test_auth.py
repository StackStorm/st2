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

from tests import AuthMiddlewareTest
from st2common.util import isotime
from st2common.models.db.access import TokenDB
from st2common.persistence.access import Token
from st2common.exceptions.access import TokenNotFoundError


OBJ_ID = bson.ObjectId()
USER = 'stanley'
TOKEN = uuid.uuid4().hex
NOW = isotime.add_utc_tz(datetime.datetime.utcnow())
FUTURE = NOW + datetime.timedelta(seconds=300)
PAST = NOW + datetime.timedelta(seconds=-300)


class TestTokenValidation(AuthMiddlewareTest):

    @mock.patch.object(
        Token, 'get',
        mock.Mock(return_value=TokenDB(id=OBJ_ID, user=USER, token=TOKEN, expiry=FUTURE)))
    def test_token_validation(self):
        response = self.app.get('/actions', headers={'X-Auth-Token': TOKEN}, expect_errors=False)
        self.assertEqual(response.status_int, 200)

    @mock.patch.object(
        Token, 'get',
        mock.Mock(return_value=TokenDB(id=OBJ_ID, user=USER, token=TOKEN, expiry=PAST)))
    def test_token_expired(self):
        response = self.app.get('/actions', headers={'X-Auth-Token': TOKEN}, expect_errors=True)
        self.assertEqual(response.status_int, 401)

    @mock.patch.object(
        Token, 'get', mock.MagicMock(side_effect=TokenNotFoundError()))
    def test_token_not_found(self):
        response = self.app.get('/actions', headers={'X-Auth-Token': TOKEN}, expect_errors=True)
        self.assertEqual(response.status_int, 401)

    def test_token_not_provided(self):
        response = self.app.get('/actions', expect_errors=True)
        self.assertEqual(response.status_int, 401)

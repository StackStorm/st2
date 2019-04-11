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

import bson
import copy
import datetime
import mock
import uuid

try:
    import simplejson as json
except ImportError:
    import json

import st2common.validators.api.action as action_validator
from st2common.util import date as date_utils
from st2common.models.db.auth import TokenDB
from st2common.models.db.auth import UserDB
from st2common.persistence.auth import Token
from st2common.persistence.auth import User
from st2common.transport.publishers import PoolPublisher
from st2tests.api import SUPER_SECRET_PARAMETER
from st2tests.fixturesloader import FixturesLoader
from st2tests.api import FunctionalTest


ACTION_1 = {
    'name': 'st2.dummy.action1',
    'description': 'test description',
    'enabled': True,
    'entry_point': '/tmp/test/action1.sh',
    'pack': 'sixpack',
    'runner_type': 'remote-shell-cmd',
    'parameters': {
        'a': {
            'type': 'string',
            'default': 'abc'
        },
        'b': {
            'type': 'number',
            'default': 123
        },
        'c': {
            'type': 'number',
            'default': 123,
            'immutable': True
        },
        'd': {
            'type': 'string',
            'secret': True
        }
    }
}

LIVE_ACTION_1 = {
    'action': 'sixpack.st2.dummy.action1',
    'parameters': {
        'hosts': 'localhost',
        'cmd': 'uname -a',
        'd': SUPER_SECRET_PARAMETER
    }
}

# NOTE: We use a longer expiry time because this variable is initialized on module import (aka
# when nosetests or similar imports this module before running the tests.
# Depending on when the import happens and when the tests actually run, token could already expire
# by that time and the tests would fail.
NOW = date_utils.get_datetime_utc_now()
EXPIRY = NOW + datetime.timedelta(seconds=1000)
SYS_TOKEN = TokenDB(id=bson.ObjectId(), user='system', token=uuid.uuid4().hex, expiry=EXPIRY)
USR_TOKEN = TokenDB(id=bson.ObjectId(), user='tokenuser', token=uuid.uuid4().hex, expiry=EXPIRY)

FIXTURES_PACK = 'generic'
FIXTURES = {
    'users': ['system_user.yaml', 'token_user.yaml']
}


def mock_get_token(*args, **kwargs):
    if args[0] == SYS_TOKEN.token:
        return SYS_TOKEN
    return USR_TOKEN


@mock.patch.object(PoolPublisher, 'publish', mock.MagicMock())
class ActionExecutionControllerTestCaseAuthEnabled(FunctionalTest):

    enable_auth = True

    @classmethod
    @mock.patch.object(
        Token, 'get',
        mock.MagicMock(side_effect=mock_get_token))
    @mock.patch.object(User, 'get_by_name', mock.MagicMock(side_effect=UserDB))
    @mock.patch.object(action_validator, 'validate_action', mock.MagicMock(
        return_value=True))
    def setUpClass(cls):
        super(ActionExecutionControllerTestCaseAuthEnabled, cls).setUpClass()
        cls.action = copy.deepcopy(ACTION_1)
        headers = {'content-type': 'application/json', 'X-Auth-Token': str(SYS_TOKEN.token)}
        post_resp = cls.app.post_json('/v1/actions', cls.action, headers=headers)
        cls.action['id'] = post_resp.json['id']

        FixturesLoader().save_fixtures_to_db(fixtures_pack=FIXTURES_PACK,
                                             fixtures_dict=FIXTURES)

    @classmethod
    @mock.patch.object(
        Token, 'get',
        mock.MagicMock(side_effect=mock_get_token))
    def tearDownClass(cls):
        headers = {'content-type': 'application/json', 'X-Auth-Token': str(SYS_TOKEN.token)}
        cls.app.delete('/v1/actions/%s' % cls.action['id'], headers=headers)
        super(ActionExecutionControllerTestCaseAuthEnabled, cls).tearDownClass()

    def _do_post(self, liveaction, *args, **kwargs):
        return self.app.post_json('/v1/executions', liveaction, *args, **kwargs)

    @mock.patch.object(
        Token, 'get',
        mock.MagicMock(side_effect=mock_get_token))
    def test_post_with_st2_context_in_headers(self):
        headers = {'content-type': 'application/json', 'X-Auth-Token': str(USR_TOKEN.token)}
        resp = self._do_post(copy.deepcopy(LIVE_ACTION_1), headers=headers)
        self.assertEqual(resp.status_int, 201)
        token_user = resp.json['context']['user']
        self.assertEqual(token_user, 'tokenuser')
        context = {'parent': {'execution_id': str(resp.json['id']), 'user': token_user}}
        headers = {'content-type': 'application/json',
                   'X-Auth-Token': str(SYS_TOKEN.token),
                   'st2-context': json.dumps(context)}
        resp = self._do_post(copy.deepcopy(LIVE_ACTION_1), headers=headers)
        self.assertEqual(resp.status_int, 201)
        self.assertEqual(resp.json['context']['user'], 'tokenuser')
        self.assertEqual(resp.json['context']['parent'], context['parent'])

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

import httplib

import mock
import six

from st2common.router import Response
from st2api.controllers.v1.actionexecutions import ActionExecutionsControllerMixin
from tests.base import APIControllerWithRBACTestCase

http_client = six.moves.http_client

__all__ = [
    'PackControllerRBACTestCase'
]


class PackControllerRBACTestCase(APIControllerWithRBACTestCase):
    @mock.patch.object(ActionExecutionsControllerMixin, '_handle_schedule_execution')
    def test_install(self, _handle_schedule_execution):
        user_db = self.users['system_admin']
        self.use_user(user_db)

        _handle_schedule_execution.return_value = Response(json={'id': '123'})
        payload = {'packs': ['some']}

        resp = self.app.post_json('/v1/packs/install', payload)

        self.assertEqual(resp.status_int, 202)
        self.assertEqual(resp.json, {'execution_id': '123'})

        # Verify created execution correctly used the user which performed the API operation
        call_kwargs = _handle_schedule_execution.call_args[1]
        self.assertEqual(call_kwargs['requester_user'], user_db)
        self.assertEqual(call_kwargs['liveaction_api'].user, user_db.name)

        # Try with a different user
        user_db = self.users['admin']
        self.use_user(user_db)

        resp = self.app.post_json('/v1/packs/install', payload)

        self.assertEqual(resp.status_int, 202)
        self.assertEqual(resp.json, {'execution_id': '123'})

        # Verify created execution correctly used the user which performed the API operation
        call_kwargs = _handle_schedule_execution.call_args[1]
        self.assertEqual(call_kwargs['requester_user'], user_db)
        self.assertEqual(call_kwargs['liveaction_api'].user, user_db.name)

    @mock.patch.object(ActionExecutionsControllerMixin, '_handle_schedule_execution')
    def test_uninstall(self, _handle_schedule_execution):
        user_db = self.users['system_admin']
        self.use_user(user_db)

        _handle_schedule_execution.return_value = Response(json={'id': '123'})
        payload = {'packs': ['some']}

        resp = self.app.post_json('/v1/packs/uninstall', payload)

        self.assertEqual(resp.status_int, 202)
        self.assertEqual(resp.json, {'execution_id': '123'})

        # Verify created execution correctly used the user which performed the API operation
        call_kwargs = _handle_schedule_execution.call_args[1]
        self.assertEqual(call_kwargs['requester_user'], user_db)
        self.assertEqual(call_kwargs['liveaction_api'].user, user_db.name)

    def test_get_all_limit_minus_one(self):
        user_db = self.users['observer']
        self.use_user(user_db)

        resp = self.app.get('/v1/packs?limit=-1', expect_errors=True)
        self.assertEqual(resp.status_code, httplib.FORBIDDEN)

        user_db = self.users['admin']
        self.use_user(user_db)

        resp = self.app.get('/v1/packs?limit=-1')
        self.assertEqual(resp.status_code, httplib.OK)

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

from __future__ import absolute_import

import base64

import mock
from oslo_config import cfg

from st2tests.base import CleanDbTestCase
import st2auth.handlers as handlers
from st2common.models.db.auth import UserDB
from st2common.persistence.auth import User
from st2common.router import exc

from st2tests.mocks.auth import DUMMY_CREDS
from st2tests.mocks.auth import MockRequest
from st2tests.mocks.auth import get_mock_backend

__all__ = [
    'AuthHandlerTestCase'
]


@mock.patch('st2auth.handlers.get_auth_backend_instance', get_mock_backend)
class AuthHandlerTestCase(CleanDbTestCase):
    def setUp(self):
        super(AuthHandlerTestCase, self).setUp()

        cfg.CONF.auth.backend = 'mock'

    def test_proxy_handler(self):
        h = handlers.ProxyAuthHandler()
        request = {}
        token = h.handle_auth(
            request, headers={}, remote_addr=None,
            remote_user='test_proxy_handler')
        self.assertEqual(token.user, 'test_proxy_handler')

    def test_standalone_bad_auth_type(self):
        h = handlers.StandaloneAuthHandler()
        request = {}

        with self.assertRaises(exc.HTTPUnauthorized):
            h.handle_auth(
                request, headers={}, remote_addr=None,
                remote_user=None, authorization=('complex', DUMMY_CREDS))

    def test_standalone_no_auth(self):
        h = handlers.StandaloneAuthHandler()
        request = {}

        with self.assertRaises(exc.HTTPUnauthorized):
            h.handle_auth(
                request, headers={}, remote_addr=None,
                remote_user=None, authorization=None)

    def test_standalone_bad_auth_value(self):
        h = handlers.StandaloneAuthHandler()
        request = {}

        with self.assertRaises(exc.HTTPUnauthorized):
            h.handle_auth(
                request, headers={}, remote_addr=None,
                remote_user=None, authorization=('basic', 'gobblegobble'))

    def test_standalone_handler(self):
        h = handlers.StandaloneAuthHandler()
        request = {}

        token = h.handle_auth(
            request, headers={}, remote_addr=None,
            remote_user=None, authorization=('basic', DUMMY_CREDS))
        self.assertEqual(token.user, 'auser')

    def test_standalone_handler_ttl(self):
        h = handlers.StandaloneAuthHandler()

        token1 = h.handle_auth(
            MockRequest(23), headers={}, remote_addr=None,
            remote_user=None, authorization=('basic', DUMMY_CREDS))
        token2 = h.handle_auth(
            MockRequest(2300), headers={}, remote_addr=None,
            remote_user=None, authorization=('basic', DUMMY_CREDS))
        self.assertEqual(token1.user, 'auser')
        self.assertNotEqual(token1.expiry, token2.expiry)

    @mock.patch.object(
        User, 'get_by_name',
        mock.MagicMock(return_value=UserDB(name='auser')))
    def test_standalone_for_user_not_service(self):
        h = handlers.StandaloneAuthHandler()
        request = MockRequest(60)
        request.user = 'anotheruser'

        with self.assertRaises(exc.HTTPBadRequest):
            h.handle_auth(
                request, headers={}, remote_addr=None,
                remote_user=None, authorization=('basic', DUMMY_CREDS))

    @mock.patch.object(
        User, 'get_by_name',
        mock.MagicMock(return_value=UserDB(name='auser', is_service=True)))
    def test_standalone_for_user_service(self):
        h = handlers.StandaloneAuthHandler()
        request = MockRequest(60)
        request.user = 'anotheruser'

        token = h.handle_auth(
            request, headers={}, remote_addr=None,
            remote_user=None, authorization=('basic', DUMMY_CREDS))
        self.assertEqual(token.user, 'anotheruser')

    def test_standalone_for_user_not_found(self):
        h = handlers.StandaloneAuthHandler()
        request = MockRequest(60)
        request.user = 'anotheruser'

        with self.assertRaises(exc.HTTPBadRequest):
            h.handle_auth(
                request, headers={}, remote_addr=None,
                remote_user=None, authorization=('basic', DUMMY_CREDS))

    def test_standalone_impersonate_user_not_found(self):
        h = handlers.StandaloneAuthHandler()
        request = MockRequest(60)
        request.impersonate_user = 'anotheruser'

        with self.assertRaises(exc.HTTPBadRequest):
            h.handle_auth(
                request, headers={}, remote_addr=None,
                remote_user=None, authorization=('basic', DUMMY_CREDS))

    @mock.patch.object(
        User, 'get_by_name',
        mock.MagicMock(return_value=UserDB(name='auser', is_service=True)))
    @mock.patch.object(
        User, 'get_by_nickname',
        mock.MagicMock(return_value=UserDB(name='anotheruser', is_service=True)))
    def test_standalone_impersonate_user_with_nick_origin(self):
        h = handlers.StandaloneAuthHandler()
        request = MockRequest(60)
        request.impersonate_user = 'anotheruser'
        request.nickname_origin = 'slack'

        token = h.handle_auth(
            request, headers={}, remote_addr=None,
            remote_user=None, authorization=('basic', DUMMY_CREDS))
        self.assertEqual(token.user, 'anotheruser')

    def test_standalone_impersonate_user_no_origin(self):
        h = handlers.StandaloneAuthHandler()
        request = MockRequest(60)
        request.impersonate_user = '@anotheruser'

        with self.assertRaises(exc.HTTPBadRequest):
            h.handle_auth(
                request, headers={}, remote_addr=None,
                remote_user=None, authorization=('basic', DUMMY_CREDS))

    def test_password_contains_colon(self):
        h = handlers.StandaloneAuthHandler()
        request = MockRequest(60)

        authorization = ('Basic', base64.b64encode(b'username:password:password'))
        token = h.handle_auth(
            request, headers={}, remote_addr=None,
            remote_user=None, authorization=authorization)
        self.assertEqual(token.user, 'username')

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

import unittest2
import pecan
import mock
from oslo_config import cfg
import webob.exc

from tests.base import FunctionalTest

import st2auth.handlers as handlers
import st2auth.backends
from st2auth.backends.base import BaseAuthenticationBackend

# auser:apassword in b64
DUMMY_CREDS = 'YXVzZXI6YXBhc3N3b3Jk'


class MockAuthBackend(BaseAuthenticationBackend):
    def __init__(self):
        pass

    def authenticate(self, username, password):
        return True

    def get_user(self, username):
        return username


class MockRequest(object):
    body = ''


def get_mock_backend(name):
    return MockAuthBackend()


class HandlerTestCase(FunctionalTest):
    def setUp(self):
        cfg.CONF.auth.backend = 'mock'

    def test_proxy_handler(self):
        h = handlers.ProxyAuthHandler()
        request={}
        token = h.handle_auth(request, headers={}, remote_addr=None, 
        remote_user='test_proxy_handler')
        self.assertEqual(token.user, 'test_proxy_handler')

    def test_standalone_bad_auth_type(self):
        with mock.patch('st2auth.handlers.get_backend_instance', get_mock_backend) as m:
            h = handlers.StandaloneAuthHandler()
        request={}
     
        with self.assertRaises(webob.exc.HTTPUnauthorized):
            token = h.handle_auth(
                request, headers={}, remote_addr=None, 
                remote_user=None, authorization=('complex', DUMMY_CREDS))

    def test_standalone_no_auth(self):
        with mock.patch('st2auth.handlers.get_backend_instance', get_mock_backend) as m:
            h = handlers.StandaloneAuthHandler()
        request={}
     
        with self.assertRaises(webob.exc.HTTPUnauthorized):
            token = h.handle_auth(
                request, headers={}, remote_addr=None, 
                remote_user=None, authorization=None)

    def test_standalone_bad_auth_value(self):
        with mock.patch('st2auth.handlers.get_backend_instance', get_mock_backend) as m:
            h = handlers.StandaloneAuthHandler()
        request={}
     
        with self.assertRaises(webob.exc.HTTPUnauthorized):
            token = h.handle_auth(
                request, headers={}, remote_addr=None, 
                remote_user=None, authorization=('basic', 'gobblegobble'))

    def test_standalone_handler(self):
        with mock.patch('st2auth.handlers.get_backend_instance', get_mock_backend) as m:
            h = handlers.StandaloneAuthHandler()
        request=MockRequest()
     
        token = h.handle_auth(
            request, headers={}, remote_addr=None, 
            remote_user=None, authorization=('basic', DUMMY_CREDS))
        self.assertEqual(token.user, 'auser')

if __name__ == '__main__':
    unittest2.main()

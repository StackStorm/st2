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

import os
import json
import mock
import tempfile
import requests
import logging

from tests import base
from st2client import shell


LOG = logging.getLogger(__name__)

USERNAME = 'stanley'
PASSWORD = 'ShhhDontTell'
HEADERS = {'content-type': 'application/json'}
AUTH_URL = 'https://127.0.0.1:9100/tokens'
GET_RULES_URL = 'http://127.0.0.1:9101/v1/rules/?limit=50'


class TestHttps(base.BaseCLITestCase):

    def __init__(self, *args, **kwargs):
        super(TestHttps, self).__init__(*args, **kwargs)
        self.shell = shell.Shell()

    def setUp(self):
        super(TestHttps, self).setUp()

        # Setup environment.
        os.environ['ST2_BASE_URL'] = 'http://127.0.0.1'
        os.environ['ST2_AUTH_URL'] = 'https://127.0.0.1:9100'

        if 'ST2_CACERT' in os.environ:
            del os.environ['ST2_CACERT']

        # Create a temp file to mock a cert file.
        self.cacert_fd, self.cacert_path = tempfile.mkstemp()

    def tearDown(self):
        super(TestHttps, self).tearDown()

        # Clean up environment.
        if 'ST2_CACERT' in os.environ:
            del os.environ['ST2_CACERT']
        if 'ST2_BASE_URL' in os.environ:
            del os.environ['ST2_BASE_URL']

        # Clean up temp files.
        os.close(self.cacert_fd)
        os.unlink(self.cacert_path)

    @mock.patch.object(
        requests, 'post',
        mock.MagicMock(return_value=base.FakeResponse(json.dumps({}), 200, 'OK')))
    def test_decorate_https_without_cacert(self):
        self.shell.run(['auth', USERNAME, '-p', PASSWORD])
        kwargs = {'verify': False, 'headers': HEADERS, 'auth': (USERNAME, PASSWORD)}
        requests.post.assert_called_with(AUTH_URL, json.dumps({}), **kwargs)

    @mock.patch.object(
        requests, 'post',
        mock.MagicMock(return_value=base.FakeResponse(json.dumps({}), 200, 'OK')))
    def test_decorate_https_with_cacert_from_cli(self):
        self.shell.run(['--cacert', self.cacert_path, 'auth', USERNAME, '-p', PASSWORD])
        kwargs = {'verify': self.cacert_path, 'headers': HEADERS, 'auth': (USERNAME, PASSWORD)}
        requests.post.assert_called_with(AUTH_URL, json.dumps({}), **kwargs)

    @mock.patch.object(
        requests, 'post',
        mock.MagicMock(return_value=base.FakeResponse(json.dumps({}), 200, 'OK')))
    def test_decorate_https_with_cacert_from_env(self):
        os.environ['ST2_CACERT'] = self.cacert_path
        self.shell.run(['auth', USERNAME, '-p', PASSWORD])
        kwargs = {'verify': self.cacert_path, 'headers': HEADERS, 'auth': (USERNAME, PASSWORD)}
        requests.post.assert_called_with(AUTH_URL, json.dumps({}), **kwargs)

    @mock.patch.object(
        requests, 'get',
        mock.MagicMock(return_value=base.FakeResponse(json.dumps([]), 200, 'OK')))
    def test_decorate_http_without_cacert(self):
        self.shell.run(['rule', 'list'])
        requests.get.assert_called_with(GET_RULES_URL)

    @mock.patch.object(
        requests, 'get',
        mock.MagicMock(return_value=base.FakeResponse(json.dumps({}), 200, 'OK')))
    def test_decorate_http_with_cacert_from_cli(self):
        self.shell.run(['--cacert', self.cacert_path, 'rule', 'list'])
        requests.get.assert_called_with(GET_RULES_URL)

    @mock.patch.object(
        requests, 'get',
        mock.MagicMock(return_value=base.FakeResponse(json.dumps({}), 200, 'OK')))
    def test_decorate_http_with_cacert_from_env(self):
        os.environ['ST2_CACERT'] = self.cacert_path
        self.shell.run(['rule', 'list'])
        requests.get.assert_called_with(GET_RULES_URL)

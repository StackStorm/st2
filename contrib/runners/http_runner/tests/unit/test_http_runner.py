# -*- coding: utf-8 -*-
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

import six
import mock
import unittest2

from http_runner.http_runner import HTTPClient
import st2tests.config as tests_config


if six.PY2:
    EXPECTED_DATA = ''
else:
    EXPECTED_DATA = b''


class MockResult(object):
    close = mock.Mock()


class HTTPRunnerTestCase(unittest2.TestCase):
    @classmethod
    def setUpClass(cls):
        tests_config.parse_args()

    @mock.patch('http_runner.http_runner.requests')
    def test_parse_response_body(self, mock_requests):
        client = HTTPClient(url='http://127.0.0.1')
        mock_result = MockResult()

        # Unknown content type, body should be returned raw
        mock_result.text = 'foo bar ponies'
        mock_result.headers = {'Content-Type': 'text/html'}
        mock_result.status_code = 200

        mock_requests.request.return_value = mock_result
        result = client.run()

        self.assertEqual(result['body'], mock_result.text)
        self.assertEqual(result['status_code'], mock_result.status_code)
        self.assertEqual(result['headers'], mock_result.headers)

        # Unknown content type, JSON body
        mock_result.text = '{"test1": "val1"}'
        mock_result.headers = {'Content-Type': 'text/html'}

        mock_requests.request.return_value = mock_result
        result = client.run()

        self.assertEqual(result['body'], mock_result.text)

        # JSON content-type and JSON body
        mock_result.text = '{"test1": "val1"}'
        mock_result.headers = {'Content-Type': 'application/json'}

        mock_requests.request.return_value = mock_result
        result = client.run()

        self.assertTrue(isinstance(result['body'], dict))
        self.assertEqual(result['body'], {'test1': 'val1'})

        # JSON content-type with charset and JSON body
        mock_result.text = '{"test1": "val1"}'
        mock_result.headers = {'Content-Type': 'application/json; charset=UTF-8'}

        mock_requests.request.return_value = mock_result
        result = client.run()

        self.assertTrue(isinstance(result['body'], dict))
        self.assertEqual(result['body'], {'test1': 'val1'})

        # JSON content-type and invalid json body
        mock_result.text = 'not json'
        mock_result.headers = {'Content-Type': 'application/json'}

        mock_requests.request.return_value = mock_result
        result = client.run()

        self.assertFalse(isinstance(result['body'], dict))
        self.assertEqual(result['body'], mock_result.text)

    @mock.patch('http_runner.http_runner.requests')
    def test_https_verify(self, mock_requests):
        url = 'https://127.0.0.1:8888'
        client = HTTPClient(url=url, verify=True)
        mock_result = MockResult()

        mock_result.text = 'foo bar ponies'
        mock_result.headers = {'Content-Type': 'text/html'}
        mock_result.status_code = 200

        mock_requests.request.return_value = mock_result
        client.run()

        self.assertTrue(client.verify)

        if six.PY2:
            data = ''
        else:
            data = b''

        mock_requests.request.assert_called_with(
            'GET', url, allow_redirects=False, auth=None, cookies=None,
            data=data, files=None, headers={}, params=None, proxies=None,
            timeout=60, verify=True)

    @mock.patch('http_runner.http_runner.requests')
    def test_https_verify_false(self, mock_requests):
        url = 'https://127.0.0.1:8888'
        client = HTTPClient(url=url)
        mock_result = MockResult()

        mock_result.text = 'foo bar ponies'
        mock_result.headers = {'Content-Type': 'text/html'}
        mock_result.status_code = 200

        mock_requests.request.return_value = mock_result
        client.run()

        self.assertFalse(client.verify)

        mock_requests.request.assert_called_with(
            'GET', url, allow_redirects=False, auth=None, cookies=None,
            data=EXPECTED_DATA, files=None, headers={}, params=None, proxies=None,
            timeout=60, verify=False)

    @mock.patch('http_runner.http_runner.requests')
    def test_https_auth_basic(self, mock_requests):
        url = 'https://127.0.0.1:8888'
        username = 'misspiggy'
        password = 'kermit'
        client = HTTPClient(url=url, username=username, password=password)
        mock_result = MockResult()

        mock_result.text = 'muppet show'
        mock_result.headers = {'Authorization': 'bWlzc3BpZ2d5Omtlcm1pdA=='}
        mock_result.status_code = 200

        mock_requests.request.return_value = mock_result
        result = client.run()

        self.assertEqual(result['headers'], mock_result.headers)

        mock_requests.request.assert_called_once_with(
            'GET', url, allow_redirects=False, auth=client.auth, cookies=None,
            data=EXPECTED_DATA, files=None, headers={}, params=None, proxies=None,
            timeout=60, verify=False)

    @mock.patch('http_runner.http_runner.requests')
    def test_http_unicode_body_data(self, mock_requests):
        url = 'http://127.0.0.1:8888'
        method = 'POST'
        mock_result = MockResult()

        # 1. String data
        headers = {}
        body = 'žžžžž'
        client = HTTPClient(url=url, method=method, headers=headers, body=body, timeout=0.1)

        mock_result.text = '{"foo": "bar"}'
        mock_result.headers = {'Content-Type': 'application/json'}
        mock_result.status_code = 200
        mock_requests.request.return_value = mock_result

        result = client.run()
        self.assertEqual(result['status_code'], 200)

        call_kwargs = mock_requests.request.call_args_list[0][1]

        expected_data = u'žžžžž'.encode('utf-8')
        self.assertEqual(call_kwargs['data'], expected_data)

        # 1. Object / JSON data
        body = {
            'foo': u'ažž'
        }
        headers = {
            'Content-Type': 'application/json; charset=utf-8'
        }
        client = HTTPClient(url=url, method=method, headers=headers, body=body, timeout=0.1)

        mock_result.text = '{"foo": "bar"}'
        mock_result.headers = {'Content-Type': 'application/json'}
        mock_result.status_code = 200
        mock_requests.request.return_value = mock_result

        result = client.run()
        self.assertEqual(result['status_code'], 200)

        call_kwargs = mock_requests.request.call_args_list[1][1]

        if six.PY2:
            expected_data = {
                'foo': u'a\u017e\u017e'
            }
        else:
            expected_data = body

        self.assertEqual(call_kwargs['data'], expected_data)

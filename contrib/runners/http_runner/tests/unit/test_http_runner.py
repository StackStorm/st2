# -*- coding: utf-8 -*-
# Copyright 2020 The StackStorm Authors.
# Copyright 2019 Extreme Networks, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import absolute_import

import re

import six
import mock
import unittest

from st2common.constants.action import LIVEACTION_STATUS_SUCCEEDED
from http_runner.http_runner import HTTPClient
from http_runner.http_runner import HttpRunner

import st2tests.config as tests_config

__all__ = ["HTTPClientTestCase", "HTTPRunnerTestCase"]


if six.PY2:
    EXPECTED_DATA = ""
else:
    EXPECTED_DATA = b""


class MockResult(object):
    close = mock.Mock()


class HTTPClientTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        tests_config.parse_args()

    @mock.patch("http_runner.http_runner.requests")
    def test_parse_response_body(self, mock_requests):
        client = HTTPClient(url="http://127.0.0.1")
        mock_result = MockResult()

        # Unknown content type, body should be returned raw
        mock_result.text = "foo bar ponies"
        mock_result.headers = {"Content-Type": "text/html"}
        mock_result.status_code = 200

        mock_requests.request.return_value = mock_result
        result = client.run()

        self.assertEqual(result["body"], mock_result.text)
        self.assertEqual(result["status_code"], mock_result.status_code)
        self.assertEqual(result["headers"], mock_result.headers)

        # Unknown content type, JSON body
        mock_result.text = '{"test1": "val1"}'
        mock_result.headers = {"Content-Type": "text/html"}

        mock_requests.request.return_value = mock_result
        result = client.run()

        self.assertEqual(result["body"], mock_result.text)

        # JSON content-type and JSON body
        mock_result.text = '{"test1": "val1"}'
        mock_result.headers = {"Content-Type": "application/json"}

        mock_requests.request.return_value = mock_result
        result = client.run()

        self.assertIsInstance(result["body"], dict)
        self.assertEqual(result["body"], {"test1": "val1"})

        # JSON content-type with charset and JSON body
        mock_result.text = '{"test1": "val1"}'
        mock_result.headers = {"Content-Type": "application/json; charset=UTF-8"}

        mock_requests.request.return_value = mock_result
        result = client.run()

        self.assertIsInstance(result["body"], dict)
        self.assertEqual(result["body"], {"test1": "val1"})

        # JSON content-type and invalid json body
        mock_result.text = "not json"
        mock_result.headers = {"Content-Type": "application/json"}

        mock_requests.request.return_value = mock_result
        result = client.run()

        self.assertNotIsInstance(result["body"], dict)
        self.assertEqual(result["body"], mock_result.text)

    @mock.patch("http_runner.http_runner.requests")
    def test_https_verify(self, mock_requests):
        url = "https://127.0.0.1:8888"
        client = HTTPClient(url=url, verify=True)
        mock_result = MockResult()

        mock_result.text = "foo bar ponies"
        mock_result.headers = {"Content-Type": "text/html"}
        mock_result.status_code = 200

        mock_requests.request.return_value = mock_result
        client.run()

        self.assertTrue(client.verify)

        if six.PY2:
            data = ""
        else:
            data = b""

        mock_requests.request.assert_called_with(
            "GET",
            url,
            allow_redirects=False,
            auth=None,
            cookies=None,
            data=data,
            files=None,
            headers={},
            params=None,
            proxies=None,
            timeout=60,
            verify=True,
        )

    @mock.patch("http_runner.http_runner.requests")
    def test_https_verify_false(self, mock_requests):
        url = "https://127.0.0.1:8888"
        client = HTTPClient(url=url)
        mock_result = MockResult()

        mock_result.text = "foo bar ponies"
        mock_result.headers = {"Content-Type": "text/html"}
        mock_result.status_code = 200

        mock_requests.request.return_value = mock_result
        client.run()

        self.assertFalse(client.verify)

        mock_requests.request.assert_called_with(
            "GET",
            url,
            allow_redirects=False,
            auth=None,
            cookies=None,
            data=EXPECTED_DATA,
            files=None,
            headers={},
            params=None,
            proxies=None,
            timeout=60,
            verify=False,
        )

    @mock.patch("http_runner.http_runner.requests")
    def test_https_auth_basic(self, mock_requests):
        url = "https://127.0.0.1:8888"
        username = "misspiggy"
        password = "kermit"
        client = HTTPClient(url=url, username=username, password=password)
        mock_result = MockResult()

        mock_result.text = "muppet show"
        mock_result.headers = {"Authorization": "bWlzc3BpZ2d5Omtlcm1pdA=="}
        mock_result.status_code = 200

        mock_requests.request.return_value = mock_result
        result = client.run()

        self.assertEqual(result["headers"], mock_result.headers)

        mock_requests.request.assert_called_once_with(
            "GET",
            url,
            allow_redirects=False,
            auth=client.auth,
            cookies=None,
            data=EXPECTED_DATA,
            files=None,
            headers={},
            params=None,
            proxies=None,
            timeout=60,
            verify=False,
        )

    @mock.patch("http_runner.http_runner.requests")
    def test_http_unicode_body_data(self, mock_requests):
        url = "http://127.0.0.1:8888"
        method = "POST"
        mock_result = MockResult()

        # 1. String data
        headers = {}
        body = "žžžžž"
        client = HTTPClient(
            url=url, method=method, headers=headers, body=body, timeout=0.1
        )

        mock_result.text = '{"foo": "bar"}'
        mock_result.headers = {"Content-Type": "application/json"}
        mock_result.status_code = 200
        mock_requests.request.return_value = mock_result

        result = client.run()
        self.assertEqual(result["status_code"], 200)

        call_kwargs = mock_requests.request.call_args_list[0][1]

        expected_data = "žžžžž".encode("utf-8")
        self.assertEqual(call_kwargs["data"], expected_data)

        # 1. Object / JSON data
        body = {"foo": "ažž"}
        headers = {"Content-Type": "application/json; charset=utf-8"}
        client = HTTPClient(
            url=url, method=method, headers=headers, body=body, timeout=0.1
        )

        mock_result.text = '{"foo": "bar"}'
        mock_result.headers = {"Content-Type": "application/json"}
        mock_result.status_code = 200
        mock_requests.request.return_value = mock_result

        result = client.run()
        self.assertEqual(result["status_code"], 200)

        call_kwargs = mock_requests.request.call_args_list[1][1]

        if six.PY2:
            expected_data = {"foo": "a\u017e\u017e"}
        else:
            expected_data = body

        self.assertEqual(call_kwargs["data"], expected_data)

    @mock.patch("http_runner.http_runner.requests")
    def test_blacklisted_url_url_hosts_blacklist_runner_parameter(self, mock_requests):
        # Black list is empty
        self.assertEqual(mock_requests.request.call_count, 0)

        url = "http://www.example.com"
        client = HTTPClient(url=url, method="GET")
        client.run()

        self.assertEqual(mock_requests.request.call_count, 1)

        # Blacklist is set
        url_hosts_blacklist = [
            "example.com",
            "127.0.0.1",
            "::1",
            "2001:0db8:85a3:0000:0000:8a2e:0370:7334",
        ]

        # Blacklisted urls
        urls = [
            "https://example.com",
            "http://example.com",
            "http://example.com:81",
            "http://example.com:80",
            "http://example.com:9000",
            "http://[::1]:80/",
            "http://[::1]",
            "http://[::1]:9000",
            "http://[2001:0db8:85a3:0000:0000:8a2e:0370:7334]",
            "https://[2001:0db8:85a3:0000:0000:8a2e:0370:7334]:8000",
        ]

        for url in urls:
            expected_msg = r'URL "%s" is blacklisted' % (re.escape(url))
            client = HTTPClient(
                url=url, method="GET", url_hosts_blacklist=url_hosts_blacklist
            )
            self.assertRaisesRegex(ValueError, expected_msg, client.run)

        # Non blacklisted URLs
        urls = ["https://example2.com", "http://example3.com", "http://example4.com:81"]

        for url in urls:
            mock_requests.request.reset_mock()

            self.assertEqual(mock_requests.request.call_count, 0)

            client = HTTPClient(
                url=url, method="GET", url_hosts_blacklist=url_hosts_blacklist
            )
            client.run()

            self.assertEqual(mock_requests.request.call_count, 1)

    @mock.patch("http_runner.http_runner.requests")
    def test_whitelisted_url_url_hosts_whitelist_runner_parameter(self, mock_requests):
        # Whitelist is empty
        self.assertEqual(mock_requests.request.call_count, 0)

        url = "http://www.example.com"
        client = HTTPClient(url=url, method="GET")
        client.run()

        self.assertEqual(mock_requests.request.call_count, 1)

        # Whitelist is set
        url_hosts_whitelist = [
            "example.com",
            "127.0.0.1",
            "::1",
            "2001:0db8:85a3:0000:0000:8a2e:0370:7334",
        ]

        # Non whitelisted urls
        urls = [
            "https://www.google.com",
            "https://www.example2.com",
            "http://127.0.0.2",
        ]

        for url in urls:
            expected_msg = r'URL "%s" is not whitelisted' % (re.escape(url))
            client = HTTPClient(
                url=url, method="GET", url_hosts_whitelist=url_hosts_whitelist
            )
            self.assertRaisesRegex(ValueError, expected_msg, client.run)

        # Whitelisted URLS
        urls = [
            "https://example.com",
            "http://example.com",
            "http://example.com:81",
            "http://example.com:80",
            "http://example.com:9000",
            "http://[::1]:80/",
            "http://[::1]",
            "http://[::1]:9000",
            "http://[2001:0db8:85a3:0000:0000:8a2e:0370:7334]",
            "https://[2001:0db8:85a3:0000:0000:8a2e:0370:7334]:8000",
        ]

        for url in urls:
            mock_requests.request.reset_mock()

            self.assertEqual(mock_requests.request.call_count, 0)

            client = HTTPClient(
                url=url, method="GET", url_hosts_whitelist=url_hosts_whitelist
            )
            client.run()

            self.assertEqual(mock_requests.request.call_count, 1)

    def test_url_host_blacklist_and_url_host_blacklist_params_are_mutually_exclusive(
        self,
    ):
        url = "http://www.example.com"

        expected_msg = (
            r'"url_hosts_blacklist" and "url_hosts_whitelist" parameters are mutually '
            "exclusive."
        )
        self.assertRaisesRegex(
            ValueError,
            expected_msg,
            HTTPClient,
            url=url,
            method="GET",
            url_hosts_blacklist=[url],
            url_hosts_whitelist=[url],
        )


class HTTPRunnerTestCase(unittest.TestCase):
    @mock.patch("http_runner.http_runner.requests")
    def test_get_success(self, mock_requests):
        mock_result = MockResult()

        # Unknown content type, body should be returned raw
        mock_result.text = "foo bar ponies"
        mock_result.headers = {"Content-Type": "text/html"}
        mock_result.status_code = 200

        mock_requests.request.return_value = mock_result

        runner_parameters = {"url": "http://www.example.com", "method": "GET"}
        runner = HttpRunner("id")
        runner.runner_parameters = runner_parameters
        runner.pre_run()

        status, result, _ = runner.run({})
        self.assertEqual(status, LIVEACTION_STATUS_SUCCEEDED)
        self.assertEqual(result["body"], "foo bar ponies")
        self.assertEqual(result["status_code"], 200)
        self.assertEqual(result["parsed"], False)

    def test_url_host_blacklist_and_url_host_blacklist_params_are_mutually_exclusive(
        self,
    ):
        runner_parameters = {
            "url": "http://www.example.com",
            "method": "GET",
            "url_hosts_blacklist": ["http://127.0.0.1"],
            "url_hosts_whitelist": ["http://127.0.0.1"],
        }
        runner = HttpRunner("id")
        runner.runner_parameters = runner_parameters
        runner.pre_run()

        expected_msg = (
            r'"url_hosts_blacklist" and "url_hosts_whitelist" parameters are mutually '
            "exclusive."
        )
        self.assertRaisesRegex(ValueError, expected_msg, runner.run, {})

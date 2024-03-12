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
import unittest

from oslo_config import cfg

from st2common.constants.api import DEFAULT_API_VERSION
from st2common.util.api import get_base_public_api_url
from st2common.util.api import get_full_public_api_url
from st2tests.config import parse_args
from six.moves import zip

parse_args()


class APIUtilsTestCase(unittest.TestCase):
    def test_get_base_public_api_url(self):
        values = [
            "http://foo.bar.com",
            "http://foo.bar.com/",
            "http://foo.bar.com:8080",
            "http://foo.bar.com:8080/",
            "http://localhost:8080/",
        ]
        expected = [
            "http://foo.bar.com",
            "http://foo.bar.com",
            "http://foo.bar.com:8080",
            "http://foo.bar.com:8080",
            "http://localhost:8080",
        ]

        for mock_value, expected_result in zip(values, expected):
            cfg.CONF.auth.api_url = mock_value
            actual = get_base_public_api_url()
            self.assertEqual(actual, expected_result)

    def test_get_full_public_api_url(self):
        values = [
            "http://foo.bar.com",
            "http://foo.bar.com/",
            "http://foo.bar.com:8080",
            "http://foo.bar.com:8080/",
            "http://localhost:8080/",
        ]
        expected = [
            "http://foo.bar.com/" + DEFAULT_API_VERSION,
            "http://foo.bar.com/" + DEFAULT_API_VERSION,
            "http://foo.bar.com:8080/" + DEFAULT_API_VERSION,
            "http://foo.bar.com:8080/" + DEFAULT_API_VERSION,
            "http://localhost:8080/" + DEFAULT_API_VERSION,
        ]

        for mock_value, expected_result in zip(values, expected):
            cfg.CONF.auth.api_url = mock_value
            actual = get_full_public_api_url()
            self.assertEqual(actual, expected_result)

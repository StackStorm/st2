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

from st2common.util.http import parse_content_type_header
from six.moves import zip

__all__ = ["HTTPUtilTestCase"]


class HTTPUtilTestCase(unittest.TestCase):
    def test_parse_content_type_header(self):
        values = [
            "application/json",
            "foo/bar",
            "application/json; charset=utf-8",
            "application/json; charset=utf-8; foo=bar",
        ]
        expected_results = [
            ("application/json", {}),
            ("foo/bar", {}),
            ("application/json", {"charset": "utf-8"}),
            ("application/json", {"charset": "utf-8", "foo": "bar"}),
        ]

        for value, expected_result in zip(values, expected_results):
            result = parse_content_type_header(content_type=value)
            self.assertEqual(result, expected_result)

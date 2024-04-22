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

from st2common.util import jinja as jinja_utils


class JinjaUtilsJsonpathQueryTestCase(unittest.TestCase):
    def test_jsonpath_query_static(self):
        env = jinja_utils.get_jinja_environment()
        obj = {
            "people": [
                {"first": "James", "last": "d"},
                {"first": "Jacob", "last": "e"},
                {"first": "Jayden", "last": "f"},
                {"missing": "different"},
            ],
            "foo": {"bar": "baz"},
        }

        template = '{{ obj | jsonpath_query("people[*].first") }}'
        actual_str = env.from_string(template).render({"obj": obj})
        actual = eval(actual_str)
        expected = ["James", "Jacob", "Jayden"]
        self.assertEqual(actual, expected)

    def test_jsonpath_query_dynamic(self):
        env = jinja_utils.get_jinja_environment()
        obj = {
            "people": [
                {"first": "James", "last": "d"},
                {"first": "Jacob", "last": "e"},
                {"first": "Jayden", "last": "f"},
                {"missing": "different"},
            ],
            "foo": {"bar": "baz"},
        }
        query = "people[*].last"

        template = "{{ obj | jsonpath_query(query) }}"
        actual_str = env.from_string(template).render({"obj": obj, "query": query})
        actual = eval(actual_str)
        expected = ["d", "e", "f"]
        self.assertEqual(actual, expected)

    def test_jsonpath_query_no_results(self):
        env = jinja_utils.get_jinja_environment()
        obj = {
            "people": [
                {"first": "James", "last": "d"},
                {"first": "Jacob", "last": "e"},
                {"first": "Jayden", "last": "f"},
                {"missing": "different"},
            ],
            "foo": {"bar": "baz"},
        }
        query = "query_returns_no_results"

        template = "{{ obj | jsonpath_query(query) }}"
        actual_str = env.from_string(template).render({"obj": obj, "query": query})
        actual = eval(actual_str)
        expected = None
        self.assertEqual(actual, expected)

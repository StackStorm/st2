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
import json
import unittest
import yaml

from st2common.constants.keyvalue import FULL_SYSTEM_SCOPE
from st2common.util import jinja as jinja_utils
from st2common.services.keyvalues import KeyValueLookup
import st2tests.config as tests_config


class JinjaUtilsDataFilterTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        tests_config.parse_args()

    def test_filter_from_json_string(self):
        env = jinja_utils.get_jinja_environment()
        expected_obj = {"a": "b", "c": {"d": "e", "f": 1, "g": True}}
        obj_json_str = '{"a": "b", "c": {"d": "e", "f": 1, "g": true}}'

        template = "{{k1 | from_json_string}}"

        obj_str = env.from_string(template).render({"k1": obj_json_str})
        obj = eval(obj_str)
        self.assertDictEqual(obj, expected_obj)

        # With KeyValueLookup object
        env = jinja_utils.get_jinja_environment()
        obj_json_str = '["a", "b", "c"]'
        expected_obj = ["a", "b", "c"]

        template = "{{ k1 | from_json_string}}"

        lookup = KeyValueLookup(scope=FULL_SYSTEM_SCOPE, key_prefix="a")
        lookup._value_cache["a"] = obj_json_str
        obj_str = env.from_string(template).render({"k1": lookup})
        obj = eval(obj_str)
        self.assertEqual(obj, expected_obj)

    def test_filter_from_yaml_string(self):
        env = jinja_utils.get_jinja_environment()
        expected_obj = {"a": "b", "c": {"d": "e", "f": 1, "g": True}}
        obj_yaml_str = "---\n" "a: b\n" "c:\n" "  d: e\n" "  f: 1\n" "  g: true\n"

        template = "{{k1 | from_yaml_string}}"
        obj_str = env.from_string(template).render({"k1": obj_yaml_str})
        obj = eval(obj_str)
        self.assertDictEqual(obj, expected_obj)

        # With KeyValueLookup object
        env = jinja_utils.get_jinja_environment()
        obj_yaml_str = "---\n" "- a\n" "- b\n" "- c\n"
        expected_obj = ["a", "b", "c"]

        template = "{{ k1 | from_yaml_string }}"

        lookup = KeyValueLookup(scope=FULL_SYSTEM_SCOPE, key_prefix="b")
        lookup._value_cache["b"] = obj_yaml_str
        obj_str = env.from_string(template).render({"k1": lookup})
        obj = eval(obj_str)
        self.assertEqual(obj, expected_obj)

    def test_filter_to_json_string(self):
        env = jinja_utils.get_jinja_environment()
        obj = {"a": "b", "c": {"d": "e", "f": 1, "g": True}}

        template = "{{k1 | to_json_string}}"

        obj_json_str = env.from_string(template).render({"k1": obj})
        actual_obj = json.loads(obj_json_str)
        self.assertDictEqual(obj, actual_obj)

    def test_filter_to_yaml_string(self):
        env = jinja_utils.get_jinja_environment()
        obj = {"a": "b", "c": {"d": "e", "f": 1, "g": True}}

        template = "{{k1 | to_yaml_string}}"
        obj_yaml_str = env.from_string(template).render({"k1": obj})
        actual_obj = yaml.safe_load(obj_yaml_str)
        self.assertDictEqual(obj, actual_obj)

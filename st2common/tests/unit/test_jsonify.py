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
from bson import ObjectId

import st2tests.config as tests_config

import st2common.util.jsonify as jsonify


class JsonifyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        tests_config.parse_args()
        jsonify.DEFAULT_JSON_LIBRARY = "orjson"

    @classmethod
    def tearDownClass(cls):
        jsonify.DEFAULT_JSON_LIBRARY = "orjson"

    def test_none_object(self):
        obj = None
        self.assertIsNone(jsonify.json_loads(obj))

    def test_no_keys(self):
        obj = {"foo": '{"bar": "baz"}'}
        transformed_obj = jsonify.json_loads(obj)
        self.assertTrue(transformed_obj["foo"]["bar"] == "baz")

    def test_no_json_value(self):
        obj = {"foo": "bar"}
        transformed_obj = jsonify.json_loads(obj)
        self.assertTrue(transformed_obj["foo"] == "bar")

    def test_happy_case(self):
        obj = {"foo": '{"bar": "baz"}', "yo": "bibimbao"}
        transformed_obj = jsonify.json_loads(obj, ["yo"])
        self.assertTrue(transformed_obj["yo"] == "bibimbao")

    def test_try_loads(self):
        # The function json.loads will fail and the function should return the original value.
        values = ["abc", 123, True, object()]
        for value in values:
            self.assertEqual(jsonify.try_loads(value), value)

        # The function json.loads succeed.
        d = '{"a": 1, "b": true}'
        expected = {"a": 1, "b": True}
        self.assertDictEqual(jsonify.try_loads(d), expected)

    def test_json_encode_decode_roundtrip_compatibility_between_different_libs(self):
        class ObjectWithJsonMethod(object):
            def __json__(self):
                return {"mah": "json", "1": 2}

        input_data = [
            "1",
            1,
            None,
            True,
            False,
            [1, "a", True, None, [1, 2], {"a": "b", "c": 3}],
            {"a": "b", "d": [1, 2, 3], "e": 5},
            ObjectWithJsonMethod(),
            b"bytes",
            ObjectId("5609e91832ed356d04a93cc0"),
        ]
        expected_data = [
            "1",
            1,
            None,
            True,
            False,
            [1, "a", True, None, [1, 2], {"a": "b", "c": 3}],
            {"a": "b", "d": [1, 2, 3], "e": 5},
            {"mah": "json", "1": 2},
            "bytes",
            "5609e91832ed356d04a93cc0",
        ]

        json_libraries = ["json", "orjson"]

        for json_library in json_libraries:
            jsonify.DEFAULT_JSON_LIBRARY = json_library

            result_encoded = jsonify.json_encode(input_data)
            result_decoded = jsonify.json_decode(result_encoded)
            result_decoded_native = json.loads(result_encoded)

            self.assertEqual(result_decoded, expected_data)
            self.assertEqual(result_decoded, result_decoded_native)

    def test_json_encode_decode_sort_keys_indent_compatibility_between_different_libs(
        self,
    ):
        input_data = {
            "d": 4,
            "a": 1,
            "b": 2,
            "c": 3,
        }

        # 1. indent=None
        result_orjson = jsonify.json_encode_orjson(input_data, indent=None)
        result_native = jsonify.json_encode_native_json(input_data, indent=None)
        self.assertEqual(result_orjson, result_native)

        # 2. indent=2 (only mode orjson supports)
        result_orjson = jsonify.json_encode_orjson(input_data, indent=2)
        result_native = jsonify.json_encode_native_json(input_data, indent=2)
        self.assertEqual(result_orjson, result_native)

        # 3. indent=None, sort_keys=True
        result_orjson = jsonify.json_encode_orjson(
            input_data, indent=None, sort_keys=True
        )
        result_native = jsonify.json_encode_native_json(
            input_data, indent=None, sort_keys=True
        )
        self.assertEqual(result_orjson, result_native)

        # 4. indent=2 + sort_keys=True
        result_orjson = jsonify.json_encode_orjson(input_data, indent=2, sort_keys=True)
        result_native = jsonify.json_encode_native_json(
            input_data, indent=2, sort_keys=True
        )
        self.assertEqual(result_orjson, result_native)

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

import mongoengine
import unittest

from st2common.util import db as db_util


class DatabaseUtilTestCase(unittest.TestCase):
    def test_noop_mongodb_to_python_types(self):
        data = [123, 999.99, True, [10, 20, 30], {"a": 1, "b": 2}, None]

        for item in data:
            self.assertEqual(db_util.mongodb_to_python_types(item), item)

    def test_mongodb_basedict_to_dict(self):
        data = {"a": 1, "b": 2}

        obj = mongoengine.base.datastructures.BaseDict(data, None, "foobar")

        self.assertDictEqual(db_util.mongodb_to_python_types(obj), data)

    def test_mongodb_baselist_to_list(self):
        data = [2, 4, 6]

        obj = mongoengine.base.datastructures.BaseList(data, None, "foobar")

        self.assertListEqual(db_util.mongodb_to_python_types(obj), data)

    def test_nested_mongdb_to_python_types(self):
        data = {
            "a": mongoengine.base.datastructures.BaseList([1, 2, 3], None, "a"),
            "b": mongoengine.base.datastructures.BaseDict({"a": 1, "b": 2}, None, "b"),
            "c": {
                "d": mongoengine.base.datastructures.BaseList([4, 5, 6], None, "d"),
                "e": mongoengine.base.datastructures.BaseDict(
                    {"c": 3, "d": 4}, None, "e"
                ),
            },
            "f": mongoengine.base.datastructures.BaseList(
                [
                    mongoengine.base.datastructures.BaseDict({"e": 5}, None, "f1"),
                    mongoengine.base.datastructures.BaseDict({"f": 6}, None, "f2"),
                ],
                None,
                "f",
            ),
            "g": mongoengine.base.datastructures.BaseDict(
                {
                    "h": mongoengine.base.datastructures.BaseList(
                        [
                            mongoengine.base.datastructures.BaseDict(
                                {"g": 7}, None, "h1"
                            ),
                            mongoengine.base.datastructures.BaseDict(
                                {"h": 8}, None, "h2"
                            ),
                        ],
                        None,
                        "h",
                    ),
                    "i": mongoengine.base.datastructures.BaseDict(
                        {"j": 9, "k": 10}, None, "i"
                    ),
                },
                None,
                "g",
            ),
        }

        expected = {
            "a": [1, 2, 3],
            "b": {"a": 1, "b": 2},
            "c": {"d": [4, 5, 6], "e": {"c": 3, "d": 4}},
            "f": [{"e": 5}, {"f": 6}],
            "g": {"h": [{"g": 7}, {"h": 8}], "i": {"j": 9, "k": 10}},
        }

        self.assertDictEqual(db_util.mongodb_to_python_types(data), expected)

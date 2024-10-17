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

from st2common import operators
from st2common.util import date as date_utils
import st2tests.config as tests_config


def list_of_dicts_strict_equal(lofd1, lofd2):
    """
    Ensure that two unordered lists contain the same dicts
    """
    t2 = list(lofd2)  # mutable copy
    if len(lofd1) != len(lofd2):
        return False
    for i1, el1 in enumerate(lofd1):
        for i2, el2 in enumerate(t2):
            if el1 == el2:
                del t2[i2]
                break
        else:
            return False
    return not t2


class ListOfDictsStrictEqualTest(unittest.TestCase):
    """
    Tests list_of_dicts_strict_equal

    We should test our comparison functions, even if they're only used in our
    other tests.
    """

    def test_empty_lists(self):
        self.assertTrue(list_of_dicts_strict_equal([], []))

    def test_empty_dicts(self):
        self.assertTrue(list_of_dicts_strict_equal([{}], [{}]))

    def test_multiple_empty_dicts(self):
        self.assertTrue(list_of_dicts_strict_equal([{}, {}], [{}, {}]))

    def test_simple_dicts(self):
        self.assertTrue(
            list_of_dicts_strict_equal(
                [
                    {"a": 1},
                ],
                [
                    {"a": 1},
                ],
            )
        )

        self.assertFalse(
            list_of_dicts_strict_equal(
                [
                    {"a": 1},
                ],
                [
                    {"a": 2},
                ],
            )
        )

    def test_lists_of_different_lengths(self):
        self.assertFalse(
            list_of_dicts_strict_equal(
                [
                    {"a": 1},
                ],
                [
                    {"a": 1},
                    {"b": 2},
                ],
            )
        )

        self.assertFalse(
            list_of_dicts_strict_equal(
                [
                    {"a": 1},
                    {"b": 2},
                ],
                [
                    {"a": 1},
                ],
            )
        )

    def test_less_simple_dicts(self):
        self.assertTrue(
            list_of_dicts_strict_equal(
                [
                    {"a": 1},
                    {"b": 2},
                ],
                [
                    {"a": 1},
                    {"b": 2},
                ],
            )
        )

        self.assertTrue(
            list_of_dicts_strict_equal(
                [
                    {"a": 1},
                    {"a": 1},
                ],
                [
                    {"a": 1},
                    {"a": 1},
                ],
            )
        )

        self.assertFalse(
            list_of_dicts_strict_equal(
                [
                    {"a": 1},
                    {"a": 1},
                ],
                [
                    {"a": 1},
                    {"b": 2},
                ],
            )
        )

        self.assertFalse(
            list_of_dicts_strict_equal(
                [
                    {"a": 1},
                    {"b": 2},
                ],
                [
                    {"a": 1},
                    {"a": 1},
                ],
            )
        )


class SearchOperatorTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        tests_config.parse_args()

    # The search command extends the rules engine into being a recursive descent
    # parser. As such, its tests are much more complex than other commands, so we
    # pull its tests out into their own test case.
    def test_search_with_weird_condition(self):
        op = operators.get_operator("search")

        with self.assertRaises(operators.UnrecognizedConditionError):
            op([], [], "weird", None)

    def test_search_any_true(self):
        op = operators.get_operator("search")

        called_function_args = []

        def record_function_args(criterion_k, criterion_v, payload_lookup):
            called_function_args.append(
                {
                    "criterion_k": criterion_k,
                    "criterion_v": criterion_v,
                    "payload_lookup": {
                        "field_name": payload_lookup.get_value("item.field_name")[0],
                        "to_value": payload_lookup.get_value("item.to_value")[0],
                    },
                }
            )
            return len(called_function_args) < 3

        payload = [
            {
                "field_name": "Status",
                "to_value": "Approved",
            },
            {
                "field_name": "Assigned to",
                "to_value": "Stanley",
            },
        ]

        criteria_pattern = {
            "item.field_name": {
                "type": "equals",
                "pattern": "Status",
            },
            "item.to_value": {
                "type": "equals",
                "pattern": "Approved",
            },
        }

        result = op(payload, criteria_pattern, "any", record_function_args)

        self.assertTrue(result)
        self.assertTrue(
            list_of_dicts_strict_equal(
                called_function_args,
                [
                    # Outer loop: payload -> {'field_name': "Status", 'to_value': "Approved"}
                    {
                        # Inner loop: criterion -> item.field_name: {'type': "equals", 'pattern': "Status"}
                        "criterion_k": "item.field_name",
                        "criterion_v": {
                            "type": "equals",
                            "pattern": "Status",
                        },
                        "payload_lookup": {
                            "field_name": "Status",
                            "to_value": "Approved",
                        },
                    },
                    {
                        # Inner loop: criterion -> item.to_value: {'type': "equals", 'pattern': "Approved"}
                        "criterion_k": "item.to_value",
                        "criterion_v": {
                            "type": "equals",
                            "pattern": "Approved",
                        },
                        "payload_lookup": {
                            "field_name": "Status",
                            "to_value": "Approved",
                        },
                    },
                    # Outer loop: payload -> {'field_name': "Assigned to", 'to_value': "Stanley"}
                    {
                        # Inner loop: criterion -> item.field_name: {'type': "equals", 'pattern': "Status"}
                        "criterion_k": "item.field_name",
                        "criterion_v": {
                            "type": "equals",
                            "pattern": "Status",
                        },
                        "payload_lookup": {
                            "field_name": "Assigned to",
                            "to_value": "Stanley",
                        },
                    },
                    {
                        # Inner loop: criterion -> item.to_value: {'type': "equals", 'pattern': "Approved"}
                        "criterion_k": "item.to_value",
                        "criterion_v": {
                            "type": "equals",
                            "pattern": "Approved",
                        },
                        "payload_lookup": {
                            "field_name": "Assigned to",
                            "to_value": "Stanley",
                        },
                    },
                ],
            )
        )

    def test_search_any_false(self):
        op = operators.get_operator("search")

        called_function_args = []

        def record_function_args(criterion_k, criterion_v, payload_lookup):
            called_function_args.append(
                {
                    "criterion_k": criterion_k,
                    "criterion_v": criterion_v,
                    "payload_lookup": {
                        "field_name": payload_lookup.get_value("item.field_name")[0],
                        "to_value": payload_lookup.get_value("item.to_value")[0],
                    },
                }
            )
            return (len(called_function_args) % 2) == 0

        payload = [
            {
                "field_name": "Status",
                "to_value": "Denied",
            },
            {
                "field_name": "Assigned to",
                "to_value": "Stanley",
            },
        ]

        criteria_pattern = {
            "item.field_name": {
                "type": "equals",
                "pattern": "Status",
            },
            "item.to_value": {
                "type": "equals",
                "pattern": "Approved",
            },
        }

        result = op(payload, criteria_pattern, "any", record_function_args)

        self.assertFalse(result)
        self.assertEqual(
            called_function_args,
            [
                # Outer loop: payload -> {'field_name': "Status", 'to_value': "Denied"}
                {
                    # Inner loop: criterion -> item.field_name: {'type': "equals", 'pattern': "Status"}
                    "criterion_k": "item.field_name",
                    "criterion_v": {
                        "type": "equals",
                        "pattern": "Status",
                    },
                    "payload_lookup": {
                        "field_name": "Status",
                        "to_value": "Denied",
                    },
                },
                {
                    # Inner loop: criterion -> item.to_value: {'type': "equals", 'pattern': "Approved"}
                    "criterion_k": "item.to_value",
                    "criterion_v": {
                        "type": "equals",
                        "pattern": "Approved",
                    },
                    "payload_lookup": {
                        "field_name": "Status",
                        "to_value": "Denied",
                    },
                },
                # Outer loop: payload -> {'field_name': "Assigned to", 'to_value': "Stanley"}
                {
                    # Inner loop: criterion -> item.to_value: {'type': "equals", 'pattern': "Approved"}
                    "criterion_k": "item.field_name",
                    "criterion_v": {
                        "type": "equals",
                        "pattern": "Status",
                    },
                    "payload_lookup": {
                        "field_name": "Assigned to",
                        "to_value": "Stanley",
                    },
                },
                {
                    # Inner loop: criterion -> item.to_value: {'type': "equals", 'pattern': "Approved"}
                    "criterion_k": "item.to_value",
                    "criterion_v": {
                        "type": "equals",
                        "pattern": "Approved",
                    },
                    "payload_lookup": {
                        "field_name": "Assigned to",
                        "to_value": "Stanley",
                    },
                },
            ],
        )

    def test_search_all_false(self):
        op = operators.get_operator("search")

        called_function_args = []

        def record_function_args(criterion_k, criterion_v, payload_lookup):
            called_function_args.append(
                {
                    "criterion_k": criterion_k,
                    "criterion_v": criterion_v,
                    "payload_lookup": {
                        "field_name": payload_lookup.get_value("item.field_name")[0],
                        "to_value": payload_lookup.get_value("item.to_value")[0],
                    },
                }
            )
            return (len(called_function_args) % 2) == 0

        payload = [
            {
                "field_name": "Status",
                "to_value": "Approved",
            },
            {
                "field_name": "Assigned to",
                "to_value": "Stanley",
            },
        ]

        criteria_pattern = {
            "item.field_name": {
                "type": "equals",
                "pattern": "Status",
            },
            "item.to_value": {
                "type": "equals",
                "pattern": "Approved",
            },
        }

        result = op(payload, criteria_pattern, "all", record_function_args)

        self.assertFalse(result)
        self.assertEqual(
            called_function_args,
            [
                # Outer loop: payload -> {'field_name': "Status", 'to_value': "Approved"}
                {
                    # Inner loop: item.field_name -> {'type': "equals", 'pattern': "Status"}
                    "criterion_k": "item.field_name",
                    "criterion_v": {
                        "type": "equals",
                        "pattern": "Status",
                    },
                    "payload_lookup": {
                        "field_name": "Status",
                        "to_value": "Approved",
                    },
                },
                {
                    # Inner loop: item.to_value -> {'type': "equals", 'pattern': "Approved"}
                    "criterion_k": "item.to_value",
                    "criterion_v": {
                        "type": "equals",
                        "pattern": "Approved",
                    },
                    "payload_lookup": {
                        "field_name": "Status",
                        "to_value": "Approved",
                    },
                },
                # Outer loop: payload -> {'field_name': "Assigned to", 'to_value': "Stanley"}
                {
                    # Inner loop: item.field_name -> {'type': "equals", 'pattern': "Status"}
                    "criterion_k": "item.field_name",
                    "criterion_v": {
                        "type": "equals",
                        "pattern": "Status",
                    },
                    "payload_lookup": {
                        "field_name": "Assigned to",
                        "to_value": "Stanley",
                    },
                },
                {
                    # Inner loop: item.to_value -> {'type': "equals", 'pattern': "Approved"}
                    "criterion_k": "item.to_value",
                    "criterion_v": {
                        "type": "equals",
                        "pattern": "Approved",
                    },
                    "payload_lookup": {
                        "field_name": "Assigned to",
                        "to_value": "Stanley",
                    },
                },
            ],
        )

    def test_search_all_true(self):
        op = operators.get_operator("search")

        called_function_args = []

        def record_function_args(criterion_k, criterion_v, payload_lookup):
            called_function_args.append(
                {
                    "criterion_k": criterion_k,
                    "criterion_v": criterion_v,
                    "payload_lookup": {
                        "field_name": payload_lookup.get_value("item.field_name")[0],
                        "to_value": payload_lookup.get_value("item.to_value")[0],
                    },
                }
            )
            return True

        payload = [
            {
                "field_name": "Status",
                "to_value": "Approved",
            },
            {
                "field_name": "Signed off by",
                "to_value": "Approved",
            },
        ]

        criteria_pattern = {
            "item.field_name": {
                "type": "startswith",
                "pattern": "S",
            },
            "item.to_value": {
                "type": "equals",
                "pattern": "Approved",
            },
        }

        result = op(payload, criteria_pattern, "all", record_function_args)

        self.assertTrue(result)
        self.assertEqual(
            called_function_args,
            [
                # Outer loop: payload -> {'field_name': "Status", 'to_value': "Approved"}
                {
                    # Inner loop: item.field_name -> {'type': "startswith", 'pattern': "S"}
                    "criterion_k": "item.field_name",
                    "criterion_v": {
                        "type": "startswith",
                        "pattern": "S",
                    },
                    "payload_lookup": {
                        "field_name": "Status",
                        "to_value": "Approved",
                    },
                },
                {
                    # Inner loop: item.to_value -> {'type': "equals", 'pattern': "Approved"}
                    "criterion_k": "item.to_value",
                    "criterion_v": {
                        "type": "equals",
                        "pattern": "Approved",
                    },
                    "payload_lookup": {
                        "field_name": "Status",
                        "to_value": "Approved",
                    },
                },
                # Outer loop: payload -> {'field_name': "Signed off by", 'to_value': "Approved"}
                {
                    # Inner loop: item.field_name -> {'type': "startswith", 'pattern': "S"}
                    "criterion_k": "item.field_name",
                    "criterion_v": {
                        "type": "startswith",
                        "pattern": "S",
                    },
                    "payload_lookup": {
                        "field_name": "Signed off by",
                        "to_value": "Approved",
                    },
                },
                {
                    # Inner loop: item.to_value -> {'type': "equals", 'pattern': "Approved"}
                    "criterion_k": "item.to_value",
                    "criterion_v": {
                        "type": "equals",
                        "pattern": "Approved",
                    },
                    "payload_lookup": {
                        "field_name": "Signed off by",
                        "to_value": "Approved",
                    },
                },
            ],
        )

    def _test_function(self, criterion_k, criterion_v, payload_lookup):
        op = operators.get_operator(criterion_v["type"])
        return op(payload_lookup.get_value("item.to_value")[0], criterion_v["pattern"])

    def test_search_any2any(self):
        # true if any payload items match any criteria
        op = operators.get_operator("search")

        payload = [
            {
                "field_name": "waterLevel",
                "to_value": 30,
            },
            {
                "field_name": "waterLevel",
                "to_value": 45,
            },
        ]

        criteria_pattern = {
            "item.waterLevel#1": {
                "type": "lessthan",
                "pattern": 40,
            },
            "item.waterLevel#2": {
                "type": "greaterthan",
                "pattern": 50,
            },
        }

        result = op(payload, criteria_pattern, "any2any", self._test_function)
        self.assertTrue(result)

        payload[0]["to_value"] = 44

        result = op(payload, criteria_pattern, "any2any", self._test_function)
        self.assertFalse(result)

    def test_search_any(self):
        # true if any payload items match all criteria
        op = operators.get_operator("search")
        payload = [
            {
                "field_name": "waterLevel",
                "to_value": 45,
            },
            {
                "field_name": "waterLevel",
                "to_value": 20,
            },
        ]

        criteria_pattern = {
            "item.waterLevel#1": {
                "type": "greaterthan",
                "pattern": 40,
            },
            "item.waterLevel#2": {
                "type": "lessthan",
                "pattern": 50,
            },
            "item.waterLevel#3": {
                "type": "equals",
                "pattern": 46,
            },
        }

        result = op(payload, criteria_pattern, "any", self._test_function)
        self.assertFalse(result)

        payload[0]["to_value"] = 46

        result = op(payload, criteria_pattern, "any", self._test_function)
        self.assertTrue(result)

        payload[0]["to_value"] = 45
        del criteria_pattern["item.waterLevel#3"]

        result = op(payload, criteria_pattern, "any", self._test_function)
        self.assertTrue(result)

    def test_search_all2any(self):
        # true if all payload items match any criteria
        op = operators.get_operator("search")
        payload = [
            {
                "field_name": "waterLevel",
                "to_value": 45,
            },
            {
                "field_name": "waterLevel",
                "to_value": 20,
            },
        ]

        criteria_pattern = {
            "item.waterLevel#1": {
                "type": "greaterthan",
                "pattern": 40,
            },
            "item.waterLevel#2": {
                "type": "lessthan",
                "pattern": 50,
            },
            "item.waterLevel#3": {
                "type": "equals",
                "pattern": 46,
            },
        }

        result = op(payload, criteria_pattern, "all2any", self._test_function)
        self.assertTrue(result)

        criteria_pattern["item.waterLevel#2"]["type"] = "greaterthan"

        result = op(payload, criteria_pattern, "all2any", self._test_function)
        self.assertFalse(result)

    def test_search_all(self):
        # true if all payload items match all criteria items
        op = operators.get_operator("search")
        payload = [
            {
                "field_name": "waterLevel",
                "to_value": 45,
            },
            {
                "field_name": "waterLevel",
                "to_value": 46,
            },
        ]

        criteria_pattern = {
            "item.waterLevel#1": {
                "type": "greaterthan",
                "pattern": 40,
            },
            "item.waterLevel#2": {
                "type": "lessthan",
                "pattern": 50,
            },
        }

        result = op(payload, criteria_pattern, "all", self._test_function)
        self.assertTrue(result)

        payload[0]["to_value"] = 30

        result = op(payload, criteria_pattern, "all", self._test_function)
        self.assertFalse(result)

        payload[0]["to_value"] = 45

        criteria_pattern["item.waterLevel#3"] = {
            "type": "equals",
            "pattern": 46,
        }

        result = op(payload, criteria_pattern, "all", self._test_function)
        self.assertFalse(result)

    def test_search_payload_dict(self):
        op = operators.get_operator("search")
        payload = {
            "field_name": "waterLevel",
            "to_value": 45,
        }

        criteria_pattern = {
            "item.waterLevel#1": {
                "type": "greaterthan",
                "pattern": 40,
            },
            "item.waterLevel#2": {
                "type": "lessthan",
                "pattern": 50,
            },
        }

        result = op(payload, criteria_pattern, "all", self._test_function)
        self.assertTrue(result)

        payload["to_value"] = 30

        result = op(payload, criteria_pattern, "all", self._test_function)
        self.assertFalse(result)

        payload["to_value"] = 45

        criteria_pattern["item.waterLevel#3"] = {
            "type": "equals",
            "pattern": 46,
        }

        result = op(payload, criteria_pattern, "all", self._test_function)
        self.assertFalse(result)


class OperatorTest(unittest.TestCase):
    def test_matchwildcard(self):
        op = operators.get_operator("matchwildcard")
        self.assertTrue(op("v1", "v1"), "Failed matchwildcard.")

        self.assertFalse(op("test foo test", "foo"), "Passed matchwildcard.")
        self.assertTrue(op("test foo test", "*foo*"), "Failed matchwildcard.")
        self.assertTrue(op("bar", "b*r"), "Failed matchwildcard.")
        self.assertTrue(op("bar", "b?r"), "Failed matchwildcard.")

        # Mixing bytes and strings / unicode should still work
        self.assertTrue(op(b"bar", "b?r"), "Failed matchwildcard.")
        self.assertTrue(op("bar", b"b?r"), "Failed matchwildcard.")
        self.assertTrue(op(b"bar", b"b?r"), "Failed matchwildcard.")
        self.assertTrue(op("bar", b"b?r"), "Failed matchwildcard.")
        self.assertTrue(op("bar", "b?r"), "Failed matchwildcard.")

        self.assertFalse(
            op("1", None), "Passed matchwildcard with None as criteria_pattern."
        )

    def test_matchregex(self):
        op = operators.get_operator("matchregex")
        self.assertTrue(op("v1", "v1$"), "Failed matchregex.")

        # Multi line string, make sure re.DOTALL is used
        string = """ponies
        moar
        foo
        bar
        yeah!
        """
        self.assertTrue(op(string, ".*bar.*"), "Failed matchregex.")

        string = "foo\r\nponies\nbar\nfooooo"
        self.assertTrue(op(string, ".*ponies.*"), "Failed matchregex.")

        # Mixing bytes and strings / unicode should still work
        self.assertTrue(op(b"foo ponies bar", ".*ponies.*"), "Failed matchregex.")
        self.assertTrue(op("foo ponies bar", b".*ponies.*"), "Failed matchregex.")
        self.assertTrue(op(b"foo ponies bar", b".*ponies.*"), "Failed matchregex.")
        self.assertTrue(op(b"foo ponies bar", ".*ponies.*"), "Failed matchregex.")
        self.assertTrue(op("foo ponies bar", ".*ponies.*"), "Failed matchregex.")

    def test_iregex(self):
        op = operators.get_operator("iregex")
        self.assertTrue(op("V1", "v1$"), "Failed iregex.")

        string = "fooPONIESbarfooooo"
        self.assertTrue(op(string, "ponies"), "Failed iregex.")

        # Mixing bytes and strings / unicode should still work
        self.assertTrue(op(b"fooPONIESbarfooooo", "ponies"), "Failed iregex.")
        self.assertTrue(op("fooPONIESbarfooooo", b"ponies"), "Failed iregex.")
        self.assertTrue(op(b"fooPONIESbarfooooo", b"ponies"), "Failed iregex.")
        self.assertTrue(op(b"fooPONIESbarfooooo", "ponies"), "Failed iregex.")
        self.assertTrue(op("fooPONIESbarfooooo", "ponies"), "Failed iregex.")

    def test_iregex_fail(self):
        op = operators.get_operator("iregex")
        self.assertFalse(op("V1_foo", "v1$"), "Passed iregex.")
        self.assertFalse(op("1", None), "Passed iregex with None as criteria_pattern.")

    def test_regex(self):
        op = operators.get_operator("regex")
        self.assertTrue(op("v1", "v1$"), "Failed regex.")

        string = "fooponiesbarfooooo"
        self.assertTrue(op(string, "ponies"), "Failed regex.")

        # Example with | modifier
        string = "apple ponies oranges"
        self.assertTrue(op(string, "(ponies|unicorns)"), "Failed regex.")

        string = "apple unicorns oranges"
        self.assertTrue(op(string, "(ponies|unicorns)"), "Failed regex.")

        # Mixing bytes and strings / unicode should still work
        self.assertTrue(
            op(b"apples unicorns oranges", "(ponies|unicorns)"), "Failed regex."
        )
        self.assertTrue(
            op("apples unicorns oranges", b"(ponies|unicorns)"), "Failed regex."
        )
        self.assertTrue(
            op(b"apples unicorns oranges", b"(ponies|unicorns)"), "Failed regex."
        )
        self.assertTrue(
            op(b"apples unicorns oranges", "(ponies|unicorns)"), "Failed regex."
        )
        self.assertTrue(
            op("apples unicorns oranges", "(ponies|unicorns)"), "Failed regex."
        )

        string = "apple unicorns oranges"
        self.assertFalse(op(string, "(pikachu|snorlax|charmander)"), "Passed regex.")

    def test_regex_fail(self):
        op = operators.get_operator("regex")
        self.assertFalse(op("v1_foo", "v1$"), "Passed regex.")

        string = "fooPONIESbarfooooo"
        self.assertFalse(op(string, "ponies"), "Passed regex.")

        self.assertFalse(op("1", None), "Passed regex with None as criteria_pattern.")

    def test_matchregex_case_variants(self):
        op = operators.get_operator("MATCHREGEX")
        self.assertTrue(op("v1", "v1$"), "Failed matchregex.")
        op = operators.get_operator("MATCHregex")
        self.assertTrue(op("v1", "v1$"), "Failed matchregex.")

    def test_matchregex_fail(self):
        op = operators.get_operator("matchregex")
        self.assertFalse(op("v1_foo", "v1$"), "Passed matchregex.")
        self.assertFalse(
            op("1", None), "Passed matchregex with None as criteria_pattern."
        )

    def test_equals_numeric(self):
        op = operators.get_operator("equals")
        self.assertTrue(op(1, 1), "Failed equals.")

    def test_equals_string(self):
        op = operators.get_operator("equals")
        self.assertTrue(op("1", "1"), "Failed equals.")
        self.assertTrue(op("", ""), "Failed equals.")

        # Mixing bytes and strings / unicode should still work
        self.assertTrue(op(b"1", "1"), "Failed equals.")
        self.assertTrue(op("1", b"1"), "Failed equals.")
        self.assertTrue(op(b"1", b"1"), "Failed equals.")
        self.assertTrue(op(b"1", "1"), "Failed equals.")
        self.assertTrue(op("1", "1"), "Failed equals.")

    def test_equals_fail(self):
        op = operators.get_operator("equals")
        self.assertFalse(op("1", "2"), "Passed equals.")
        self.assertFalse(op("1", None), "Passed equals with None as criteria_pattern.")

    def test_nequals(self):
        op = operators.get_operator("nequals")
        self.assertTrue(op("foo", "bar"))
        self.assertTrue(op("foo", "foo1"))
        self.assertTrue(op("foo", "FOO"))
        self.assertTrue(op("True", True))
        self.assertTrue(op("None", None))

        self.assertFalse(op("True", "True"))
        self.assertFalse(op(None, None))

    def test_iequals(self):
        op = operators.get_operator("iequals")
        self.assertTrue(op("ABC", "ABC"), "Failed iequals.")
        self.assertTrue(op("ABC", "abc"), "Failed iequals.")
        self.assertTrue(op("AbC", "aBc"), "Failed iequals.")

        # Mixing bytes and strings / unicode should still work
        self.assertTrue(op(b"AbC", "aBc"), "Failed iequals.")
        self.assertTrue(op("AbC", b"aBc"), "Failed iequals.")
        self.assertTrue(op(b"AbC", b"aBc"), "Failed iequals.")
        self.assertTrue(op(b"AbC", "aBc"), "Failed iequals.")
        self.assertTrue(op("AbC", "aBc"), "Failed iequals.")

    def test_iequals_fail(self):
        op = operators.get_operator("iequals")
        self.assertFalse(op("ABC", "BCA"), "Passed iequals.")
        self.assertFalse(op("1", None), "Passed iequals with None as criteria_pattern.")

    def test_contains(self):
        op = operators.get_operator("contains")
        self.assertTrue(op("hasystack needle haystack", "needle"))
        self.assertTrue(op("needle", "needle"))
        self.assertTrue(op("needlehaystack", "needle"))
        self.assertTrue(op("needle haystack", "needle"))
        self.assertTrue(op("haystackneedle", "needle"))
        self.assertTrue(op("haystack needle", "needle"))

        # Mixing bytes and strings / unicode should still work
        self.assertTrue(op(b"haystack needle", "needle"))
        self.assertTrue(op("haystack needle", b"needle"))
        self.assertTrue(op(b"haystack needle", b"needle"))
        self.assertTrue(op(b"haystack needle", "needle"))
        self.assertTrue(op("haystack needle", b"needle"))

    def test_contains_fail(self):
        op = operators.get_operator("contains")
        self.assertFalse(op("hasystack needl haystack", "needle"))
        self.assertFalse(op("needla", "needle"))
        self.assertFalse(
            op("1", None), "Passed contains with None as criteria_pattern."
        )

    def test_icontains(self):
        op = operators.get_operator("icontains")
        self.assertTrue(op("hasystack nEEdle haystack", "needle"))
        self.assertTrue(op("neeDle", "NeedlE"))
        self.assertTrue(op("needlehaystack", "needle"))
        self.assertTrue(op("NEEDLE haystack", "NEEDLE"))
        self.assertTrue(op("haystackNEEDLE", "needle"))
        self.assertTrue(op("haystack needle", "NEEDLE"))

        # Mixing bytes and strings / unicode should still work
        self.assertTrue(op(b"haystack needle", "NEEDLE"))
        self.assertTrue(op("haystack needle", b"NEEDLE"))
        self.assertTrue(op(b"haystack needle", b"NEEDLE"))
        self.assertTrue(op(b"haystack needle", "NEEDLE"))
        self.assertTrue(op("haystack needle", b"NEEDLE"))

    def test_icontains_fail(self):
        op = operators.get_operator("icontains")
        self.assertFalse(op("hasystack needl haystack", "needle"))
        self.assertFalse(op("needla", "needle"))
        self.assertFalse(
            op("1", None), "Passed icontains with None as criteria_pattern."
        )

    def test_ncontains(self):
        op = operators.get_operator("ncontains")
        self.assertTrue(op("hasystack needle haystack", "foo"))
        self.assertTrue(op("needle", "foo"))
        self.assertTrue(op("needlehaystack", "needlex"))
        self.assertTrue(op("needle haystack", "needlex"))
        self.assertTrue(op("haystackneedle", "needlex"))
        self.assertTrue(op("haystack needle", "needlex"))

        # Mixing bytes and strings / unicode should still work
        self.assertTrue(op(b"haystack needle", "needlex"))
        self.assertTrue(op("haystack needle", b"needlex"))
        self.assertTrue(op(b"haystack needle", b"needlex"))
        self.assertTrue(op(b"haystack needle", "needlex"))
        self.assertTrue(op("haystack needle", b"needlex"))

    def test_ncontains_fail(self):
        op = operators.get_operator("ncontains")
        self.assertFalse(op("hasystack needle haystack", "needle"))
        self.assertFalse(op("needla", "needla"))
        self.assertFalse(
            op("1", None), "Passed ncontains with None as criteria_pattern."
        )

    def test_incontains(self):
        op = operators.get_operator("incontains")
        self.assertTrue(op("hasystack needle haystack", "FOO"))
        self.assertTrue(op("needle", "FOO"))
        self.assertTrue(op("needlehaystack", "needlex"))
        self.assertTrue(op("needle haystack", "needlex"))
        self.assertTrue(op("haystackneedle", "needlex"))
        self.assertTrue(op("haystack needle", "needlex"))

    def test_incontains_fail(self):
        op = operators.get_operator("incontains")
        self.assertFalse(op("hasystack needle haystack", "nEeDle"))
        self.assertFalse(op("needlA", "needlA"))
        self.assertFalse(
            op("1", None), "Passed incontains with None as criteria_pattern."
        )

    def test_startswith(self):
        op = operators.get_operator("startswith")
        self.assertTrue(op("hasystack needle haystack", "hasystack"))
        self.assertTrue(op("a hasystack needle haystack", "a "))

        # Mixing bytes and strings / unicode should still work
        self.assertTrue(op(b"haystack needle", "haystack"))
        self.assertTrue(op("haystack needle", b"haystack"))
        self.assertTrue(op(b"haystack needle", b"haystack"))
        self.assertTrue(op(b"haystack needle", "haystack"))
        self.assertTrue(op("haystack needle", b"haystack"))

    def test_startswith_fail(self):
        op = operators.get_operator("startswith")
        self.assertFalse(op("hasystack needle haystack", "needle"))
        self.assertFalse(op("a hasystack needle haystack", "haystack"))
        self.assertFalse(
            op("1", None), "Passed startswith with None as criteria_pattern."
        )

    def test_istartswith(self):
        op = operators.get_operator("istartswith")
        self.assertTrue(op("haystack needle haystack", "HAYstack"))
        self.assertTrue(op("HAYSTACK needle haystack", "haystack"))

        # Mixing bytes and strings / unicode should still work
        self.assertTrue(op(b"HAYSTACK needle haystack", "haystack"))
        self.assertTrue(op("HAYSTACK needle haystack", b"haystack"))
        self.assertTrue(op(b"HAYSTACK needle haystack", b"haystack"))
        self.assertTrue(op(b"HAYSTACK needle haystack", "haystack"))
        self.assertTrue(op("HAYSTACK needle haystack", b"haystack"))

    def test_istartswith_fail(self):
        op = operators.get_operator("istartswith")
        self.assertFalse(op("hasystack needle haystack", "NEEDLE"))
        self.assertFalse(op("a hasystack needle haystack", "haystack"))
        self.assertFalse(
            op("1", None), "Passed istartswith with None as criteria_pattern."
        )

    def test_endswith(self):
        op = operators.get_operator("endswith")
        self.assertTrue(op("hasystack needle haystackend", "haystackend"))
        self.assertTrue(op("a hasystack needle haystack b", "b"))

        # Mixing bytes and strings / unicode should still work
        self.assertTrue(op(b"a hasystack needle haystack b", "b"))
        self.assertTrue(op("a hasystack needle haystack b", b"b"))
        self.assertTrue(op(b"a hasystack needle haystack b", b"b"))
        self.assertTrue(op(b"a hasystack needle haystack b", "b"))
        self.assertTrue(op("a hasystack needle haystack b", b"b"))

    def test_endswith_fail(self):
        op = operators.get_operator("endswith")
        self.assertFalse(op("hasystack needle haystackend", "haystack"))
        self.assertFalse(op("a hasystack needle haystack", "a"))
        self.assertFalse(
            op("1", None), "Passed endswith with None as criteria_pattern."
        )

    def test_iendswith(self):
        op = operators.get_operator("iendswith")
        self.assertTrue(op("haystack needle haystackEND", "HAYstackend"))
        self.assertTrue(op("HAYSTACK needle haystackend", "haystackEND"))

    def test_iendswith_fail(self):
        op = operators.get_operator("iendswith")
        self.assertFalse(op("hasystack needle haystack", "NEEDLE"))
        self.assertFalse(op("a hasystack needle haystack", "a "))
        self.assertFalse(
            op("1", None), "Passed iendswith with None as criteria_pattern."
        )

    def test_lt(self):
        op = operators.get_operator("lessthan")
        self.assertTrue(op(1, 2), "Failed lessthan.")

    def test_lt_char(self):
        op = operators.get_operator("lessthan")
        self.assertTrue(op("a", "b"), "Failed lessthan.")

    def test_lt_fail(self):
        op = operators.get_operator("lessthan")
        self.assertFalse(op(1, 1), "Passed lessthan.")
        self.assertFalse(
            op("1", None), "Passed lessthan with None as criteria_pattern."
        )

    def test_gt(self):
        op = operators.get_operator("greaterthan")
        self.assertTrue(op(2, 1), "Failed greaterthan.")

    def test_gt_str(self):
        op = operators.get_operator("lessthan")
        self.assertTrue(op("aba", "bcb"), "Failed greaterthan.")

    def test_gt_fail(self):
        op = operators.get_operator("greaterthan")
        self.assertFalse(op(2, 3), "Passed greaterthan.")
        self.assertFalse(
            op("1", None), "Passed greaterthan with None as criteria_pattern."
        )

    def test_timediff_lt(self):
        op = operators.get_operator("timediff_lt")
        self.assertTrue(
            op(date_utils.get_datetime_utc_now().isoformat(), 10),
            "Failed test_timediff_lt.",
        )

    def test_timediff_lt_fail(self):
        op = operators.get_operator("timediff_lt")
        self.assertFalse(
            op("2014-07-01T00:01:01.000000", 10), "Passed test_timediff_lt."
        )
        self.assertFalse(
            op("2014-07-01T00:01:01.000000", None),
            "Passed test_timediff_lt with None as criteria_pattern.",
        )

    def test_timediff_lt_webui_value(self):
        op = operators.get_operator("timediff_lt")
        self.assertTrue(
            op(date_utils.get_datetime_utc_now().isoformat(), "10"),
            "Failed test_timediff_lt_webui_value.",
        )

    def test_timediff_lt_webui_value_fail(self):
        op = operators.get_operator("timediff_lt")
        self.assertFalse(
            op("2014-07-01T00:01:01.000000", "10"),
            "Passed test_timediff_lt_webui_value.",
        )

    def test_timediff_gt(self):
        op = operators.get_operator("timediff_gt")
        self.assertTrue(op("2014-07-01T00:01:01.000000", 1), "Failed test_timediff_gt.")

    def test_timediff_gt_fail(self):
        op = operators.get_operator("timediff_gt")
        self.assertFalse(
            op(date_utils.get_datetime_utc_now().isoformat(), 10),
            "Passed test_timediff_gt.",
        )
        self.assertFalse(
            op("2014-07-01T00:01:01.000000", None),
            "Passed test_timediff_gt with None as criteria_pattern.",
        )

    def test_timediff_gt_webui_value(self):
        op = operators.get_operator("timediff_gt")
        self.assertTrue(
            op("2014-07-01T00:01:01.000000", "1"),
            "Failed test_timediff_gt_webui_value.",
        )

    def test_timediff_gt_webui_value_fail(self):
        op = operators.get_operator("timediff_gt")
        self.assertFalse(
            op(date_utils.get_datetime_utc_now().isoformat(), "10"),
            "Passed test_timediff_gt_webui_value.",
        )

    def test_exists(self):
        op = operators.get_operator("exists")
        self.assertTrue(op(False, None), "Should return True")
        self.assertTrue(op(1, None), "Should return True")
        self.assertTrue(op("foo", None), "Should return True")
        self.assertFalse(op(None, None), "Should return False")

    def test_nexists(self):
        op = operators.get_operator("nexists")
        self.assertFalse(op(False, None), "Should return False")
        self.assertFalse(op(1, None), "Should return False")
        self.assertFalse(op("foo", None), "Should return False")
        self.assertTrue(op(None, None), "Should return True")

    def test_inside(self):
        op = operators.get_operator("inside")
        self.assertFalse(op("a", None), "Should return False")
        self.assertFalse(op("a", "bcd"), "Should return False")
        self.assertTrue(op("a", "abc"), "Should return True")

        # Mixing bytes and strings / unicode should still work
        self.assertTrue(op(b"a", "abc"), "Should return True")
        self.assertTrue(op("a", b"abc"), "Should return True")
        self.assertTrue(op(b"a", b"abc"), "Should return True")

    def test_ninside(self):
        op = operators.get_operator("ninside")
        self.assertFalse(op("a", None), "Should return False")
        self.assertFalse(op("a", "abc"), "Should return False")
        self.assertTrue(op("a", "bcd"), "Should return True")


class GetOperatorsTest(unittest.TestCase):
    def test_get_operator(self):
        self.assertTrue(operators.get_operator("equals"))
        self.assertTrue(operators.get_operator("EQUALS"))

    def test_get_operator_returns_same_operator_with_different_cases(self):
        equals = operators.get_operator("equals")
        EQUALS = operators.get_operator("EQUALS")
        Equals = operators.get_operator("Equals")
        self.assertEqual(equals, EQUALS)
        self.assertEqual(equals, Equals)

    def test_get_operator_with_nonexistent_operator(self):
        with self.assertRaises(Exception):
            operators.get_operator("weird")

    def test_get_allowed_operators(self):
        # This test will need to change as operators are deprecated
        self.assertGreater(len(operators.get_allowed_operators()), 0)

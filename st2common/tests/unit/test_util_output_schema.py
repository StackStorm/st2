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

import copy
import unittest

from st2common.util import output_schema

from st2common.constants.action import (
    LIVEACTION_STATUS_SUCCEEDED,
    LIVEACTION_STATUS_FAILED,
)

from st2common.constants.secrets import MASKED_ATTRIBUTE_VALUE

ACTION_RESULT = {
    "output": {
        "output_1": "Bobby",
        "output_2": 5,
        "output_3": "shhh!",
        "deep_output": {
            "deep_item_1": "Jindal",
            "extra_item_1": 42,
            "extra_item_2": 33,
        },
        "pattern_output": {
            "a": "x",
            "b": "y",
            "c": "z",
        },
        "array_output_1": [
            {"deep_item_1": "foo"},
            {"deep_item_1": "bar"},
            {"deep_item_1": "baz"},
        ],
        "array_output_2": ["answer", 4.2, True, False],
    }
}

ACTION_RESULT_ALT_TYPES = {
    "integer": {"output": 42},
    "null": {"output": None},
    "number": {"output": 1.234},
    "string": {"output": "foobar"},
    "object": {"output": {"prop": "value"}},
    "array": {"output": [{"prop": "value"}]},
}

ACTION_RESULT_BOOLEANS = {
    True: {"output": True},
    False: {"output": False},
}

RUNNER_OUTPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "output": {"type": "object"},
        "error": {"type": "array"},
    },
    "additionalProperties": False,
}

ACTION_OUTPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "output_1": {"type": "string"},
        "output_2": {"type": "integer"},
        "output_3": {"type": "string"},
        "deep_output": {
            "type": "object",
            "properties": {
                "deep_item_1": {"type": "string"},
            },
            "additionalProperties": {"type": "integer"},
        },
        "pattern_output": {
            "type": "object",
            "patternProperties": {
                "^\\w$": {"type": "string"},
            },
            "additionalProperties": False,
        },
        "array_output_1": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "deep_item_1": {"type": "string"},
                },
            },
        },
        "array_output_2": {
            "type": "array",
            "items": [
                {"type": "string"},
                {"type": "number"},
            ],
            "additionalItems": {"type": "boolean"},
        },
    },
    "additionalProperties": False,
}

RUNNER_OUTPUT_SCHEMA_FAIL = {
    "type": "object",
    "properties": {
        "not_a_key_you_have": {"type": "string"},
    },
    "additionalProperties": False,
}

ACTION_OUTPUT_SCHEMA_FAIL = {
    "type": "object",
    "properties": {
        "not_a_key_you_have": {"type": "string"},
    },
    "additionalProperties": False,
}

OUTPUT_KEY = "output"

ACTION_OUTPUT_SCHEMA_WITH_SECRET = {
    "type": "object",
    "properties": {
        "output_1": {"type": "string"},
        "output_2": {"type": "integer"},
        "output_3": {"type": "string", "secret": True},
        "deep_output": {
            "type": "object",
            "properties": {
                "deep_item_1": {"type": "string"},
            },
            "additionalProperties": {"type": "integer", "secret": True},
        },
        "pattern_output": {
            "type": "object",
            "patternProperties": {
                "^\\w$": {"type": "string", "secret": True},
            },
            "additionalProperties": False,
        },
        "array_output_1": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "deep_item_1": {"type": "string", "secret": True},
                },
            },
        },
        "array_output_2": {
            "type": "array",
            "items": [
                {"type": "string"},
                {"type": "number", "secret": True},
            ],
            "additionalItems": {"type": "boolean", "secret": True},
        },
    },
    "additionalProperties": False,
}

# Legacy schemas were implicitly a "properties" schema of an object.
# Now, this should be ignored as a malformed schema.
LEGACY_ACTION_OUTPUT_SCHEMA = ACTION_OUTPUT_SCHEMA_WITH_SECRET["properties"]

MALFORMED_ACTION_OUTPUT_SCHEMA_1 = {"output_1": "bool"}
MALFORMED_ACTION_OUTPUT_SCHEMA_2 = {
    "type": "object",
    "properties": {
        "output_1": "bool",
    },
    "additionalProperties": False,
}


class OutputSchemaTestCase(unittest.TestCase):
    def test_valid_schema(self):
        result, status = output_schema.validate_output(
            copy.deepcopy(RUNNER_OUTPUT_SCHEMA),
            copy.deepcopy(ACTION_OUTPUT_SCHEMA),
            copy.deepcopy(ACTION_RESULT),
            LIVEACTION_STATUS_SUCCEEDED,
            OUTPUT_KEY,
        )

        self.assertEqual(result, ACTION_RESULT)
        self.assertEqual(status, LIVEACTION_STATUS_SUCCEEDED)

    def test_invalid_runner_schema(self):
        result, status = output_schema.validate_output(
            copy.deepcopy(RUNNER_OUTPUT_SCHEMA_FAIL),
            copy.deepcopy(ACTION_OUTPUT_SCHEMA),
            copy.deepcopy(ACTION_RESULT),
            LIVEACTION_STATUS_SUCCEEDED,
            OUTPUT_KEY,
        )

        expected_result = {
            "error": (
                "Additional properties are not allowed ('output' was unexpected)\n\n"
                "Failed validating 'additionalProperties' in schema:\n"
                "    {'additionalProperties': False,\n"
                "     'properties': {'not_a_key_you_have': {'type': 'string'}},\n"
                "     'type': 'object'}\n\n"
                "On instance:\n"
                "    {'output': {'array_output_1': [{'deep_item_1': 'foo'},\n"
                "                                   {'deep_item_1': 'bar'},\n"
                "                                   {'deep_item_1': 'baz'}],\n"
                "                'array_output_2': ['answer', 4.2, True, False],\n"
                "                'deep_output': {'deep_item_1': 'Jindal',\n"
                "                                'extra_item_1': 42,\n"
                "                                'extra_item_2': 33},\n"
                "                'output_1': 'Bobby',\n"
                "                'output_2': 5,\n"
                "                'output_3': 'shhh!',\n"
                "                'pattern_output': {'a': 'x', 'b': 'y', 'c': 'z'}}}"
            ),
            "message": "Error validating output. See error output for more details.",
        }

        self.assertEqual(result, expected_result)
        self.assertEqual(status, LIVEACTION_STATUS_FAILED)

    def test_invalid_action_schema(self):
        result, status = output_schema.validate_output(
            copy.deepcopy(RUNNER_OUTPUT_SCHEMA),
            copy.deepcopy(ACTION_OUTPUT_SCHEMA_FAIL),
            copy.deepcopy(ACTION_RESULT),
            LIVEACTION_STATUS_SUCCEEDED,
            OUTPUT_KEY,
        )

        expected_result = {
            "error": "Additional properties are not allowed",
            "message": "Error validating output. See error output for more details.",
        }

        # To avoid random failures (especially in python3) this assert cant be
        # exact since the parameters can be ordered differently per execution.
        self.assertIn(expected_result["error"], result["error"])
        self.assertEqual(result["message"], expected_result["message"])
        self.assertEqual(status, LIVEACTION_STATUS_FAILED)

    def test_mask_secret_output(self):
        ac_ex = {
            "action": {
                "output_schema": ACTION_OUTPUT_SCHEMA_WITH_SECRET,
            },
            "runner": {
                "output_key": OUTPUT_KEY,
                "output_schema": RUNNER_OUTPUT_SCHEMA,
            },
        }

        expected_masked_output = {
            "output": {
                "output_1": "Bobby",
                "output_2": 5,
                "output_3": MASKED_ATTRIBUTE_VALUE,
                "deep_output": {
                    "deep_item_1": "Jindal",
                    "extra_item_1": MASKED_ATTRIBUTE_VALUE,
                    "extra_item_2": MASKED_ATTRIBUTE_VALUE,
                },
                "pattern_output": {
                    "a": MASKED_ATTRIBUTE_VALUE,
                    "b": MASKED_ATTRIBUTE_VALUE,
                    "c": MASKED_ATTRIBUTE_VALUE,
                },
                "array_output_1": [
                    {"deep_item_1": MASKED_ATTRIBUTE_VALUE},
                    {"deep_item_1": MASKED_ATTRIBUTE_VALUE},
                    {"deep_item_1": MASKED_ATTRIBUTE_VALUE},
                ],
                "array_output_2": [
                    "answer",
                    MASKED_ATTRIBUTE_VALUE,
                    MASKED_ATTRIBUTE_VALUE,
                    MASKED_ATTRIBUTE_VALUE,
                ],
            }
        }

        masked_output = output_schema.mask_secret_output(
            ac_ex, copy.deepcopy(ACTION_RESULT)
        )
        self.assertDictEqual(masked_output, expected_masked_output)

    def test_mask_secret_output_all_output(self):
        ac_ex = {
            "action": {
                "output_schema": {
                    "secret": True,
                },
            },
            "runner": {
                "output_key": OUTPUT_KEY,
                "output_schema": RUNNER_OUTPUT_SCHEMA,
            },
        }

        expected_masked_output = {"output": MASKED_ATTRIBUTE_VALUE}

        for kind, action_result in ACTION_RESULT_ALT_TYPES.items():
            ac_ex["action"]["output_schema"]["type"] = kind
            masked_output = output_schema.mask_secret_output(
                ac_ex, copy.deepcopy(action_result)
            )
            self.assertDictEqual(masked_output, expected_masked_output)

        for _, action_result in ACTION_RESULT_BOOLEANS.items():
            ac_ex["action"]["output_schema"]["type"] = "boolean"
            masked_output = output_schema.mask_secret_output(
                ac_ex, copy.deepcopy(action_result)
            )
            self.assertDictEqual(masked_output, expected_masked_output)

    def test_mask_secret_output_no_secret(self):
        ac_ex = {
            "action": {
                "output_schema": ACTION_OUTPUT_SCHEMA,
            },
            "runner": {
                "output_key": OUTPUT_KEY,
                "output_schema": RUNNER_OUTPUT_SCHEMA,
            },
        }

        expected_masked_output = copy.deepcopy(ACTION_RESULT)

        masked_output = output_schema.mask_secret_output(
            ac_ex, copy.deepcopy(ACTION_RESULT)
        )
        self.assertDictEqual(masked_output, expected_masked_output)

    def test_mask_secret_output_noop(self):
        ac_ex = {
            "action": {
                "output_schema": ACTION_OUTPUT_SCHEMA_WITH_SECRET,
            },
            "runner": {
                "output_key": OUTPUT_KEY,
                "output_schema": RUNNER_OUTPUT_SCHEMA,
            },
        }

        # The result is type of None.
        ac_ex_result = None
        expected_masked_output = None
        masked_output = output_schema.mask_secret_output(ac_ex, ac_ex_result)
        self.assertEqual(masked_output, expected_masked_output)

        # The result is empty.
        ac_ex_result = {}
        expected_masked_output = {}
        masked_output = output_schema.mask_secret_output(ac_ex, ac_ex_result)
        self.assertDictEqual(masked_output, expected_masked_output)

        # output_schema covers objects but output is not a dict/object.
        for _, action_result in ACTION_RESULT_ALT_TYPES.items():
            ac_ex_result = copy.deepcopy(action_result)
            expected_masked_output = copy.deepcopy(action_result)
            masked_output = output_schema.mask_secret_output(ac_ex, ac_ex_result)
            self.assertDictEqual(masked_output, expected_masked_output)

        # output_schema covers objects but output is a bool.
        for _, action_result in ACTION_RESULT_BOOLEANS.items():
            ac_ex_result = copy.deepcopy(action_result)
            expected_masked_output = copy.deepcopy(action_result)
            masked_output = output_schema.mask_secret_output(ac_ex, ac_ex_result)
            self.assertDictEqual(masked_output, expected_masked_output)

        # The output key is missing.
        ac_ex_result = {"output1": None}
        expected_masked_output = {"output1": None}
        masked_output = output_schema.mask_secret_output(ac_ex, ac_ex_result)
        self.assertDictEqual(masked_output, expected_masked_output)

    def test_mask_secret_output_with_legacy_schema(self):
        ac_ex = {
            "action": {
                "output_schema": LEGACY_ACTION_OUTPUT_SCHEMA,
            },
            "runner": {
                "output_key": OUTPUT_KEY,
                "output_schema": RUNNER_OUTPUT_SCHEMA,
            },
        }

        ac_ex_result = {OUTPUT_KEY: {"output_1": "foobar", "output_3": "fubar"}}

        expected_masked_output = {
            OUTPUT_KEY: {
                "output_1": "foobar",
                "output_3": MASKED_ATTRIBUTE_VALUE,
            }
        }

        # Legacy schemas are not full json schemas, but they should still mask secrets.
        masked_output = output_schema.mask_secret_output(ac_ex, ac_ex_result)
        self.assertDictEqual(masked_output, expected_masked_output)

    def test_mask_secret_output_noop_malformed_schema(self):
        # Malformed schemas can't be used to validate.
        ac_ex = {
            "action": {
                "output_schema": {},
            },
            "runner": {
                "output_key": OUTPUT_KEY,
                "output_schema": RUNNER_OUTPUT_SCHEMA,
            },
        }
        ac_ex_result = {"output_1": "foobar"}
        expected_masked_output = {"output_1": "foobar"}

        ac_ex["action"]["output_schema"] = MALFORMED_ACTION_OUTPUT_SCHEMA_1
        masked_output = output_schema.mask_secret_output(ac_ex, ac_ex_result)
        self.assertDictEqual(masked_output, expected_masked_output)

        ac_ex["action"]["output_schema"] = MALFORMED_ACTION_OUTPUT_SCHEMA_2
        masked_output = output_schema.mask_secret_output(ac_ex, ac_ex_result)
        self.assertDictEqual(masked_output, expected_masked_output)

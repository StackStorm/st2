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
import unittest2

from st2common.util import output_schema

from st2common.constants.action import (
    LIVEACTION_STATUS_SUCCEEDED,
    LIVEACTION_STATUS_FAILED,
)

from st2common.constants.exit_codes import FAILURE_EXIT_CODE
from st2common.constants.secrets import MASKED_ATTRIBUTE_VALUE

ACTION_RESULT = {
    "output": {
        "output_1": "Bobby",
        "output_2": 5,
        "output_3": "shhh!",
        "deep_output": {
            "deep_item_1": "Jindal",
        },
    }
}

RUNNER_OUTPUT_SCHEMA = {
    "output": {"type": "object"},
    "error": {"type": "array"},
}

ACTION_OUTPUT_SCHEMA = {
    "output_1": {"type": "string"},
    "output_2": {"type": "integer"},
    "output_3": {"type": "string"},
    "deep_output": {
        "type": "object",
        "parameters": {
            "deep_item_1": {
                "type": "string",
            },
        },
    },
}

RUNNER_OUTPUT_SCHEMA_FAIL = {
    "not_a_key_you_have": {"type": "string"},
}

ACTION_OUTPUT_SCHEMA_FAIL = {
    "not_a_key_you_have": {"type": "string"},
}

OUTPUT_KEY = "output"

ACTION_OUTPUT_SCHEMA_WITH_SECRET = {
    "output_1": {"type": "string"},
    "output_2": {"type": "integer"},
    "output_3": {"type": "string", "secret": True},
    "deep_output": {
        "type": "object",
        "parameters": {
            "deep_item_1": {
                "type": "string",
            },
        },
    },
}

RUNNER_OUTPUT_SCHEMA_FOR_VALIDATION = {
    "result": {
        "anyOf": [
            {"type": "object"},
            {"type": "string"},
            {"type": "integer"},
            {"type": "number"},
            {"type": "boolean"},
            {"type": "array"},
            {"type": "null"},
        ]
    },
    "stderr": {"type": "string", "required": True},
    "stdout": {"type": "string", "required": True},
    "exit_code": {"type": "integer", "required": True},
}

ACTION_OUTPUT_SCHEMA_FOR_STRING_TYPE_VALIDATION = {
    "output_1": {"type": "string"},
    "output_2": {"type": "string"},
    "output_3": {"type": "string"},
}


BAD_RESULT_FOR_STRING_TYPE_PARAMS = {
    "stdout": "",
    "stderr": "",
    "exit_code": 0,
    "result": {
        "output_1": "foo",
        "output_2": None,
        "output_3": 50,
    },
}

ACTION_OUTPUT_SCHEMA_FOR_OBJECT_TYPE_VALIDATION = {
    "output_1": {"type": "object"},
    "output_2": {"type": "object"},
    "output_3": {"type": "object"},
}


BAD_RESULT_FOR_OBJECT_TYPE_PARAMS = {
    "stdout": "",
    "stderr": "",
    "exit_code": 0,
    "result": {
        "output_1": {"a": "bar", "b": "baz"},
        "output_2": {"x": "abc", "y": "mnp"},
        "output_3": "foo",
    },
}


ACTION_OUTPUT_SCHEMA_FOR_INTEGER_TYPE_VALIDATION = {
    "output_1": {"type": "integer"},
    "output_2": {"type": "integer"},
    "output_3": {"type": "integer"},
}


BAD_RESULT_FOR_INTEGER_TYPE_PARAMS = {
    "stdout": "",
    "stderr": "",
    "exit_code": 0,
    "result": {
        "output_1": 50,
        "output_2": "foo",
        "output_3": {"a": "bar", "b": "baz"},
    },
}


class OutputSchemaTestCase(unittest2.TestCase):
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
            "exit_code": 1,
            "result": "None",
            "stderr": "Additional properties are not allowed ('output' was unexpected)\n\nFailed validating 'additionalProperties' in schema:\n    {'additionalProperties': False,\n     'properties': {'not_a_key_you_have': {'type': 'string'}},\n     'type': 'object'}\n\nOn instance:\n    {'output': {'deep_output': {'deep_item_1': 'Jindal'},\n                'output_1': 'Bobby',\n                'output_2': 5,\n                'output_3': 'shhh!'}}",
            "stdout": "",
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
            "exit_code": 1,
            "result": "None",
            "stderr": "Additional properties are not allowed",
            "stdout": "",
        }

        # To avoid random failures (especially in python3) this assert cant be
        # exact since the parameters can be ordered differently per execution.
        self.assertIn(expected_result["stderr"], result["stderr"])
        self.assertEqual(result["result"], expected_result["result"])
        self.assertEqual(result["exit_code"], expected_result["exit_code"])
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
                },
            }
        }

        masked_output = output_schema.mask_secret_output(
            ac_ex, copy.deepcopy(ACTION_RESULT)
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

        expected_masked_output = {
            "output": {
                "output_1": "Bobby",
                "output_2": 5,
                "output_3": "shhh!",
                "deep_output": {
                    "deep_item_1": "Jindal",
                },
            }
        }

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

        # The output is type of None.
        ac_ex_result = {"output": None}
        expected_masked_output = {"output": None}
        masked_output = output_schema.mask_secret_output(ac_ex, ac_ex_result)
        self.assertDictEqual(masked_output, expected_masked_output)

        # The output is not type of dict or list.
        ac_ex_result = {"output": "foobar"}
        expected_masked_output = {"output": "foobar"}
        masked_output = output_schema.mask_secret_output(ac_ex, ac_ex_result)
        self.assertDictEqual(masked_output, expected_masked_output)

        # The output key is missing.
        ac_ex_result = {"output1": None}
        expected_masked_output = {"output1": None}
        masked_output = output_schema.mask_secret_output(ac_ex, ac_ex_result)
        self.assertDictEqual(masked_output, expected_masked_output)

    def test_validation_of_output_schema_for_string_type_params(self):
        """
        Testing that output schema validation error occurs if a parameter is of type string
        and entry point file has same parameter other than string equivalent type.
        """
        OUTPUT_KEY = "result"
        result, status = output_schema.validate_output(
            copy.deepcopy(RUNNER_OUTPUT_SCHEMA_FOR_VALIDATION),
            copy.deepcopy(ACTION_OUTPUT_SCHEMA_FOR_STRING_TYPE_VALIDATION),
            copy.deepcopy(BAD_RESULT_FOR_STRING_TYPE_PARAMS),
            LIVEACTION_STATUS_SUCCEEDED,
            OUTPUT_KEY,
        )

        expected_result = {
            "stdout": "",
            "stderr": "None is not of type 'string'\n\nFailed validating 'type' in schema['properties']['output_2']:\n    {'type': 'string'}\n\nOn instance['output_2']:\n    None",
            "exit_code": FAILURE_EXIT_CODE,
            "result": "None",
        }

        expected_status = LIVEACTION_STATUS_FAILED

        self.assertEqual(result["result"], expected_result["result"])
        self.assertEqual(result["stderr"], expected_result["stderr"])
        self.assertEqual(result["exit_code"], expected_result["exit_code"])
        self.assertEqual(status, expected_status)

    def test_validation_of_output_schema_for_object_type_params(self):
        OUTPUT_KEY = "result"
        result, status = output_schema.validate_output(
            copy.deepcopy(RUNNER_OUTPUT_SCHEMA_FOR_VALIDATION),
            copy.deepcopy(ACTION_OUTPUT_SCHEMA_FOR_OBJECT_TYPE_VALIDATION),
            copy.deepcopy(BAD_RESULT_FOR_OBJECT_TYPE_PARAMS),
            LIVEACTION_STATUS_SUCCEEDED,
            OUTPUT_KEY,
        )

        expected_result = {
            "stdout": "",
            "stderr": "'foo' is not of type 'object'\n\nFailed validating 'type' in schema['properties']['output_3']:\n    {'type': 'object'}\n\nOn instance['output_3']:\n    'foo'",
            "exit_code": 1,
            "result": "None",
        }

        expected_status = LIVEACTION_STATUS_FAILED
        self.assertEqual(result["result"], expected_result["result"])
        self.assertEqual(result["stderr"], expected_result["stderr"])
        self.assertEqual(result["exit_code"], expected_result["exit_code"])
        self.assertEqual(status, expected_status)

    def test_validation_of_output_schema_for_integer_type_params(self):
        OUTPUT_KEY = "result"
        result, status = output_schema.validate_output(
            copy.deepcopy(RUNNER_OUTPUT_SCHEMA_FOR_VALIDATION),
            copy.deepcopy(ACTION_OUTPUT_SCHEMA_FOR_INTEGER_TYPE_VALIDATION),
            copy.deepcopy(BAD_RESULT_FOR_INTEGER_TYPE_PARAMS),
            LIVEACTION_STATUS_SUCCEEDED,
            OUTPUT_KEY,
        )

        expected_result = {
            "stdout": "",
            "stderr": "'foo' is not of type 'integer'\n\nFailed validating 'type' in schema['properties']['output_2']:\n    {'type': 'integer'}\n\nOn instance['output_2']:\n    'foo'",
            "exit_code": 1,
            "result": "None",
        }

        expected_status = LIVEACTION_STATUS_FAILED
        self.assertEqual(result["result"], expected_result["result"])
        self.assertEqual(result["stderr"], expected_result["stderr"])
        self.assertEqual(result["exit_code"], expected_result["exit_code"])
        self.assertEqual(status, expected_status)

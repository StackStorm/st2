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

ACTION_RESULT = {
    "output": {
        "output_1": "Bobby",
        "output_2": 5,
        "deep_output": {
            "deep_item_1": "Jindal",
        },
    }
}

RUNNER_SCHEMA = {
    "output": {"type": "object"},
    "error": {"type": "array"},
}

ACTION_SCHEMA = {
    "output_1": {"type": "string"},
    "output_2": {"type": "integer"},
    "deep_output": {
        "type": "object",
        "parameters": {
            "deep_item_1": {
                "type": "string",
            },
        },
    },
}

RUNNER_SCHEMA_FAIL = {
    "not_a_key_you_have": {"type": "string"},
}

ACTION_SCHEMA_FAIL = {
    "not_a_key_you_have": {"type": "string"},
}

ACTION_SCHEMA_WITH_SECRET_PARAMS = {
    "type": "object",
    "properties": {
        "param_1": {"type": "string", "required": True, "secret": True},
        "param_2": {"type": "string", "required": True},
        "param_3": {
            "type": "string",
            "required": True,
            "secret": True,
            "description": "sample description",
        },
    },
    "additionalProperties": False,
}

RESULT_BEFORE_MASKING_WITH_SECRET_PARAMS = {
    "stdout": "",
    "stderr": "",
    "exit_code": 0,
    "result": {
        "param_1": "to_be_masked",
        "param_2": "not_to_be_masked",
        "param_3": "to_be_masked",
    },
}

ACTION_SCHEMA_WITHOUT_SECRET_PARAMS = {
    "type": "object",
    "properties": {
        "param_1": {
            "type": "string",
            "required": True,
        },
        "param_2": {"type": "string", "required": True},
        "param_3": {
            "type": "string",
            "required": True,
            "description": "sample description",
        },
    },
    "additionalProperties": False,
}

RESULT_BEFORE_MASKING_WITHOUT_SECRET_PARAMS = {
    "stdout": "",
    "stderr": "",
    "exit_code": 0,
    "result": {
        "param_1": "not_to_be_masked",
        "param_2": "not_to_be_masked",
        "param_3": "not_to_be_masked",
    },
}

OUTPUT_KEY = "output"


class OutputSchemaTestCase(unittest2.TestCase):
    def test_valid_schema(self):
        result, status = output_schema.validate_output(
            copy.deepcopy(RUNNER_SCHEMA),
            copy.deepcopy(ACTION_SCHEMA),
            copy.deepcopy(ACTION_RESULT),
            LIVEACTION_STATUS_SUCCEEDED,
            OUTPUT_KEY,
        )

        self.assertEqual(result, ACTION_RESULT)
        self.assertEqual(status, LIVEACTION_STATUS_SUCCEEDED)

    def test_invalid_runner_schema(self):
        result, status = output_schema.validate_output(
            copy.deepcopy(RUNNER_SCHEMA_FAIL),
            copy.deepcopy(ACTION_SCHEMA),
            copy.deepcopy(ACTION_RESULT),
            LIVEACTION_STATUS_SUCCEEDED,
            OUTPUT_KEY,
        )

        expected_result = {
            "error": (
                "Additional properties are not allowed ('output' was unexpected)"
                "\n\nFailed validating 'additionalProperties' in schema:\n    {'addi"
                "tionalProperties': False,\n     'properties': {'not_a_key_you_have': "
                "{'type': 'string'}},\n     'type': 'object'}\n\nOn instance:\n    {'"
                "output': {'deep_output': {'deep_item_1': 'Jindal'},\n                "
                "'output_1': 'Bobby',\n                'output_2': 5}}"
            ),
            "message": "Error validating output. See error output for more details.",
        }

        self.assertEqual(result, expected_result)
        self.assertEqual(status, LIVEACTION_STATUS_FAILED)

    def test_invalid_action_schema(self):
        result, status = output_schema.validate_output(
            copy.deepcopy(RUNNER_SCHEMA),
            copy.deepcopy(ACTION_SCHEMA_FAIL),
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

    def test_output_schema_secret_masking(self):
        """Test case for testing final output result for the output schema with secret parameters."""

        OUTPUT_KEY = "result"
        result = output_schema.output_schema_secret_masking(
            result=RESULT_BEFORE_MASKING_WITH_SECRET_PARAMS,
            output_key=OUTPUT_KEY,
            action_schema=ACTION_SCHEMA_WITH_SECRET_PARAMS,
        )

        expected_result = {
            "param_1": MASKED_ATTRIBUTE_VALUE,
            "param_2": "not_to_be_masked",
            "param_3": MASKED_ATTRIBUTE_VALUE,
        }

        self.assertEqual(result, expected_result)

    def test_output_schema_without_secret_params(self):
        """Test case for testing final output result for the output schema without secret parameters."""

        OUTPUT_KEY = "result"
        result = output_schema.output_schema_secret_masking(
            result=RESULT_BEFORE_MASKING_WITHOUT_SECRET_PARAMS,
            output_key=OUTPUT_KEY,
            action_schema=ACTION_SCHEMA_WITHOUT_SECRET_PARAMS,
        )

        expected_result = {
            "param_1": "not_to_be_masked",
            "param_2": "not_to_be_masked",
            "param_3": "not_to_be_masked",
        }

        self.assertEqual(result, expected_result)

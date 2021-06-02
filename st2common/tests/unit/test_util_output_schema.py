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
            "error": (
                "Additional properties are not allowed ('output' was unexpected)\n\n"
                "Failed validating 'additionalProperties' in schema:\n    "
                "{'additionalProperties': False,\n     'properties': {'not_a_key_you_have': "
                "{'type': 'string'}},\n     'type': 'object'}\n\nOn instance:\n    {'output': "
                "{'deep_output': {'deep_item_1': 'Jindal'},\n                'output_1': 'Bobby',"
                "\n                'output_2': 5,\n                'output_3': 'shhh!'}}"
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

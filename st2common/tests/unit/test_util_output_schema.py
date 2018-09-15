# Licensed to the StackStorm, Inc ('StackStorm') under one or more
# contributor license agreements.  See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.
# The ASF licenses this file to You under the Apache License, Version 2.0
# (the "License"); you may not use this file except in compliance with
# the License.  You may obtain a copy of the License at
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
    LIVEACTION_STATUS_FAILED
)

ACTION_RESULT = {
    'output': {
        'output_1': 'Bobby',
        'output_2': 5,
        'deep_output': {
            'deep_item_1': 'Jindal',
        },
    }
}

RUNNER_SCHEMA = {
    'output': {
        'type': 'object'
    },
    'error': {
        'type': 'array'
    },
}

ACTION_SCHEMA = {
    'output_1': {
        'type': 'string'
    },
    'output_2': {
        'type': 'integer'
    },
    'deep_output': {
        'type': 'object',
        'parameters': {
            'deep_item_1': {
                'type': 'string',
            },
        },
    },
}

RUNNER_SCHEMA_FAIL = {
    'not_a_key_you_have': {
        'type': 'string'
    },
}

ACTION_SCHEMA_FAIL = {
    'not_a_key_you_have': {
        'type': 'string'
    },
}

OUTPUT_KEY = 'output'


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
            'error': (
                "Additional properties are not allowed ('output' was unexpected)"
                "\n\nFailed validating 'additionalProperties' in schema:\n    {'addi"
                "tionalProperties': False,\n     'properties': {'not_a_key_you_have': "
                "{'type': 'string'}},\n     'type': 'object'}\n\nOn instance:\n    {'"
                "output': {'deep_output': {'deep_item_1': 'Jindal'},\n                "
                "'output_1': 'Bobby',\n                'output_2': 5}}"
            ),
            'message': 'Error validating output. See error output for more details.'
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
            'error':
                "Additional properties are not allowed ('deep_output', 'output_2', "
                "'output_1' were unexpected)\n\nFailed validating 'additionalProper"
                "ties' in schema:\n    {'additionalProperties': False,\n     'prope"
                "rties': {'not_a_key_you_have': {'type': 'string'}},\n     'type': "
                "'object'}\n\nOn instance:\n    {'deep_output': {'deep_item_1': 'Ji"
                "ndal'},\n     'output_1': 'Bobby',\n     'output_2': 5}",
            'message': 'Error validating output. See error output for more details.'
        }

        self.assertEqual(result, expected_result)
        self.assertEqual(status, LIVEACTION_STATUS_FAILED)

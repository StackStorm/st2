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
import copy
import mock
import unittest2

from st2common.util import output_schema

from st2common.constants.action import (
    LIVEACTION_STATUS_SUCCEEDED,
    LIVEACTION_STATUS_FAILED,
)
from st2common.constants.secrets import MASKED_ATTRIBUTE_VALUE
from st2common.exceptions.db import StackStormDBObjectNotFoundError
from st2common.models.db.execution import ActionExecutionDB
from st2common.persistence.execution import ActionExecution
from st2common.transport.publishers import PoolPublisher

from st2tests import DbTestCase


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

OUTPUT_SCHEMA_RESULT_1 = {
    "stdout": "",
    "stderr": "",
    "result": {
        "os_secret_param": "to_be_masked",
    },
}

OUTPUT_SCHEMA_RESULT_2 = {
    "stdout": "",
    "stderr": "",
    "result": {
        "os_non_secret_param": "not_to_be_masked",
    },
}

OUTPUT_SCHEMA_LIVEACTION_1 = {
    "action": "core.ask",
    "parameters": {},
}

OUTPUT_SCHEMA_LIVEACTION_2 = {
    "action": "core.ask",
    "parameters": {},
}

ACTIONEXECUTIONS = {
    "execution_1": {
        "action": {
            "uid": "action:core:ask",
            "output_schema": {
                "os_secret_param": {"type": "string", "required": True, "secret": True},
            },
        },
        "status": "succeeded",
        "runner": {"name": "inquirer"},
        "liveaction": OUTPUT_SCHEMA_LIVEACTION_1,
        "result": OUTPUT_SCHEMA_RESULT_1,
    },
    "execution_2": {
        "action": {
            "uid": "action:core:ask",
            "output_schema": {
                "os_non_secret_param": {"type": "string", "required": True},
            },
        },
        "status": "succeeded",
        "runner": {"name": "inquirer"},
        "liveaction": OUTPUT_SCHEMA_LIVEACTION_2,
        "result": OUTPUT_SCHEMA_RESULT_2,
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
    
    
    @mock.patch.object(PoolPublisher, "publish", mock.MagicMock())
class ActionExecutionModelTest(DbTestCase):
    def setUp(self):

        self.executions = {}

        for name, execution in ACTIONEXECUTIONS.items():

            created = ActionExecutionDB()
            created.action = execution["action"]
            created.status = execution["status"]
            created.runner = execution["runner"]
            created.liveaction = execution["liveaction"]
            created.result = execution["result"]
            saved = ActionExecutionModelTest._save_execution(created)
            retrieved = ActionExecution.get_by_id(saved.id)
            self.assertEqual(
                saved.action, retrieved.action, "Same action was not returned."
            )

            self.executions[name] = retrieved

    def tearDown(self):

        for name, execution in self.executions.items():
            ActionExecutionModelTest._delete([execution])
            try:
                retrieved = ActionExecution.get_by_id(execution.id)
            except StackStormDBObjectNotFoundError:
                retrieved = None
            self.assertIsNone(retrieved, "managed to retrieve after failure.")

    def test_output_schema_secret_param_masking(self):
        """
        Test that the parameter marked secret as true in output schema is masked in the output
        result. Here the parameter in output schema is marked secret as true and we are
        asserting this is masked in the output result.
        """

        masked = self.executions["execution_1"].mask_secrets(
            self.executions["execution_1"].to_serializable_dict()
        )
        print("masked: ", masked)
        self.assertEqual(
            masked["result"]["result"]["os_secret_param"], MASKED_ATTRIBUTE_VALUE
        )

    def test_output_schema_non_secret_param_not_masking(self):
        """
        Test that the parameters is marked secret as true in output schema is not masked in
        the output result. Here the parameter in output schema is not marked secret as
        true and we are asserting this isn't masked in the output result.
        """

        non_masked = self.executions["execution_2"].mask_secrets(
            self.executions["execution_2"].to_serializable_dict()
        )
        print("non_masked: ", non_masked)
        self.assertEqual(
            non_masked["result"]["result"]["os_non_secret_param"], "not_to_be_masked"
        )

    @staticmethod
    def _save_execution(execution):
        return ActionExecution.add_or_update(execution)

    @staticmethod
    def _delete(model_objects):
        for model_object in model_objects:
            model_object.delete()

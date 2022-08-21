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
import mock

from st2common.constants.secrets import MASKED_ATTRIBUTE_VALUE
from st2common.exceptions.db import StackStormDBObjectNotFoundError
from st2common.models.db.execution import ActionExecutionDB
from st2common.persistence.execution import ActionExecution
from st2common.transport.publishers import PoolPublisher
from st2common.util import date as date_utils

from st2tests import DbTestCase


INQUIRY_RESULT = {
    "users": [],
    "roles": [],
    "route": "developers",
    "ttl": 1440,
    "response": {"secondfactor": "supersecretvalue"},
    "schema": {
        "type": "object",
        "properties": {
            "secondfactor": {
                "secret": True,
                "required": True,
                "type": "string",
                "description": 'Please enter second factor for authenticating to "foo" service',
            }
        },
    },
}

INQUIRY_LIVEACTION = {
    "parameters": {
        "route": "developers",
        "schema": {
            "type": "object",
            "properties": {
                "secondfactor": {
                    "secret": True,
                    "required": True,
                    "type": "string",
                    "description": 'Please enter second factor for authenticating to "foo" service',
                }
            },
        },
    },
    "action": "core.ask",
}

RESPOND_LIVEACTION = {
    "parameters": {
        "response": {
            "secondfactor": "omgsupersecret",
        }
    },
    "action": "st2.inquiry.respond",
}

OUTPUT_SCHEMA_RESULT = {
    "stdout": "",
    "stderr": "",
    "result": {
        "os_secret_param": "to_be_masked",
        "os_non_secret_param": "not_to_be_masked",
    },
}

OUTPUT_SCHEMA_LIVEACTION = {
    "action": "core.ask",
    "parameters": {},
}

ACTIONEXECUTIONS = {
    "execution_1": {
        "action": {"uid": "action:core:ask", "output_schema": {}},
        "status": "succeeded",
        "runner": {"name": "inquirer"},
        "liveaction": INQUIRY_LIVEACTION,
        "result": INQUIRY_RESULT,
    },
    "execution_2": {
        "action": {"uid": "action:st2:inquiry.respond", "output_schema": {}},
        "status": "succeeded",
        "runner": {"name": "python-script"},
        "liveaction": RESPOND_LIVEACTION,
        "result": {"exit_code": 0, "result": None, "stderr": "", "stdout": ""},
    },
    "execution_3": {
        "action": {
            "uid": "action:core:ask",
            "output_schema": {
                "type": "object",
                "properties": {
                    "os_secret_param": {
                        "type": "string",
                        "required": True,
                        "secret": True,
                    },
                    "os_non_secret_param": {"type": "string", "required": True},
                },
                "additionalProperties": False,
            },
        },
        "status": "succeeded",
        "runner": {"name": "inquirer", "output_key": "result"},
        "liveaction": OUTPUT_SCHEMA_LIVEACTION,
        "result": OUTPUT_SCHEMA_RESULT,
    },
}


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

    def test_update_execution(self):
        """Test ActionExecutionDb update"""
        self.assertIsNone(self.executions["execution_1"].end_timestamp)
        self.executions["execution_1"].end_timestamp = date_utils.get_datetime_utc_now()
        updated = ActionExecution.add_or_update(self.executions["execution_1"])
        self.assertTrue(
            updated.end_timestamp == self.executions["execution_1"].end_timestamp
        )

    def test_execution_inquiry_secrets(self):
        """Corner case test for Inquiry responses that contain secrets.

        Should properly mask these if the Inquiry is being retrieved
        directly via `execution get` commands.

        TODO(mierdin): Move this once Inquiries get their own data model
        """

        # Test Inquiry response masking is done properly within this model
        masked = self.executions["execution_1"].mask_secrets(
            self.executions["execution_1"].to_serializable_dict()
        )
        self.assertEqual(
            masked["result"]["response"]["secondfactor"], MASKED_ATTRIBUTE_VALUE
        )
        self.assertEqual(
            self.executions["execution_1"].result["response"]["secondfactor"],
            "supersecretvalue",
        )

    def test_execution_inquiry_response_action(self):
        """Test that the response parameters for any `st2.inquiry.respond` executions are masked

        We aren't bothering to get the inquiry schema in the `st2.inquiry.respond` action,
        so we mask all response values. This test ensures this happens.
        """

        masked = self.executions["execution_2"].mask_secrets(
            self.executions["execution_2"].to_serializable_dict()
        )
        for value in masked["parameters"]["response"].values():
            self.assertEqual(value, MASKED_ATTRIBUTE_VALUE)

    def test_output_schema_secret_param_masking(self):
        """Test that the output marked as secret in the output schema is masked in the output result

        In this test case, one of the output parameters is marked as secret in the output schema
        while the other output parameter is not marked as secret. The value of the first output
        parameter should be masked in the output result.
        """

        masked = self.executions["execution_3"].mask_secrets(
            self.executions["execution_3"].to_serializable_dict()
        )
        self.assertEqual(
            masked["result"]["result"]["os_secret_param"], MASKED_ATTRIBUTE_VALUE
        )
        self.assertEqual(
            masked["result"]["result"]["os_non_secret_param"], "not_to_be_masked"
        )

    @staticmethod
    def _save_execution(execution):
        return ActionExecution.add_or_update(execution)

    @staticmethod
    def _delete(model_objects):
        for model_object in model_objects:
            model_object.delete()

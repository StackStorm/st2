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
import sys
import logging

import traceback
import jsonschema

from st2common.util import schema
from st2common.constants import action as action_constants
from st2common.constants.secrets import MASKED_ATTRIBUTE_VALUE


LOG = logging.getLogger(__name__)


def _validate_runner(runner_schema, result):
    LOG.debug("Validating runner output: %s", runner_schema)

    runner_schema = {
        "type": "object",
        "properties": runner_schema,
        "additionalProperties": False,
    }

    schema.validate(result, runner_schema, cls=schema.get_validator("custom"))


def _validate_action(action_schema, result, output_key):
    LOG.debug("Validating action output: %s", action_schema)

    final_result = result[output_key]

    action_schema = {
        "type": "object",
        "properties": action_schema,
        "additionalProperties": False,
    }

    schema.validate(final_result, action_schema, cls=schema.get_validator("custom"))


def mask_secret_output(value, output_schema_result):
    value = copy.deepcopy(value)
    if (
        value["action"]["runner_type"] != "local-shell-cmd"
        and value["action"]["runner_type"] != "orquesta"
        and value["action"]["runner_type"] != "announcement"
        and value["action"]["runner_type"] != "inquirer"
        and value["action"]["runner_type"] != "noop"
        and value["action"]["runner_type"] != "remote-shell-script"
        and value["action"]["runner_type"] != "winrm-cmd"
        and value["action"]["runner_type"] != "winrm-ps-cmd"
        and value["action"]["runner_type"] != "winrm-ps-script"
    ):
        output_key = value["runner"]["output_key"]
        for key, spec in six.iteritems(value["action"]["output_schema"]):
            if spec.get("secret", False):
                if output_schema_result.get(output_key):
                    output_schema_result[output_key][key] = MASKED_ATTRIBUTE_VALUE

    return output_schema_result


def validate_output(runner_schema, action_schema, result, status, output_key):
    """Validate output of action with runner and action schema."""
    try:
        LOG.debug("Validating action output: %s", result)
        LOG.debug("Output Key: %s", output_key)
        if runner_schema:
            _validate_runner(runner_schema, result)

            if action_schema:
                _validate_action(action_schema, result, output_key)

    except jsonschema.ValidationError:
        LOG.exception("Failed to validate output.")
        _, ex, _ = sys.exc_info()
        # mark execution as failed.
        status = action_constants.LIVEACTION_STATUS_FAILED
        # include the error message and traceback to try and provide some hints.
        result = {
            "error": str(ex),
            "message": "Error validating output. See error output for more details.",
        }
        return (result, status)
    except:
        LOG.exception("Failed to validate output.")
        _, ex, tb = sys.exc_info()
        # mark execution as failed.
        status = action_constants.LIVEACTION_STATUS_FAILED
        # include the error message and traceback to try and provide some hints.
        result = {
            "traceback": "".join(traceback.format_tb(tb, 20)),
            "error": str(ex),
            "message": "Error validating output. See error output for more details.",
        }
        return (result, status)

    return (result, status)

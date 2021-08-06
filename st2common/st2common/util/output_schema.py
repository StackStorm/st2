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

import logging
import re
import sys
import traceback
import jsonschema

from collections.abc import Mapping
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


def _get_masked_value(spec, value):
    # malformed schema
    if not isinstance(spec, Mapping):
        return value

    if spec.get("secret", False):
        return MASKED_ATTRIBUTE_VALUE

    kind = spec.get("type")

    if kind in ("boolean", "integer", "null", "number", "string"):
        # already checked for spec["secret"] above; nothing else to check.
        return value

    elif kind == "object":
        properties_schema = spec.get("properties", {})
        if properties_schema and isinstance(properties_schema, Mapping):
            # properties is not empty or malformed
            for key, property_spec in properties_schema.items():
                if key in value:
                    value[key] = _get_masked_value(property_spec, value[key])
            unhandled_keys = set(value.keys()) - set(properties_schema.keys())
        else:
            # properties is empty or malformed
            unhandled_keys = set(value.keys())

        pattern_properties_schema = spec.get("patternProperties")
        if pattern_properties_schema and isinstance(pattern_properties_schema, Mapping):
            # patternProperties is not malformed
            for key_pattern, pattern_property_spec in pattern_properties_schema:
                key_re = re.compile(key_pattern)
                for key in list(unhandled_keys):
                    if key_re.search(key):
                        value[key] = _get_masked_value(
                            pattern_property_spec, value[key]
                        )
                        unhandled_keys.remove(key)

        additional_properties_schema = spec.get("additionalProperties")
        if additional_properties_schema and isinstance(
            additional_properties_schema, Mapping
        ):
            # additionalProperties is a schema, not a boolean, and not malformed
            for key in unhandled_keys:
                value[key] = _get_masked_value(additional_properties_schema, value[key])

        return value

    elif kind == "array":
        items_schema = spec.get("items", {})
        output_count = len(value)
        if isinstance(items_schema, Mapping):
            # explicit schema for each item
            for i, item_spec in enumerate(items_schema):
                if i >= output_count:
                    break
                value[i] = _get_masked_value(item_spec, value[key])
            handled_count = len(items_schema)
        else:
            for i in range(output_count):
                value[i] = _get_masked_value(items_schema, value[key])
            handled_count = output_count

        if handled_count >= output_count:
            return value

        additional_items_schema = spec.get("additionalItems")
        if additional_items_schema and isinstance(additional_items_schema, Mapping):
            # additionalItems is a schema, not a boolean
            for i in range(handled_count, output_count):
                value[i] = _get_masked_value(additional_items_schema, value[i])

        return value
    else:
        # "type" is not defined or is invalid: ignore it
        return value


def mask_secret_output(ac_ex, output_value):
    # We only support output_schema validation when the output_value is a JSON object.
    # Invididual keys of that object can be marked secret, but the entire output
    # object cannot be marked as secret.

    if not output_value or not isinstance(output_value, Mapping):
        return output_value

    output_key = ac_ex["runner"].get("output_key")
    output_schema = ac_ex["action"].get("output_schema")

    # nothing to validate
    if not output_key or not output_schema:
        return output_value

    # malformed schema
    if not isinstance(output_schema, Mapping):
        return output_value

    # TODO: a better way to see if only the values are valid json schemas, or the whole thing?
    if "type" not in output_schema:
        # see st2common/st2common/models/api/action.py
        # output_schema_schema = {
        #    "description": "Schema for the runner's/action's output.",
        #    "type": "object",
        #    "patternProperties": {r"^\w+$": customized_draft4_jsonschema}
        #    "additionalProperties": False,
        #    "default": {},
        # }
        # This implies the following schema (as in _validate_runner/_validate_action above)
        implied_schema = {
            "type": "object",
            "properties": output_schema,
            "additionalProperties": False,
        }
        output_value[output_key] = _get_masked_value(
            implied_schema, output_value[output_key]
        )
    else:
        output_value[output_key] = _get_masked_value(
            output_schema, output_value[output_key]
        )
    return output_value


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

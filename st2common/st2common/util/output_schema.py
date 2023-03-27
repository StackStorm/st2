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

from collections.abc import Mapping, MutableMapping, MutableSequence, Sequence
from st2common.util import schema
from st2common.constants import action as action_constants
from st2common.constants.secrets import MASKED_ATTRIBUTE_VALUE


LOG = logging.getLogger(__name__)

_JSON_BASIC_TYPES = {"boolean", "integer", "null", "number", "string"}
_JSON_COMPLEX_TYPES = {"object", "array"}
_JSON_TYPES = _JSON_BASIC_TYPES | _JSON_COMPLEX_TYPES


def _output_schema_is_valid(_schema):
    if not isinstance(_schema, Mapping):
        # malformed schema
        return False

    if "type" not in _schema:
        # legacy schema format
        return False

    try:
        # the validator is smart enough to handle
        # schema that is similar to the input schema
        schema.validate(
            _schema,
            schema.get_action_output_schema(),
            cls=schema.get_validator("custom"),
        )
    except jsonschema.ValidationError as e:
        LOG.debug("output_schema not valid: %s", e)
        return False

    return True


def _normalize_legacy_output_schema(_schema):
    if not isinstance(_schema, Mapping):
        return _schema

    _normalized_schema = {
        "type": "object",
        "properties": _schema,
        "additionalProperties": True,
    }

    return _normalized_schema


def _validate_runner(runner_schema, result):
    LOG.debug("Validating runner output: %s", runner_schema)

    if not _output_schema_is_valid(runner_schema):
        LOG.warning("Ignoring invalid runner schema: %s", runner_schema)
        return

    schema.validate(result, runner_schema, cls=schema.get_validator("custom"))


def _validate_action(action_schema, result, output_key):
    LOG.debug("Validating action output: %s", action_schema)

    if not _output_schema_is_valid(action_schema):
        LOG.warning("Ignoring invalid action schema: %s", action_schema)
        return

    final_result = result[output_key]

    schema.validate(final_result, action_schema, cls=schema.get_validator("custom"))


def _get_masked_value(spec, value):
    # malformed schema
    if not isinstance(spec, Mapping):
        return value

    if spec.get("secret", False):
        return MASKED_ATTRIBUTE_VALUE

    kind = spec.get("type")

    if kind in _JSON_BASIC_TYPES:
        # already checked for spec["secret"] above; nothing else to check.
        return value

    elif kind == "object":
        if not isinstance(value, MutableMapping):
            # we can't process it unless it matches the expected type
            return value

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
        if (
            unhandled_keys
            and pattern_properties_schema
            and isinstance(pattern_properties_schema, Mapping)
        ):
            # patternProperties is not malformed
            for key_pattern, pattern_property_spec in pattern_properties_schema.items():
                if not unhandled_keys:
                    # nothing to check, don't compile the next pattern
                    break
                key_re = re.compile(key_pattern)
                for key in list(unhandled_keys):
                    if key_re.search(key):
                        value[key] = _get_masked_value(
                            pattern_property_spec, value[key]
                        )
                        unhandled_keys.remove(key)

        additional_properties_schema = spec.get("additionalProperties")
        if (
            unhandled_keys
            and additional_properties_schema
            and isinstance(additional_properties_schema, Mapping)
        ):
            # additionalProperties is a schema, not a boolean, and not malformed
            for key in unhandled_keys:
                value[key] = _get_masked_value(additional_properties_schema, value[key])

        return value

    elif kind == "array":
        if not isinstance(value, MutableSequence):
            # we can't process it unless it matches the expected type
            return value

        items_schema = spec.get("items", {})
        output_count = len(value)
        if isinstance(items_schema, Sequence):
            # explicit schema for each item
            for i, item_spec in enumerate(items_schema):
                if i >= output_count:
                    break
                value[i] = _get_masked_value(item_spec, value[i])
            handled_count = len(items_schema)
        else:
            for i in range(output_count):
                value[i] = _get_masked_value(items_schema, value[i])
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
    if not output_value:
        return output_value

    output_key = ac_ex["runner"].get("output_key")
    # output_schema has masking info for data in output_value[output_key]
    output_schema = ac_ex["action"].get("output_schema")

    if (
        # without output_key we cannot use output_schema
        not output_key
        # cannot access output_key if output_value is not a dict
        or not isinstance(output_value, MutableMapping)
        # cannot mask output if it is missing
        or output_key not in output_value
        # no action output_schema defined
        or not output_schema
    ):
        # nothing to mask
        return output_value

    # backward compatibility for legacy output_schema so secrets stay masked
    if not _output_schema_is_valid(output_schema):
        # normalized the legacy schema to a full JSON schema and check if it is valid
        normalized_output_schema = _normalize_legacy_output_schema(output_schema)

        if not _output_schema_is_valid(normalized_output_schema):
            # nothing to mask
            return output_value

        # mask secret for the legacy output schema
        output_value[output_key] = _get_masked_value(
            normalized_output_schema, output_value[output_key]
        )

        return output_value

    # mask secret for the output schema
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

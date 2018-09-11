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
import sys
import traceback
import logging

import jsonschema

from st2common.util import schema
from st2common.util.ujson import fast_deepcopy
from st2common.constants import action as action_constants


LOG = logging.getLogger(__name__)


def _validate_runner(runner, result):
    LOG.debug('Validating runner output: %s', runner.output_schema)

    if runner.output_schema.get('unmodeled'):
        runner.output_schema.pop('unmodeled')
        LOG.warn(
            """Deprecation Notice: This runner has previously had unmodeled
            output. In StackStorm 3.1 the output will be placed under the
            `output` key."""
        )
        runner_schema = {
            "additionalProperties": True
        }
    else:
        runner_schema = {
            "type": "object",
            "properties": runner.output_schema,
            "additionalProperties": False
        }

    schema.validate(result, runner_schema, cls=schema.get_validator('custom'))


def _validate_action(runner_db, action_db, result):
    output_schema = fast_deepcopy(runner_db.output_schema)
    output_schema.update(action_db.output_schema)
    action_schema = {
        "type": "object",
        "properties": output_schema,
        "additionalProperties": False
    }
    LOG.debug('Validating action output: %s', action_schema)
    schema.validate(result, action_schema, cls=schema.get_validator('custom'))


def validate_output(runner_db, action_db, result, status):
    """ Validate output of action with runner and action schema.
    """
    try:
        LOG.debug('Validating action output: %s', result)
        _validate_runner(runner_db, result)

        if action_db.output_schema:
            _validate_action(runner_db, action_db, result)

    except jsonschema.ValidationError as _:
        LOG.exception('Failed to validate output.')
        _, ex, _ = sys.exc_info()
        # mark execution as failed.
        status = action_constants.LIVEACTION_STATUS_FAILED
        # include the error message and traceback to try and provide some hints.
        result = {
            'error': str(ex),
            'message': 'Error validating output. See error output for more details.',
        }
        return (result, status)

    return (result, status)

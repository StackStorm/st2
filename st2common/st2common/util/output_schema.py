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
import logging

import jsonschema

from st2common.util import schema
from st2common.constants import action as action_constants


LOG = logging.getLogger(__name__)
PATH_KEY = 'output_path'


def _validate_runner(runner_schema, result):
    LOG.debug('Validating runner output: %s', runner_schema)

    runner_schema = {
        "type": "object",
        "properties": runner_schema,
        "additionalProperties": False
    }

    schema.validate(result, runner_schema, cls=schema.get_validator('custom'))


def _validate_action(action_schema, result, output_path):
    LOG.debug('Validating action output: %s', action_schema)
    final_result = result
    output_path = action_schema.pop(PATH_KEY, output_path)

    for key in output_path:
        final_result = final_result[key]

    action_schema = {
        "type": "object",
        "properties": action_schema,
        "additionalProperties": False
    }
    schema.validate(final_result, action_schema, cls=schema.get_validator('custom'))


def validate_output(runner_schema, action_schema, result, status):
    """ Validate output of action with runner and action schema.
    """
    try:
        LOG.debug('Validating action output: %s', result)
        if runner_schema:
            output_path = runner_schema.pop(PATH_KEY, [])
            _validate_runner(runner_schema, result)

        if action_schema:
            _validate_action(action_schema, result, output_path)

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
    except:
        LOG.exception('Failed to validate output.')
        _, ex, tb = sys.exc_info()
        # mark execution as failed.
        status = action_constants.LIVEACTION_STATUS_FAILED
        # include the error message and traceback to try and provide some hints.
        result = {
            'traceback': str(tb),
            'error': str(ex),
            'message': 'Error validating output. See error output for more details.',
        }
        return (result, status)

    return (result, status)

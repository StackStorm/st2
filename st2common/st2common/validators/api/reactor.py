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

import six

from apscheduler.triggers.cron import CronTrigger

from st2common.exceptions.apivalidation import ValueValidationException
from st2common.constants.triggers import SYSTEM_TRIGGER_TYPES
from st2common.constants.triggers import CRON_TIMER_TRIGGER_REF
from st2common.util import schema as util_schema
import st2common.operators as criteria_operators
from st2common.services import triggers

__all__ = [
    'validate_criteria',
    'validate_trigger_parameters'
]

allowed_operators = criteria_operators.get_allowed_operators()


def validate_criteria(criteria):
    if not isinstance(criteria, dict):
        raise ValueValidationException('Criteria should be a dict.')

    for key, value in six.iteritems(criteria):
        operator = value.get('type', None)
        if operator is None:
            raise ValueValidationException('Operator not specified for field: ' + key)
        if operator not in allowed_operators:
            raise ValueValidationException('For field: ' + key + ', operator ' + operator +
                                           ' not in list of allowed operators: ' +
                                           str(allowed_operators.keys()))
        pattern = value.get('pattern', None)
        if pattern is None:
            raise ValueValidationException('For field: ' + key + ', no pattern specified ' +
                                           'for operator ' + operator)


def validate_trigger_parameters(trigger_type_ref, parameters):
    """
    This function validates parameters for system triggers (e.g. webhook and timers).

    Note: Eventually we should also validate parameters for user defined triggers which correctly
    specify JSON schema for the parameters.

    :param trigger_type_ref: Reference of a trigger type.
    :type trigger_type_ref: ``str``

    :param parameters: Trigger parameters.
    :type parameters: ``dict``
    """
    if not trigger_type_ref:
        return None

    trigger_type = triggers.get_trigger_type_db(trigger_type_ref)
    if trigger_type_ref in SYSTEM_TRIGGER_TYPES:
        parameters_schema = SYSTEM_TRIGGER_TYPES[trigger_type_ref]['parameters_schema']
    elif trigger_type and trigger_type.payload_schema:
        parameters_schema = trigger_type.payload_schema
    else:
        return None

    cleaned = util_schema.validate(instance=parameters, schema=parameters_schema,
                                   cls=util_schema.CustomValidator, use_default=True,
                                   allow_default_none=True)

    # Additional validation for CronTimer trigger
    # TODO: If we need to add more checks like this we should consider abstracting this out.
    if trigger_type_ref == CRON_TIMER_TRIGGER_REF:
        # Validate that the user provided parameters are valid. This is required since JSON schema
        # allows arbitrary strings, but not any arbitrary string is a valid CronTrigger argument
        # Note: Constructor throws ValueError on invalid parameters
        CronTrigger(**parameters)

    return cleaned

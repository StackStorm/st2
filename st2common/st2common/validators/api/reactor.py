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

from st2common.exceptions.apivalidation import ValueValidationException
from st2common.constants.triggers import SYSTEM_TRIGGER_TYPES
from st2common.util import schema as util_schema
import st2common.operators as criteria_operators

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


def validate_trigger_parameters(trigger_db):
    """
    This function validates parameters for system triggers (e.g. timers).

    Note: Eventually we should also validate parameters for user defined triggers which correctly
    specify JSON schema for the parameters.

    :param trigger_db: Trigger DB object.
    :type trigger_db: :class:`TriggerDB`
    """
    if not trigger_db:
        return None

    trigger_type_ref = trigger_db.type
    parameters = trigger_db.parameters

    if trigger_type_ref not in SYSTEM_TRIGGER_TYPES:
        # Not a system trigger, skip validation for now
        return None

    parameters_schema = SYSTEM_TRIGGER_TYPES[trigger_type_ref]['parameters_schema']
    cleaned = util_schema.validate(instance=parameters, schema=parameters_schema,
                                   cls=util_schema.CustomValidator, use_default=True)
    return cleaned

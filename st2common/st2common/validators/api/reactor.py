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

from oslo_config import cfg
from apscheduler.triggers.cron import CronTrigger

from st2common import log as logging
from st2common.exceptions.apivalidation import ValueValidationException
from st2common.constants.triggers import SYSTEM_TRIGGER_TYPES
from st2common.constants.triggers import CRON_TIMER_TRIGGER_REF
from st2common.util import schema as util_schema
import st2common.operators as criteria_operators
from st2common.services import triggers

__all__ = [
    'validate_criteria',

    'validate_trigger_parameters',
    'validate_trigger_payload'
]


LOG = logging.getLogger(__name__)

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
    This function validates parameters for system and user-defined triggers.

    :param trigger_type_ref: Reference of a trigger type.
    :type trigger_type_ref: ``str``

    :param parameters: Trigger parameters.
    :type parameters: ``dict``

    :return: Cleaned parameters on success, None if validation is not performed.
    """
    if not trigger_type_ref:
        return None

    is_system_trigger = trigger_type_ref in SYSTEM_TRIGGER_TYPES
    if is_system_trigger:
        # System trigger
        parameters_schema = SYSTEM_TRIGGER_TYPES[trigger_type_ref]['parameters_schema']
    else:
        trigger_type_db = triggers.get_trigger_type_db(trigger_type_ref)
        if not trigger_type_db:
            # Trigger doesn't exist in the database
            return None

        parameters_schema = getattr(trigger_type_db, 'parameters_schema', {})
        if not parameters_schema:
            # Parameters schema not defined for the this trigger
            return None

    # We only validate non-system triggers if config option is set (enabled)
    if not is_system_trigger and not cfg.CONF.system.validate_trigger_parameters:
        LOG.debug('Got non-system trigger "%s", but trigger parameter validation for non-system'
                  'triggers is disabled, skipping validation.' % (trigger_type_ref))
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


def validate_trigger_payload(trigger_type_ref, payload):
    """
    This function validates trigger payload parameters for system and user-defined triggers.

    :param trigger_type_ref: Reference of a trigger type.
    :type trigger_type_ref: ``str``

    :param payload: Trigger payload.
    :type payload: ``dict``

    :return: Cleaned payload on success, None if validation is not performed.
    """
    if not trigger_type_ref:
        return None

    is_system_trigger = trigger_type_ref in SYSTEM_TRIGGER_TYPES
    if is_system_trigger:
        # System trigger
        payload_schema = SYSTEM_TRIGGER_TYPES[trigger_type_ref]['payload_schema']
    else:
        trigger_type_db = triggers.get_trigger_type_db(trigger_type_ref)
        if not trigger_type_db:
            # Trigger doesn't exist in the database
            return None

        payload_schema = getattr(trigger_type_db, 'payload_schema', {})
        if not payload_schema:
            # Payload schema not defined for the this trigger
            return None

    # We only validate non-system triggers if config option is set (enabled)
    if not is_system_trigger and not cfg.CONF.system.validate_trigger_payload:
        LOG.debug('Got non-system trigger "%s", but trigger payload validation for non-system'
                  'triggers is disabled, skipping validation.' % (trigger_type_ref))
        return None

    cleaned = util_schema.validate(instance=payload, schema=payload_schema,
                                   cls=util_schema.CustomValidator, use_default=True,
                                   allow_default_none=True)

    return cleaned

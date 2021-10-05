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

import six

from mongoengine import ValidationError
from mongoengine import NotUniqueError
from oslo_config import cfg

from st2common import log as logging
from st2common.constants.triggers import INTERNAL_TRIGGER_TYPES, ACTION_SENSOR_TRIGGER
from st2common.exceptions.db import StackStormDBObjectConflictError
from st2common.services.triggers import create_trigger_type_db
from st2common.services.triggers import create_shadow_trigger
from st2common.services.triggers import get_trigger_type_db
from st2common.models.system.common import ResourceReference

__all__ = ["register_internal_trigger_types"]

LOG = logging.getLogger(__name__)


def _register_internal_trigger_type(trigger_definition):
    try:
        trigger_type_db = create_trigger_type_db(
            trigger_type=trigger_definition, log_not_unique_error_as_debug=True
        )
    except (NotUniqueError, StackStormDBObjectConflictError):
        # We ignore conflict error since this operation is idempotent and race is not an issue
        LOG.debug(
            'Internal trigger type "%s" already exists, ignoring error...'
            % (trigger_definition["name"])
        )

        ref = ResourceReference.to_string_reference(
            name=trigger_definition["name"], pack=trigger_definition["pack"]
        )
        trigger_type_db = get_trigger_type_db(ref)

    if trigger_type_db:
        LOG.debug("Registered internal trigger: %s.", trigger_definition["name"])

    # trigger types with parameters do no require a shadow trigger.
    if trigger_type_db and not trigger_type_db.parameters_schema:
        try:
            trigger_db = create_shadow_trigger(
                trigger_type_db, log_not_unique_error_as_debug=True
            )

            extra = {"trigger_db": trigger_db}
            LOG.audit(
                "Trigger created for parameter-less internal TriggerType. Trigger.id=%s"
                % (trigger_db.id),
                extra=extra,
            )
        except (NotUniqueError, StackStormDBObjectConflictError):
            LOG.debug(
                'Shadow trigger "%s" already exists. Ignoring.',
                trigger_type_db.get_reference().ref,
                exc_info=True,
            )

        except (ValidationError, ValueError):
            LOG.exception(
                "Validation failed in shadow trigger. TriggerType=%s.",
                trigger_type_db.get_reference().ref,
            )
            raise

    return trigger_type_db


def register_internal_trigger_types():
    """
    Register internal trigger types.

    NOTE 1: This method blocks until all the trigger types have been registered.

    NOTE 2: We log "NotUniqueError" errors under debug and not error. Those errors are not fatal
    because this operation is idempotent and NotUniqueError simply means internal trigger type
    has already been registered by some other service.
    """
    action_sensor_enabled = cfg.CONF.action_sensor.enable

    registered_trigger_types_db = []

    for _, trigger_definitions in six.iteritems(INTERNAL_TRIGGER_TYPES):
        for trigger_definition in trigger_definitions:
            LOG.debug("Registering internal trigger: %s", trigger_definition["name"])

            is_action_trigger = (
                trigger_definition["name"] == ACTION_SENSOR_TRIGGER["name"]
            )
            if is_action_trigger and not action_sensor_enabled:
                continue
            try:
                trigger_type_db = _register_internal_trigger_type(
                    trigger_definition=trigger_definition
                )
            except Exception:
                LOG.exception(
                    "Failed registering internal trigger: %s.", trigger_definition
                )
                raise
            else:
                registered_trigger_types_db.append(trigger_type_db)

    return registered_trigger_types_db

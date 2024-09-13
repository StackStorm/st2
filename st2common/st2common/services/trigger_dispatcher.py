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
from oslo_config import cfg
from jsonschema import ValidationError

from st2common.models.api.trace import TraceContext
from st2common.transport.reactor import TriggerDispatcher
from st2common.validators.api.reactor import validate_trigger_payload

__all__ = ["TriggerDispatcherService"]


class TriggerDispatcherService(object):
    """
    Class for handling dispatching of trigger.
    """

    def __init__(self, logger):
        self._logger = logger
        self._dispatcher = TriggerDispatcher(self._logger)

    def dispatch(
        self, trigger, payload=None, trace_tag=None, throw_on_validation_error=False
    ):
        """
        Method which dispatches the trigger.

        :param trigger: Reference to the TriggerTypeDB (<pack>.<name>) or TriggerDB object.
        :type trigger: ``str``

        :param payload: Trigger payload.
        :type payload: ``dict``

        :param trace_tag: Tracer to track the triggerinstance.
        :type trace_tags: ``str``

        :param throw_on_validation_error: True to throw on validation error (if validate_payload is
                                          True) instead of logging the error.
        :type throw_on_validation_error: ``boolean``
        """
        # empty strings
        trace_context = TraceContext(trace_tag=trace_tag) if trace_tag else None
        self._logger.debug(
            "Added trace_context %s to trigger %s.", trace_context, trigger
        )
        return self.dispatch_with_context(
            trigger,
            payload=payload,
            trace_context=trace_context,
            throw_on_validation_error=throw_on_validation_error,
        )

    def dispatch_with_context(
        self, trigger, payload=None, trace_context=None, throw_on_validation_error=False
    ):
        """
        Method which dispatches the trigger.

        :param trigger: Reference to the TriggerTypeDB (<pack>.<name>) or TriggerDB object.
        :type trigger: ``str``

        :param payload: Trigger payload.
        :type payload: ``dict``

        :param trace_context: Trace context to associate with Trigger.
        :type trace_context: ``st2common.api.models.api.trace.TraceContext``

        :param throw_on_validation_error: True to throw on validation error (if validate_payload is
                                          True) instead of logging the error.
        :type throw_on_validation_error: ``boolean``
        """
        # Note: We perform validation even if it's disabled in the config so we can at least warn
        # the user if validation fals (but not throw if it's disabled)
        try:
            validate_trigger_payload(
                trigger_type_ref=trigger,
                payload=payload,
                throw_on_inexistent_trigger=True,
            )
        except (ValidationError, ValueError, Exception) as e:
            self._logger.warning(
                'Failed to validate payload (%s) for trigger "%s": %s'
                % (str(payload), trigger, six.text_type(e))
            )

            # If validation is disabled, still dispatch a trigger even if it failed validation
            # This condition prevents unexpected restriction.
            if cfg.CONF.system.validate_trigger_payload:
                msg = (
                    "Trigger payload validation failed and validation is enabled, not "
                    'dispatching a trigger "%s" (%s): %s'
                    % (trigger, str(payload), six.text_type(e))
                )

                if throw_on_validation_error:
                    raise ValueError(msg)

                self._logger.warning(msg)
                return None

        self._logger.debug("Dispatching trigger %s with payload %s.", trigger, payload)
        return self._dispatcher.dispatch(
            trigger, payload=payload, trace_context=trace_context
        )

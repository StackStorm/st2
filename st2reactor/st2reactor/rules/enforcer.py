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

import sys
import json
import traceback

import six

from st2common import log as logging
from st2common.constants import action as action_constants
from st2common.constants.trace import TRACE_CONTEXT
from st2common.constants.rules import TRIGGER_PAYLOAD_PREFIX
from st2common.constants.rule_enforcement import RULE_ENFORCEMENT_STATUS_SUCCEEDED
from st2common.constants.rule_enforcement import RULE_ENFORCEMENT_STATUS_FAILED
from st2common.models.api.trace import TraceContext
from st2common.models.db.liveaction import LiveActionDB
from st2common.models.db.rule_enforcement import RuleEnforcementDB
from st2common.models.api.auth import get_system_username
from st2common.persistence.rule_enforcement import RuleEnforcement
from st2common.services import action as action_service
from st2common.services import trace as trace_service
from st2common.util import reference
from st2common.util import action_db as action_utils
from st2common.util import param as param_utils
from st2common.exceptions import param as param_exc
from st2common.exceptions import apivalidation as validation_exc

__all__ = ["RuleEnforcer"]


LOG = logging.getLogger("st2reactor.ruleenforcement.enforce")

EXEC_KICKED_OFF_STATES = [
    action_constants.LIVEACTION_STATUS_SCHEDULED,
    action_constants.LIVEACTION_STATUS_REQUESTED,
]


class RuleEnforcer(object):
    def __init__(self, trigger_instance, rule):
        self.trigger_instance = trigger_instance
        self.rule = rule

    def get_action_execution_context(self, action_db, trace_context=None):
        context = {
            "trigger_instance": reference.get_ref_from_model(self.trigger_instance),
            "rule": reference.get_ref_from_model(self.rule),
            "user": get_system_username(),
            "pack": action_db.pack,
        }

        if trace_context is not None:
            context[TRACE_CONTEXT] = trace_context

        # Additional non-action / global context
        additional_context = {TRIGGER_PAYLOAD_PREFIX: self.trigger_instance.payload}

        return context, additional_context

    def get_resolved_parameters(
        self, action_db, runnertype_db, params, context=None, additional_contexts=None
    ):
        resolved_params = param_utils.render_live_params(
            runner_parameters=runnertype_db.runner_parameters,
            action_parameters=action_db.parameters,
            params=params,
            action_context=context,
            additional_contexts=additional_contexts,
        )

        return resolved_params

    def enforce(self):
        rule_spec = {
            "ref": self.rule.ref,
            "id": str(self.rule.id),
            "uid": self.rule.uid,
        }
        enforcement_db = RuleEnforcementDB(
            trigger_instance_id=str(self.trigger_instance.id), rule=rule_spec
        )
        extra = {"trigger_instance_db": self.trigger_instance, "rule_db": self.rule}
        execution_db = None
        try:
            execution_db = self._do_enforce()
            # pylint: disable=no-member
            enforcement_db.execution_id = str(execution_db.id)
            enforcement_db.status = RULE_ENFORCEMENT_STATUS_SUCCEEDED
            extra["execution_db"] = execution_db
        except Exception as e:
            # Record the failure reason in the RuleEnforcement.
            enforcement_db.status = RULE_ENFORCEMENT_STATUS_FAILED
            enforcement_db.failure_reason = six.text_type(e)
            LOG.exception(
                "Failed kicking off execution for rule %s.", self.rule, extra=extra
            )
        finally:
            self._update_enforcement(enforcement_db)

        # pylint: disable=no-member
        if not execution_db or execution_db.status not in EXEC_KICKED_OFF_STATES:
            LOG.audit(
                "Rule enforcement failed. Execution of Action %s failed. "
                "TriggerInstance: %s and Rule: %s",
                self.rule.action.ref,
                self.trigger_instance,
                self.rule,
                extra=extra,
            )
        else:
            LOG.audit(
                "Rule enforced. Execution %s, TriggerInstance %s and Rule %s.",
                execution_db,
                self.trigger_instance,
                self.rule,
                extra=extra,
            )

        return execution_db

    def _do_enforce(self):
        # TODO: Refactor this to avoid additional lookup in cast_params
        action_ref = self.rule.action["ref"]

        # Verify action referenced in the rule exists in the database
        action_db = action_utils.get_action_by_ref(action_ref)
        if not action_db:
            raise ValueError('Action "%s" doesn\'t exist' % (action_ref))

        runnertype_db = action_utils.get_runnertype_by_name(
            action_db.runner_type["name"]
        )

        params = self.rule.action.parameters
        LOG.info(
            "Invoking action %s for trigger_instance %s with params %s.",
            self.rule.action.ref,
            self.trigger_instance.id,
            json.dumps(params),
        )

        # update trace before invoking the action.
        trace_context = self._update_trace()
        LOG.debug("Updated trace %s with rule %s.", trace_context, self.rule.id)

        context, additional_contexts = self.get_action_execution_context(
            action_db=action_db, trace_context=trace_context
        )

        return self._invoke_action(
            action_db=action_db,
            runnertype_db=runnertype_db,
            params=params,
            context=context,
            additional_contexts=additional_contexts,
        )

    def _update_trace(self):
        """
        :rtype: ``dict`` trace_context as a dict; could be None
        """
        trace_db = None
        try:
            trace_db = trace_service.get_trace_db_by_trigger_instance(
                self.trigger_instance
            )
        except:
            LOG.exception(
                "No Trace found for TriggerInstance %s.", self.trigger_instance.id
            )
            return None

        # This would signify some sort of coding error so raise ValueError.
        if not trace_db:
            raise ValueError("Trace database not found.")

        trace_db = trace_service.add_or_update_given_trace_db(
            trace_db=trace_db,
            rules=[
                trace_service.get_trace_component_for_rule(
                    self.rule, self.trigger_instance
                )
            ],
        )
        return vars(TraceContext(id_=str(trace_db.id), trace_tag=trace_db.trace_tag))

    def _update_enforcement(self, enforcement_db):
        try:
            RuleEnforcement.add_or_update(enforcement_db)
        except:
            extra = {"enforcement_db": enforcement_db}
            LOG.exception("Failed writing enforcement model to db.", extra=extra)

    def _invoke_action(
        self, action_db, runnertype_db, params, context=None, additional_contexts=None
    ):
        """
        Schedule an action execution.

        :type action_exec_spec: :class:`ActionExecutionSpecDB`

        :param params: Partially rendered parameters to execute the action with.
        :type params: ``dict``

        :rtype: :class:`LiveActionDB` on successful scheduling, None otherwise.
        """
        action_ref = action_db.ref
        runnertype_db = action_utils.get_runnertype_by_name(
            action_db.runner_type["name"]
        )

        liveaction_db = LiveActionDB(
            action=action_ref, context=context, parameters=params
        )

        try:
            liveaction_db.parameters = self.get_resolved_parameters(
                runnertype_db=runnertype_db,
                action_db=action_db,
                params=liveaction_db.parameters,
                context=liveaction_db.context,
                additional_contexts=additional_contexts,
            )
        except param_exc.ParamException as e:
            # We still need to create a request, so liveaction_db is assigned an ID
            liveaction_db, execution_db = action_service.create_request(liveaction_db)

            # By this point the execution is already in the DB therefore need to mark it failed.
            _, e, tb = sys.exc_info()
            action_service.update_status(
                liveaction=liveaction_db,
                new_status=action_constants.LIVEACTION_STATUS_FAILED,
                result={
                    "error": six.text_type(e),
                    "traceback": "".join(traceback.format_tb(tb, 20)),
                },
            )

            # Might be a good idea to return the actual ActionExecution rather than bubble up
            # the exception.
            raise validation_exc.ValueValidationException(six.text_type(e))

        liveaction_db, execution_db = action_service.request(liveaction_db)

        return execution_db

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

import json

from st2common import log as logging
from st2common.constants import action as action_constants
from st2common.constants.trace import TRACE_CONTEXT
from st2common.models.api.trace import TraceContext
from st2common.models.db.liveaction import LiveActionDB
from st2common.models.db.rule_enforcement import RuleEnforcementDB
from st2common.models.utils import action_param_utils
from st2common.models.api.auth import get_system_username
from st2common.persistence.rule_enforcement import RuleEnforcement
from st2common.services import action as action_service
from st2common.services import trace as trace_service
from st2common.util import reference
from st2common.util import action_db as action_db_util
from st2reactor.rules.datatransform import get_transformer


LOG = logging.getLogger('st2reactor.ruleenforcement.enforce')

EXEC_KICKED_OFF_STATES = [action_constants.LIVEACTION_STATUS_SCHEDULED,
                          action_constants.LIVEACTION_STATUS_REQUESTED]


class RuleEnforcer(object):
    def __init__(self, trigger_instance, rule):
        self.trigger_instance = trigger_instance
        self.rule = rule

        try:
            self.data_transformer = get_transformer(trigger_instance.payload)
        except Exception as e:
            message = ('Failed to template-ize trigger payload: %s. If the payload contains '
                       'special characters such as "{{" which dont\'t reference value in '
                       'a datastore, those characters need to be escaped' % (str(e)))
            raise ValueError(message)

    def enforce(self):
        # TODO: Refactor this to avoid additional lookup in cast_params
        # TODO: rename self.rule.action -> self.rule.action_exec_spec
        action_ref = self.rule.action['ref']
        action_db = action_db_util.get_action_by_ref(action_ref)
        if not action_db:
            raise ValueError('Action "%s" doesn\'t exist' % (action_ref))

        data = self.data_transformer(self.rule.action.parameters)
        LOG.info('Invoking action %s for trigger_instance %s with data %s.',
                 self.rule.action.ref, self.trigger_instance.id,
                 json.dumps(data))

        # update trace before invoking the action.
        trace_context = self._update_trace()
        LOG.debug('Updated trace %s with rule %s.', trace_context, self.rule.id)

        context = {
            'trigger_instance': reference.get_ref_from_model(self.trigger_instance),
            'rule': reference.get_ref_from_model(self.rule),
            'user': get_system_username(),
            TRACE_CONTEXT: trace_context
        }

        extra = {'trigger_instance_db': self.trigger_instance, 'rule_db': self.rule}
        rule_spec = {'ref': self.rule.ref, 'id': str(self.rule.id), 'uid': self.rule.uid}
        enforcement_db = RuleEnforcementDB(trigger_instance_id=str(self.trigger_instance.id),
                                           rule=rule_spec)
        try:
            execution_db = RuleEnforcer._invoke_action(self.rule.action, data, context)
            # pylint: disable=no-member
            enforcement_db.execution_id = str(execution_db.id)
            # pylint: enable=no-member
        except:
            LOG.exception('Failed kicking off execution for rule %s.', self.rule, extra=extra)
            return None
        finally:
            self._update_enforcement(enforcement_db)

        extra['execution_db'] = execution_db
        # pylint: disable=no-member
        if execution_db.status not in EXEC_KICKED_OFF_STATES:
            # pylint: enable=no-member
            LOG.audit('Rule enforcement failed. Execution of Action %s failed. '
                      'TriggerInstance: %s and Rule: %s',
                      self.rule.action.name, self.trigger_instance, self.rule,
                      extra=extra)
            return execution_db

        LOG.audit('Rule enforced. Execution %s, TriggerInstance %s and Rule %s.',
                  execution_db, self.trigger_instance, self.rule, extra=extra)

        return execution_db

    def _update_trace(self):
        """
        :rtype: ``dict`` trace_context as a dict; could be None
        """
        trace_db = None
        try:
            trace_db = trace_service.get_trace_db_by_trigger_instance(self.trigger_instance)
        except:
            LOG.exception('No Trace found for TriggerInstance %s.', self.trigger_instance.id)
            return None

        # This would signify some sort of coding error so assert.
        assert trace_db

        trace_db = trace_service.add_or_update_given_trace_db(
            trace_db=trace_db,
            rules=[
                trace_service.get_trace_component_for_rule(self.rule, self.trigger_instance)
            ])
        return vars(TraceContext(id_=str(trace_db.id), trace_tag=trace_db.trace_tag))

    def _update_enforcement(self, enforcement_db):
        try:
            RuleEnforcement.add_or_update(enforcement_db)
        except:
            extra = {'enforcement_db': enforcement_db}
            LOG.exception('Failed writing enforcement model to db.', extra=extra)

    @staticmethod
    def _invoke_action(action_exec_spec, params, context=None):
        """
        Schedule an action execution.

        :type action_exec_spec: :class:`ActionExecutionSpecDB`

        :param params: Parameters to execute the action with.
        :type params: ``dict``

        :rtype: :class:`LiveActionDB` on successful schedueling, None otherwise.
        """
        action_ref = action_exec_spec['ref']

        # prior to shipping off the params cast them to the right type.
        params = action_param_utils.cast_params(action_ref, params)
        liveaction = LiveActionDB(action=action_ref, context=context, parameters=params)
        liveaction, execution = action_service.request(liveaction)

        return execution

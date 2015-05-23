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
from st2common.util import reference
from st2common.util import action_db as action_db_util
from st2reactor.rules.datatransform import get_transformer
from st2common.services import action as action_service
from st2common.models.db.liveaction import LiveActionDB
from st2common.models.utils import action_param_utils
from st2common.constants import action as action_constants
from st2common.models.api.auth import get_system_username


LOG = logging.getLogger('st2reactor.ruleenforcement.enforce')


class RuleEnforcer(object):
    def __init__(self, trigger_instance, rule):
        self.trigger_instance = trigger_instance
        self.rule = rule

        try:
            self.data_transformer = get_transformer(trigger_instance.payload)
        except Exception as e:
            message = ('Failed to template-ize trigger payload: %s. If the payload contains'
                       'special characters such as "{{" which dont\'t reference value in '
                       'a datastore, those characters need to be escaped' % (str(e)))
            raise ValueError(message)

    def enforce(self):
        # TODO: Refactor this to avoid additiona lookup in cast_params
        # TODO: rename self.rule.action -> self.rule.action_exec_spec
        action_ref = self.rule.action['ref']
        action_db = action_db_util.get_action_by_ref(action_ref)
        if not action_db:
            raise ValueError('Action "%s" doesn\'t exist' % (action_ref))

        data = self.data_transformer(self.rule.action.parameters)
        LOG.info('Invoking action %s for trigger_instance %s with data %s.',
                 self.rule.action.ref, self.trigger_instance.id,
                 json.dumps(data))

        context = {
            'trigger_instance': reference.get_ref_from_model(self.trigger_instance),
            'rule': reference.get_ref_from_model(self.rule),
            'user': get_system_username()
        }

        liveaction_db = RuleEnforcer._invoke_action(self.rule.action, data, context)
        if not liveaction_db:
            extra = {'trigger_instance_db': self.trigger_instance, 'rule_db': self.rule}
            LOG.audit('Rule enforcement failed. Liveaction for Action %s failed. '
                      'TriggerInstance: %s and Rule: %s',
                      self.rule.action.name, self.trigger_instance, self.rule,
                      extra=extra)
            return None

        extra = {'trigger_instance_db': self.trigger_instance, 'rule_db': self.rule,
                 'liveaction_db': liveaction_db}
        LOG.audit('Rule enforced. Liveaction %s, TriggerInstance %s and Rule %s.',
                  liveaction_db, self.trigger_instance, self.rule, extra=extra)

        return liveaction_db

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
        liveaction, _ = action_service.request(liveaction)

        if liveaction.status == action_constants.LIVEACTION_STATUS_REQUESTED:
            return liveaction
        else:
            return None

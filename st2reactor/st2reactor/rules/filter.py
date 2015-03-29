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

import st2common.operators as criteria_operators

from jsonpath_rw import parse
from st2common import log as logging
from st2common.constants.rules import TRIGGER_PAYLOAD_PREFIX
from st2common.constants.system import SYSTEM_KV_PREFIX
from st2common.services.keyvalues import KeyValueLookup
from st2common.util.templating import render_template_with_system_context


LOG = logging.getLogger('st2reactor.ruleenforcement.filter')


class RuleFilter(object):
    def __init__(self, trigger_instance, trigger, rule):
        """
        :param trigger_instance: TriggerInstance DB object.
        :type trigger_instance: :class:`TriggerInstanceDB``

        :param trigger: Trigger DB object.
        :type trigger: :class:`TriggerDB`

        :param rule: Rule DB object.
        :type rule: :class:`RuleDB`
        """
        self.trigger_instance = trigger_instance
        self.trigger = trigger
        self.rule = rule

    def filter(self):
        LOG.info('Validating rule %s for %s.', self.rule.id, self.trigger['name'])
        if not self.rule.enabled:
            return False

        criteria = self.rule.criteria
        is_rule_applicable = True

        if criteria and not self.trigger_instance.payload:
            return False

        payload_lookup = PayloadLookup(self.trigger_instance.payload)

        LOG.debug('Trigger payload: %s', self.trigger_instance.payload)
        for criterion_k in criteria.keys():
            criterion_v = criteria[criterion_k]
            is_rule_applicable = self._check_criterion(criterion_k, criterion_v, payload_lookup)
            if not is_rule_applicable:
                break

        if not is_rule_applicable:
            LOG.debug('Rule %s not applicable for %s.', self.rule.id,
                      self.trigger['name'])

        return is_rule_applicable

    def _check_criterion(self, criterion_k, criterion_v, payload_lookup):
        criteria_operator = ''

        if 'type' in criterion_v:
            criteria_operator = criterion_v['type']
        else:
            return False

        if 'pattern' not in criterion_v:
            criterion_v['pattern'] = None
        else:
            # Render the pattern (it can contain jinja expressions)
            value = criterion_v['pattern']

            try:
                criterion_v['pattern'] = render_template_with_system_context(value=value)
            except Exception:
                LOG.exception('Failed to render pattern value for key %s' % (criterion_k))
                return False

        try:
            matches = payload_lookup.get_value(criterion_k)
            # pick value if only 1 matches else will end up being an array match.
            if matches:
                payload_value = matches[0] if len(matches) > 0 else matches
            else:
                payload_value = None
        except:
            LOG.exception('Failed transforming criteria key %s', criterion_k)
            return False

        criteria_pattern = criterion_v['pattern']

        op_func = criteria_operators.get_operator(criteria_operator)

        try:
            return op_func(value=payload_value, criteria_pattern=criteria_pattern)
        except:
            LOG.exception('There might be a problem with critera in rule %s.', self.rule)
            return False


class PayloadLookup():

    def __init__(self, payload):
        self._context = {
            SYSTEM_KV_PREFIX: KeyValueLookup(),
            TRIGGER_PAYLOAD_PREFIX: payload
        }

    def get_value(self, lookup_key):
        expr = parse(lookup_key)
        matches = [match.value for match in expr.find(self._context)]
        if not matches:
            return None
        return matches

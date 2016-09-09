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
from jsonpath_rw import parse

from st2common import log as logging
import st2common.operators as criteria_operators
from st2common.constants.rules import TRIGGER_PAYLOAD_PREFIX, RULE_TYPE_BACKSTOP
from st2common.constants.keyvalue import SYSTEM_SCOPE
from st2common.services.keyvalues import KeyValueLookup
from st2common.util.templating import render_template_with_system_context


LOG = logging.getLogger('st2reactor.ruleenforcement.filter')


class RuleFilter(object):
    def __init__(self, trigger_instance, trigger, rule, extra_info=False):
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
        self.extra_info = extra_info

        # Base context used with a logger
        self._base_logger_context = {
            'rule': self.rule,
            'trigger': self.trigger,
            'trigger_instance': self.trigger_instance
        }

    def filter(self):
        """
        Return true if the rule is applicable to the provided trigger instance.

        :rtype: ``bool``
        """
        LOG.info('Validating rule %s for %s.', self.rule.ref, self.trigger['name'],
                 extra=self._base_logger_context)

        if not self.rule.enabled:
            if self.extra_info:
                LOG.info('Validation failed for rule %s as it is disabled.', self.rule.ref)
            return False

        criteria = self.rule.criteria
        is_rule_applicable = True

        if criteria and not self.trigger_instance.payload:
            return False

        payload_lookup = PayloadLookup(self.trigger_instance.payload)

        LOG.debug('Trigger payload: %s', self.trigger_instance.payload,
                  extra=self._base_logger_context)

        for criterion_k in criteria.keys():
            criterion_v = criteria[criterion_k]
            is_rule_applicable, payload_value, criterion_pattern = self._check_criterion(
                criterion_k, criterion_v, payload_lookup)
            if not is_rule_applicable:
                if self.extra_info:
                    criteria_extra_info = '\n'.join([
                        '  key: %s' % criterion_k,
                        '  pattern: %s' % criterion_pattern,
                        '  type: %s' % criterion_v['type'],
                        '  payload: %s' % payload_value
                    ])
                    LOG.info('Validation for rule %s failed on criteria -\n%s', self.rule.ref,
                             criteria_extra_info,
                             extra=self._base_logger_context)
                break

        if not is_rule_applicable:
            LOG.debug('Rule %s not applicable for %s.', self.rule.id, self.trigger['name'],
                      extra=self._base_logger_context)

        return is_rule_applicable

    def _check_criterion(self, criterion_k, criterion_v, payload_lookup):
        if 'type' not in criterion_v:
            # Comparison operator type not specified, can't perform a comparison
            return False

        criteria_operator = criterion_v['type']
        criteria_pattern = criterion_v.get('pattern', None)

        # Render the pattern (it can contain a jinja expressions)
        try:
            criteria_pattern = self._render_criteria_pattern(criteria_pattern=criteria_pattern)
        except Exception:
            LOG.exception('Failed to render pattern value "%s" for key "%s"' %
                          (criteria_pattern, criterion_k), extra=self._base_logger_context)
            return False

        try:
            matches = payload_lookup.get_value(criterion_k)
            # pick value if only 1 matches else will end up being an array match.
            if matches:
                payload_value = matches[0] if len(matches) > 0 else matches
            else:
                payload_value = None
        except:
            LOG.exception('Failed transforming criteria key %s', criterion_k,
                          extra=self._base_logger_context)
            return False

        op_func = criteria_operators.get_operator(criteria_operator)

        try:
            result = op_func(value=payload_value, criteria_pattern=criteria_pattern)
        except:
            LOG.exception('There might be a problem with the criteria in rule %s.', self.rule,
                          extra=self._base_logger_context)
            return False

        return result, payload_value, criteria_pattern

    def _render_criteria_pattern(self, criteria_pattern):
        # Note: Here we want to use strict comparison to None to make sure that
        # other falsy values such as integer 0 are handled correctly.
        if criteria_pattern is None:
            return None

        if not isinstance(criteria_pattern, six.string_types):
            # We only perform rendering if value is a string - rendering a non-string value
            # makes no sense
            return criteria_pattern

        criteria_pattern = render_template_with_system_context(value=criteria_pattern)
        return criteria_pattern


class SecondPassRuleFilter(RuleFilter):
    """
    Special filter that handles all second pass rules. For not these are only
    backstop rules i.e. those that can match when no other rule has matched.
    """
    def __init__(self, trigger_instance, trigger, rule, first_pass_matched):
        """
        :param trigger_instance: TriggerInstance DB object.
        :type trigger_instance: :class:`TriggerInstanceDB``

        :param trigger: Trigger DB object.
        :type trigger: :class:`TriggerDB`

        :param rule: Rule DB object.
        :type rule: :class:`RuleDB`

        :param first_pass_matched: Rules that matched in the first pass.
        :type first_pass_matched: `list`
        """
        super(SecondPassRuleFilter, self).__init__(trigger_instance, trigger, rule)
        self.first_pass_matched = first_pass_matched

    def filter(self):
        # backstop rules only apply if no rule matched in the first pass.
        if self.first_pass_matched and self._is_backstop_rule():
            return False
        return super(SecondPassRuleFilter, self).filter()

    def _is_backstop_rule(self):
        return self.rule.type['ref'] == RULE_TYPE_BACKSTOP


class PayloadLookup(object):

    def __init__(self, payload):
        self._context = {
            SYSTEM_SCOPE: KeyValueLookup(scope=SYSTEM_SCOPE),
            TRIGGER_PAYLOAD_PREFIX: payload
        }

    def get_value(self, lookup_key):
        expr = parse(lookup_key)
        matches = [match.value for match in expr.find(self._context)]
        if not matches:
            return None
        return matches

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

from st2common import log as logging
from st2common.constants.rules import RULE_TYPE_BACKSTOP
from st2reactor.rules.filter import RuleFilter, SecondPassRuleFilter

LOG = logging.getLogger('st2reactor.rules.RulesMatcher')


class RulesMatcher(object):
    def __init__(self, trigger_instance, trigger, rules, extra_info=False):
        self.trigger_instance = trigger_instance
        self.trigger = trigger
        self.rules = rules
        self.extra_info = extra_info

    def get_matching_rules(self):
        first_pass, second_pass = self._split_rules_into_passes()
        # first pass
        rule_filters = [RuleFilter(trigger_instance=self.trigger_instance,
                                   trigger=self.trigger,
                                   rule=rule,
                                   extra_info=self.extra_info)
                        for rule in first_pass]
        matched_rules = [rule_filter.rule for rule_filter in rule_filters if rule_filter.filter()]
        LOG.debug('[1st_pass] %d rule(s) found to enforce for %s.', len(matched_rules),
                  self.trigger['name'])
        # second pass
        rule_filters = [SecondPassRuleFilter(self.trigger_instance, self.trigger, rule,
                                             matched_rules)
                        for rule in second_pass]
        matched_in_second_pass = [rule_filter.rule for rule_filter in rule_filters
                                  if rule_filter.filter()]
        LOG.debug('[2nd_pass] %d rule(s) found to enforce for %s.', len(matched_in_second_pass),
                  self.trigger['name'])
        matched_rules.extend(matched_in_second_pass)
        LOG.info('%d rule(s) found to enforce for %s.', len(matched_rules),
                 self.trigger['name'])
        return matched_rules

    def _split_rules_into_passes(self):
        """
        Splits the rules in the Matcher into first_pass and second_pass collections.

        Since the
        """
        first_pass = []
        second_pass = []
        for rule in self.rules:
            if self._is_first_pass_rule(rule):
                first_pass.append(rule)
            else:
                second_pass.append(rule)
        return first_pass, second_pass

    def _is_first_pass_rule(self, rule):
        return rule.type['ref'] != RULE_TYPE_BACKSTOP

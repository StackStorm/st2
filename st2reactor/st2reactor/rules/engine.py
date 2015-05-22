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
from st2common.persistence.rule import Rule
from st2common.services.triggers import get_trigger_db_by_ref
from st2reactor.rules.enforcer import RuleEnforcer
from st2reactor.rules.matcher import RulesMatcher

LOG = logging.getLogger('st2reactor.rules.RulesEngine')


class RulesEngine(object):
    def handle_trigger_instance(self, trigger_instance):
        # Find matching rules for trigger instance.
        matching_rules = self.get_matching_rules_for_trigger(trigger_instance)

        # Create rule enforcers.
        enforcers = self.create_rule_enforcers(trigger_instance, matching_rules)

        # Enforce the rules.
        self.enforce_rules(enforcers)

    def get_matching_rules_for_trigger(self, trigger_instance):
        trigger = trigger_instance.trigger
        trigger = get_trigger_db_by_ref(trigger_instance.trigger)
        rules = Rule.query(trigger=trigger_instance.trigger, enabled=True)
        LOG.info('Found %d rules defined for trigger %s (type=%s)', len(rules), trigger['name'],
                 trigger['type'])
        matcher = RulesMatcher(trigger_instance=trigger_instance,
                               trigger=trigger, rules=rules)

        matching_rules = matcher.get_matching_rules()
        LOG.info('Matched %s rule(s) for trigger_instance %s (type=%s)', len(matching_rules),
                 trigger['name'], trigger['type'])
        return matching_rules

    def create_rule_enforcers(self, trigger_instance, matching_rules):
        enforcers = []
        for matching_rule in matching_rules:
            enforcers.append(RuleEnforcer(trigger_instance, matching_rule))
        return enforcers

    def enforce_rules(self, enforcers):
        for enforcer in enforcers:
            try:
                enforcer.enforce()  # Should this happen in an eventlet pool?
            except Exception as e:
                LOG.error('Exception enforcing rule %s: %s', enforcer.rule, e, exc_info=True)

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
from st2common.services.rules import get_rules_given_trigger
from st2common.services.triggers import get_trigger_db_by_ref
from st2reactor.rules.enforcer import RuleEnforcer
from st2reactor.rules.matcher import RulesMatcher

LOG = logging.getLogger('st2reactor.rules.RulesEngine')


class RulesEngine(object):
    def handle_trigger_instance(self, trigger_instance):
        # Find matching rules for trigger instance.
        matching_rules = self.get_matching_rules_for_trigger(trigger_instance)

        if matching_rules:
            # Create rule enforcers.
            enforcers = self.create_rule_enforcers(trigger_instance, matching_rules)

            # Enforce the rules.
            self.enforce_rules(enforcers)
        else:
            LOG.info('No matching rules found for trigger instance %s.', trigger_instance['id'])

    def get_matching_rules_for_trigger(self, trigger_instance):
        trigger = trigger_instance.trigger

        trigger_db = get_trigger_db_by_ref(trigger_instance.trigger)

        if not trigger_db:
            LOG.error('No matching trigger found in db for trigger instance %s.', trigger_instance)
            return None

        rules = get_rules_given_trigger(trigger=trigger)

        LOG.info('Found %d rules defined for trigger %s', len(rules),
                 trigger_db.get_reference().ref)

        if len(rules) < 1:
            return rules

        matcher = RulesMatcher(trigger_instance=trigger_instance,
                               trigger=trigger_db, rules=rules)

        matching_rules = matcher.get_matching_rules()
        LOG.info('Matched %s rule(s) for trigger_instance %s (trigger=%s)', len(matching_rules),
                 trigger_instance['id'], trigger_db.ref)
        return matching_rules

    def create_rule_enforcers(self, trigger_instance, matching_rules):
        """
        Creates a RuleEnforcer matching to each rule.

        This method is trigger_instance specific therefore if creation of 1 RuleEnforcer
        fails it is likely that all wil be broken.
        """
        enforcers = []
        for matching_rule in matching_rules:
            enforcers.append(RuleEnforcer(trigger_instance, matching_rule))
        return enforcers

    def enforce_rules(self, enforcers):
        for enforcer in enforcers:
            try:
                enforcer.enforce()  # Should this happen in an eventlet pool?
            except:
                LOG.exception('Exception enforcing rule %s.', enforcer.rule)

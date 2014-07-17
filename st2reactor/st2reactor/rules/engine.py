from sets import Set

from st2common import log as logging
from st2common.persistence.reactor import Rule
from st2reactor.rules.enforcer import RuleEnforcer
from st2reactor.rules.matcher import RulesMatcher

LOG = logging.getLogger('st2reactor.rules.RulesEngine')


class RulesEngine(object):
    def handle_trigger_instances(self, trigger_instances):
        # Find matching rules for each trigger instance.
        matching_rules_map = self.get_matching_rules_for_triggers(trigger_instances)

        # Create rule enforcers.
        enforcers = self.create_rule_enforcers(matching_rules_map)

        # Enforce the rules.
        self.enforce_rules(enforcers)

    def get_rules_for_triggers(self, trigger_names):
        trigger_rules_map = {}
        for trigger_name in trigger_names:
            rules = self.get_rules_for_trigger_from_db(trigger_name)
            trigger_rules_map[trigger_name] = rules
        return trigger_rules_map

    def get_rules_for_trigger_from_db(self, trigger_name):
        trigger_type = {'name': trigger_name}
        rules = Rule.query(trigger_type=trigger_type, enabled=True)
        LOG.info('Found %d rules defined for trigger %s.', len(rules), trigger_name)
        return rules

    def get_matching_rules_for_triggers(self, trigger_instances):
        trigger_names = [trigger_instance.trigger['name'] for trigger_instance in trigger_instances]
        trigger_names = Set(trigger_names)  # uniquify the list
        trigger_rules_map = self.get_rules_for_triggers(trigger_names)  # Saves some queries to db.
        matchers = [(trigger_instance, RulesMatcher(trigger_instance,
                        trigger_rules_map[trigger_instance.trigger['name']]))
                    for trigger_instance in trigger_instances]

        matching_rules_map = {}
        for trigger_instance, matcher in matchers:
            matching_rules = matcher.get_matching_rules()
            LOG.info('Matched %s rule(s) for trigger_instance %s.', len(matching_rules),
                     trigger_instance.trigger['name'])
            if not matching_rules:
                continue
            matching_rules_map[trigger_instance] = matching_rules
        return matching_rules_map

    def create_rule_enforcers(self, matching_rules_map):
        enforcers = []
        for trigger_instance, matching_rules in matching_rules_map.iteritems():
            for matching_rule in matching_rules:
                enforcers.append(RuleEnforcer(trigger_instance, matching_rule))
        return enforcers

    def enforce_rules(self, enforcers):
        for enforcer in enforcers:
            enforcer.enforce()  # Should this happen in an eventlet pool?

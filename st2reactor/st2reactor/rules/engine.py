from st2common import log as logging
from st2common.persistence.reactor import Rule
from st2common.services.triggers import get_trigger_db
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

    def get_rules_for_trigger(self, trigger):
        return self.get_rules_for_trigger_from_db(trigger)

    def get_rules_for_trigger_from_db(self, trigger):
        rules = Rule.query(trigger__id=trigger['id'], enabled=True)
        LOG.info('Found %d rules defined for trigger %s', len(rules), trigger['name'])
        return rules

    def get_matching_rules_for_trigger(self, trigger_instance):
        trigger = get_trigger_db(trigger=trigger_instance.trigger)
        rules = self.get_rules_for_trigger(trigger=trigger)
        matcher = RulesMatcher(trigger_instance=trigger_instance,
                               trigger=trigger, rules=rules)

        matching_rules = matcher.get_matching_rules()
        LOG.info('Matched %s rule(s) for trigger_instance %s.', len(matching_rules),
                 trigger['name'])
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

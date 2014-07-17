from sets import Set

from st2common import log as logging
from st2common.persistence.reactor import Rule
from st2reactor.rules.enforcer import RuleEnforcer
from st2reactor.rules.matcher import RulesMatcher

LOG = logging.getLogger('st2reactor.rules.RulesEngine')


class RulesEngine(object):
    def __init__(self):
        pass

    def handle_trigger_instances(self, trigger_instances):
        trigger_names = [trigger_instance.trigger['name'] for trigger_instance in trigger_instances]
        trigger_names = Set(trigger_names)  # uniquify the list
        trigger_rules_map = self.get_rules_for_triggers(trigger_names)  # Saves some queries to db.
        matchers = [(trigger_instance, RulesMatcher(trigger_instance,
                        trigger_rules_map[trigger_instance.trigger['name']]))
                    for trigger_instance in trigger_instances]

        for trigger_instance, matcher in matchers:
            matching_rules = matcher.get_matching_rules()
            LOG.info('Matched %s rule(s) for trigger_instance %s.', len(matching_rules),
                     trigger_instance)
            enforcer = RuleEnforcer(trigger_instance, matching_rules)
            enforcer.enforce()  # XXX: Should this happen inside an eventlet pool?

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

from st2common import log as logging
from st2reactor.rules.filter import RuleFilter

LOG = logging.getLogger('st2reactor.rules.RulesMatcher')


class RulesMatcher(object):
    def __init__(self, trigger_instance, rules):
        self.trigger_instance = trigger_instance
        self.rules = rules

    def get_matching_rules(self):
        rule_filters = [RuleFilter(self.trigger_instance, rule) for rule in self.rules]
        matched_rules = [rule_filter.rule for rule_filter in rule_filters if rule_filter.filter()]
        LOG.info('%d rule(s) found to enforce for %s.', len(matched_rules),
                 self.trigger_instance.trigger['name'])
        return matched_rules

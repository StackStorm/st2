from st2common import log as logging
from st2reactor.rules import operators


LOG = logging.getLogger('st2reactor.ruleenforcement.filter')


class RuleFilter(object):
    def __init__(self, trigger_instance, rule):
        self.trigger_instance = trigger_instance
        self.rule = rule

    def filter(self):
        LOG.info('Validating rule %s for %s.', self.rule.id, self.trigger_instance.trigger['name'])
        criteria = self.rule.criteria
        is_rule_applicable = True
        for criterion_k in criteria.keys():
            criterion_v = criteria[criterion_k]
            is_rule_applicable = self._check_criterion(criterion_k, criterion_v)
            if not is_rule_applicable:
                break
        return is_rule_applicable

    def _check_criterion(self, criterion_k, criterion_v):
        # No payload or matching criterion_k in the payload therefore cannot apply a criteria.
        if self.trigger_instance.payload is None or\
           criterion_k not in self.trigger_instance.payload or\
           'pattern' not in criterion_v or\
           criterion_v['pattern'] is None:
            return False

        payload_value = self.trigger_instance.payload[criterion_k]
        criteria_operator = ''
        criteria_pattern = criterion_v['pattern']
        if 'type' in criterion_v:
            criteria_operator = criterion_v['type']
        operator = operators.get_operator(criteria_operator)
        return operator(payload_value, criteria_pattern)

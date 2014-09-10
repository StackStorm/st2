from st2common import log as logging
from st2common.models.api.reactor import RuleAPI
import st2common.operators as criteria_operators
from st2reactor.rules.datatransform import get_transformer


LOG = logging.getLogger('st2reactor.ruleenforcement.filter')


class RuleFilter(object):
    def __init__(self, trigger_instance, rule):
        self.trigger_instance = trigger_instance
        self.rule = rule

    def filter(self):
        LOG.info('Validating rule %s for %s.', self.rule.id, self.trigger_instance.trigger['name'])
        criteria = RuleAPI.from_model(self.rule).criteria
        is_rule_applicable = True

        if criteria and not self.trigger_instance.payload:
            return False

        transform = get_transformer(self.trigger_instance.payload, self.rule)

        for criterion_k in criteria.keys():
            criterion_v = criteria[criterion_k]
            is_rule_applicable = self._check_criterion(criterion_k, criterion_v, transform)
            if not is_rule_applicable:
                break
        return is_rule_applicable

    def _check_criterion(self, criterion_k, criterion_v, transform):
        # No payload or matching criterion_k in the payload therefore cannot apply a criteria.
        if 'pattern' not in criterion_v or criterion_v['pattern'] is None:
            return False

        payload_value = transform({'result': '{{' + criterion_k + '}}'})
        criteria_operator = ''
        criteria_pattern = criterion_v['pattern']
        if 'type' in criterion_v:
            criteria_operator = criterion_v['type']
        op_func = criteria_operators.get_operator(criteria_operator)
        return op_func(payload_value['result'], criteria_pattern)

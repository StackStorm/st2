import re

from st2common import log as logging


LOG = logging.getLogger('st2reactor.ruleenforcement.filter')


def get_filter(trigger_instance):
    return Filter(trigger_instance)


def match_regex(value, match_pattern):
    regex = re.compile(match_pattern)
    # check for a match and not for details of the match.
    return regex.match(value) is not None


def equals(value, expected):
    # assuming strings
    return value == expected


MATCH_REGEX = 'matchregex'
EQUALS = 'equals'
operators = {
    MATCH_REGEX: match_regex,
    EQUALS: equals
}


class Filter(object):
    def __init__(self, trigger_instance):
        self._trigger_instance = trigger_instance

    def apply_filter(self, rule):
        LOG.info('Validating rule %s for %s.', rule.id, self._trigger_instance.trigger.name)
        criteria = Filter._get_criteria(rule)
        is_rule_applicable = True
        for criterion_k in criteria.keys():
            criterion_v = criteria[criterion_k]
            is_rule_applicable = self.__check_criterion(criterion_k, criterion_v)
            if not is_rule_applicable:
                break
        return is_rule_applicable

    @staticmethod
    def _get_criteria(rule):
        return rule.criteria

    def __check_criterion(self, criterion_k, criterion_v):
        # No payload or matching criterion_k in the payload therefore cannot apply a criteria.
        if self._trigger_instance.payload is None or\
           criterion_k not in self._trigger_instance.payload or\
           'pattern' not in criterion_v or\
           criterion_v['pattern'] is None:
            return False

        payload_value = self._trigger_instance.payload[criterion_k]
        criteria_operator = MATCH_REGEX
        criteria_pattern = criterion_v['pattern']
        if 'type' in criterion_v and criterion_v['type'] is not None:
            criteria_operator = criterion_v['type']
        operator = operators[criteria_operator] if criteria_operator in operators else \
            operators[MATCH_REGEX]

        return operator(payload_value, criteria_pattern)

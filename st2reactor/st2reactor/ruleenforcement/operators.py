import re

from datetime import datetime

# operator impls
equals = lambda v1, v2: v1 == v2

less_than = lambda v1, v2: v1 < v2

greater_than = lambda v1, v2: v1 > v2

def match_regex(value, match_pattern):
    regex = re.compile(match_pattern)
    # check for a match and not for details of the match.
    return regex.match(value) is not None

def _timediff(diff_target, period_seconds, operator):
    # pickup now in UTC to compare against
    utc_now = datetime.utcnow()
    # assuming diff_target is UTC and specified in python iso format.
    # python iso format is the format of datetime.datetime.isoformat()
    diff_target_utc = datetime.strptime(diff_target, '%Y-%m-%dT%H:%M:%S.%f')
    return operator((utc_now - diff_target_utc).total_seconds(), period_seconds)

def timediff_lt(diff_target, period):
    return _timediff(diff_target, period, less_than)

def timediff_gt(diff_target, period):
        return _timediff(diff_target, period, greater_than)


# operator match strings
MATCH_REGEX = 'matchregex'
EQUALS_SHORT = 'eq'
EQUALS_LONG = 'equals'
LESS_THAN_SHORT = 'lt'
LESS_THAN_LONG = 'lessthan'
GREATER_THAN_SHORT = 'gt'
GREATER_THAN_LONG = 'greaterthan'
TIMEDIFF_LT_SHORT = 'td_lt'
TIMEDIFF_LT_LONG = 'timediff_lt'
TIMEDIFF_GT_SHORT = 'td_gt'
TIMEDIFF_GT_LONG = 'timediff_gt'
DEFAULT = 'default'

# operator lookups
operators = {
    MATCH_REGEX: match_regex,
    EQUALS_SHORT: equals,
    EQUALS_LONG: equals,
    LESS_THAN_SHORT: less_than,
    LESS_THAN_LONG: less_than,
    GREATER_THAN_SHORT: greater_than,
    GREATER_THAN_LONG: greater_than,
    TIMEDIFF_LT_SHORT: timediff_lt,
    TIMEDIFF_LT_LONG: timediff_lt,
    TIMEDIFF_GT_SHORT: timediff_gt,
    TIMEDIFF_GT_LONG: timediff_gt,
    DEFAULT: match_regex
}

def get_operator(op):
    return operators[op] if op in operators else operators[DEFAULT]

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

import re

from datetime import datetime

__all__ = [
    'get_operator',
    'get_allowed_operators'
]

# Operation implementations


def equals(value, criteria_pattern):
    return value == criteria_pattern


def nequals(value, criteria_pattern):
    return value != criteria_pattern


def iequals(value, criteria_pattern):
    return value.lower() == criteria_pattern.lower()


def contains(value, criteria_pattern):
    return criteria_pattern in value


def icontains(value, criteria_pattern):
    return criteria_pattern.lower() in value.lower()


def ncontains(value, criteria_pattern):
    return criteria_pattern not in value


def incontains(value, criteria_pattern):
    return criteria_pattern.lower() not in value.lower()


def startswith(value, criteria_pattern):
    return value.startswith(criteria_pattern)


def istartswith(value, criteria_pattern):
    return value.lower().startswith(criteria_pattern.lower())


def endswith(value, criteria_pattern):
    return value.endswith(criteria_pattern)


def iendswith(value, criteria_pattern):
    return value.lower().endswith(criteria_pattern.lower())


def less_than(value, criteria_pattern):
    return value < criteria_pattern


def greater_than(value, criteria_pattern):
    return value > criteria_pattern


def get_allowed_operators():
    return operators


def get_operator(op):
    op = op.lower()
    if op in operators:
        return operators[op]
    else:
        raise Exception('Invalid operator: ' + op)


def match_regex(value, criteria_pattern):
    regex = re.compile(criteria_pattern)
    # check for a match and not for details of the match.
    return regex.match(value) is not None


def _timediff(diff_target, period_seconds, operator):
    # pickup now in UTC to compare against
    utc_now = datetime.utcnow()
    # assuming diff_target is UTC and specified in python iso format.
    # python iso format is the format of datetime.datetime.isoformat()
    diff_target_utc = datetime.strptime(diff_target, '%Y-%m-%dT%H:%M:%S.%f')
    return operator((utc_now - diff_target_utc).total_seconds(), period_seconds)


def timediff_lt(value, criteria_pattern):
    return _timediff(diff_target=value, period_seconds=criteria_pattern, operator=less_than)


def timediff_gt(value, criteria_pattern):
    return _timediff(diff_target=value, period_seconds=criteria_pattern, operator=greater_than)

# operator match strings
MATCH_REGEX = 'matchregex'
EQUALS_SHORT = 'eq'
EQUALS_LONG = 'equals'
NEQUALS_LONG = 'nequals'
NEQUALS_SHORT = 'neq'
IEQUALS_SHORT = 'ieq'
IEQUALS_LONG = 'iequals'
CONTAINS_LONG = 'contains'
ICONTAINS_LONG = 'icontains'
NCONTAINS_LONG = 'ncontains'
INCONTAINS_LONG = 'incontains'
STARTSWITH_LONG = 'startswith'
ISTARTSWITH_LONG = 'istartswith'
ENDSWITH_LONG = 'endswith'
IENDSWITH_LONG = 'iendswith'
LESS_THAN_SHORT = 'lt'
LESS_THAN_LONG = 'lessthan'
GREATER_THAN_SHORT = 'gt'
GREATER_THAN_LONG = 'greaterthan'
TIMEDIFF_LT_SHORT = 'td_lt'
TIMEDIFF_LT_LONG = 'timediff_lt'
TIMEDIFF_GT_SHORT = 'td_gt'
TIMEDIFF_GT_LONG = 'timediff_gt'

# operator lookups
operators = {
    MATCH_REGEX: match_regex,
    EQUALS_SHORT: equals,
    EQUALS_LONG: equals,
    NEQUALS_SHORT: nequals,
    NEQUALS_LONG: nequals,
    IEQUALS_SHORT: iequals,
    IEQUALS_LONG: iequals,
    CONTAINS_LONG: contains,
    ICONTAINS_LONG: icontains,
    NCONTAINS_LONG: ncontains,
    INCONTAINS_LONG: incontains,
    STARTSWITH_LONG: startswith,
    ISTARTSWITH_LONG: istartswith,
    ENDSWITH_LONG: endswith,
    IENDSWITH_LONG: iendswith,
    LESS_THAN_SHORT: less_than,
    LESS_THAN_LONG: less_than,
    GREATER_THAN_SHORT: greater_than,
    GREATER_THAN_LONG: greater_than,
    TIMEDIFF_LT_SHORT: timediff_lt,
    TIMEDIFF_LT_LONG: timediff_lt,
    TIMEDIFF_GT_SHORT: timediff_gt,
    TIMEDIFF_GT_LONG: timediff_gt
}

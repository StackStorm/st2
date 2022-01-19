# Copyright 2020 The StackStorm Authors.
# Copyright 2019 Extreme Networks, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import absolute_import

import re
import six
import fnmatch

from st2common.util import date as date_utils
from st2common.constants.rules import TRIGGER_ITEM_PAYLOAD_PREFIX
from st2common.util.payload import PayloadLookup

__all__ = [
    "SEARCH",
    "get_operator",
    "get_allowed_operators",
    "UnrecognizedConditionError",
]


def get_allowed_operators():
    return operators


def get_operator(op):
    op = op.lower()
    if op in operators:
        return operators[op]
    else:
        raise Exception("Invalid operator: " + op)


class UnrecognizedConditionError(Exception):
    pass


# Operation implementations


def search(value, criteria_pattern, criteria_condition, check_function):
    """
    Search a list of values that match all child criteria. If condition is 'any', return a
    successful match if any items match all child criteria. If condition is 'all', return a
    successful match if ALL items match all child criteria.

    value: the payload list to search
    condition: one of:
      * any - return true if any payload items of the list match all criteria items
      * all - return true if all payload items of the list match all criteria items
      * all2any - return true if all payload items of the list match any criteria items
      * any2any - return true if any payload items match any criteria items
    pattern: a dictionary of criteria to apply to each item of the list

    This operator has O(n) algorithmic complexity in terms of number of child patterns.
    This operator has O(n) algorithmic complexity in terms of number of payload fields.

    However, it has O(n_patterns * n_payloads) algorithmic complexity, where:
      n_patterns = number of child patterns
      n_payloads = number of fields in payload
    It is therefore very easy to write a slow rule when using this operator.

    This operator should ONLY be used when trying to match a small number of child patterns and/or
    a small number of payload list elements.

    Other conditions (such as 'count', 'count_gt', 'count_gte', etc.) can be added as needed.

    Data from the trigger:

    {
        "fields": [
            {
                "field_name": "Status",
                "to_value": "Approved"
            }
        ]
    }

    Example #1

    ---
    criteria:
      trigger.fields:
        type: search
        # Controls whether this criteria has to match any or all items of the list
        condition: any  # or all or all2any or any2any
        pattern:
          # Here our context is each item of the list
          # All of these patterns have to match the item for the item to match
          # These are simply other operators applied to each item in the list
          # "#" and text after are ignored.
          # This allows dictionary keys to be unique but refer to the same field
          item.field_name:
            type: "equals"
            pattern: "Status"

          item.to_value:
            type: "equals"
            pattern: "Approved"

          item.field_name#1:
            type: "greaterthan"
            pattern: 40

          item.field_name#2:
            type: "lessthan"
            pattern: 50
    """
    if isinstance(value, dict):
        value = [value]
    payloadItemMatch = all
    patternMatch = all
    if criteria_condition == "any":
        payloadItemMatch = any
    elif criteria_condition == "all2any":
        patternMatch = any
    elif criteria_condition == "any2any":
        payloadItemMatch = any
        patternMatch = any
    elif criteria_condition != "all":
        raise UnrecognizedConditionError(
            "The '%s' condition is not recognized for type search, 'any', 'all', 'any2any'"
            " and 'all2any' are allowed" % criteria_condition
        )

    rtn = payloadItemMatch(
        [
            # any/all payload item can match
            patternMatch(
                [
                    # Match any/all patterns
                    check_function(
                        child_criterion_k,
                        child_criterion_v,
                        PayloadLookup(
                            child_payload, prefix=TRIGGER_ITEM_PAYLOAD_PREFIX
                        ),
                    )
                    for child_criterion_k, child_criterion_v in six.iteritems(
                        criteria_pattern
                    )
                ]
            )
            for child_payload in value
        ]
    )
    return rtn


def equals(value, criteria_pattern):
    if criteria_pattern is None:
        return False

    value, criteria_pattern = ensure_operators_are_strings(value, criteria_pattern)
    return value == criteria_pattern


def nequals(value, criteria_pattern):
    value, criteria_pattern = ensure_operators_are_strings(value, criteria_pattern)
    return value != criteria_pattern


def iequals(value, criteria_pattern):
    if criteria_pattern is None:
        return False

    value, criteria_pattern = ensure_operators_are_strings(value, criteria_pattern)
    return value.lower() == criteria_pattern.lower()


def contains(value, criteria_pattern):
    if criteria_pattern is None:
        return False

    value, criteria_pattern = ensure_operators_are_strings(value, criteria_pattern)
    return criteria_pattern in value


def icontains(value, criteria_pattern):
    if criteria_pattern is None:
        return False

    value, criteria_pattern = ensure_operators_are_strings(value, criteria_pattern)
    return criteria_pattern.lower() in value.lower()


def ncontains(value, criteria_pattern):
    if criteria_pattern is None:
        return False

    value, criteria_pattern = ensure_operators_are_strings(value, criteria_pattern)
    return criteria_pattern not in value


def incontains(value, criteria_pattern):
    if criteria_pattern is None:
        return False

    value, criteria_pattern = ensure_operators_are_strings(value, criteria_pattern)
    return criteria_pattern.lower() not in value.lower()


def startswith(value, criteria_pattern):
    if criteria_pattern is None:
        return False

    value, criteria_pattern = ensure_operators_are_strings(value, criteria_pattern)
    return value.startswith(criteria_pattern)


def istartswith(value, criteria_pattern):
    if criteria_pattern is None:
        return False

    value, criteria_pattern = ensure_operators_are_strings(value, criteria_pattern)
    return value.lower().startswith(criteria_pattern.lower())


def endswith(value, criteria_pattern):
    if criteria_pattern is None:
        return False

    value, criteria_pattern = ensure_operators_are_strings(value, criteria_pattern)
    return value.endswith(criteria_pattern)


def iendswith(value, criteria_pattern):
    if criteria_pattern is None:
        return False

    value, criteria_pattern = ensure_operators_are_strings(value, criteria_pattern)
    return value.lower().endswith(criteria_pattern.lower())


def less_than(value, criteria_pattern):
    if criteria_pattern is None:
        return False
    return value < criteria_pattern


def greater_than(value, criteria_pattern):
    if criteria_pattern is None:
        return False
    return value > criteria_pattern


def match_wildcard(value, criteria_pattern):
    if criteria_pattern is None:
        return False

    value, criteria_pattern = ensure_operators_are_strings(value, criteria_pattern)
    return fnmatch.fnmatch(value, criteria_pattern)


def match_regex(value, criteria_pattern):
    # match_regex is deprecated, please use 'regex' and 'iregex'
    if criteria_pattern is None:
        return False

    value, criteria_pattern = ensure_operators_are_strings(value, criteria_pattern)
    regex = re.compile(criteria_pattern, re.DOTALL)
    # check for a match and not for details of the match.
    return regex.match(value) is not None


def regex(value, criteria_pattern):
    if criteria_pattern is None:
        return False

    value, criteria_pattern = ensure_operators_are_strings(value, criteria_pattern)
    regex = re.compile(criteria_pattern)
    # check for a match and not for details of the match.
    return regex.search(value) is not None


def iregex(value, criteria_pattern):
    if criteria_pattern is None:
        return False

    value, criteria_pattern = ensure_operators_are_strings(value, criteria_pattern)
    regex = re.compile(criteria_pattern, re.IGNORECASE)
    # check for a match and not for details of the match.
    return regex.search(value) is not None


def _timediff(diff_target, period_seconds, operator):
    """
    :param diff_target: Date string.
    :type diff_target: ``str``

    :param period_seconds: Seconds.
    :type period_seconds: ``int``

    :rtype: ``bool``
    """
    # Pickup now in UTC to compare against
    utc_now = date_utils.get_datetime_utc_now()

    # assuming diff_target is UTC and specified in python iso format.
    # Note: date_utils.parse uses dateutil.parse which is way more flexible then strptime and
    # supports many date formats
    diff_target_utc = date_utils.parse(diff_target)
    return operator((utc_now - diff_target_utc).total_seconds(), float(period_seconds))


def timediff_lt(value, criteria_pattern):
    if criteria_pattern is None:
        return False
    return _timediff(
        diff_target=value, period_seconds=criteria_pattern, operator=less_than
    )


def timediff_gt(value, criteria_pattern):
    if criteria_pattern is None:
        return False
    return _timediff(
        diff_target=value, period_seconds=criteria_pattern, operator=greater_than
    )


def exists(value, criteria_pattern):
    return value is not None


def nexists(value, criteria_pattern):
    return value is None


def inside(value, criteria_pattern):
    if criteria_pattern is None:
        return False

    value, criteria_pattern = ensure_operators_are_strings(value, criteria_pattern)
    return value in criteria_pattern


def ninside(value, criteria_pattern):
    if criteria_pattern is None:
        return False

    value, criteria_pattern = ensure_operators_are_strings(value, criteria_pattern)
    return value not in criteria_pattern


def ensure_operators_are_strings(value, criteria_pattern):
    """
    This function ensures that both value and criteria_pattern arguments are unicode (string)
    values if the input value type is bytes.

    If a value is of types bytes and not a unicode, it's converted to unicode. This way we
    ensure all the operators which expect string / unicode values work, even if one of the
    values is bytes (this can happen when input is not controlled by the end user - e.g. trigger
    payload under Python 3 deployments).

    :return: tuple(value, criteria_pattern)
    """
    if isinstance(value, bytes):
        value = value.decode("utf-8")

    if isinstance(criteria_pattern, bytes):
        criteria_pattern = criteria_pattern.decode("utf-8")

    return value, criteria_pattern


# operator match strings
MATCH_WILDCARD = "matchwildcard"
MATCH_REGEX = "matchregex"
REGEX = "regex"
IREGEX = "iregex"
EQUALS_SHORT = "eq"
EQUALS_LONG = "equals"
NEQUALS_LONG = "nequals"
NEQUALS_SHORT = "neq"
IEQUALS_SHORT = "ieq"
IEQUALS_LONG = "iequals"
CONTAINS_LONG = "contains"
ICONTAINS_LONG = "icontains"
NCONTAINS_LONG = "ncontains"
INCONTAINS_LONG = "incontains"
STARTSWITH_LONG = "startswith"
ISTARTSWITH_LONG = "istartswith"
ENDSWITH_LONG = "endswith"
IENDSWITH_LONG = "iendswith"
LESS_THAN_SHORT = "lt"
LESS_THAN_LONG = "lessthan"
GREATER_THAN_SHORT = "gt"
GREATER_THAN_LONG = "greaterthan"
TIMEDIFF_LT_SHORT = "td_lt"
TIMEDIFF_LT_LONG = "timediff_lt"
TIMEDIFF_GT_SHORT = "td_gt"
TIMEDIFF_GT_LONG = "timediff_gt"
KEY_EXISTS = "exists"
KEY_NOT_EXISTS = "nexists"
INSIDE_LONG = "inside"
INSIDE_SHORT = "in"
NINSIDE_LONG = "ninside"
NINSIDE_SHORT = "nin"
SEARCH = "search"

# operator lookups
operators = {
    MATCH_WILDCARD: match_wildcard,
    MATCH_REGEX: match_regex,
    REGEX: regex,
    IREGEX: iregex,
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
    TIMEDIFF_GT_LONG: timediff_gt,
    KEY_EXISTS: exists,
    KEY_NOT_EXISTS: nexists,
    INSIDE_LONG: inside,
    INSIDE_SHORT: inside,
    NINSIDE_LONG: ninside,
    NINSIDE_SHORT: ninside,
    SEARCH: search,
}

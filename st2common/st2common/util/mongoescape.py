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

import six
from six.moves import zip

from st2common.util.deep_copy import fast_deepcopy_dict

# Note: Because of old rule escaping code, two different characters can be translated back to dot
RULE_CRITERIA_UNESCAPED = ["."]
RULE_CRITERIA_ESCAPED = ["\u2024"]
RULE_CRITERIA_ESCAPE_TRANSLATION = dict(
    list(zip(RULE_CRITERIA_UNESCAPED, RULE_CRITERIA_ESCAPED))
)
RULE_CRITERIA_UNESCAPE_TRANSLATION = dict(
    list(zip(RULE_CRITERIA_ESCAPED, RULE_CRITERIA_UNESCAPED))
)

# http://docs.mongodb.org/manual/faq/developers/#faq-dollar-sign-escaping
UNESCAPED = [".", "$"]
ESCAPED = ["\uFF0E", "\uFF04"]
ESCAPE_TRANSLATION = dict(list(zip(UNESCAPED, ESCAPED)))
UNESCAPE_TRANSLATION = dict(
    list(zip(ESCAPED, UNESCAPED))
    + list(zip(RULE_CRITERIA_ESCAPED, RULE_CRITERIA_UNESCAPED))
)


def _translate_chars(field, translation):
    if isinstance(field, list):
        return _translate_chars_in_list(field, translation)

    if isinstance(field, dict):
        return _translate_chars_in_dict(field, translation)

    return field


def _translate_chars_in_list(field, translation):
    return [_translate_chars(value, translation) for value in field]


def _translate_chars_in_key(key, translation):
    for k, v in six.iteritems(translation):
        if k in key:
            key = key.replace(k, v)

    return key


def _translate_chars_in_dict(field, translation):
    return {
        _translate_chars_in_key(k, translation): _translate_chars(v, translation)
        for k, v in six.iteritems(field)
    }


def escape_chars(field):
    if not isinstance(field, dict) and not isinstance(field, list):
        return field

    value = fast_deepcopy_dict(field)

    return _translate_chars(value, ESCAPE_TRANSLATION)


def unescape_chars(field):
    if not isinstance(field, dict) and not isinstance(field, list):
        return field

    value = fast_deepcopy_dict(field)

    return _translate_chars(value, UNESCAPE_TRANSLATION)

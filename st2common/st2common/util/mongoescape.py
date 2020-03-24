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

try:  # Python 3
    from functools import singledispatch
except ImportError:  # Python 2
    from singledispatch import singledispatch

import six
from six.moves import zip

from st2common.util.ujson import fast_deepcopy

# Note: Because of old rule escaping code, two different characters can be translated back to dot
RULE_CRITERIA_UNESCAPED = ['.']
RULE_CRITERIA_ESCAPED = [u'\u2024']
RULE_CRITERIA_ESCAPE_TRANSLATION = dict(list(zip(RULE_CRITERIA_UNESCAPED, RULE_CRITERIA_ESCAPED)))
RULE_CRITERIA_UNESCAPE_TRANSLATION = dict(list(zip(RULE_CRITERIA_ESCAPED, RULE_CRITERIA_UNESCAPED)))

# http://docs.mongodb.org/manual/faq/developers/#faq-dollar-sign-escaping
UNESCAPED = ['.', '$']
ESCAPED = [u'\uFF0E', u'\uFF04']
ESCAPE_TRANSLATION = dict(list(zip(UNESCAPED, ESCAPED)))
UNESCAPE_TRANSLATION = dict(
    list(zip(ESCAPED, UNESCAPED)) + list(zip(RULE_CRITERIA_ESCAPED, RULE_CRITERIA_UNESCAPED))
)


@singledispatch
def _translate_chars(field, translation):
    return field


@_translate_chars.register(list)
def _translate_chars_in_list(field, translation):
    return [_translate_chars(value, translation) for value in field]


def _translate_chars_in_key(key, translation):
    for k, v in [(k, v) for k, v in six.iteritems(translation) if k in key]:
        key = key.replace(k, v)

    return key


@_translate_chars.register(dict)
def _translate_chars_in_dict(field, translation):
    return {
        _translate_chars_in_key(k, translation): _translate_chars(v, translation)
        for k, v in six.iteritems(field)
    }


def escape_chars(field):
    return _translate_chars(fast_deepcopy(field), ESCAPE_TRANSLATION)


def unescape_chars(field):
    return _translate_chars(fast_deepcopy(field), UNESCAPE_TRANSLATION)

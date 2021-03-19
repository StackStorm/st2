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

import json
import jsonpath_rw
import six
import orjson

from st2common.util import db as db_util
from st2common.constants.meta import yaml_safe_load
from st2common.constants.meta import yaml_safe_dump


__all__ = [
    "from_json_string",
    "from_yaml_string",
    "json_escape",
    "jsonpath_query",
    "to_complex",
    "to_json_string",
    "to_yaml_string",
]


def from_json_string(value):
    return orjson.loads(six.text_type(value))


def from_yaml_string(value):
    return yaml_safe_load(six.text_type(value))


def to_json_string(value, indent=None, sort_keys=False, separators=(",", ": ")):
    value = db_util.mongodb_to_python_types(value)

    options = {}

    if indent is not None:
        options["indent"] = indent

    if sort_keys is not None:
        options["sort_keys"] = sort_keys

    if separators is not None:
        options["separators"] = separators

    return json.dumps(value, **options)


def to_yaml_string(value, indent=None, allow_unicode=True):
    value = db_util.mongodb_to_python_types(value)

    options = {"default_flow_style": False}

    if indent is not None:
        options["indent"] = indent

    if allow_unicode is not None:
        options["allow_unicode"] = allow_unicode

    return yaml_safe_dump(value, **options)


def json_escape(value):
    """Adds escape sequences to problematic characters in the string
    This filter simply passes the value to json.dumps
    as a convenient way of escaping characters in it
    However, before returning, we want to strip the double
    quotes at the ends of the string, since we're not looking
    for a valid JSON value at the end, just conveniently using
    this function to do the escaping. The value could be any
    arbitrary value
    """

    return json.dumps(value).strip('"')


def jsonpath_query(value, query):
    """Extracts data from an object `value` using a JSONPath `query`.
    :link: https://github.com/kennknowles/python-jsonpath-rw
    :param value: a object (dict, array, etc) to query
    :param query: a JSONPath query expression (string)
    :returns: the result of the query executed on the value
    :rtype: dict, array, int, string, bool
    """
    expr = jsonpath_rw.parse(query)

    matches = [match.value for match in expr.find(value)]

    if not matches:
        return None

    return matches


def to_complex(value):
    return json.dumps(value)


# Magic string to which None type is serialized when using use_none filter
NONE_MAGIC_VALUE = "%*****__%NONE%__*****%"


def use_none(value):
    return NONE_MAGIC_VALUE if value is None else value

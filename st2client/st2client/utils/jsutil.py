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

from __future__ import absolute_import
from jsonpath_rw import parse
import re

# A simple expression is defined as a series of letters [a-zA-Z], numbers [0-9],
# dashes '-', and underscores '_' separated by one period '.'.
# A simple expression must not start with a period.
# A simple expression must not end with a period.
# A simple expression must not have more than one period in succession, ie. in
# between each period must be one or more of the valid non-period characters.
#
# Examples of valid "simple expressions":
#  abc
#  abc.def.ghi
#
# Examples of non-simple expressions:
#  .aaa
#  a..b
#  abc.
#  a(*
SIMPLE_EXPRESSION_REGEX = r"^([a-zA-Z0-9\-_]+\.)*([a-zA-Z0-9\-_]+)$"
SIMPLE_EXPRESSION_REGEX_CMPL = re.compile(SIMPLE_EXPRESSION_REGEX)


def _get_value_simple(doc, key):
    """
    Extracts a value from a nested set of dictionaries 'doc' based on
    a 'key' string.
    The key string is expected to be of the format 'x.y.z'
    where each component in the string is a key in a dictionary separated
    by '.' to denote the next key is in a nested dictionary.

    Returns the extracted value from the key specified (if found)
    Returns None if the key can not be found
    """
    split_key = key.split('.')
    if not split_key:
        return None

    value = doc
    for k in split_key:
        if isinstance(value, dict) and k in value:
            value = value[k]
        else:
            return None
    return value


def _get_value_complex(doc, key):
    """
    Extracts a value from a nested set of dictionaries 'doc' based on
    a 'key' string.
    The key is expected to be a jsonpath_rw expression:
    http://jsonpath-rw.readthedocs.io/en/stable/

    Returns the extracted value from the key specified (if found)
    Returns None if the key can not be found
    """
    jsonpath_expr = parse(key)
    matches = jsonpath_expr.find(doc)
    value = None if len(matches) < 1 else matches[0].value
    return value


def get_value(doc, key):
    if not key:
        raise ValueError("key is None or empty: '{}'".format(key))

    if not isinstance(doc, dict):
        raise ValueError("doc is not an instance of dict: type={} value='{}'".format(type(doc),
                                                                                     doc))
    # jsonpath_rw can be very slow when processing expressions.
    # In the case of a simple expression we've created a "fast path" that avoids
    # the complexity introduced by running jsonpath_rw code.
    # For more complex expressions we fall back to using jsonpath_rw.
    # This provides flexibility and increases performance in the base case.
    match = SIMPLE_EXPRESSION_REGEX_CMPL.match(key)
    if match:
        return _get_value_simple(doc, key)
    else:
        return _get_value_complex(doc, key)


def get_kvps(doc, keys):
    """
    Extracts one or more keys ('keys' can be a string or list of strings)
    from the dictionary 'doc'.

    Return a subset of 'doc' with only the 'keys' specified as members, all
    other data in the dictionary will be filtered out.
    Return an empty dict if no keys are found.
    """
    if not isinstance(keys, list):
        keys = [keys]

    new_doc = {}
    for key in keys:
        value = get_value(doc, key)
        if value is not None:
            nested = new_doc
            while '.' in key:
                attr = key[:key.index('.')]
                if attr not in nested:
                    nested[attr] = {}
                nested = nested[attr]
                key = key[key.index('.') + 1:]
            nested[key] = value

    return new_doc

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

import functools
import operator


def get_value(doc, key):
    """
    Extracts a value from a nested set of dictionaries 'doc' based on
    a 'key' string.
    The key string is expected to be of the format 'x.y.z'
    where each component in the string is a key in a dictionary separated
    by '.' to denote the next key is in a nested dictionary.

    Returns the extracted value from the key specified (if found)
    Returns None if the key can not be found
    """
    if not key or not isinstance(doc, dict):
        raise ValueError()

    split_key = key.split('.')
    if not split_key:
        return None

    value = doc
    for k in split_key:
        if isinstance(value, dict) and key in value:
            value = value[key]
        else:
            return None
    return value

def get_kvps(doc, keys):
    """
    Extracts one or more keys ('keys' can be a string or list of strings)
    from the dictionary 'doc'.
    The key string is expected to be of the format 'x.y.z'
    where each component in the string is a key in a dictionary separated
    by '.' to denote the next key is in a nested dictionary.

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

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

from jsonpath_rw import parse


def get_value(doc, key):
    if not key or not isinstance(doc, dict):
        raise ValueError()
    jsonpath_expr = parse(key)
    matches = jsonpath_expr.find(doc)
    value = None if len(matches) < 1 else matches[0].value
    return value


def get_kvps(doc, keys):
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

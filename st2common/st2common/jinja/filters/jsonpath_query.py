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

import jsonpath-rw

__all__ = [
    'jsonpath_query',
]


def jsonpath_query(value, query):
    """Extracts data from an object `value` using a JSONPath `query`.
    :link: https://github.com/kennknowles/python-jsonpath-rw
    :param value: a object (dict, array, etc) to query
    :param query: a JSONPath query expression (string)
    :returns: the result of the query executed on the value
    :rtype: dict, array, int, string, bool
    """
    expr = jsonpath_rw.parse(query)
    matches = [match.value for match in expr.find(obj)]
    if not matches:
        return None
    return matches

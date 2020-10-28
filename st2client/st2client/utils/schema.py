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
#
import sys


TYPE_TABLE = {
    dict: 'object',
    list: 'array',
    int: 'integer',
    str: 'string',
    float: 'number',
    bool: 'boolean',
    type(None): 'null',
}

if sys.version_info[0] < 3:
    TYPE_TABLE[unicode] = 'string'  # noqa  # pylint: disable=E0602


def _dict_to_schema(item):
    schema = {}
    for key, value in item.iteritems():
        if isinstance(value, dict):
            schema[key] = {
                'type': 'object',
                'parameters': _dict_to_schema(value)
            }
        else:
            schema[key] = {
                'type': TYPE_TABLE[type(value)]
            }

    return schema


def render_output_schema_from_output(output):
    """Given an action output produce a reasonable schema to match.
    """
    return _dict_to_schema(output)

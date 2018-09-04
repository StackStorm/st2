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

import json
import mongoengine
import six
import yaml

__all__ = [
    'from_json_string',
    'from_yaml_string',
    'to_json_string',
    'to_yaml_string',
]


def from_json_string(value):
    return json.loads(six.text_type(value))


def from_yaml_string(value):
    return yaml.safe_load(six.text_type(value))


def to_json_string(value, indent=None, sort_keys=False, separators=(',', ': ')):
    options = {}

    if indent is not None:
        options['indent'] = indent

    if sort_keys is not None:
        options['sort_keys'] = sort_keys

    if separators is not None:
        options['separators'] = separators

    return json.dumps(value, **options)


def to_yaml_string(value, indent=None, allow_unicode=True):
    if isinstance(value, mongoengine.base.datastructures.BaseDict):
        value = dict(value)

    options = {'default_flow_style': False}

    if indent is not None:
        options['indent'] = indent

    if allow_unicode is not None:
        options['allow_unicode'] = allow_unicode

    return yaml.safe_dump(value, **options)

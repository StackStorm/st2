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

import re
import json
import copy
import jinja2

from st2common.persistence.datastore import KeyValuePair
import six


PAYLOAD_PREFIX = 'trigger'
RULE_DATA_PREFIX = 'rule'
SYSTEM_PREFIX = 'system'


class Jinja2BasedTransformer(object):
    def __init__(self, payload):
        self._payload_context = Jinja2BasedTransformer.\
            _construct_context(PAYLOAD_PREFIX, payload, {})

    def __call__(self, mapping):
        context = copy.copy(self._payload_context)
        context = self._construct_system_context(mapping, context)
        resolved_mapping = {}
        for mapping_k, mapping_v in six.iteritems(mapping):
            template = jinja2.Template(mapping_v)
            resolved_mapping[mapping_k] = template.render(context)
        return resolved_mapping

    @staticmethod
    def _construct_context(prefix, data, context):
        if data is None:
            return context
        context = Jinja2BasedTransformer.\
            _construct_system_context(data, context)
        template = jinja2.Template(json.dumps(data))
        resolved_data = json.loads(template.render(context))
        if resolved_data:
            if prefix not in context:
                context[prefix] = {}
            context[prefix].update(resolved_data)
        return context

    @staticmethod
    def _construct_system_context(data, context):
        """Identify the system context in the data."""
        # The following regex will look for all occurrences of "{{system.*}}",
        # "{{ system.* }}", "{{ system.*}}", and "{{system.* }}" in the data.
        regex = '{{\s*' + SYSTEM_PREFIX + '.(.*?)\s*}}'
        keys = re.findall(regex, json.dumps(data))
        if not keys:
            return context
        kvps = {}
        for key in keys:
            kvp = KeyValuePair.get_by_name(key)
            kvps[key] = kvp.value
        if kvps:
            if SYSTEM_PREFIX not in context:
                context[SYSTEM_PREFIX] = {}
            context[SYSTEM_PREFIX].update(kvps)
        return context


def get_transformer(payload):
    return Jinja2BasedTransformer(payload)

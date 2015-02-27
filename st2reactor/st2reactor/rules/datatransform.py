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

import json
import copy
import jinja2

from st2common.constants.rules import TRIGGER_PAYLOAD_PREFIX
from st2common.constants.system import SYSTEM_KV_PREFIX
from st2common.services.keyvalues import KeyValueLookup
from st2common.util import jinja as jinja_utils


class Jinja2BasedTransformer(object):
    def __init__(self, payload):
        self._payload_context = Jinja2BasedTransformer.\
            _construct_context(TRIGGER_PAYLOAD_PREFIX, payload, {})

    def __call__(self, mapping):
        context = copy.copy(self._payload_context)
        context[SYSTEM_KV_PREFIX] = KeyValueLookup()
        return jinja_utils.render_values(mapping=mapping, context=context)

    @staticmethod
    def _construct_context(prefix, data, context):
        if data is None:
            return context
        # setup initial context as system context to help resolve the original context
        # which may itself contain references to system variables.
        context = {SYSTEM_KV_PREFIX: KeyValueLookup()}
        template = jinja2.Template(json.dumps(data))
        resolved_data = json.loads(template.render(context))
        if resolved_data:
            if prefix not in context:
                context[prefix] = {}
            context[prefix].update(resolved_data)
        return context


def get_transformer(payload):
    return Jinja2BasedTransformer(payload)

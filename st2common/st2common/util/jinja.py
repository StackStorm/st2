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

import jinja2
import six


def render_values(mapping=None, context=None):
    """
    Render an incoming mapping using context provided in context using Jinja2. Returns a dict
    containing rendered mapping.

    :param mapping: Input as a dictionary of key value pairs.
    :type mapping: ``dict``

    :param context: Context to be used for dictionary.
    :type context: ``dict``

    :rtype: ``dict``
    """

    if not context or not mapping:
        return mapping

    env = jinja2.Environment(undefined=jinja2.StrictUndefined)
    rendered_mapping = {}
    for k, v in six.iteritems(mapping):
        # jinja2 works with string so transform list and dict to strings.
        reverse_json_dumps = False
        if isinstance(v, dict) or isinstance(v, list):
            v = json.dumps(v)
            reverse_json_dumps = True
        else:
            v = str(v)
        rendered_v = env.from_string(v).render(context)
        # no change therefore no templatization so pick params from original to retain
        # original type
        if rendered_v == v:
            rendered_mapping[k] = mapping[k]
            continue
        if reverse_json_dumps:
            rendered_v = json.loads(rendered_v)
        rendered_mapping[k] = rendered_v
    return rendered_mapping

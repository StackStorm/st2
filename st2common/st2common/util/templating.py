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

import six
from jinja2 import Environment, StrictUndefined

from st2common.constants.system import SYSTEM_KV_PREFIX
from st2common.services.keyvalues import KeyValueLookup

__all__ = [
    'render_template',
    'render_template_with_system_context'
]


def render_template(value, context=None):
    """
    Render provided template with the provided context.

    :param value: Template string.
    :type value: ``str``

    :param context: Template context.
    :type context: ``dict``
    """
    assert isinstance(value, six.string_types)
    context = context or {}

    env = Environment(undefined=StrictUndefined)
    template = env.from_string(value)
    rendered = template.render(context)

    return rendered


def render_template_with_system_context(value):
    """
    Render provided template with a default system context.

    :param value: Template string.
    :type value: ``str``

    :param context: Template context.
    :type context: ``dict``
    """
    context = {
        SYSTEM_KV_PREFIX: KeyValueLookup(),
    }

    rendered = render_template(value=value, context=context)
    return rendered

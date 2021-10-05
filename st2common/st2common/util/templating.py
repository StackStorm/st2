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

from __future__ import absolute_import
import six

from st2common.util.jinja import get_jinja_environment
from st2common.constants.keyvalue import DATASTORE_PARENT_SCOPE
from st2common.constants.keyvalue import SYSTEM_SCOPE, FULL_SYSTEM_SCOPE
from st2common.constants.keyvalue import USER_SCOPE, FULL_USER_SCOPE
from st2common.services.keyvalues import KeyValueLookup
from st2common.services.keyvalues import UserKeyValueLookup

__all__ = [
    "render_template",
    "render_template_with_system_context",
    "render_template_with_system_and_user_context",
]


def render_template(value, context=None):
    """
    Render provided template with the provided context.

    :param value: Template string.
    :type value: ``str``

    :param context: Template context.
    :type context: ``dict``
    """
    if not isinstance(value, six.string_types):
        raise TypeError(
            f"The template value needs to be of type string (was {type(value)})."
        )
    context = context or {}

    env = get_jinja_environment(allow_undefined=False)  # nosec
    template = env.from_string(value)
    rendered = template.render(context)

    return rendered


def render_template_with_system_context(value, context=None, prefix=None):
    """
    Render provided template with a default system context.

    :param value: Template string.
    :type value: ``str``

    :param context: Template context (optional).
    :type context: ``dict``

    :param prefix: Datastore key prefix (optional).
    :type prefix: ``str``

    :rtype: ``str``
    """
    context = context or {}
    context[DATASTORE_PARENT_SCOPE] = {
        SYSTEM_SCOPE: KeyValueLookup(prefix=prefix, scope=FULL_SYSTEM_SCOPE)
    }

    rendered = render_template(value=value, context=context)
    return rendered


def render_template_with_system_and_user_context(
    value, user, context=None, prefix=None
):
    """
    Render provided template with a default system context and user context for the provided user.

    :param value: Template string.
    :type value: ``str``

    :param user: Name (PK) of the user for the user scope.
    :type user: ``str``

    :param context: Template context (optional).
    :type context: ``dict``

    :param prefix: Datastore key prefix (optional).
    :type prefix: ``str``

    :rtype: ``str``
    """
    context = context or {}
    context[DATASTORE_PARENT_SCOPE] = {
        SYSTEM_SCOPE: KeyValueLookup(prefix=prefix, scope=FULL_SYSTEM_SCOPE),
        USER_SCOPE: UserKeyValueLookup(prefix=prefix, user=user, scope=FULL_USER_SCOPE),
    }

    rendered = render_template(value=value, context=context)
    return rendered

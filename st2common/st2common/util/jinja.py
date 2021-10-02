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

import re

import six

from st2common import log as logging
from st2common.util.compat import to_unicode
from st2common.util.jsonify import json_encode
from st2common.util.jsonify import json_decode


__all__ = ["get_jinja_environment", "render_values", "is_jinja_expression"]


JINJA_EXPRESSIONS_START_MARKERS = ["{{", "{%"]

JINJA_REGEX = "({{(.*)}})"
JINJA_REGEX_PTRN = re.compile(JINJA_REGEX)
JINJA_BLOCK_REGEX = "({%(.*)%})"
JINJA_BLOCK_REGEX_PTRN = re.compile(JINJA_BLOCK_REGEX)


LOG = logging.getLogger(__name__)


def get_filters():
    # Lazy / late import to avoid long module import times
    from st2common.expressions.functions import datastore
    from st2common.expressions.functions import data
    from st2common.expressions.functions import regex
    from st2common.expressions.functions import time
    from st2common.expressions.functions import version
    from st2common.expressions.functions import path

    return {
        "decrypt_kv": datastore.decrypt_kv,
        "from_json_string": data.from_json_string,
        "from_yaml_string": data.from_yaml_string,
        "json_escape": data.json_escape,
        "jsonpath_query": data.jsonpath_query,
        "to_complex": data.to_complex,
        "to_json_string": data.to_json_string,
        "to_yaml_string": data.to_yaml_string,
        "regex_match": regex.regex_match,
        "regex_replace": regex.regex_replace,
        "regex_search": regex.regex_search,
        "regex_substring": regex.regex_substring,
        "to_human_time_from_seconds": time.to_human_time_from_seconds,
        "version_compare": version.version_compare,
        "version_more_than": version.version_more_than,
        "version_less_than": version.version_less_than,
        "version_equal": version.version_equal,
        "version_match": version.version_match,
        "version_bump_major": version.version_bump_major,
        "version_bump_minor": version.version_bump_minor,
        "version_bump_patch": version.version_bump_patch,
        "version_strip_patch": version.version_strip_patch,
        "use_none": data.use_none,
        "basename": path.basename,
        "dirname": path.dirname,
    }


def get_jinja_environment(allow_undefined=False, trim_blocks=True, lstrip_blocks=True):
    """
    jinja2.Environment object that is setup with right behaviors and custom filters.

    :param strict_undefined: If should allow undefined variables in templates
    :type strict_undefined: ``bool``

    """
    # Late import to avoid very expensive in-direct import (~1 second) when this function
    # is not called / used
    import jinja2
    import jinja2.sandbox

    undefined = jinja2.Undefined if allow_undefined else jinja2.StrictUndefined
    env = jinja2.sandbox.SandboxedEnvironment(  # nosec
        undefined=undefined, trim_blocks=trim_blocks, lstrip_blocks=lstrip_blocks
    )
    env.filters.update(get_filters())
    env.tests["in"] = lambda item, list: item in list
    return env


def render_values(mapping=None, context=None, allow_undefined=False):
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

    # Add in special __context variable that provides an easy way to get access to entire context.
    # This mean __context is a reserve key word although backwards compat is preserved by making
    # sure that real context is updated later and therefore will override the __context value.
    super_context = {}
    super_context["__context"] = context
    super_context.update(context)

    env = get_jinja_environment(allow_undefined=allow_undefined)
    rendered_mapping = {}
    for k, v in six.iteritems(mapping):
        # jinja2 works with string so transform list and dict to strings.
        reverse_json_dumps = False
        if isinstance(v, dict) or isinstance(v, list):
            v = json_encode(v)
            reverse_json_dumps = True
        else:
            # Special case for text type to handle unicode
            if isinstance(v, six.string_types):
                v = to_unicode(v)
            else:
                # Other types (e.g. boolean, etc.)
                v = str(v)

        try:
            LOG.info("Rendering string %s. Super context=%s", v, super_context)
            rendered_v = env.from_string(v).render(super_context)
        except Exception as e:
            # Attach key and value which failed the rendering
            e.key = k
            e.value = v
            raise e

        # no change therefore no templatization so pick params from original to retain
        # original type
        if rendered_v == v:
            rendered_mapping[k] = mapping[k]
            continue
        if reverse_json_dumps:
            rendered_v = json_decode(rendered_v)
        rendered_mapping[k] = rendered_v
    LOG.info(
        "Mapping: %s, rendered_mapping: %s, context: %s",
        mapping,
        rendered_mapping,
        context,
    )
    return rendered_mapping


def is_jinja_expression(value):
    """
    Function which very simplisticly detect if the provided value contains or is a Jinja
    expression.
    """
    if not value or not isinstance(value, six.string_types):
        return False

    for marker in JINJA_EXPRESSIONS_START_MARKERS:
        if marker in value:
            return True

    return False


def convert_jinja_to_raw_block(value):
    if isinstance(value, dict):
        return {k: convert_jinja_to_raw_block(v) for k, v in six.iteritems(value)}

    if isinstance(value, list):
        return [convert_jinja_to_raw_block(v) for v in value]

    if isinstance(value, six.string_types):
        if JINJA_REGEX_PTRN.findall(value) or JINJA_BLOCK_REGEX_PTRN.findall(value):
            return "{% raw %}" + value + "{% endraw %}"

    return value

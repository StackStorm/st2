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
import re

import semver


class CustomFilters(object):
    '''
    Collection of CustomFilters for jinja2
    '''

    ###############
    # regex filters
    @staticmethod
    def _get_regex_flags(ignorecase=False):
        return re.I if ignorecase else 0

    @staticmethod
    def _regex_match(value, pattern='', ignorecase=False):
        if not isinstance(value, six.string_types):
            value = str(value)
        flags = CustomFilters._get_regex_flags(ignorecase)
        return bool(re.match(pattern, value, flags))

    @staticmethod
    def _regex_replace(value='', pattern='', replacement='', ignorecase=False):
        if not isinstance(value, six.string_types):
            value = str(value)
        flags = CustomFilters._get_regex_flags(ignorecase)
        regex = re.compile(pattern, flags)
        return regex.sub(replacement, value)

    @staticmethod
    def _regex_search(value, pattern='', ignorecase=False):
        if not isinstance(value, six.string_types):
            value = str(value)
        flags = CustomFilters._get_regex_flags(ignorecase)
        return bool(re.search(pattern, value, flags))

    #################
    # version filters
    @staticmethod
    def _version_compare(value, pattern):
        return semver.compare(value, pattern)

    @staticmethod
    def _version_more_than(value, pattern):
        return semver.compare(value, pattern) == 1

    @staticmethod
    def _version_less_than(value, pattern):
        return semver.compare(value, pattern) == -1

    @staticmethod
    def _version_equal(value, pattern):
        return semver.compare(value, pattern) == 0

    @staticmethod
    def _version_match(value, pattern):
        return semver.match(value, pattern)

    @staticmethod
    def _version_bump_major(value):
        return semver.bump_major(value)

    @staticmethod
    def _version_bump_minor(value):
        return semver.bump_minor(value)

    @staticmethod
    def _version_bump_patch(value):
        return semver.bump_patch(value)

    @staticmethod
    def _version_strip_patch(value):
        return "{major}.{minor}".format(**semver.parse(value))

    @staticmethod
    def get_filters():
        return {
            'regex_match': CustomFilters._regex_match,
            'regex_replace': CustomFilters._regex_replace,
            'regex_search': CustomFilters._regex_search,
            'version_compare': CustomFilters._version_compare,
            'version_more_than': CustomFilters._version_more_than,
            'version_less_than': CustomFilters._version_less_than,
            'version_equal': CustomFilters._version_equal,
            'version_match': CustomFilters._version_match,
            'version_bump_major': CustomFilters._version_bump_major,
            'version_bump_minor': CustomFilters._version_bump_minor,
            'version_bump_patch': CustomFilters._version_bump_patch,
            'version_strip_patch': CustomFilters._version_strip_patch
        }


def get_jinja_environment(allow_undefined=False):
    '''
    jinja2.Environment object that is setup with right behaviors and custom filters.

    :param strict_undefined: If should allow undefined variables in templates
    :type strict_undefined: ``bool``

    '''
    undefined = jinja2.Undefined if allow_undefined else jinja2.StrictUndefined
    env = jinja2.Environment(undefined=undefined)
    env.filters.update(CustomFilters.get_filters())
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

    env = get_jinja_environment(allow_undefined=allow_undefined)
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

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

from st2common.exceptions.content import ParseException
from st2common.models.utils.action_alias_utils import extract_parameters

__all__ = [
    'list_format_strings_from_aliases',
    'normalise_alias_format_string',
    'match_command_to_alias'
]


def list_format_strings_from_aliases(aliases):
    '''
    List patterns from a collection of alias objects

    :param aliases: The list of aliases
    :type  aliases: ``list`` of :class:`st2common.models.api.action.ActionAliasAPI`

    :return: A description of potential execution patterns in a list of aliases.
    :rtype: ``list`` of ``list``
    '''
    patterns = []
    for alias in aliases:
        for format_ in alias.formats:
            display, representations = normalise_alias_format_string(format_)
            patterns.extend([(display, representation) for representation in representations])
    return patterns


def normalise_alias_format_string(alias_format):
    '''
    StackStorm action aliases can have two types;
        1. A simple string holding the format
        2. A dictionary which hold numerous alias format "representation(s)"
           With a single "display" for help about the action alias.
    This function processes both forms and returns a standardized form.

    :param alias_format: The alias format
    :type  alias_format: ``str`` or ``dict``

    :return: The representation of the alias
    :rtype: ``tuple`` of (``str``, ``str``)
    '''
    display = None
    representation = []

    if isinstance(alias_format, six.string_types):
        display = alias_format
        representation.append(alias_format)
    elif isinstance(alias_format, dict):
        display = alias_format['display']
        representation = alias_format['representation']
    else:
        raise TypeError("alias_format '%s' is neither a dictionary or string type."
                        % repr(alias_format))
    return (display, representation)


def match_command_to_alias(command, aliases):
    """
    Match the text against an action and return the action reference.
    """
    results = []

    for alias in aliases:
        format_strings = list_format_strings_from_aliases([alias])
        for format_string in format_strings:
            try:
                extract_parameters(format_str=format_string[1],
                                   param_stream=command)
            except ParseException:
                continue

            results.append((alias, format_string[0], format_string[1]))
    return results

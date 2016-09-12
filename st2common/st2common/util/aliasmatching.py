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
import re
import copy.deepcopy


def list_patterns_from_aliases(aliases):
    '''
    List patterns from a collection of alias objects

    :param aliases: The list of aliases
    :type  aliases: ``list`` of :class:`st2common.persistence.actionalias.ActionAlias`

    :return: A description of potential execution patterns in a list of aliases.
    :rtype: ``list`` of ``dict``
    '''
    patterns = []
    for alias in aliases:
        for _format in alias.formats:
            display, representations = normalise_alias_format(_format)
            for representation in representations:
                if isinstance(representation, six.string_types):
                    pattern_context, kwargs = alias_format_string_to_pattern(representation)
                    patterns.append({
                        'context': pattern_context,
                        'action_ref': alias.action_ref,
                        'kwargs': kwargs
                    })
    return patterns


def normalise_alias_format(self, alias_format):
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
        raise TypeError("alias_format is neither a dictionary or string type.")
    return (display, representation)



def alias_format_string_to_pattern(alias_format, prefix=''):
    '''
    Extract named arguments from format to create a keyword argument list.
    Transform tokens into regular expressions.

    :param alias_format: The alias format
    :type  alias_format: ``str`` or ``dict``

    :return: The representation of the alias
    :rtype: ``tuple`` of (``str``, ``str``)
    '''
    kwargs = {}
    # Step 1: Extract action alias arguments so they can be used later
    #         when calling the stackstorm action.
    tokens = re.findall(r"{{(.*?)}}", alias_format, re.IGNORECASE)
    for token in tokens:
        if token.find("=") > -1:
            name, val = token.split("=")
            # Remove unnecessary whitespace
            name = name.strip()
            val = val.strip()
            kwargs[name] = val
            name = r"?P<{}>[\s\S]+?".format(name)
        else:
            name = token.strip()
            kwargs[name] = None
            name = r"?P<{}>[\s\S]+?".format(name)
        # The below code causes a regex exception to be raised under certain conditions.  Using replace() as alternative.
        #~ alias_format = re.sub( r"\s*{{{{{}}}}}\s*".format(token), r"\\s*({})\\s*".format(name), alias_format)
        # Replace token with named group match.
        alias_format = alias_format.replace(r"{{{{{}}}}}".format(token), r"({})".format(name))


    # Step 2: Append regex to match any extra parameters that weren't declared in the action alias.
    extra_params = r"""(:?\s+(\S+)\s*=("([\s\S]*?)"|'([\s\S]*?)'|({[\s\S]*?})|(\S+))\s*)*"""
    alias_format = r'^{}{}{}$'.format(prefix, alias_format, extra_params)

    return (re.compile(alias_format, re.I), kwargs)


def _extract_extra_params(extra_params):
    """
    Returns a dictionary of extra parameters supplied in the action_alias.
    """
    kwargs = {}
    for arg in extra_params.groups():
        if arg and "=" in arg:
            k, v = arg.split("=", 1)
            kwargs[k.strip()] = v.strip()
    return kwargs


def match_text_to_alias(text, aliases):
    """
    Match the text against an action and return the action reference.
    """
    results = []
    for pattern in aliases:
        res = pattern.search(text)
        if res:
            data = {}
            # Create keyword arguments starting with the defaults.
            # Deep copy is used here to avoid exposing the reference
            # outside the match function.
            data.update(copy.deepcopy(pattern.context)) #  check this!
            # Merge in the named arguments.
            data["kwargs"].update(res.groupdict())
            # Merge in any extra arguments supplied as a key/value pair.
            data["kwargs"].update(_extract_extra_params(res))
            results.append(data)

    if not results:
        return None

    results.sort(reverse=True)

    return results[0]
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

from st2common.util.actionalias_matching import normalise_alias_format_string


__all__ = [
    'generate_helpstring_list'
]


def generate_helpstring_list(aliases, filtering="", pack="", limit=0, offset=0):
    """
    List help strings from a collection of alias objects.

    :param aliases: The list of aliases
    :type  aliases: ``list`` of :class:`st2common.models.api.action.ActionAliasAPI`
    :param filtering: A search pattern.
    :type  filtering: ``string``
    :param pack: Name of a pack
    :type  pack: ``string``
    :param limit: The number of help strings to return in the list.
    :type  limit: ``integer``
    :param offset: The offset in the list to start return help strings.
    :type  limit: ``integer``

    :return: A list of aliases help strings.
    :rtype: ``list`` of ``list``
    """
    matches = {}
    cnt = 0
    for alias in aliases:
        # Skip disable aliases.
        if not alias.enabled:
            continue
        # Skip packs which don't explicitly match the requested pack.
        if pack != alias.pack and pack != "":
            continue
        for format_ in alias.formats:
            display, _ = normalise_alias_format_string(format_)
            if display:
                # Skip over help strings until the requested offset is reached.
                if cnt < offset:
                    cnt += 1
                    continue
                # Skip help string not containing keyword.
                if not re.search(filtering, display):
                    continue
                if not matches.get(alias.pack):
                    matches[alias.pack] = []
                matches[alias.pack].append({
                    "display": display,
                    "description": alias.description
                })
                cnt += 1
            # Return the list of help strings when we reach the requested limit.
            if (cnt >= offset + limit) and limit > 0:
                return matches
    return matches

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
from st2common.util.actionalias_matching import normalise_alias_format_string


__all__ = ["generate_helpstring_result"]


def generate_helpstring_result(aliases, filter=None, pack=None, limit=0, offset=0):
    """
    List help strings from a collection of alias objects.

    :param aliases: The list of aliases
    :type  aliases: ``list`` of :class:`st2common.models.api.action.ActionAliasAPI`
    :param filter_: A search pattern.
    :type  filter_: ``string``
    :param pack: Name of a pack
    :type  pack: ``string``
    :param limit: The number of help strings to return in the list.
    :type  limit: ``integer``
    :param offset: The offset in the list to start returning help strings.
    :type  limit: ``integer``

    :return: A list of aliases help strings.
    :rtype: ``list`` of ``list``
    """
    matches = []
    count = 0
    if not (isinstance(limit, int) and isinstance(offset, int)):
        raise TypeError("limit or offset argument is not an integer")
    for alias in aliases:
        # Skip disable aliases.
        if not alias.enabled:
            continue
        # Skip packs which don't explicitly match the requested pack.
        if pack and pack != alias.pack:
            continue
        for format_ in alias.formats:
            display, _, _ = normalise_alias_format_string(format_)
            if display:
                # Skip help strings not containing keyword.
                if not re.search(filter or "", display, flags=re.IGNORECASE):
                    continue
                # Skip over help strings not within the requested offset/limit range.
                if (offset == 0 and limit > 0) and count >= limit:
                    count += 1
                    continue
                elif (offset > 0 and limit == 0) and count < offset:
                    count += 1
                    continue
                elif (offset > 0 and limit > 0) and (
                    count < offset or count >= offset + limit
                ):
                    count += 1
                    continue

                matches.append(
                    {
                        "pack": alias.pack,
                        "display": display,
                        "description": alias.description,
                    }
                )
                count += 1
    return {"available": count, "helpstrings": matches}

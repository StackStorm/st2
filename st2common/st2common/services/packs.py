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

import itertools

import requests
import six
from oslo_config import cfg

from st2common import log as logging
from st2common.models.api.pack import PackAPI
from st2common.persistence.pack import Pack

__all__ = [
    'get_pack_by_ref',
    'fetch_pack_index',
    'get_pack_from_index',
    'search_pack_index'
]

EXCLUDE_FIELDS = [
    "repo_url",
    "email"
]

SEARCH_PRIORITY = [
    "name",
    "keywords"
]

LOG = logging.getLogger(__name__)


def get_pack_by_ref(pack_ref):
    """
    Retrieve PackDB by the provided reference.
    """
    pack_db = Pack.get_by_ref(pack_ref)
    return pack_db


def fetch_pack_index(index_url=None, logger=None):
    """
    Fetch the pack indexes (either from the config or provided as an argument)
    and return the object.
    """
    logger = logger or LOG

    if not index_url:
        # Reversing the indexes list from config so that the indexes have
        # descending (left-to-right) priority.
        # When multiple indexes have a pack with a given name, the index
        # that comes first in the list will be used.
        index_urls = cfg.CONF.content.index_url[::-1]
    elif isinstance(index_url, str):
        index_urls = [index_url]
    elif hasattr(index_url, '__iter__'):
        index_urls = index_url
    else:
        raise TypeError('"index_url" should either be a string or an iterable object.')

    errors = []
    result = {}
    for index_url in index_urls:
        try:
            result.update(requests.get(index_url).json())
        except ValueError:
            errors.append(index_url)
            logger.debug('Malformed index: %s' % index_url)
        except requests.exceptions.RequestException:
            errors.append(index_url)
            logger.debug('Could not fetch index: %s' % index_url)
    # If one of the indexes on the list is unresponsive, we do not throw
    # immediately. The only case where an exception is raised is when no
    # results could be obtained from all listed indexes.
    # This behavior allows for mirrors / backups and handling connection
    # or network issues in one of the indexes.
    if not result:
        raise ValueError("Malformed or empty %s: could not get results from %s." % (
            ("index" if len(errors) == 1 else "indexes"), ", ".join(errors)
        ))
    return result


def get_pack_from_index(pack):
    """
    Search index by pack name.
    Returns a pack.
    """
    if not pack:
        raise ValueError("Pack name must be specified.")

    index = fetch_pack_index()

    return PackAPI(**index.get(pack))


def search_pack_index(query, exclude=None, priority=None):
    """
    Search the pack index by query.
    Returns a list of matches for a query.
    """
    if not query:
        raise ValueError("Query must be specified.")

    if not exclude:
        exclude = EXCLUDE_FIELDS
    if not priority:
        priority = SEARCH_PRIORITY

    index = fetch_pack_index()

    matches = [[] for _ in range(len(priority) + 1)]
    for pack_dict in six.itervalues(index):
        pack = PackAPI(**pack_dict)

        for key, value in six.iteritems(vars(pack)):
            if not hasattr(value, '__contains__'):
                value = str(value)

            if key not in exclude and query in value:
                if key in priority:
                    matches[priority.index(key)].append(pack)
                else:
                    matches[-1].append(pack)
                break

    return list(itertools.chain.from_iterable(matches))

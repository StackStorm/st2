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

import itertools

import os
import requests
import six
from six.moves import range
from oslo_config import cfg

from st2common import log as logging
from st2common.content.utils import get_pack_base_path
from st2common.exceptions.content import ResourceDiskFilesRemovalError
from st2common.persistence.pack import Pack
from st2common.util.misc import lowercase_value
from st2common.util.jsonify import json_encode

__all__ = [
    "get_pack_by_ref",
    "fetch_pack_index",
    "get_pack_from_index",
    "search_pack_index",
    "delete_action_files_from_pack",
]

EXCLUDE_FIELDS = ["repo_url", "email"]

SEARCH_PRIORITY = ["name", "keywords"]

LOG = logging.getLogger(__name__)


def _build_index_list(index_url):
    if not index_url:
        # Reversing the indexes list from config so that the indexes have
        # descending (left-to-right) priority.
        # When multiple indexes have a pack with a given name, the index
        # that comes first in the list will be used.
        index_urls = cfg.CONF.content.index_url[::-1]
    elif isinstance(index_url, str):
        index_urls = [index_url]
    elif hasattr(index_url, "__iter__"):
        index_urls = index_url
    else:
        raise TypeError('"index_url" should either be a string or an iterable object.')
    return index_urls


def _fetch_and_compile_index(index_urls, logger=None, proxy_config=None):
    """
    Go through the index list and compile results into a single object.
    """
    status = []
    index = {}

    proxies_dict = {}
    verify = True

    if proxy_config:
        https_proxy = proxy_config.get("https_proxy", None)
        http_proxy = proxy_config.get("http_proxy", None)
        ca_bundle_path = proxy_config.get("proxy_ca_bundle_path", None)

        if https_proxy:
            proxies_dict["https"] = https_proxy
            verify = ca_bundle_path or True

        if http_proxy:
            proxies_dict["http"] = http_proxy

    for index_url in index_urls:
        index_status = {
            "url": index_url,
            "packs": 0,
            "message": None,
            "error": None,
        }
        index_json = None

        try:
            request = requests.get(index_url, proxies=proxies_dict, verify=verify)
            request.raise_for_status()
            index_json = request.json()
        except ValueError as e:
            index_status["error"] = "malformed"
            index_status["message"] = repr(e)
        except requests.exceptions.RequestException as e:
            index_status["error"] = "unresponsive"
            index_status["message"] = repr(e)
        except Exception as e:
            index_status["error"] = "other errors"
            index_status["message"] = repr(e)

        if index_json == {}:
            index_status["error"] = "empty"
            index_status["message"] = "The index URL returned an empty object."
        elif type(index_json) is list:
            index_status["error"] = "malformed"
            index_status["message"] = "Expected an index object, got a list instead."
        elif index_json and "packs" not in index_json:
            index_status["error"] = "malformed"
            index_status["message"] = 'Index object is missing "packs" attribute.'

        if index_status["error"]:
            logger.error(
                "Index parsing error: %s" % json_encode(index_status, indent=4)
            )
        else:
            # TODO: Notify on a duplicate pack aka pack being overwritten from a different index
            packs_data = index_json["packs"]
            index_status["message"] = "Success."
            index_status["packs"] = len(packs_data)
            index.update(packs_data)

        status.append(index_status)

    return index, status


def get_pack_by_ref(pack_ref):
    """
    Retrieve PackDB by the provided reference.
    """
    pack_db = Pack.get_by_ref(pack_ref)
    return pack_db


def fetch_pack_index(index_url=None, logger=None, allow_empty=False, proxy_config=None):
    """
    Fetch the pack indexes (either from the config or provided as an argument)
    and return the object.
    """
    logger = logger or LOG

    index_urls = _build_index_list(index_url)
    index, status = _fetch_and_compile_index(
        index_urls=index_urls, logger=logger, proxy_config=proxy_config
    )

    # If one of the indexes on the list is unresponsive, we do not throw
    # immediately. The only case where an exception is raised is when no
    # results could be obtained from all listed indexes.
    # This behavior allows for mirrors / backups and handling connection
    # or network issues in one of the indexes.
    if not index and not allow_empty:
        raise ValueError(
            "No results from the %s: tried %s.\nStatus: %s"
            % (
                ("index" if len(index_urls) == 1 else "indexes"),
                ", ".join(index_urls),
                json_encode(status, indent=4),
            )
        )
    return (index, status)


def get_pack_from_index(pack, proxy_config=None):
    """
    Search index by pack name.
    Returns a pack.
    """
    if not pack:
        raise ValueError("Pack name must be specified.")

    index, _ = fetch_pack_index(proxy_config=proxy_config)

    return index.get(pack)


def search_pack_index(
    query, exclude=None, priority=None, case_sensitive=True, proxy_config=None
):
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

    if not case_sensitive:
        query = str(query).lower()

    index, _ = fetch_pack_index(proxy_config=proxy_config)

    matches = [[] for i in range(len(priority) + 1)]
    for pack in six.itervalues(index):
        for key, value in six.iteritems(pack):
            if not hasattr(value, "__contains__"):
                value = str(value)

            if not case_sensitive:
                value = lowercase_value(value=value)

            if key not in exclude and query in value:
                if key in priority:
                    matches[priority.index(key)].append(pack)
                else:
                    matches[-1].append(pack)
                break

    return list(itertools.chain.from_iterable(matches))


def delete_action_files_from_pack(pack_name, entry_point, metadata_file):
    """
    Prepares the path for entry_point file and metadata file of action and
    deletes them from disk.
    """

    pack_base_path = get_pack_base_path(pack_name=pack_name)
    action_entrypoint_file_path = os.path.join(pack_base_path, "actions", entry_point)
    action_metadata_file_path = os.path.join(pack_base_path, metadata_file)

    if os.path.isfile(action_entrypoint_file_path):
        try:
            os.remove(action_entrypoint_file_path)
        except PermissionError:
            LOG.error(
                'No permission to delete the "%s" file',
                action_entrypoint_file_path,
            )
            msg = 'No permission to delete "%s" file from disk' % (
                action_entrypoint_file_path
            )
            raise PermissionError(msg)
        except Exception as e:
            LOG.error(
                'Unable to delete "%s" file. Exception was "%s"',
                action_entrypoint_file_path,
                e,
            )
            msg = (
                'The action file "%s" could not be removed from disk, please '
                "check the logs or ask your StackStorm administrator to check "
                "and delete the actions files manually" % (action_entrypoint_file_path)
            )
            raise ResourceDiskFilesRemovalError(msg)
    else:
        LOG.warning(
            'The action entry point file "%s" does not exists on disk.',
            action_entrypoint_file_path,
        )

    if os.path.isfile(action_metadata_file_path):
        try:
            os.remove(action_metadata_file_path)
        except PermissionError:
            LOG.error(
                'No permission to delete the "%s" file',
                action_metadata_file_path,
            )
            msg = 'No permission to delete "%s" file from disk' % (
                action_metadata_file_path
            )
            raise PermissionError(msg)
        except Exception as e:
            LOG.error(
                'Could not delete "%s" file. Exception was "%s"',
                action_metadata_file_path,
                e,
            )
            msg = (
                'The action file "%s" could not be removed from disk, please '
                "check the logs or ask your StackStorm administrator to check "
                "and delete the actions files manually" % (action_metadata_file_path)
            )
            raise ResourceDiskFilesRemovalError(msg)
    else:
        LOG.warning(
            'The action metadata file "%s" does not exists on disk.',
            action_metadata_file_path,
        )

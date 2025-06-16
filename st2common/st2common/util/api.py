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
from oslo_config import cfg

from st2common import log as logging
from st2common.constants.api import DEFAULT_API_VERSION
from st2common.util.url import get_url_without_trailing_slash

__all__ = [
    "get_base_public_api_url",
    "get_full_public_api_url",
]

LOG = logging.getLogger(__name__)


def get_base_public_api_url():
    """
    Return full public URL to the API endpoint (excluding the API version).

    :rtype: ``str``
    """
    # Note: This is here for backward compatibility reasons - if api_url is not set we fall back
    # to the old approach (using api listen host and port)
    if cfg.CONF.auth.api_url:
        api_url = get_url_without_trailing_slash(cfg.CONF.auth.api_url)
    else:
        LOG.warning('"auth.api_url" configuration option is not configured')
        api_url = "http://%s:%s" % (cfg.CONF.api.host, cfg.CONF.api.port)

    return api_url


def get_full_public_api_url(api_version=DEFAULT_API_VERSION):
    """
    Return full public URL to the API endpoint (including the API version).

    :rtype: ``str``
    """
    api_url = get_base_public_api_url()
    api_url = "%s/%s" % (api_url, api_version)
    return api_url

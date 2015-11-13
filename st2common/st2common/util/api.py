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

from oslo_config import cfg

from st2common import log as logging
from st2common.constants.api import DEFAULT_API_VERSION
from st2common.util.url import get_url_without_trailing_slash

__all__ = [
    'get_base_public_api_url',
    'get_full_public_api_url',

    'get_mistral_api_url'
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
        LOG.warn('"auth.api_url" configuration option is not configured')
        api_url = 'http://%s:%s' % (cfg.CONF.api.host, cfg.CONF.api.port)

    return api_url


def get_full_public_api_url(api_version=DEFAULT_API_VERSION):
    """
    Return full public URL to the API endpoint (including the API version).

    :rtype: ``str``
    """
    api_url = get_base_public_api_url()
    api_url = '%s/%s' % (api_url, api_version)
    return api_url


def get_mistral_api_url(api_version=DEFAULT_API_VERSION):
    """
    Return a URL which Mistral uses to talk back to the StackStorm API.

    Note: If not provided it defaults to the public API url.
    """
    if cfg.CONF.mistral.api_url:
        api_url = get_url_without_trailing_slash(cfg.CONF.mistral.api_url)
        api_url = '%s/%s' % (api_url, api_version)
    else:
        LOG.warn('"mistral.api_url" not set, using auth.api_url')
        api_url = get_full_public_api_url(api_version=api_version)

    return api_url

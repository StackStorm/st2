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

from oslo.config import cfg

from st2common.constants.api import DEFAULT_API_VERSION

__all__ = [
    'get_full_api_url'
]


def get_full_api_url(api_version=DEFAULT_API_VERSION):
    """
    Return full URL to the API endpoint.

    :rtype: ``str``
    """
    api_url = 'http://%s:%s/%s' % (cfg.CONF.api.host, cfg.CONF.api.port, api_version)
    return api_url

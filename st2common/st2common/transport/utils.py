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

__all__ = [
    'get_messaging_urls'
]

CONF = cfg.CONF


def get_messaging_urls():
    '''
    Determines the right messaging urls to supply. In case the `cluster_urls` config is
    specified then that is used. Else the single `url` property is used.

    :rtype: ``list``
    '''
    if CONF.messaging.cluster_urls:
        return CONF.messaging.cluster_urls
    return [CONF.messaging.url]

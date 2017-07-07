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

from st2common.runners.base_action import Action
from st2common.services.packs import search_pack_index


class PackSearch(Action):
    def __init__(self, config=None, action_service=None):
        super(PackSearch, self).__init__(config=config, action_service=action_service)
        self.https_proxy = self.config.get('https_proxy', None)
        self.https_proxy = self.config.get('http_proxy', None)
        self.ca_bundle_path = self.config.get('ca_bundle_path', None)
        self.proxy_config = {
            'https_proxy': self.https_proxy,
            'http_proxy': self.http_proxy,
            'ca_bundle_path': self.ca_bundle_path
        }

    """"Search for packs in StackStorm Exchange and other directories."""
    def run(self, query):
        """
        :param query: A word or a phrase to search for
        :type query: ``str``
        """
        return search_pack_index(query, proxy_config=self.proxy_config)

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

try:
    import simplejson as json
except ImportError:
    import json
import urlparse

import requests


class BaseClient(object):

    def __init__(self, api_base_url=None, api_version='v1', debug=False):
        self._api_version = api_version
        self._api_base_url = api_base_url
        self._versioned_base_url = urlparse.urljoin(self._api_base_url, self._api_version)
        self._authenticated = False
        self._debug = False

    def post(self, relative_url, payload, headers=None, debug=False):
        full_url = self._get_full_url()
        resp = requests.post(full_url, data=json.dumps(payload), headers=headers)
        if self._debug or debug:
            self._log_request_resp(url=full_url, payload=payload, headers=headers, resp=resp)

    def put(self, relative_url, payload, headers=None, debug=False):
        full_url = self._get_full_url()
        resp = requests.put(self._get_full_url(), data=json.dumps(payload), headers=headers)
        if self._debug or debug:
            self._log_request_resp(url=full_url, payload=payload, headers=headers, resp=resp)

    def get(self, relative_url, payload=None, headers=None, debug=False):
        full_url = self._get_full_url()
        resp = requests.get(self._get_full_url(), data=json.dumps(payload), headers=headers)
        if self._debug or debug:
            self._log_request_resp(url=full_url, payload=payload, headers=headers, resp=resp)

    def delete(self, relative_url, headers=None, debug=False):
        full_url = self._get_full_url()
        resp = requests.get(self._get_full_url(), headers=headers)
        if self._debug or debug:
            self._log_request_resp(url=full_url, headers=headers, resp=resp)

    def _get_full_url(self, relative_url):
        return urlparse.join(self._versioned_base_url, relative_url)

    @staticmethod
    def log_request_resp(url, payload=None, headers={}, resp=None):
        pass  # Curl format

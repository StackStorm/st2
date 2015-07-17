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

from st2pyclient.http_client.base import BaseClient


class AuthedClient(BaseClient):

    def __init__(self, auth_base_url=None, auth_api_version='v1', auth_credentials=None,
                 api_base_url=None, api_version='v1', creds_file_path='~/.st2/config',
                 debug=False):
        self._auth_base_url = auth_base_url
        self._auth_api_version = auth_api_version
        self._auth_credentials = auth_credentials

        if not self._auth_credentials:
            self._auth_credentials = self._get_credentials_from_file(creds_file_path)

        self._api_base_url = api_base_url
        self._api_version = api_version
        self._token = self._negotiate_auth_token()
        self._debug = debug

    def post(self, relative_url, payload):
        super(AuthedClient, self).post(relative_url, payload, headers=self._get_auth_headers())

    def get(self, relative_url, payload=None):
        super(AuthedClient, self).get(relative_url, payload=payload, headers=self._get_auth_headers())

    def put(self, relative_url, payload):
        super(AuthedClient, self).put(relative_url, payload, headers=self._get_auth_headers())

    def delete(self, relative_url):
        super(AuthedClient, self).delete(relative_url, headers=self._get_auth_headers())

    def _negotiate_auth_token(self):
        pass

    def _get_auth_headers(self):
        if self._is_token_expired(self._token):
            self._token = self._negotiate_auth_token()

        headers = {'X-Auth-Token': self._token['token']}
        return headers

    @staticmethod
    def _get_credentials_from_file(file_path):
        pass

    @staticmethod
    def _is_token_expired(token):
        pass

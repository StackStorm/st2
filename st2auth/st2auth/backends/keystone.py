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


from st2common import log as logging
from st2auth.backends.base import BaseAuthenticationBackend
import requests
import httplib

from six.moves.urllib import parse as urlparse
from six.moves.urllib.parse import urljoin

__all__ = [
    'KeystoneAuthenticationBackend'
]

LOG = logging.getLogger(__name__)


class KeystoneAuthenticationBackend(BaseAuthenticationBackend):
    """
    Backend which reads authentication information from keystone

    Note: This backend depends on the "requests" library.
    """

    def __init__(self, keystone_url, keystone_version=2):
        """
        :param keystone_url: Url of the Keystone server to authenticate against.
        :type keystone_url: ``str``
        :param keystone_version: Keystone version to authenticate against (default to 2).
        :type keystone_version: ``int``
        """
        url = urlparse(keystone_url)
        if url.path != '' or url.query != '' or url.fragment != '':
            raise Exception("The Keystone url {} does not seem to be correct.\n"
                            "Please only set the scheme+url+port "
                            "(e.x.: http://example.com:5000)".format(keystone_url))
        self._keystone_url = keystone_url
        self._keystone_version = keystone_version

    def authenticate(self, username, password):
        if self._keystone_version == 2:
            creds = {
                "auth": {
                    "passwordCredentials": {
                        "username": username,
                        "password": password
                    }
                }
            }
            login = requests.post(urljoin(self._keystone_url, 'v2.0/tokens'), json=creds)

        elif self._keystone_version == 3:
            creds = {
                "auth": {
                    "identity": {
                        "methods": [
                            "password"
                        ],
                        "password": {
                            "domain": {
                                "id": "default"
                            },
                            "user": {
                                "name": username,
                                "password": password
                            }
                        }
                    }
                }
            }
            login = requests.post(urljoin(self._keystone_url, 'v3/auth/tokens'), json=creds)
        else:
            raise Exception("Keystone version {} not supported".format(self._keystone_version))

        if login.status_code in [httplib.OK, httplib.CREATED]:
            LOG.debug('Authentication for user "{}" successful'.format(username))
            return True
        else:
            LOG.debug('Authentication for user "{}" failed: {}'.format(username, login.content))
            return False

    def get_user(self, username):
        pass

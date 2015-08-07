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

from passlib.apache import HtpasswdFile

from st2common import log as logging
from st2auth.backends.base import BaseAuthenticationBackend

__all__ = [
    'FlatFileAuthenticationBackend'
]

LOG = logging.getLogger(__name__)


class FlatFileAuthenticationBackend(BaseAuthenticationBackend):
    """
    Backend which reads authentication information from a local file.

    Entries need to be in a htpasswd file like format. This means entries can be managed with
    the htpasswd utility (https://httpd.apache.org/docs/current/programs/htpasswd.html) which
    ships with Apache HTTP server.

    Note: This backends depends on the "passlib" library.
    """

    def __init__(self, file_path):
        """
        :param file_path: Path to the file with authentication information.
        :type file_path: ``str``
        """
        self._file_path = file_path

    def authenticate(self, username, password):
        htpasswd_file = HtpasswdFile(path=self._file_path)
        result = htpasswd_file.check_password(username, password)

        if result is None:
            LOG.debug('User "%s" doesn\'t exist' % (username))
        elif result is False:
            LOG.debug('Invalid password for user "%s"' % (username))
        elif result is True:
            LOG.debug('Authentication for user "%s" successful' % (username))

        return bool(result)

    def get_user(self, username):
        pass

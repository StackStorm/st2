# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.

# to be able to import ldap run pip install python-ldap
import ldap

from st2common import log as logging
from st2auth.backends.base import BaseAuthenticationBackend

__all__ = [
    'LdapAuthenticationBackend'
]

LOG = logging.getLogger(__name__)


class LdapAuthenticationBackend(BaseAuthenticationBackend):
    """
    Backend which reads authentication information from a ldap server
    """

    def __init__(self, ldap_server, base_dn, group_dn):
        """
        :param ldap_server: URL of the LDAP Server
        :type ldap_server: ``str``
        :param base_dn: Base DN on the LDAP Server
        :type base_dn: ``str``
        """
        self._ldap_server = ldap_server
        self._base_dn = base_dn
        self._group_dn = group_dn

    def authenticate(self, username, password):
        search_filter = "uniqueMember=uid=" + username + "," + self._base_dn
        try:
            connect = ldap.open(self._ldap_server)
            connect.bind_s("uid=" + username + "," + self._base_dn, password)
            result = connect.search_s(self._group_dn, ldap.SCOPE_SUBTREE, search_filter)
            connect.unbind_s()
            if result is None:
                LOG.debug('User "%s" doesn\'t exist' % (username))
            elif result is False:
                LOG.debug('Invalid password for user "%s"' % (username))
            elif result is True:
                LOG.debug('Authentication for user "%s" successful' % (username))
            return bool(result)
        except ldap.LDAPError:
            LOG.debug('LDAP Error')

    def get_user(self, username):
        pass

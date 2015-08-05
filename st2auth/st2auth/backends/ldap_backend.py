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
    Backend which reads authentication information from a ldap server.
    The backend tries to bind the ldap user with given username and password.
    If the bind was successful, it tries to find the user in the given group.
    If the user is in the group, he will be authenticated.
    """

    def __init__(self, ldap_server, base_dn, group_dn, scope, use_tls, search_filter):
        """
        :param ldap_server: URL of the LDAP Server
        :type ldap_server: ``str``
        :param base_dn: Base DN on the LDAP Server
        :type base_dn: ``str``
        :param group_dn: Group DN on the LDAP Server which contains the user as member
        :type group_dn: ``str``
        :param scope: Scope search parameter. Can be base, onelevel or subtree (default: subtree)
        :type scope: ``str``
        :param use_tls: Boolean parameter to set if tls is required
        :type use_tls: ``bool``
        :param search_filter: Should contain the placeholder %(username)s for the username
        :type use_tls: ``str``
        """
        self._ldap_server = ldap_server
        self._base_dn = base_dn
        self._group_dn = group_dn
        if "base" in scope:
            self._scope = ldap.SCOPE_BASE
        elif "onelevel" in scope:
            self._scope = ldap.SCOPE_ONELEVEL
        else:
            self._scope = ldap.SCOPE_SUBTREE
        if use_tls != "True" or "ldaps" in ldap_server:
            self._use_tls = False
        else:
            self._use_tls = True
        self._search_filter = search_filter

    def authenticate(self, username, password):
        if self._search_filter:
            search_filter = self._search_filter % { "username": username }
        else:
            search_filter = "uniqueMember=uid=" + username + "," + self._base_dn
        try:
            ldap.set_option(ldap.OPT_X_TLS_REQUIRE_CERT, ldap.OPT_X_TLS_NEVER)
            connect = ldap.initialize(self._ldap_server)
            connect.set_option(ldap.OPT_PROTOCOL_VERSION, 3)
            if self._use_tls:
                connect.set_option(ldap.OPT_X_TLS,ldap.OPT_X_TLS_DEMAND)
                connect.start_tls_s()
                LOG.debug('using TLS')
            connect.simple_bind_s("uid=" + username + "," + self._base_dn, password)
            try:
                result = connect.search_s(self._group_dn, self._scope, search_filter)
                if result is None:
                    LOG.debug('User "%s" doesn\'t exist in group "%s"' % (username, self._group_dn))
                elif result:
                    LOG.debug('Authentication for user "%s" successful' % (username))
                    return True
                return False
            except:
                return False
            finally:
                connect.unbind()
        except ldap.LDAPError as e:
            LOG.debug('LDAP Error: %s' % (str(e)))
            return False

    def get_user(self, username):
        pass

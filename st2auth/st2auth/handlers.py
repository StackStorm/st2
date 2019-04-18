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

import base64

import six
from six.moves import http_client
from oslo_config import cfg

from st2common import log as logging
from st2common.exceptions.auth import TTLTooLargeException, UserNotFoundError
from st2common.exceptions.db import StackStormDBObjectNotFoundError
from st2common.exceptions.auth import NoNicknameOriginProvidedError, AmbiguousUserError
from st2common.exceptions.auth import NotServiceUserError
from st2common.persistence.auth import User
from st2common.router import abort
from st2common.services.access import create_token
from st2common.models.api.auth import TokenAPI
from st2common.models.db.auth import UserDB
from st2common.rbac.backends import get_rbac_backend
from st2auth.backends import get_backend_instance as get_auth_backend_instance

LOG = logging.getLogger(__name__)


def abort_request(status_code=http_client.UNAUTHORIZED, message='Invalid or missing credentials'):
    return abort(status_code, message)


class AuthHandlerBase(object):
    def handle_auth(self, request, headers=None, remote_addr=None,
                    remote_user=None, authorization=None, **kwargs):
        raise NotImplementedError()

    def _create_token_for_user(self, username, ttl=None):
        tokendb = create_token(username=username, ttl=ttl)
        return TokenAPI.from_model(tokendb)

    def _get_username_for_request(self, username, request):
        impersonate_user = getattr(request, 'user', None)

        if impersonate_user is not None:
            # check this is a service account
            try:
                if not User.get_by_name(username).is_service:
                    message = "Current user is not a service and cannot " \
                              "request impersonated tokens"
                    abort_request(status_code=http_client.BAD_REQUEST,
                                  message=message)
                    return
                username = impersonate_user
            except (UserNotFoundError, StackStormDBObjectNotFoundError):
                message = "Could not locate user %s" % \
                          (impersonate_user)
                abort_request(status_code=http_client.BAD_REQUEST,
                              message=message)
                return
        else:
            impersonate_user = getattr(request, 'impersonate_user', None)
            nickname_origin = getattr(request, 'nickname_origin', None)
            if impersonate_user is not None:
                try:
                    # check this is a service account
                    if not User.get_by_name(username).is_service:
                        raise NotServiceUserError()
                    username = User.get_by_nickname(impersonate_user,
                                                    nickname_origin).name
                except NotServiceUserError:
                    message = "Current user is not a service and cannot " \
                              "request impersonated tokens"
                    abort_request(status_code=http_client.BAD_REQUEST,
                                  message=message)
                    return
                except (UserNotFoundError, StackStormDBObjectNotFoundError):
                    message = "Could not locate user %s@%s" % \
                              (impersonate_user, nickname_origin)
                    abort_request(status_code=http_client.BAD_REQUEST,
                                  message=message)
                    return
                except NoNicknameOriginProvidedError:
                    message = "Nickname origin is not provided for nickname '%s'" % \
                              impersonate_user
                    abort_request(status_code=http_client.BAD_REQUEST,
                                  message=message)
                    return
                except AmbiguousUserError:
                    message = "%s@%s matched more than one username" % \
                              (impersonate_user, nickname_origin)
                    abort_request(status_code=http_client.BAD_REQUEST,
                                  message=message)
                    return
        return username


class ProxyAuthHandler(AuthHandlerBase):
    def handle_auth(self, request, headers=None, remote_addr=None,
                    remote_user=None, authorization=None, **kwargs):
        remote_addr = headers.get('x-forwarded-for',
                                  remote_addr)
        extra = {'remote_addr': remote_addr}

        if remote_user:
            ttl = getattr(request, 'ttl', None)
            username = self._get_username_for_request(remote_user, request)
            try:
                token = self._create_token_for_user(username=username,
                                                    ttl=ttl)
            except TTLTooLargeException as e:
                abort_request(status_code=http_client.BAD_REQUEST,
                              message=six.text_type(e))
            return token

        LOG.audit('Access denied to anonymous user.', extra=extra)
        abort_request()


class StandaloneAuthHandler(AuthHandlerBase):
    def __init__(self, *args, **kwargs):
        self._auth_backend = get_auth_backend_instance(name=cfg.CONF.auth.backend)
        super(StandaloneAuthHandler, self).__init__(*args, **kwargs)

    def handle_auth(self, request, headers=None, remote_addr=None, remote_user=None,
                    authorization=None, **kwargs):
        auth_backend = self._auth_backend.__class__.__name__

        extra = {'auth_backend': auth_backend, 'remote_addr': remote_addr}

        if not authorization:
            LOG.audit('Authorization header not provided', extra=extra)
            abort_request()
            return

        auth_type, auth_value = authorization
        if auth_type.lower() not in ['basic']:
            extra['auth_type'] = auth_type
            LOG.audit('Unsupported authorization type: %s' % (auth_type), extra=extra)
            abort_request()
            return

        try:
            auth_value = base64.b64decode(auth_value)
        except Exception:
            LOG.audit('Invalid authorization header', extra=extra)
            abort_request()
            return

        split = auth_value.split(b':', 1)
        if len(split) != 2:
            LOG.audit('Invalid authorization header', extra=extra)
            abort_request()
            return

        username, password = split

        if six.PY3 and isinstance(username, six.binary_type):
            username = username.decode('utf-8')

        if six.PY3 and isinstance(password, six.binary_type):
            password = password.decode('utf-8')

        result = self._auth_backend.authenticate(username=username, password=password)

        if result is True:
            ttl = getattr(request, 'ttl', None)
            username = self._get_username_for_request(username, request)
            try:
                token = self._create_token_for_user(username=username, ttl=ttl)
            except TTLTooLargeException as e:
                abort_request(status_code=http_client.BAD_REQUEST,
                              message=six.text_type(e))
                return

            # If remote group sync is enabled, sync the remote groups with local StackStorm roles
            if cfg.CONF.rbac.sync_remote_groups and cfg.CONF.rbac.backend != 'noop':
                LOG.debug('Retrieving auth backend groups for user "%s"' % (username),
                          extra=extra)
                try:
                    user_groups = self._auth_backend.get_user_groups(username=username)
                except (NotImplementedError, AttributeError):
                    LOG.debug('Configured auth backend doesn\'t expose user group membership '
                              'information, skipping sync...')
                    return token

                if not user_groups:
                    # No groups, return early
                    return token

                extra['username'] = username
                extra['user_groups'] = user_groups

                LOG.debug('Found "%s" groups for user "%s"' % (len(user_groups), username),
                          extra=extra)

                user_db = UserDB(name=username)

                rbac_backend = get_rbac_backend()
                syncer = rbac_backend.get_remote_group_to_role_syncer()

                try:
                    syncer.sync(user_db=user_db, groups=user_groups)
                except Exception as e:
                    # Note: Failed sync is not fatal
                    LOG.exception('Failed to synchronize remote groups for user "%s"' % (username),
                                  extra=extra)
                else:
                    LOG.debug('Successfully synchronized groups for user "%s"' % (username),
                              extra=extra)

                return token
            return token

        LOG.audit('Invalid credentials provided', extra=extra)
        abort_request()

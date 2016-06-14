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

import pecan
from pecan import rest
from six.moves import http_client
from oslo_config import cfg

from st2common.exceptions.auth import TokenNotFoundError, TokenExpiredError
from st2common.exceptions.auth import TTLTooLargeException
from st2common.models.api.base import jsexpose
from st2common.models.api.auth import TokenAPI
from st2common.services.access import create_token
from st2common.util import auth as auth_utils
from st2common import log as logging
from st2auth.backends import get_backend_instance


LOG = logging.getLogger(__name__)


class TokenValidationController(rest.RestController):

    @jsexpose(body_cls=TokenAPI, status_code=http_client.OK)
    def post(self, request, **kwargs):
        token = getattr(request, 'token', None)

        if not token:
            pecan.abort(http_client.BAD_REQUEST, 'Token is not provided.')

        try:
            return {'valid': auth_utils.validate_token(token) is not None}
        except (TokenNotFoundError, TokenExpiredError):
            return {'valid': False}
        except Exception:
            msg = 'Unexpected error occurred while verifying token.'
            LOG.exception(msg)
            pecan.abort(http_client.INTERNAL_SERVER_ERROR, msg)


class TokenController(rest.RestController):
    validate = TokenValidationController()

    def __init__(self, *args, **kwargs):
        super(TokenController, self).__init__(*args, **kwargs)

        if cfg.CONF.auth.mode == 'standalone':
            self._auth_backend = get_backend_instance(name=cfg.CONF.auth.backend)
        else:
            self._auth_backend = None

    @jsexpose(body_cls=TokenAPI, status_code=http_client.CREATED)
    def post(self, request, **kwargs):
        if cfg.CONF.auth.mode == 'proxy':
            return self._handle_proxy_auth(request=request, **kwargs)
        elif cfg.CONF.auth.mode == 'standalone':
            return self._handle_standalone_auth(request=request, **kwargs)

    def _handle_proxy_auth(self, request, **kwargs):
        remote_addr = pecan.request.headers.get('x-forwarded-for', pecan.request.remote_addr)
        extra = {'remote_addr': remote_addr}

        if pecan.request.remote_user:
            ttl = getattr(request, 'ttl', None)
            try:
                token = self._create_token_for_user(username=pecan.request.remote_user, ttl=ttl)
            except TTLTooLargeException as e:
                self._abort_request(status_code=http_client.BAD_REQUEST,
                                    message=e.message)
            return self._process_successful_response(token=token)

        LOG.audit('Access denied to anonymous user.', extra=extra)
        self._abort_request()

    def _handle_standalone_auth(self, request, **kwargs):
        authorization = pecan.request.authorization

        auth_backend = self._auth_backend.__class__.__name__
        remote_addr = pecan.request.remote_addr
        extra = {'auth_backend': auth_backend, 'remote_addr': remote_addr}

        if not authorization:
            LOG.audit('Authorization header not provided', extra=extra)
            self._abort_request()
            return

        auth_type, auth_value = authorization
        if auth_type.lower() not in ['basic']:
            extra['auth_type'] = auth_type
            LOG.audit('Unsupported authorization type: %s' % (auth_type), extra=extra)
            self._abort_request()
            return

        try:
            auth_value = base64.b64decode(auth_value)
        except Exception:
            LOG.audit('Invalid authorization header', extra=extra)
            self._abort_request()
            return

        split = auth_value.split(':')
        if len(split) != 2:
            LOG.audit('Invalid authorization header', extra=extra)
            self._abort_request()
            return

        username, password = split
        result = self._auth_backend

        result = self._auth_backend.authenticate(username=username, password=password)
        if result is True:
            ttl = getattr(request, 'ttl', None)
            try:
                token = self._create_token_for_user(username=username, ttl=ttl)
                return self._process_successful_response(token=token)
            except TTLTooLargeException as e:
                self._abort_request(status_code=http_client.BAD_REQUEST,
                                    message=e.message)
                return

        LOG.audit('Invalid credentials provided', extra=extra)
        self._abort_request()

    def _abort_request(self, status_code=http_client.UNAUTHORIZED,
                       message='Invalid or missing credentials'):
        pecan.abort(status_code, message)

    def _process_successful_response(self, token):
        api_url = cfg.CONF.auth.api_url
        pecan.response.headers['X-API-URL'] = api_url
        return token

    def _create_token_for_user(self, username, ttl=None):
        tokendb = create_token(username=username, ttl=ttl)
        return TokenAPI.from_model(tokendb)

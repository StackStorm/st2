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
from oslo.config import cfg

from st2common.models.base import jsexpose
from st2common.models.api.access import TokenAPI
from st2common.services.access import create_token
from st2common import log as logging
from st2auth.backends import get_backend_instance


LOG = logging.getLogger(__name__)


class TokenController(rest.RestController):
    def __init__(self, *args, **kwargs):
        super(TokenController, self).__init__(*args, **kwargs)

        if cfg.CONF.auth.mode == 'standalone':
            self._auth_backend = get_backend_instance(name=cfg.CONF.auth.backend)
        else:
            self._auth_backend = None

    @jsexpose(body=TokenAPI, status_code=http_client.CREATED)
    def post(self, request, **kwargs):
        if cfg.CONF.auth.mode == 'proxy':
            return self._handle_proxy_auth(request=request, **kwargs)
        elif cfg.CONF.auth.mode == 'standalone':
            return self._handle_standalone_auth(request=request, **kwargs)

    def _handle_proxy_auth(self, request, **kwargs):
        if not pecan.request.remote_user:
            LOG.audit('Access denied to anonymous user.')
            pecan.abort(http_client.UNAUTHORIZED)
            return

        ttl = getattr(request, 'ttl', None)
        token = self._create_token_for_user(username=pecan.request.remote_user, ttl=ttl)
        return token

    def _handle_standalone_auth(self, request, **kwargs):
        authorization = pecan.request.authorization

        if not authorization:
            LOG.audit('Authorization header not provided')
            pecan.abort(http_client.UNAUTHORIZED)
            return

        auth_type, auth_value = authorization
        if auth_type.lower() not in ['basic']:
            LOG.audit('Unsupported authorization type: %s' % (auth_type))
            pecan.abort(http_client.UNAUTHORIZED)
            return

        try:
            auth_value = base64.b64decode(auth_value)
        except Exception:
            LOG.audit('Invalid authorization header')
            pecan.abort(http_client.UNAUTHORIZED)
            return

        split = auth_value.split(':')
        if len(split) != 2:
            LOG.audit('Invalid authorization header')
            pecan.abort(http_client.UNAUTHORIZED)
            return

        username, password = split
        result = self._auth_backend

        result = self._auth_backend.authenticate(username=username, password=password)
        if result is True:
            ttl = getattr(request, 'ttl', None)
            token = self._create_token_for_user(username=username, ttl=ttl)
            return token

        LOG.audit('Invalid credentials provided')
        pecan.abort(http_client.UNAUTHORIZED)

    def _create_token_for_user(self, username, ttl=None):
        tokendb = create_token(username=username, ttl=ttl)
        return TokenAPI.from_model(tokendb)

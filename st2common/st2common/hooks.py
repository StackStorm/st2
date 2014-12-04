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

import datetime
from oslo.config import cfg
from pecan.hooks import PecanHook
import webob

from st2common import log as logging
from st2common.exceptions import access as exceptions
from st2common.persistence.access import Token
from st2common.util import isotime
from st2common.util.jsonify import json_encode


LOG = logging.getLogger(__name__)


class CorsHook(PecanHook):

    def after(self, state):
        headers = state.response.headers

        origin = state.request.headers.get('Origin')
        origins = cfg.CONF.api.allow_origin
        if origin:
            if '*' in origins:
                origin_allowed = '*'
            else:
                # See http://www.w3.org/TR/cors/#access-control-allow-origin-response-header
                origin_allowed = origin if origin in origins else 'null'
        else:
            origin_allowed = origins[0] if len(origins) > 0 else 'http://localhost:3000'

        methods_allowed = ['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS']
        request_headers_allowed = ['Content-Type', 'Authorization', 'X-Auth-Token']
        response_headers_allowed = ['Content-Type', 'X-Limit', 'X-Total-Count']

        headers['Access-Control-Allow-Origin'] = origin_allowed
        headers['Access-Control-Allow-Methods'] = ','.join(methods_allowed)
        headers['Access-Control-Allow-Headers'] = ','.join(request_headers_allowed)
        headers['Access-Control-Expose-Headers'] = ','.join(response_headers_allowed)
        if not headers['Content-Length']:
            headers['Content-Length'] = str(len(state.response.body))

    def on_error(self, state, e):
        if state.request.method == 'OPTIONS':
            return webob.Response()


class AuthHook(PecanHook):

    def before(self, state):
        # OPTIONS requests doesn't need to be authenticated
        if state.request.method == 'OPTIONS':
            return

        state.request.context['token'] = self._validate_token(state.request.headers)

    def on_error(self, state, e):
        if isinstance(e, exceptions.TokenNotProvidedError):
            LOG.exception('Token is not provided.')
            return self._abort_unauthorized()
        if isinstance(e, exceptions.TokenNotFoundError):
            LOG.exception('Token is not found.')
            return self._abort_unauthorized()
        if isinstance(e, exceptions.TokenExpiredError):
            LOG.exception('Token has expired.')
            return self._abort_unauthorized()

    @staticmethod
    def _abort_unauthorized():
        return webob.Response(json_encode({
            'faultstring': 'Unauthorized'
        }), status=401)

    @staticmethod
    def _abort_other_errors():
        return webob.Response(json_encode({
            'faultstring': 'Internal Server Error'
        }), status=500)

    @staticmethod
    def _validate_token(headers):
        """Validate token"""
        if 'X_Auth_Token' not in headers:
            LOG.audit('Token is not found in header.')
            raise exceptions.TokenNotProvidedError('Token is not provided.')

        token = Token.get(headers['X_Auth_Token'])

        if token.expiry <= isotime.add_utc_tz(datetime.datetime.utcnow()):
            LOG.audit('Token "%s" has expired.' % headers['X_Auth_Token'])
            raise exceptions.TokenExpiredError('Token has expired.')

        LOG.audit('Token "%s" is validated.' % headers['X_Auth_Token'])

        return token

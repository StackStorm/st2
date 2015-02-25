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


import webob
from oslo.config import cfg
from pecan.hooks import PecanHook
from six.moves.urllib import parse as urlparse

from st2common import log as logging
from st2common.exceptions import access as exceptions
from st2common.util.jsonify import json_encode
from st2common.util.auth import validate_token
from st2common.util.api import get_full_api_url
from st2common.constants.auth import HEADER_ATTRIBUTE_NAME
from st2common.constants.auth import QUERY_PARAM_ATTRIBUTE_NAME


LOG = logging.getLogger(__name__)


class CorsHook(PecanHook):

    def after(self, state):
        headers = state.response.headers

        origin = state.request.headers.get('Origin')
        origins = cfg.CONF.api.allow_origin

        # Build a list of the default allowed origins
        api_port = cfg.CONF.api.port
        public_api_url = cfg.CONF.auth.api_url
        default_allowed_origins = []

        # Default WebUI URL
        default_allowed_origins.append('http://localhost:3000')

        # Local API URL
        default_allowed_origins.append('http://localhost:%s' % (api_port))
        default_allowed_origins.append('http://127.0.0.1:%s' % (api_port))

        if public_api_url:
            # Public API URL
            default_allowed_origins.append(public_api_url)

        if origin:
            if '*' in origins:
                origin_allowed = '*'
            else:
                # See http://www.w3.org/TR/cors/#access-control-allow-origin-response-header
                if origin in default_allowed_origins:
                    # Allow requests originating from the API server
                    origin_allowed = origin
                else:
                    origin_allowed = origin if origin in origins else 'null'
        else:
            default_allowed_origins = ','.join(default_allowed_origins)
            origin_allowed = origins[0] if len(origins) > 0 else default_allowed_origins

        methods_allowed = ['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS']
        request_headers_allowed = ['Content-Type', 'Authorization', 'X-Auth-Token']
        response_headers_allowed = ['Content-Type', 'X-Limit', 'X-Total-Count']

        headers['Access-Control-Allow-Origin'] = origin_allowed
        headers['Access-Control-Allow-Methods'] = ','.join(methods_allowed)
        headers['Access-Control-Allow-Headers'] = ','.join(request_headers_allowed)
        headers['Access-Control-Expose-Headers'] = ','.join(response_headers_allowed)
        if not headers.get('Content-Length') \
                and not headers.get('Content-type', '').startswith('text/event-stream'):
            headers['Content-Length'] = str(len(state.response.body))

    def on_error(self, state, e):
        if state.request.method == 'OPTIONS':
            return webob.Response()


class AuthHook(PecanHook):

    def before(self, state):
        # OPTIONS requests doesn't need to be authenticated
        if state.request.method == 'OPTIONS':
            return

        state.request.context['token'] = self._validate_token(request=state.request)

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
    def _validate_token(request):
        """
        Validate token provided either in headers or query parameters.
        """
        headers = request.headers
        query_string = request.query_string
        query_params = dict(urlparse.parse_qsl(query_string))

        token_in_headers = headers.get(HEADER_ATTRIBUTE_NAME, None)
        token_in_query_params = query_params.get(QUERY_PARAM_ATTRIBUTE_NAME, None)
        return validate_token(token_in_headers=token_in_headers,
                              token_in_query_params=token_in_query_params)

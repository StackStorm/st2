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

import httplib
import traceback

import webob
from oslo_config import cfg
from pecan.hooks import PecanHook
from six.moves.urllib import parse as urlparse
from webob import exc

from st2common import log as logging
from st2common.persistence.auth import User
from st2common.exceptions import auth as exceptions
from st2common.exceptions import db as db_exceptions
from st2common.util.jsonify import json_encode
from st2common.util.auth import validate_token
from st2common.constants.auth import HEADER_ATTRIBUTE_NAME
from st2common.constants.auth import QUERY_PARAM_ATTRIBUTE_NAME


LOG = logging.getLogger(__name__)

# A list of method names for which we don't want to log the result / response
RESPONSE_LOGGING_METHOD_NAME_BLACKLIST = [
    'get_all'
]

# A list of controller classes for which we don't want to log the result / response
RESPONSE_LOGGING_CONTROLLER_NAME_BLACKLIST = [
    'ActionExecutionChildrenController',  # action executions can be big
    'ActionExecutionAttributeController',  # result can be big
    'ActionExecutionsController'  # action executions can be big
]


class CorsHook(PecanHook):

    def after(self, state):
        headers = state.response.headers

        origin = state.request.headers.get('Origin')
        origins = set(cfg.CONF.api.allow_origin)

        # Build a list of the default allowed origins
        public_api_url = cfg.CONF.auth.api_url

        # Default gulp development server WebUI URL
        origins.add('http://localhost:3000')

        # By default WebUI simple http server listens on 8080
        origins.add('http://localhost:8080')
        origins.add('http://127.0.0.1:8080')

        if public_api_url:
            # Public API URL
            origins.add(public_api_url)

        if origin:
            if '*' in origins:
                origin_allowed = '*'
            else:
                # See http://www.w3.org/TR/cors/#access-control-allow-origin-response-header
                origin_allowed = origin if origin in origins else 'null'
        else:
            origin_allowed = list(origins)[0]

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

        token_db = self._validate_token(request=state.request)

        try:
            user_db = User.get(token_db.user)
        except ValueError:
            # User doesn't exist - we should probably also invalidate token if
            # this happens
            user_db = None

        # Store token and related user object in the context
        # Note: We also store token outside of auth dict for backward compatibility
        state.request.context['token'] = token_db
        state.request.context['auth'] = {
            'token': token_db,
            'user': user_db
        }

        if QUERY_PARAM_ATTRIBUTE_NAME in state.arguments.keywords:
            del state.arguments.keywords[QUERY_PARAM_ATTRIBUTE_NAME]

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


class JSONErrorResponseHook(PecanHook):
    """
    Handle all the errors and respond with JSON.
    """

    def on_error(self, state, e):
        error_msg = getattr(e, 'comment', str(e))
        LOG.debug('API call failed: %s', error_msg)
        LOG.debug(traceback.format_exc())

        if hasattr(e, 'body') and isinstance(e.body, dict):
            body = e.body
        else:
            body = {}

        if isinstance(e, exc.HTTPException):
            status_code = state.response.status
            message = str(e)
        elif isinstance(e, db_exceptions.StackStormDBObjectNotFoundError):
            status_code = httplib.NOT_FOUND
            message = str(e)
        elif isinstance(e, ValueError):
            status_code = httplib.BAD_REQUEST
            message = getattr(e, 'message', str(e))
        else:
            status_code = httplib.INTERNAL_SERVER_ERROR
            message = 'Internal Server Error'

        body['faultstring'] = message

        response_body = json_encode(body)

        headers = state.response.headers or {}

        headers['Content-Type'] = 'application/json'
        headers['Content-Length'] = str(len(response_body))

        return webob.Response(response_body, status=status_code, headers=headers)


class LoggingHook(PecanHook):
    """
    Logs all incoming requests and outgoing responses
    """

    def before(self, state):
        # Note: We use getattr since in some places (tests) request is mocked
        method = getattr(state.request, 'method', None)
        path = getattr(state.request, 'path', None)
        remote_addr = getattr(state.request, 'remote_addr', None)

        # Log the incoming request
        values = {'method': method, 'path': path, 'remote_addr': remote_addr}
        values['filters'] = state.arguments.keywords
        LOG.info('%(method)s %(path)s with filters=%(filters)s' % values, extra=values)

    def after(self, state):
        # Note: We use getattr since in some places (tests) request is mocked
        method = getattr(state.request, 'method', None)
        path = getattr(state.request, 'path', None)
        remote_addr = getattr(state.request, 'remote_addr', None)

        # Log the outgoing response
        values = {'method': method, 'path': path, 'remote_addr': remote_addr}
        values['status_code'] = state.response.status

        if hasattr(state.controller, 'im_self'):
            function_name = state.controller.im_func.__name__
            controller_name = state.controller.im_class.__name__

            log_result = True
            log_result &= function_name not in RESPONSE_LOGGING_METHOD_NAME_BLACKLIST
            log_result &= controller_name not in RESPONSE_LOGGING_CONTROLLER_NAME_BLACKLIST
        else:
            log_result = False

        if log_result:
            values['result'] = state.response.body
            log_msg = '%(method)s %(path)s result=%(result)s' % values
        else:
            # Note: We don't want to include a result for some
            # methods which have a large result
            log_msg = '%(method)s %(path)s' % values

        LOG.info(log_msg, extra=values)

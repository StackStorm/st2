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
import re
import traceback
import uuid

import webob
from oslo_config import cfg
from pecan.hooks import PecanHook
from six.moves.urllib import parse as urlparse
from webob import exc

from st2common import log as logging
from st2common.persistence.auth import User
from st2common.exceptions import db as db_exceptions
from st2common.exceptions import auth as auth_exceptions
from st2common.exceptions import rbac as rbac_exceptions
from st2common.exceptions.db import StackStormDBObjectNotFoundError
from st2common.exceptions.apivalidation import ValueValidationException
from st2common.util import auth as auth_utils
from st2common.util.jsonify import json_encode
from st2common.util.debugging import is_enabled as is_debugging_enabled
from st2common.constants.api import REQUEST_ID_HEADER
from st2common.constants.auth import HEADER_ATTRIBUTE_NAME
from st2common.constants.auth import QUERY_PARAM_ATTRIBUTE_NAME
from st2common.constants.auth import HEADER_API_KEY_ATTRIBUTE_NAME
from st2common.constants.auth import QUERY_PARAM_API_KEY_ATTRIBUTE_NAME


LOG = logging.getLogger(__name__)

# A list of method names for which we don't want to log the result / response
RESPONSE_LOGGING_METHOD_NAME_BLACKLIST = [
    'get_all'
]

# A list of controller classes for which we don't want to log the result / response
RESPONSE_LOGGING_CONTROLLER_NAME_BLACKLIST = [
    'ActionExecutionChildrenController',  # action executions can be big
    'ActionExecutionAttributeController',  # result can be big
    'ActionExecutionsController'  # action executions can be big,
    'FilesController',  # files controller returns files content
    'FileController'  # file controller returns binary file data
]

# Regex for the st2 auth tokens endpoint (i.e. /tokens or /v1/tokens).
AUTH_TOKENS_URL_REGEX = '^(?:/tokens|/v\d+/tokens)$'


class CorsHook(PecanHook):

    def after(self, state):
        headers = state.response.headers

        origin = state.request.headers.get('Origin')
        origins = set(cfg.CONF.api.allow_origin)

        # Build a list of the default allowed origins
        public_api_url = cfg.CONF.auth.api_url

        # Default gulp development server WebUI URL
        origins.add('http://127.0.0.1:3000')

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
        request_headers_allowed = ['Content-Type', 'Authorization', 'X-Auth-Token',
                                   HEADER_API_KEY_ATTRIBUTE_NAME, REQUEST_ID_HEADER]
        response_headers_allowed = ['Content-Type', 'X-Limit', 'X-Total-Count',
                                    REQUEST_ID_HEADER]

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

        # Token request is authenticated separately.
        if (state.request.method == 'POST' and
                re.search(AUTH_TOKENS_URL_REGEX, state.request.path)):
            return

        user_db = self._validate_creds_and_get_user(request=state.request)

        # Store related user object in the context. The token is not passed
        # along any longer as that should only be used in the auth domain.
        state.request.context['auth'] = {
            'user': user_db
        }

        if QUERY_PARAM_ATTRIBUTE_NAME in state.arguments.keywords:
            del state.arguments.keywords[QUERY_PARAM_ATTRIBUTE_NAME]

        if QUERY_PARAM_API_KEY_ATTRIBUTE_NAME in state.arguments.keywords:
            del state.arguments.keywords[QUERY_PARAM_API_KEY_ATTRIBUTE_NAME]

    def on_error(self, state, e):
        if isinstance(e, (auth_exceptions.NoAuthSourceProvidedError,
                          auth_exceptions.MultipleAuthSourcesError)):
            LOG.error(str(e))
            return self._abort_unauthorized(str(e))
        if isinstance(e, auth_exceptions.TokenNotProvidedError):
            LOG.exception('Token is not provided.')
            return self._abort_unauthorized(str(e))
        if isinstance(e, auth_exceptions.TokenNotFoundError):
            LOG.exception('Token is not found.')
            return self._abort_unauthorized(str(e))
        if isinstance(e, auth_exceptions.TokenExpiredError):
            LOG.exception('Token has expired.')
            return self._abort_unauthorized(str(e))
        if isinstance(e, auth_exceptions.ApiKeyNotProvidedError):
            LOG.exception('API key is not provided.')
            return self._abort_unauthorized(str(e))
        if isinstance(e, auth_exceptions.ApiKeyNotFoundError):
            LOG.exception('API key is not found.')
            return self._abort_unauthorized(str(e))
        if isinstance(e, auth_exceptions.ApiKeyDisabledError):
            LOG.exception('API key is disabled.')
            return self._abort_unauthorized(str(e))

    @staticmethod
    def _abort_unauthorized(msg):
        faultstring = 'Unauthorized - %s' % msg if msg else 'Unauthorized'
        body = json_encode({
            'faultstring': faultstring
        })
        headers = {}
        headers['Content-Type'] = 'application/json'
        status = httplib.UNAUTHORIZED

        return webob.Response(body=body, status=status, headers=headers)

    @staticmethod
    def _abort_other_errors():
        body = json_encode({
            'faultstring': 'Internal Server Error'
        })
        headers = {}
        headers['Content-Type'] = 'application/json'
        status = httplib.INTERNAL_SERVER_ERROR

        return webob.Response(body=body, status=status, headers=headers)

    @staticmethod
    def _validate_creds_and_get_user(request):
        """
        Validate one of token or api_key provided either in headers or query parameters.
        Will returnt the User

        :rtype: :class:`UserDB`
        """

        headers = request.headers
        query_string = request.query_string
        query_params = dict(urlparse.parse_qsl(query_string))

        token_in_headers = headers.get(HEADER_ATTRIBUTE_NAME, None)
        token_in_query_params = query_params.get(QUERY_PARAM_ATTRIBUTE_NAME, None)

        api_key_in_headers = headers.get(HEADER_API_KEY_ATTRIBUTE_NAME, None)
        api_key_in_query_params = query_params.get(QUERY_PARAM_API_KEY_ATTRIBUTE_NAME, None)

        if ((token_in_headers or token_in_query_params) and
                (api_key_in_headers or api_key_in_query_params)):
            raise auth_exceptions.MultipleAuthSourcesError(
                'Only one of Token or API key expected.')

        user = None

        if token_in_headers or token_in_query_params:
            token_db = auth_utils.validate_token_and_source(
                token_in_headers=token_in_headers,
                token_in_query_params=token_in_query_params)
            user = token_db.user
        elif api_key_in_headers or api_key_in_query_params:
            api_key_db = auth_utils.validate_api_key_and_source(
                api_key_in_headers=api_key_in_headers,
                api_key_query_params=api_key_in_query_params)
            user = api_key_db.user
        else:
            raise auth_exceptions.NoAuthSourceProvidedError('One of Token or API key required.')

        if not user:
            LOG.warn('User not found for supplied token or api-key.')
            return None

        try:
            return User.get(user)
        except StackStormDBObjectNotFoundError:
            # User doesn't exist - we should probably also invalidate token/apikey if
            # this happens.
            LOG.warn('User %s not found.', user)
            return None


class JSONErrorResponseHook(PecanHook):
    """
    Handle all the errors and respond with JSON.
    """

    def on_error(self, state, e):
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
        elif isinstance(e, db_exceptions.StackStormDBObjectConflictError):
            status_code = httplib.CONFLICT
            message = str(e)
            body['conflict-id'] = e.conflict_id
        elif isinstance(e, rbac_exceptions.AccessDeniedError):
            status_code = httplib.FORBIDDEN
            message = str(e)
        elif isinstance(e, (ValueValidationException, ValueError)):
            status_code = httplib.BAD_REQUEST
            message = getattr(e, 'message', str(e))
        else:
            status_code = httplib.INTERNAL_SERVER_ERROR
            message = 'Internal Server Error'

        # Log the error
        is_internal_server_error = status_code == httplib.INTERNAL_SERVER_ERROR
        error_msg = getattr(e, 'comment', str(e))
        extra = {
            'exception_class': e.__class__.__name__,
            'exception_message': str(e),
            'exception_data': e.__dict__
        }

        if is_internal_server_error:
            LOG.exception('API call failed: %s', error_msg, extra=extra)
            LOG.exception(traceback.format_exc())
        else:
            LOG.debug('API call failed: %s', error_msg, extra=extra)

            if is_debugging_enabled():
                LOG.debug(traceback.format_exc())

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

        request_id = state.request.headers.get(REQUEST_ID_HEADER, None)
        values['request_id'] = request_id

        LOG.info('%(request_id)s -  %(method)s %(path)s with filters=%(filters)s' %
                 values, extra=values)

    def after(self, state):
        # Note: We use getattr since in some places (tests) request is mocked
        method = getattr(state.request, 'method', None)
        path = getattr(state.request, 'path', None)
        remote_addr = getattr(state.request, 'remote_addr', None)
        request_id = state.request.headers.get(REQUEST_ID_HEADER, None)

        # Log the outgoing response
        values = {'method': method, 'path': path, 'remote_addr': remote_addr}
        values['status_code'] = state.response.status
        values['request_id'] = request_id

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
            log_msg = '%(request_id)s - %(method)s %(path)s result=%(result)s' % values
        else:
            # Note: We don't want to include a result for some
            # methods which have a large result
            log_msg = '%(request_id)s - %(method)s %(path)s' % values

        LOG.info(log_msg, extra=values)


class RequestIDHook(PecanHook):
    """
    If request id header isn't present, this hooks adds one.
    """

    def before(self, state):
        headers = getattr(state.request, 'headers', None)

        if headers:
            req_id_header = getattr(headers, REQUEST_ID_HEADER, None)

            if not req_id_header:
                req_id = str(uuid.uuid4())
                state.request.headers[REQUEST_ID_HEADER] = req_id

    def after(self, state):
        req_headers = getattr(state.request, 'headers', None)
        resp_headers = getattr(state.response, 'headers', None)

        if req_headers and resp_headers:
            req_id_header = req_headers.get(REQUEST_ID_HEADER, None)
            if req_id_header:
                resp_headers[REQUEST_ID_HEADER] = req_id_header

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

from six.moves.urllib import parse as urlparse

from st2common.util import isotime
from st2common.exceptions import auth as exceptions
from st2common import log as logging
from st2common.util.auth import validate_token
from st2common.constants.auth import QUERY_PARAM_ATTRIBUTE_NAME


LOG = logging.getLogger(__name__)

# HTTP header name format (i.e. 'X-Auth-Token')
# WSGI environment variable name format (ex. 'HTTP_X_AUTH_TOKEN')
HEADERS = ['HTTP_X_AUTH_TOKEN_EXPIRY', 'HTTP_X_USER_NAME']


class AuthMiddleware(object):
    """WSGI middleware to handle authentication"""

    def __init__(self, app):
        self.app = app

    def __call__(self, environ, start_response):
        try:
            self._remove_auth_headers(environ)
            token = self._validate_token(environ)
            self._add_auth_headers(environ, token)
        except exceptions.TokenNotProvidedError:
            LOG.exception('Token is not provided.')
            return self._abort_unauthorized(environ, start_response)
        except exceptions.TokenNotFoundError:
            LOG.exception('Token is not found.')
            return self._abort_unauthorized(environ, start_response)
        except exceptions.TokenExpiredError:
            LOG.exception('Token has expired.')
            return self._abort_unauthorized(environ, start_response)
        except Exception:
            LOG.exception('Unexpected exception.')
            return self._abort_other_errors(environ, start_response)
        else:
            return self.app(environ, start_response)

    def _abort_other_errors(self, environ, start_response):
        start_response('500 INTERNAL SERVER ERROR', [('Content-Type', 'text/plain')])
        return ['Internal Server Error']

    def _abort_unauthorized(self, environ, start_response):
        start_response('401 UNAUTHORIZED', [('Content-Type', 'text/plain')])
        return ['Unauthorized']

    def _remove_auth_headers(self, env):
        """Remove middleware generated auth headers to prevent user from supplying them."""
        headers_found = [k for k in HEADERS if k in env]
        for header in headers_found:
            del env[header]

    def _validate_token(self, env):
        """Validate token"""
        query_string = env.get('QUERY_STRING', '')
        query_params = dict(urlparse.parse_qsl(query_string))

        # Note: This is a WSGI environment variable name
        token_in_headers = env.get('HTTP_X_AUTH_TOKEN', None)
        token_in_query_params = query_params.get(QUERY_PARAM_ATTRIBUTE_NAME, None)

        return validate_token(token_in_headers=token_in_headers,
                              token_in_query_params=token_in_query_params)

    def _add_auth_headers(self, env, token):
        """Write authenticated user data to headers

        Build headers that represent authenticated user:
         * HTTP_X_AUTH_TOKEN_EXPIRY: Token expiration datetime
         * HTTP_X_USER_NAME: Name of confirmed user

        """
        env['HTTP_X_AUTH_TOKEN_EXPIRY'] = isotime.format(token.expiry)
        env['HTTP_X_USER_NAME'] = str(token.user)

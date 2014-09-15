import datetime

from st2common.persistence.access import Token
from st2common.exceptions import access as exceptions

from st2common import log as logging


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
        if 'HTTP_X_AUTH_TOKEN' not in env:
            LOG.audit('Token is not found in header.')
            raise exceptions.TokenNotProvidedError('Token is not provided.')
        token = Token.get(env['HTTP_X_AUTH_TOKEN'])
        if token.expiry <= datetime.datetime.now():
            LOG.audit('Token "%s" has expired.' % env['HTTP_X_AUTH_TOKEN'])
            raise exceptions.TokenExpiredError('Token has expired.')
        LOG.audit('Token "%s" is validated.' % env['HTTP_X_AUTH_TOKEN'])
        return token

    def _add_auth_headers(self, env, token):
        """Write authenticated user data to headers

        Build headers that represent authenticated user:
         * HTTP_X_AUTH_TOKEN_EXPIRY: Token expiration datetime
         * HTTP_X_USER_NAME: Name of confirmed user

        """
        env['HTTP_X_AUTH_TOKEN_EXPIRY'] = str(token.expiry)
        env['HTTP_X_USER_NAME'] = str(token.user)

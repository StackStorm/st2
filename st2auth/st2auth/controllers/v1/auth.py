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


import pecan
from pecan import rest
from six.moves import http_client
from oslo_config import cfg

from st2common.exceptions.auth import TokenNotFoundError, TokenExpiredError
from st2common.exceptions.param import ParamException
from st2common.models.api.base import jsexpose


from st2common.util import auth as auth_utils
from st2common import log as logging
from st2common.models.api.auth import TokenAPI
import st2auth.handlers as handlers


HANDLER_MAPPINGS = {
    'proxy': handlers.ProxyAuthHandler,
    'standalone': handlers.StandaloneAuthHandler
}

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

        try:
            self.handler = HANDLER_MAPPINGS[cfg.CONF.auth.mode]()
        except KeyError:
            raise ParamException("%s is not a valid auth mode" %
                                 cfg.CONF.auth.mode)

    @jsexpose(body_cls=TokenAPI, status_code=http_client.CREATED)
    def post(self, request, **kwargs):
        token = self.handler.handle_auth(request=request, headers=pecan.request.headers,
                                         remote_addr=pecan.request.remote_addr,
                                         remote_user=pecan.request.remote_user,
                                         authorization=pecan.request.authorization,
                                         **kwargs)
        return process_successful_response(token=token)


def process_successful_response(token):
    api_url = cfg.CONF.auth.api_url
    pecan.response.headers['X-API-URL'] = api_url
    return token

# Copyright 2020 The StackStorm Authors.
# Copyright 2019 Extreme Networks, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


from six.moves import http_client
from oslo_config import cfg


from st2common.exceptions.auth import TokenNotFoundError, TokenExpiredError
from st2common.exceptions.param import ParamException
from st2common.router import exc
from st2common.router import Response
from st2common.util import auth as auth_utils
from st2common.util import api as api_utils
from st2common import log as logging
import st2auth.handlers as handlers


HANDLER_MAPPINGS = {
    "proxy": handlers.ProxyAuthHandler,
    "standalone": handlers.StandaloneAuthHandler,
}

LOG = logging.getLogger(__name__)


class TokenValidationController(object):
    def post(self, request):
        token = getattr(request, "token", None)

        if not token:
            raise exc.HTTPBadRequest("Token is not provided.")

        try:
            return {"valid": auth_utils.validate_token(token) is not None}
        except (TokenNotFoundError, TokenExpiredError):
            return {"valid": False}
        except Exception:
            msg = "Unexpected error occurred while verifying token."
            LOG.exception(msg)
            raise exc.HTTPInternalServerError(msg)


class TokenController(object):
    validate = TokenValidationController()

    def __init__(self):
        try:
            self.handler = HANDLER_MAPPINGS[cfg.CONF.auth.mode]()
        except KeyError:
            raise ParamException("%s is not a valid auth mode" % cfg.CONF.auth.mode)

    def post(self, request, **kwargs):
        headers = {}
        if "x-forwarded-for" in kwargs:
            headers["x-forwarded-for"] = kwargs.pop("x-forwarded-for")

        remote_user = kwargs.pop("remote_user", None)
        if not remote_user and "x-forwarded-user" in kwargs:
            remote_user = kwargs.pop("x-forwarded-user", None)

        authorization = kwargs.pop("authorization", None)
        if authorization:
            authorization = tuple(authorization.split(" "))

        token = self.handler.handle_auth(
            request=request,
            headers=headers,
            remote_addr=kwargs.pop("remote_addr", None),
            remote_user=remote_user,
            authorization=authorization,
            **kwargs,
        )
        return process_successful_response(token=token)


def process_successful_response(token):
    resp = Response(json=token, status=http_client.CREATED)
    # NOTE: gunicon fails and throws an error if header value is not a string (e.g. if it's None)
    resp.headers["X-API-URL"] = api_utils.get_base_public_api_url()
    return resp


token_controller = TokenController()
token_validation_controller = TokenValidationController()

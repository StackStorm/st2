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

import datetime
import json
import six

if six.PY2:
    from urllib import quote
else:
    from urllib.parse import quote

from six.moves import http_client

import st2auth.handlers as handlers

from st2auth import sso as st2auth_sso
from st2common.exceptions import auth as auth_exc
from st2common import log as logging
from st2common import router


LOG = logging.getLogger(__name__)
SSO_BACKEND = st2auth_sso.get_sso_backend()


class IdentityProviderCallbackController(object):

    def __init__(self):
        self.st2_auth_handler = handlers.ProxyAuthHandler()

    def post(self, response, **kwargs):
        try:
            verified_user = SSO_BACKEND.verify_response(response)

            st2_auth_token_create_request = {'user': verified_user['username'], 'ttl': None}

            st2_auth_token = self.st2_auth_handler.handle_auth(
                request=st2_auth_token_create_request,
                remote_addr=verified_user['referer'],
                remote_user=verified_user['username'],
                headers={}
            )

            return process_successful_response(verified_user['referer'], st2_auth_token)
        except NotImplementedError as e:
            return process_failure_response(http_client.INTERNAL_SERVER_ERROR, e)
        except auth_exc.SSOVerificationError as e:
            return process_failure_response(http_client.UNAUTHORIZED, e)
        except Exception as e:
            raise e


class SingleSignOnController(object):
    callback = IdentityProviderCallbackController()

    def get(self, referer):
        try:
            response = router.Response(status=http_client.TEMPORARY_REDIRECT)
            response.location = SSO_BACKEND.get_request_redirect_url(referer)
            return response
        except NotImplementedError as e:
            return process_failure_response(http_client.INTERNAL_SERVER_ERROR, e)
        except Exception as e:
            raise e


CALLBACK_SUCCESS_RESPONSE_BODY = """
<html>
    <script>
        function getCookie(name) {
            var v = document.cookie.match('(^|;) ?' + name + '=([^;]*)(;|$)');
            return v ? v[2] : null;
        }

        data = JSON.parse(window.localStorage.getItem('st2Session'));
        data['token'] = JSON.parse(decodeURIComponent(getCookie('st2-auth-token')));
        window.localStorage.setItem('st2Session', JSON.stringify(data));
        window.location.replace("%s");
    </script>
    <body/>
</html>
"""


def process_successful_response(referer, token):
    token_json = {
        'id': str(token.id),
        'user': token.user,
        'token': token.token,
        'expiry': str(token.expiry),
        'service': False,
        'metadata': {}
    }

    body = CALLBACK_SUCCESS_RESPONSE_BODY % referer
    resp = router.Response(body=body)
    resp.headers['Content-Type'] = 'text/html'

    resp.set_cookie(
        'st2-auth-token',
        value=quote(json.dumps(token_json)),
        expires=datetime.timedelta(seconds=60),
        overwrite=True
    )

    return resp


def process_failure_response(status_code, exception):
    LOG.error(str(exception))
    json_body = {'faultstring': str(exception)}
    return router.Response(status_code=status_code, json_body=json_body)


sso_controller = SingleSignOnController()
idp_callback_controller = IdentityProviderCallbackController()

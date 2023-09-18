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
from uuid import uuid4

from oslo_config import cfg
from six.moves import http_client
from six.moves import urllib
from st2common.router import GenericRequestParam

import st2auth.handlers as handlers

from st2auth import sso as st2auth_sso
from st2auth.sso.base import BaseSingleSignOnBackendResponse
from st2common.exceptions import auth as auth_exc
from st2common import log as logging
from st2common import router
from st2common.models.db.auth import SSORequestDB
from st2common.services.access import (
    create_cli_sso_request,
    create_web_sso_request,
    get_sso_request_by_request_id,
)
from st2common.exceptions.auth import SSORequestNotFoundError
from st2common.util.crypto import read_crypto_key_from_dict, symmetric_encrypt
from st2common.util.date import get_datetime_utc_now
from st2common.util.jsonify import json_decode

LOG = logging.getLogger(__name__)
SSO_BACKEND = st2auth_sso.get_sso_backend()


class IdentityProviderCallbackController(object):
    def __init__(self):
        self.st2_auth_handler = handlers.ProxyAuthHandler()

    # Validates the incoming SSO response by getting its ID, checking against
    # the database for outstanding SSO requests and checking to see if they have already expired
    def _validate_and_delete_sso_request(self, response):

        # Grabs the ID from the SSO response based on the backend
        request_id = SSO_BACKEND.get_request_id_from_response(response)
        if request_id is None:
            raise ValueError("Invalid request id coming from SAML response")

        LOG.debug("Validating SSO request %s from received response!", request_id)

        # Grabs the original SSO request based on the ID
        original_sso_request = None
        try:
            original_sso_request = get_sso_request_by_request_id(request_id)
        except SSORequestNotFoundError:
            pass

        if original_sso_request is None:
            raise ValueError(
                "This SSO request is invalid (it may have already been used)"
            )

        # Verifies if the request has expired already
        LOG.info(
            "Incoming SSO response matching request: %s, with expiry: %s",
            original_sso_request.request_id,
            original_sso_request.expiry,
        )
        if original_sso_request.expiry <= get_datetime_utc_now():
            raise ValueError(
                "The SSO request associated with this response has already expired!"
            )

        # All done, we should not need to use this again :)
        LOG.debug(
            "Deleting original SSO request from database with ID %s",
            original_sso_request.id,
        )
        original_sso_request.delete()

        return original_sso_request

    def post(self, response, **kwargs):
        try:

            original_sso_request = self._validate_and_delete_sso_request(response)

            # Obtain user details from the SSO response from the backend
            verified_user = SSO_BACKEND.verify_response(response)
            if not isinstance(verified_user, BaseSingleSignOnBackendResponse):
                return process_failure_response(
                    http_client.INTERNAL_SERVER_ERROR,
                    "Unexpected SSO backend response type. Expected "
                    "BaseSingleSignOnBackendResponse instance!",
                )

            LOG.info(
                "Authenticating SSO user [%s] with groups [%s]",
                verified_user.username,
                verified_user.groups,
            )

            st2_auth_token_create_request = GenericRequestParam(
                ttl=None,
                groups=verified_user.groups,
            )

            st2_auth_token = self.st2_auth_handler.handle_auth(
                request=st2_auth_token_create_request,
                remote_addr=verified_user.referer,
                remote_user=verified_user.username,
                headers={},
            )

            # Depending on the type of SSO request we should handle the response differently
            # ie WEB gets redirected and CLI gets an encrypted callback
            if original_sso_request.type == SSORequestDB.Type.WEB:
                return process_successful_sso_web_response(
                    verified_user.referer, st2_auth_token
                )
            elif original_sso_request.type == SSORequestDB.Type.CLI:
                return process_successful_sso_cli_response(
                    verified_user.referer, original_sso_request.key, st2_auth_token
                )
            else:
                raise NotImplementedError(
                    "Unexpected SSO request type [%s] -- I can deal with web and cli"
                    % original_sso_request.type
                )
        except NotImplementedError as e:
            return process_failure_response(http_client.INTERNAL_SERVER_ERROR, e)
        except auth_exc.SSOVerificationError as e:
            return process_failure_response(http_client.UNAUTHORIZED, e)
        except Exception as e:
            raise e


class SingleSignOnRequestController(object):
    def _create_sso_request(self, handler, **kwargs):

        request_id = "id_%s" % str(uuid4())
        sso_request = handler(request_id=request_id, **kwargs)
        LOG.debug(
            "Created SSO request with request id %s and expiry %s and type %s",
            request_id,
            sso_request.expiry,
            sso_request.type,
        )
        return sso_request

    # web-intended SSO
    def get_web(self, referer):
        try:
            sso_request = self._create_sso_request(create_web_sso_request)

            response = router.Response(status=http_client.TEMPORARY_REDIRECT)
            response.location = SSO_BACKEND.get_request_redirect_url(
                sso_request.request_id, referer
            )
            return response
        except NotImplementedError as e:
            if sso_request:
                sso_request.delete()
            return process_failure_response(http_client.INTERNAL_SERVER_ERROR, e)
        except Exception as e:
            if sso_request:
                sso_request.delete()
            raise e

    # cli-intended SSO
    def post_cli(self, response):
        sso_request = None
        try:
            key = getattr(response, "key", None)
            callback_url = getattr(response, "callback_url", None)
            # This is already checked at the API level, but aanyway..
            if not key or not callback_url:
                raise ValueError("Missing either key and/or callback_url!")

            try:
                read_crypto_key_from_dict(json_decode(key))
            except Exception:
                LOG.warn("Could not decode incoming SSO CLI request key")
                raise ValueError(
                    "The provided key is invalid! It should be stackstorm-compatible AES key"
                )

            sso_request = self._create_sso_request(create_cli_sso_request, key=key)
            response = router.Response(status=http_client.OK)
            response.content_type = "application/json"
            response.json = {
                "sso_url": SSO_BACKEND.get_request_redirect_url(
                    sso_request.request_id, callback_url
                ),
                # this is needed because the db doesnt save microseconds
                # pylint: disable=E1101
                "expiry": sso_request.expiry.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3]
                + "000+00:00",
            }

            return response
        except NotImplementedError as e:
            if sso_request:
                sso_request.delete()
            return process_failure_response(http_client.INTERNAL_SERVER_ERROR, e)
        except Exception as e:
            if sso_request:
                sso_request.delete()
            raise e


class SingleSignOnController(object):
    request = SingleSignOnRequestController()
    callback = IdentityProviderCallbackController()

    def _get_sso_enabled_config(self):
        return {"enabled": cfg.CONF.auth.sso}

    def get(self):
        try:
            result = self._get_sso_enabled_config()
            return process_successful_response(http_client.OK, result)
        except Exception:
            LOG.exception("Error encountered while getting SSO configuration.")
            result = {"enabled": False}
            return process_successful_response(http_client.OK, result)


CALLBACK_SUCCESS_RESPONSE_BODY = """
<html>
    <script>
        function setCookie(name, value, days) {
            var expires = "";
            if (days) {
                var date = new Date();
                date.setTime(date.getTime() + (days * 24 * 60 * 60 * 1000));
                expires = "; expires=" + date.toUTCString();
            }
            document.cookie = name + "=" + (value || "") + expires + "; path=/";
        }
        function getCookie(name) {
            var v = document.cookie.match('(^|;) ?' + name + '=([^;]*)(;|$)');
            return v ? v[2] : null;
        }

        // This cookie should've been set by the sso module
        tokenDetails = JSON.parse(decodeURIComponent(getCookie('st2-auth-token')));

        // Defining what to be set
        data = JSON.parse(window.localStorage.getItem('st2Session') || "{}");
        data['token'] = tokenDetails

        if (!data['server']) {
            serverPrefix = location.protocol + '//' + location.host;
            data['server'] = {
                "api": `${serverPrefix}/api`,
                "auth": `${serverPrefix}/auth`,
                "stream": `${serverPrefix}/stream`,
                "token": null
            }
            console.log("Configured default server endpoints to [%%s]", data['server'])
        }

        // Persising data
        console.log("Setting credentials to persistent stores")
        window.localStorage.setItem('st2Session', JSON.stringify(data));
        window.localStorage.setItem('logged_in', { "loggedIn": true })
        setCookie("auth-token", tokenDetails.token)

        window.location.replace("%s");
    </script>
</html>
"""


def token_to_json(token):
    return {
        "id": str(token.id),
        "user": token.user,
        "token": token.token,
        "expiry": str(token.expiry),
        "service": False,
        "metadata": {},
    }


def process_successful_sso_cli_response(callback_url, key, token):
    token_json = token_to_json(token)

    aes_key = read_crypto_key_from_dict(json_decode(key))
    encrypted_token = symmetric_encrypt(aes_key, json.dumps(token_json))

    LOG.debug(
        "Redirecting successfuly SSO CLI login to url [%s] "
        "with extra parameters for the encrypted token",
        callback_url,
    )

    # Response back to the browser has all the data in the query string, in an encrypted formta :)
    resp = router.Response(status=http_client.FOUND)
    resp.location = "%s?response=%s" % (callback_url, encrypted_token.decode("utf-8"))

    return resp


def process_successful_sso_web_response(referer, token):
    token_json = token_to_json(token)

    body = CALLBACK_SUCCESS_RESPONSE_BODY % referer
    resp = router.Response(body=body)
    resp.headers["Content-Type"] = "text/html"

    resp.set_cookie(
        "st2-auth-token",
        value=urllib.parse.quote(json.dumps(token_json)),
        expires=datetime.timedelta(seconds=60),
        overwrite=True,
    )

    return resp


def process_successful_response(status_code, json_body):
    return router.Response(status_code=status_code, json_body=json_body)


def process_failure_response(status_code, exception):
    LOG.error(str(exception))
    json_body = {"faultstring": str(exception)}
    return router.Response(status_code=status_code, json_body=json_body)


sso_controller = SingleSignOnController()
sso_request_controller = SingleSignOnRequestController()
idp_callback_controller = IdentityProviderCallbackController()

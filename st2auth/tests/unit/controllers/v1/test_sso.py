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
from typing import List
from st2common.models.db.auth import SSORequestDB
from st2common.persistence.auth import SSORequest
from st2common.services.access import DEFAULT_SSO_REQUEST_TTL
import st2tests.config as tests_config

from st2common.util import date as date_utils

tests_config.parse_args()

import json
import mock

from oslo_config import cfg
from six.moves import http_client
from six.moves import urllib

from st2auth.controllers.v1 import sso as sso_api_controller
from st2auth.sso import noop
from st2common.exceptions import auth as auth_exc
from tests.base import FunctionalTest


SSO_V1_PATH = "/v1/sso"
SSO_REQUEST_WEB_V1_PATH = SSO_V1_PATH + "/request/web"
SSO_REQUEST_CLI_V1_PATH = SSO_V1_PATH + "/request/cli"
SSO_CALLBACK_V1_PATH = SSO_V1_PATH + "/callback"
MOCK_REFERER = "https://127.0.0.1"
MOCK_USER = "stanley"
MOCK_CALLBACK_URL = 'http://localhost:34999'
MOCK_CLI_REQUEST_KEY = json.dumps({
    "hmacKey": {
        "hmacKeyString": "-qdRklvhm4xvzIfaL6Z2nmQ-2N-c4IUtNa1_BowCVfg", 
        "size": 256
    }, 
    "aesKeyString": "0UyXFjBTQ9PMyHZ0mqrvuqCSzesuFup1d6m-4Vi3vdo", 
    "mode": "CBC", 
    "size": 256
})

class TestSingleSignOnController(FunctionalTest):
    def test_sso_enabled(self):
        cfg.CONF.set_override(group="auth", name="sso", override=True)
        response = self.app.get(SSO_V1_PATH, expect_errors=False)
        self.assertTrue(response.status_code, http_client.OK)
        self.assertDictEqual(response.json, {"enabled": True})

    def test_sso_disabled(self):
        cfg.CONF.set_override(group="auth", name="sso", override=False)
        response = self.app.get(SSO_V1_PATH, expect_errors=False)
        self.assertTrue(response.status_code, http_client.OK)
        self.assertDictEqual(response.json, {"enabled": False})

    @mock.patch.object(
        sso_api_controller.SingleSignOnController,
        "_get_sso_enabled_config",
        mock.MagicMock(side_effect=KeyError("foobar")),
    )
    def test_unknown_exception(self):
        cfg.CONF.set_override(group="auth", name="sso", override=True)
        response = self.app.get(SSO_V1_PATH, expect_errors=False)
        self.assertTrue(response.status_code, http_client.OK)
        self.assertDictEqual(response.json, {"enabled": False})
        self.assertTrue(
            sso_api_controller.SingleSignOnController._get_sso_enabled_config.called
        )

# Base SSO request test class, to be used by CLI/WEB
class TestSingleSignOnRequestController(FunctionalTest):

    # Cleanup sso requests
    def setUp(self):
        for x in SSORequest.get_all():
            SSORequest.delete(x)

    def _assert_response(self, response, status_code, expected_body):
        self.assertTrue(response.status_code, status_code)
        self.assertDictEqual(response.json, expected_body)


    def _assert_sso_requests_len(self, expected):
        sso_requests : List[SSORequestDB] = SSORequest.get_all()
        self.assertEqual(len(sso_requests), expected)
        return sso_requests

    def _assert_sso_request_success(self, sso_request, type):
        self.assertEqual(sso_request.type, type)
        self.assertLessEqual(
            abs(
                sso_request.expiry.timestamp() 
                - date_utils.get_datetime_utc_now().timestamp() 
                - DEFAULT_SSO_REQUEST_TTL
            ), 2)
        sso_api_controller.SSO_BACKEND.get_request_redirect_url.assert_called_with(sso_request.request_id, MOCK_REFERER)

    def _test_cli_request_bad_parameter_helper(self, params, expected_error):
        response = self._default_cli_request(
            params=params,
            expect_errors=True
        )
        self._assert_response(
            response,
            http_client.INTERNAL_SERVER_ERROR, 
            {"faultstring": expected_error})
        self._assert_sso_requests_len(0)



    def _default_web_request(self, expect_errors):
        return self.app.get(SSO_REQUEST_WEB_V1_PATH, 
            headers={"referer": MOCK_REFERER}, expect_errors=expect_errors)
    def _default_cli_request(
        self, 
        params={
            'callback_url': MOCK_CALLBACK_URL, 
            'key': MOCK_CLI_REQUEST_KEY
        }, 
        expect_errors=False):
        return self.app.post(
            SSO_REQUEST_CLI_V1_PATH, 
            content_type="application/json",
            params=json.dumps(params), 
            expect_errors=expect_errors
        )


    @mock.patch.object(
        sso_api_controller.SSO_BACKEND,
        "get_request_redirect_url",
        mock.MagicMock(side_effect=Exception("fooobar")),
    )
    def test_web_default_backend_unknown_exception(self):
        response = self._default_web_request(True)
        self._assert_response(
            response,
            http_client.INTERNAL_SERVER_ERROR, 
            {"faultstring": "Internal Server Error"})
        self._assert_sso_requests_len(0)

    def test_web_default_backend_invalid_key(self):
        response = self._default_web_request(True)
        self._assert_response(
            response,
            http_client.INTERNAL_SERVER_ERROR, 
            {"faultstring": noop.NOT_IMPLEMENTED_MESSAGE})
        self._assert_sso_requests_len(0)


    def test_web_default_backend_not_implemented(self):
        response = self._default_web_request(True)
        self._assert_response(
            response,
            http_client.INTERNAL_SERVER_ERROR, 
            {"faultstring": noop.NOT_IMPLEMENTED_MESSAGE})
        self._assert_sso_requests_len(0)

    @mock.patch.object(
        sso_api_controller.SSO_BACKEND,
        "get_request_redirect_url",
        mock.MagicMock(return_value="https://127.0.0.1"),
    )
    def test_web_idp_redirect(self):
        response = self._default_web_request(False)
        self.assertTrue(response.status_code, http_client.TEMPORARY_REDIRECT)
        self.assertEqual(response.location, "https://127.0.0.1")

        # Make sure we have created a SSO request based on this call :)
        sso_requests = self._assert_sso_requests_len(1)
        sso_request = sso_requests[0]
        self._assert_sso_request_success(sso_request, SSORequestDB.Type.WEB)


    @mock.patch.object(
        sso_api_controller.SSO_BACKEND,
        "get_request_redirect_url",
        mock.MagicMock(side_effect=Exception("fooobar")),
    )
    def test_cli_default_backend_unknown_exception(self):
        response = self._default_cli_request(expect_errors=True)
        self._assert_response(
            response,
            http_client.INTERNAL_SERVER_ERROR, 
            {"faultstring": "Internal Server Error"})
        self._assert_sso_requests_len(0)

    def test_cli_default_backend_bad_key(self):
        self._test_cli_request_bad_parameter_helper(
            {
                'callback_url': MOCK_CALLBACK_URL,
                'key': 'bad-key'
            },
            "The provided key is invalid! It should be stackstorm-compatible AES key"
        )

    def test_cli_default_backend_missing_key(self):
        self._test_cli_request_bad_parameter_helper(
            {
                'callback_url': MOCK_CALLBACK_URL,
            },
            "Missing either key and/or callback_url!"
        )

    def test_cli_default_backend_missing_callback_url(self):
        self._test_cli_request_bad_parameter_helper(
            {
                'key': MOCK_CLI_REQUEST_KEY,
            },
            "Missing either key and/or callback_url!"
        )

    def test_cli_default_backend_missing_key_and_callback_url(self):
        self._test_cli_request_bad_parameter_helper(
            {
                'ops': 'ops'
            },
            "Missing either key and/or callback_url!"
        )

    def test_cli_default_backend_not_implemented(self):
        response = self._default_cli_request(expect_errors=True)
        self._assert_response(
            response,
            http_client.INTERNAL_SERVER_ERROR, 
            {"faultstring": noop.NOT_IMPLEMENTED_MESSAGE})
        self._assert_sso_requests_len(0)


    @mock.patch.object(
        sso_api_controller.SSO_BACKEND,
        "get_request_redirect_url",
        mock.MagicMock(return_value="https://127.0.0.1"),
    )
    def test_cli_default_backend(self):
        response = self._default_cli_request(
            params={
                'callback_url': MOCK_REFERER,
                'key': MOCK_CLI_REQUEST_KEY
            },
            expect_errors=False
        )

        # Make sure we have created a SSO request based on this call :)
        sso_requests = self._assert_sso_requests_len(1)
        sso_request = sso_requests[0]
        self._assert_sso_request_success(sso_request, SSORequestDB.Type.CLI)
        self._assert_response(
            response,
            http_client.OK, 
            {
                "sso_url": "https://127.0.0.1",
                "expiry": sso_request.expiry.isoformat()
            })
        

class TestIdentityProviderCallbackController(FunctionalTest):
    @mock.patch.object(
        sso_api_controller.SSO_BACKEND,
        "verify_response",
        mock.MagicMock(side_effect=Exception("fooobar")),
    )
    def test_default_backend_unknown_exception(self):
        expected_error = {"faultstring": "Internal Server Error"}
        response = self.app.post_json(
            SSO_CALLBACK_V1_PATH, {"foo": "bar"}, expect_errors=True
        )
        self.assertTrue(response.status_code, http_client.INTERNAL_SERVER_ERROR)
        self.assertDictEqual(response.json, expected_error)

    def test_default_backend_not_implemented(self):
        expected_error = {"faultstring": noop.NOT_IMPLEMENTED_MESSAGE}
        response = self.app.post_json(
            SSO_CALLBACK_V1_PATH, {"foo": "bar"}, expect_errors=True
        )
        self.assertTrue(response.status_code, http_client.INTERNAL_SERVER_ERROR)
        self.assertDictEqual(response.json, expected_error)

    @mock.patch.object(
        sso_api_controller.SSO_BACKEND,
        "verify_response",
        mock.MagicMock(return_value={"referer": MOCK_REFERER, "username": MOCK_USER}),
    )
    def test_idp_callback(self):
        expected_body = sso_api_controller.CALLBACK_SUCCESS_RESPONSE_BODY % MOCK_REFERER
        response = self.app.post_json(
            SSO_CALLBACK_V1_PATH, {"foo": "bar"}, expect_errors=False
        )
        self.assertTrue(response.status_code, http_client.OK)
        self.assertEqual(expected_body, response.body.decode("utf-8"))

        set_cookies_list = [h for h in response.headerlist if h[0] == "Set-Cookie"]
        self.assertEqual(len(set_cookies_list), 1)
        self.assertIn("st2-auth-token", set_cookies_list[0][1])

        cookie = urllib.parse.unquote(set_cookies_list[0][1]).split("=")
        st2_auth_token = json.loads(cookie[1].split(";")[0])
        self.assertIn("token", st2_auth_token)
        self.assertEqual(st2_auth_token["user"], MOCK_USER)

    @mock.patch.object(
        sso_api_controller.SSO_BACKEND,
        "verify_response",
        mock.MagicMock(return_value={"referer": MOCK_REFERER, "username": MOCK_USER}),
    )
    def test_callback_url_encoded_payload(self):
        data = {"foo": ["bar"]}
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        response = self.app.post(SSO_CALLBACK_V1_PATH, data, headers=headers)
        self.assertTrue(response.status_code, http_client.OK)

    @mock.patch.object(
        sso_api_controller.SSO_BACKEND,
        "verify_response",
        mock.MagicMock(
            side_effect=auth_exc.SSOVerificationError("Verification Failed")
        ),
    )
    def test_idp_callback_verification_failed(self):
        expected_error = {"faultstring": "Verification Failed"}
        response = self.app.post_json(
            SSO_CALLBACK_V1_PATH, {"foo": "bar"}, expect_errors=True
        )
        self.assertTrue(response.status_code, http_client.UNAUTHORIZED)
        self.assertDictEqual(response.json, expected_error)

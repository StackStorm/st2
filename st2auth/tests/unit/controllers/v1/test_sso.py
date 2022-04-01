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

import st2tests.config as tests_config

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
SSO_REQUEST_V1_PATH = SSO_V1_PATH + "/request"
SSO_CALLBACK_V1_PATH = SSO_V1_PATH + "/callback"
MOCK_REFERER = "https://127.0.0.1"
MOCK_USER = "stanley"


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


class TestSingleSignOnRequestController(FunctionalTest):
    @mock.patch.object(
        sso_api_controller.SSO_BACKEND,
        "get_request_redirect_url",
        mock.MagicMock(side_effect=Exception("fooobar")),
    )
    def test_default_backend_unknown_exception(self):
        expected_error = {"faultstring": "Internal Server Error"}
        response = self.app.get(SSO_REQUEST_V1_PATH, expect_errors=True)
        self.assertTrue(response.status_code, http_client.INTERNAL_SERVER_ERROR)
        self.assertDictEqual(response.json, expected_error)

    def test_default_backend_not_implemented(self):
        expected_error = {"faultstring": noop.NOT_IMPLEMENTED_MESSAGE}
        response = self.app.get(SSO_REQUEST_V1_PATH, expect_errors=True)
        self.assertTrue(response.status_code, http_client.INTERNAL_SERVER_ERROR)
        self.assertDictEqual(response.json, expected_error)

    @mock.patch.object(
        sso_api_controller.SSO_BACKEND,
        "get_request_redirect_url",
        mock.MagicMock(return_value="https://127.0.0.1"),
    )
    def test_idp_redirect(self):
        response = self.app.get(SSO_REQUEST_V1_PATH, expect_errors=False)
        self.assertTrue(response.status_code, http_client.TEMPORARY_REDIRECT)
        self.assertEqual(response.location, "https://127.0.0.1")


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

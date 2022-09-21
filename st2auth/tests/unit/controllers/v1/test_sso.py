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

# NOTE: We need to perform monkeypatch before importing ssl module otherwise tests will fail.
# See https://github.com/StackStorm/st2/pull/4834 for details
from st2common.util.monkey_patch import monkey_patch

monkey_patch()

from tests.base import FunctionalTest
from st2common.exceptions import auth as auth_exc
from st2auth.sso import noop
from st2auth.controllers.v1 import sso as sso_api_controller
from six.moves import urllib
from six.moves import http_client
from oslo_config import cfg
import mock
import json
from typing import List
from st2auth.sso.base import BaseSingleSignOnBackendResponse
from st2common.models.db.auth import SSORequestDB
from st2common.persistence.auth import SSORequest, Token
from st2common.persistence.rbac import GroupToRoleMapping, UserRoleAssignment, Role
from st2common.models.db.rbac import GroupToRoleMappingDB, RoleDB
from st2common.services.access import (
    DEFAULT_SSO_REQUEST_TTL,
    create_web_sso_request,
    create_cli_sso_request,
)
import st2tests.config as tests_config
from st2common.util.crypto import read_crypto_key_from_dict, symmetric_decrypt

from st2common.util import date as date_utils

tests_config.parse_args()


SSO_V1_PATH = "/v1/sso"
SSO_REQUEST_WEB_V1_PATH = SSO_V1_PATH + "/request/web"
SSO_REQUEST_CLI_V1_PATH = SSO_V1_PATH + "/request/cli"
SSO_CALLBACK_V1_PATH = SSO_V1_PATH + "/callback"
MOCK_REFERER = "https://127.0.0.1"
MOCK_USER = "stanley"
MOCK_CALLBACK_URL = "http://localhost:34999"
MOCK_CLI_REQUEST_KEY = read_crypto_key_from_dict(
    {
        "hmacKey": {
            "hmacKeyString": "-qdRklvhm4xvzIfaL6Z2nmQ-2N-c4IUtNa1_BowCVfg",
            "size": 256,
        },
        "aesKeyString": "0UyXFjBTQ9PMyHZ0mqrvuqCSzesuFup1d6m-4Vi3vdo",
        "mode": "CBC",
        "size": 256,
    }
)
MOCK_CLI_REQUEST_KEY_ALTERNATIVE = read_crypto_key_from_dict(
    {
        "hmacKey": {
            "hmacKeyString": "ENb-2COFGmdnshSnjjz3wePrxypVzCf9Jq2iuhXEgbc",
            "size": 256,
        },
        "aesKeyString": "8TpT_RaA6dlharswjqVlJSw027B60UkgnQqcgGfmf08",
        "mode": "CBC",
        "size": 256,
    }
)
MOCK_CLI_REQUEST_KEY_JSON = MOCK_CLI_REQUEST_KEY.to_json()
MOCK_REQUEST_ID = "test-id"
MOCK_GROUPS = ["test", "test2"]
MOCK_VERIFIED_USER_OBJECT = BaseSingleSignOnBackendResponse(
    referer=MOCK_REFERER, groups=MOCK_GROUPS, username=MOCK_USER
)


class TestSingleSignOnController(FunctionalTest):
    def test_sso_enabled(self):
        cfg.CONF.set_override(group="auth", name="sso", override=True)
        response = self.app.get(SSO_V1_PATH, expect_errors=False)
        self.assertEqual(response.status_code, http_client.OK)
        self.assertDictEqual(response.json, {"enabled": True})

    def test_sso_disabled(self):
        cfg.CONF.set_override(group="auth", name="sso", override=False)
        response = self.app.get(SSO_V1_PATH, expect_errors=False)
        self.assertEqual(response.status_code, http_client.OK)
        self.assertDictEqual(response.json, {"enabled": False})

    @mock.patch.object(
        sso_api_controller.SingleSignOnController,
        "_get_sso_enabled_config",
        mock.MagicMock(side_effect=KeyError("foobar")),
    )
    def test_unknown_exception(self):
        cfg.CONF.set_override(group="auth", name="sso", override=True)
        response = self.app.get(SSO_V1_PATH, expect_errors=False)
        self.assertEqual(response.status_code, http_client.OK)
        self.assertDictEqual(response.json, {"enabled": False})
        self.assertTrue(
            sso_api_controller.SingleSignOnController._get_sso_enabled_config.called
        )


# Base SSO request test class, to be used by CLI/WEB
class TestSingleSignOnRequestController(FunctionalTest):

    #
    # Settupers
    #

    # Cleanup sso requests
    def setUp(self):
        for x in SSORequest.get_all():
            SSORequest.delete(x)

    #
    # Helpers
    #

    def _assert_response(self, response, status_code, expected_body):
        self.assertEqual(response.status_code, status_code)
        self.assertDictEqual(response.json, expected_body)

    def _assert_sso_requests_len(self, expected):
        sso_requests: List[SSORequestDB] = SSORequest.get_all()
        self.assertEqual(len(sso_requests), expected)
        return sso_requests

    def _assert_sso_request_success(self, sso_request, type):
        self.assertEqual(sso_request.type, type)
        self.assertLessEqual(
            abs(
                sso_request.expiry.timestamp()
                - date_utils.get_datetime_utc_now().timestamp()
                - DEFAULT_SSO_REQUEST_TTL
            ),
            2,
        )
        sso_api_controller.SSO_BACKEND.get_request_redirect_url.assert_called_with(
            sso_request.request_id, MOCK_REFERER
        )

    def _test_cli_request_bad_parameter_helper(self, params, expected_error):
        response = self._default_cli_request(params=params, expect_errors=True)
        self._assert_response(
            response, http_client.BAD_REQUEST, {"faultstring": expected_error}
        )
        self._assert_sso_requests_len(0)

    def _default_web_request(self, expect_errors):
        return self.app.get(
            SSO_REQUEST_WEB_V1_PATH,
            headers={"referer": MOCK_REFERER},
            expect_errors=expect_errors,
        )

    def _default_cli_request(
        self,
        params={"callback_url": MOCK_CALLBACK_URL, "key": MOCK_CLI_REQUEST_KEY_JSON},
        expect_errors=False,
    ):
        return self.app.post(
            SSO_REQUEST_CLI_V1_PATH,
            content_type="application/json",
            params=json.dumps(params),
            expect_errors=expect_errors,
        )

    #
    # Tests :)
    #

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
            {"faultstring": "Internal Server Error"},
        )
        self._assert_sso_requests_len(0)

    def test_web_default_backend_invalid_key(self):
        response = self._default_web_request(True)
        self._assert_response(
            response,
            http_client.INTERNAL_SERVER_ERROR,
            {"faultstring": noop.NOT_IMPLEMENTED_MESSAGE},
        )
        self._assert_sso_requests_len(0)

    def test_web_default_backend_not_implemented(self):
        response = self._default_web_request(True)
        self._assert_response(
            response,
            http_client.INTERNAL_SERVER_ERROR,
            {"faultstring": noop.NOT_IMPLEMENTED_MESSAGE},
        )
        self._assert_sso_requests_len(0)

    @mock.patch.object(
        sso_api_controller.SSO_BACKEND,
        "get_request_redirect_url",
        mock.MagicMock(return_value="https://127.0.0.1"),
    )
    def test_web_idp_redirect(self):
        response = self._default_web_request(False)
        self.assertEqual(response.status_code, http_client.TEMPORARY_REDIRECT)
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
            {"faultstring": "Internal Server Error"},
        )
        self._assert_sso_requests_len(0)

    def test_cli_default_backend_bad_key(self):
        self._test_cli_request_bad_parameter_helper(
            {"callback_url": MOCK_CALLBACK_URL, "key": "bad-key"},
            "The provided key is invalid! It should be stackstorm-compatible AES key",
        )

    def test_cli_default_backend_missing_key(self):
        self._test_cli_request_bad_parameter_helper(
            {
                "callback_url": MOCK_CALLBACK_URL,
            },
            "'key' is a required property",
        )

    def test_cli_default_backend_missing_callback_url(self):
        self._test_cli_request_bad_parameter_helper(
            {
                "key": MOCK_CLI_REQUEST_KEY_JSON,
            },
            "'callback_url' is a required property",
        )

    def test_cli_default_backend_missing_key_and_callback_url(self):
        self._test_cli_request_bad_parameter_helper(
            {"ops": "ops"}, "'key' is a required property"
        )

    def test_cli_default_backend_not_implemented(self):
        response = self._default_cli_request(expect_errors=True)
        self._assert_response(
            response,
            http_client.INTERNAL_SERVER_ERROR,
            {"faultstring": noop.NOT_IMPLEMENTED_MESSAGE},
        )
        self._assert_sso_requests_len(0)

    @mock.patch.object(
        sso_api_controller.SSO_BACKEND,
        "get_request_redirect_url",
        mock.MagicMock(return_value="https://127.0.0.1"),
    )
    def test_cli_default_backend(self):
        response = self._default_cli_request(
            params={"callback_url": MOCK_REFERER, "key": MOCK_CLI_REQUEST_KEY_JSON},
            expect_errors=False,
        )

        # Make sure we have created a SSO request based on this call :)
        sso_requests = self._assert_sso_requests_len(1)
        sso_request = sso_requests[0]
        self._assert_sso_request_success(sso_request, SSORequestDB.Type.CLI)
        self._assert_response(
            response,
            http_client.OK,
            {"sso_url": "https://127.0.0.1", "expiry": sso_request.expiry.isoformat()},
        )


class TestIdentityProviderCallbackController(FunctionalTest):
    def setUp(self):
        for x in SSORequest.get_all():
            SSORequest.delete(x)

    def setUp_for_rbac(self):
        # Set up standard roles
        for x in Role.get_all():
            Role.delete(x)

        RoleDB(name="system_admin", system=True).save()
        RoleDB(name="admin", system=True).save()
        RoleDB(name="my-test", system=True).save()

        # Cleanup user assignments
        for x in UserRoleAssignment.get_all():
            UserRoleAssignment.delete(x)

        for x in GroupToRoleMapping.get_all():
            GroupToRoleMapping.delete(x)

        # Set up assignment mappings
        GroupToRoleMappingDB(
            group="test2", roles=["system_admin", "admin"], source="test", enabled=True
        ).save()

        GroupToRoleMappingDB(
            group="test", roles=["my-test"], source="test", enabled=True
        ).save()

        cfg.CONF.set_override(group="rbac", name="enable", override=True)
        cfg.CONF.set_override(group="rbac", name="backend", override="default")

    def tearDown_for_rbac(self):

        for x in UserRoleAssignment.get_all():
            UserRoleAssignment.delete(x)

        for x in GroupToRoleMapping.get_all():
            GroupToRoleMapping.delete(x)

        for x in Role.get_all():
            Role.delete(x)

        cfg.CONF.set_override(group="rbac", name="enable", override=False)
        cfg.CONF.set_override(group="rbac", name="backend", override="default")

    # Helpers
    #

    def _assert_response(
        self, response, status_code, expected_body, response_type="json"
    ):
        self.assertEqual(response.status_code, status_code)
        if response_type == "json":
            self.assertDictEqual(response.json, expected_body)
        else:
            self.assertEqual(response.body.decode("utf-8"), expected_body)

    def _assert_sso_requests_len(self, expected):
        sso_requests: List[SSORequestDB] = SSORequest.get_all()
        self.assertEqual(len(sso_requests), expected)
        return sso_requests

    def _assert_role_assignment_len(self, expected):
        role_assignments: List[UserRoleAssignment] = UserRoleAssignment.get_all()
        self.assertEqual(len(role_assignments), expected)
        return role_assignments

    def _assert_token_data_is_valid(self, token_data):
        self.assertEqual(token_data["user"], MOCK_USER)
        self.assertIsNotNone(token_data["expiry"])
        self.assertIsNotNone(token_data["token"])

        # Validate actual token :)
        token = Token.get(token_data["token"])
        self.assertIsNotNone(token)
        self.assertEqual(token.user, MOCK_USER)
        self.assertEqual(token.expiry.isoformat()[0:19], token_data["expiry"][0:19])

    def _assert_response_has_token_cookie_only(self, response):

        set_cookies_list = [h for h in response.headerlist if h[0] == "Set-Cookie"]
        self.assertEqual(len(set_cookies_list), 1)
        self.assertIn("st2-auth-token", set_cookies_list[0][1])

        cookie = urllib.parse.unquote(set_cookies_list[0][1]).split("=")
        st2_auth_token = json.loads(cookie[1].split(";")[0])
        self.assertIn("token", st2_auth_token)

        return st2_auth_token

    def _default_callback_request(self, params={}, expect_errors=False):
        return self.app.post_json(
            SSO_CALLBACK_V1_PATH, params, expect_errors=expect_errors
        )

    #
    # Tests
    #

    @mock.patch.object(
        sso_api_controller.SSO_BACKEND,
        "get_request_id_from_response",
        mock.MagicMock(side_effect=Exception("fooobar")),
    )
    def test_default_backend_unknown_exception(self):
        response = self._default_callback_request({"foo": "bar"}, expect_errors=True)
        self._assert_response(
            response,
            http_client.INTERNAL_SERVER_ERROR,
            {"faultstring": "Internal Server Error"},
        )

    def test_default_backend_not_implemented(self):
        response = self._default_callback_request({"foo": "bar"}, expect_errors=True)
        self._assert_response(
            response,
            http_client.INTERNAL_SERVER_ERROR,
            {"faultstring": noop.NOT_IMPLEMENTED_MESSAGE},
        )

    @mock.patch.object(
        sso_api_controller.SSO_BACKEND,
        "get_request_id_from_response",
        mock.MagicMock(return_value=None),
    )
    def test_default_backend_invalid_request_id(self):
        response = self._default_callback_request({"foo": "bar"}, expect_errors=True)
        self._assert_response(
            response,
            http_client.BAD_REQUEST,
            {"faultstring": "Invalid request id coming from SAML response"},
        )

    @mock.patch.object(
        sso_api_controller.SSO_BACKEND,
        "get_request_id_from_response",
        mock.MagicMock(return_value=MOCK_REQUEST_ID),
    )
    @mock.patch.object(
        sso_api_controller.SSO_BACKEND,
        "verify_response",
        mock.MagicMock(return_value={"test": "user"}),
    )
    def test_default_backend_invalid_backend_response(self):
        create_web_sso_request(MOCK_REQUEST_ID)
        response = self._default_callback_request({"foo": "bar"}, expect_errors=True)
        self._assert_response(
            response,
            http_client.INTERNAL_SERVER_ERROR,
            {
                "faultstring": (
                    "Unexpected SSO backend response type."
                    " Expected BaseSingleSignOnBackendResponse instance!"
                )
            },
        )

    @mock.patch.object(
        sso_api_controller.SSO_BACKEND,
        "get_request_id_from_response",
        mock.MagicMock(return_value=MOCK_REQUEST_ID),
    )
    def test_idp_callback_missing_sso_request(self):
        self._assert_sso_requests_len(0)
        response = self._default_callback_request({"foo": "bar"}, expect_errors=True)

        self._assert_response(
            response,
            http_client.BAD_REQUEST,
            {
                "faultstring": "This SSO request is invalid (it may have already been used)"
            },
        )

    @mock.patch.object(
        sso_api_controller.SSO_BACKEND,
        "get_request_id_from_response",
        mock.MagicMock(return_value=MOCK_REQUEST_ID),
    )
    def test_idp_callback_sso_request_expired(self):
        # given
        # Create fake expired request
        create_web_sso_request(MOCK_REQUEST_ID, -20)
        self._assert_sso_requests_len(1)
        response = self._default_callback_request({"foo": "bar"}, expect_errors=True)

        self._assert_response(
            response,
            http_client.BAD_REQUEST,
            {
                "faultstring": "The SSO request associated with this response has already expired!"
            },
        )

    @mock.patch.object(
        sso_api_controller.SSO_BACKEND,
        "get_request_id_from_response",
        mock.MagicMock(return_value=MOCK_REQUEST_ID),
    )
    @mock.patch.object(
        sso_api_controller.SSO_BACKEND,
        "verify_response",
        mock.MagicMock(return_value=MOCK_VERIFIED_USER_OBJECT),
    )
    def _test_idp_callback_web(self):
        # given
        # Create fake request
        create_web_sso_request(MOCK_REQUEST_ID)
        self._assert_sso_requests_len(1)

        # when
        # Callback based onthe fake request :) -- as mocked above
        response = self._default_callback_request({"foo": "bar"}, expect_errors=False)

        # then
        # Validate request has been processed and response is as expected
        self._assert_sso_requests_len(0)
        self._assert_response(
            response,
            http_client.OK,
            sso_api_controller.CALLBACK_SUCCESS_RESPONSE_BODY % MOCK_REFERER,
            "str",
        )

        # Validate token is valid
        token_data = self._assert_response_has_token_cookie_only(response)
        self._assert_token_data_is_valid(token_data)

    def test_idp_callback_web_without_rbac(self):
        self._assert_role_assignment_len(0)
        self._test_idp_callback_web()
        self._assert_role_assignment_len(0)

    def test_idp_callback_web_with_rbac(self):
        self.setUp_for_rbac()
        self._assert_role_assignment_len(0)

        self._test_idp_callback_web()

        self._assert_role_assignment_len(3)
        self.tearDown_for_rbac()

    @mock.patch.object(
        sso_api_controller.SSO_BACKEND,
        "get_request_id_from_response",
        mock.MagicMock(return_value=MOCK_REQUEST_ID),
    )
    @mock.patch.object(
        sso_api_controller.SSO_BACKEND,
        "verify_response",
        mock.MagicMock(return_value=MOCK_VERIFIED_USER_OBJECT),
    )
    def _test_idp_callback_cli(self):
        # given
        # Create fake request
        create_cli_sso_request(MOCK_REQUEST_ID, MOCK_CLI_REQUEST_KEY_JSON)
        self._assert_sso_requests_len(1)

        # when
        # Callback based onthe fake request :) -- as mocked above
        response = self._default_callback_request({"foo": "bar"}, expect_errors=False)

        # then
        # Validate request has been processed and response is as expected
        self._assert_sso_requests_len(0)
        self.assertEqual(response.status_code, http_client.FOUND)
        self.assertRegex(
            response.location, "^" + MOCK_REFERER + r"\?response=[A-Z0-9]+$"
        )

        # decrypt token
        encrypted_response = response.location.split("response=")[1]
        token_data_json = symmetric_decrypt(MOCK_CLI_REQUEST_KEY, encrypted_response)
        self.assertIsNotNone(token_data_json)

        # Validate token is valid
        token_data = json.loads(token_data_json)
        self._assert_token_data_is_valid(token_data)

    def test_idp_callback_cli_without_rbac(self):
        self._assert_role_assignment_len(0)
        self._test_idp_callback_cli()
        self._assert_role_assignment_len(0)

    def test_idp_callback_cli_with_rbac(self):
        self.setUp_for_rbac()
        self._assert_role_assignment_len(0)

        self._test_idp_callback_cli()

        self._assert_role_assignment_len(3)
        self.tearDown_for_rbac()

    @mock.patch.object(
        sso_api_controller.SSO_BACKEND,
        "get_request_id_from_response",
        mock.MagicMock(return_value=MOCK_REQUEST_ID),
    )
    @mock.patch.object(
        sso_api_controller.SSO_BACKEND,
        "verify_response",
        mock.MagicMock(return_value=MOCK_VERIFIED_USER_OBJECT),
    )
    def test_idp_callback_cli_invalid_decryption_key(self):
        # given
        # Create fake request
        create_cli_sso_request(MOCK_REQUEST_ID, MOCK_CLI_REQUEST_KEY_JSON)
        self._assert_sso_requests_len(1)
        self._assert_role_assignment_len(0)

        # when
        # Callback based onthe fake request :) -- as mocked above
        response = self._default_callback_request({"foo": "bar"}, expect_errors=False)

        # then
        # Validate request has been processed and response is as expected
        self._assert_sso_requests_len(0)
        self._assert_role_assignment_len(0)
        self.assertEqual(response.status_code, http_client.FOUND)
        self.assertRegex(
            response.location, "^" + MOCK_REFERER + r"\?response=[A-Z0-9]+$"
        )

        # decrypt token
        encrypted_response = response.location.split("response=")[1]
        with self.assertRaises(Exception):
            symmetric_decrypt(MOCK_CLI_REQUEST_KEY_ALTERNATIVE, encrypted_response)

    @mock.patch.object(
        sso_api_controller.SSO_BACKEND,
        "get_request_id_from_response",
        mock.MagicMock(return_value=MOCK_REQUEST_ID),
    )
    @mock.patch.object(
        sso_api_controller.SSO_BACKEND,
        "verify_response",
        mock.MagicMock(return_value=MOCK_VERIFIED_USER_OBJECT),
    )
    def test_callback_url_encoded_payload(self):
        create_web_sso_request(MOCK_REQUEST_ID)
        data = {"foo": ["bar"]}
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        response = self.app.post(SSO_CALLBACK_V1_PATH, data, headers=headers)
        self.assertEqual(response.status_code, http_client.OK)

    @mock.patch.object(
        sso_api_controller.SSO_BACKEND,
        "get_request_id_from_response",
        mock.MagicMock(return_value=MOCK_REQUEST_ID),
    )
    @mock.patch.object(
        sso_api_controller.SSO_BACKEND,
        "verify_response",
        mock.MagicMock(
            side_effect=auth_exc.SSOVerificationError("Verification Failed")
        ),
    )
    def test_idp_callback_verification_failed(self):
        create_web_sso_request(MOCK_REQUEST_ID)
        expected_error = {"faultstring": "Verification Failed"}
        response = self.app.post_json(
            SSO_CALLBACK_V1_PATH, {"foo": "bar"}, expect_errors=True
        )
        self.assertEqual(response.status_code, http_client.UNAUTHORIZED)
        self.assertDictEqual(response.json, expected_error)

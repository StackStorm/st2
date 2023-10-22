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

# pytest: make sure monkey_patching happens before importing mongoengine
from st2common.util.monkey_patch import monkey_patch

monkey_patch()

import uuid
import datetime
import random
import string

import mock
from oslo_config import cfg

from tests.base import FunctionalTest
from st2common.util import isotime
from st2common.util import date as date_utils
from st2common.models.db.auth import UserDB, TokenDB, ApiKeyDB
from st2common.models.api.auth import TokenAPI
from st2common.persistence.auth import User, Token, ApiKey


USERNAME = "".join(random.choice(string.ascii_lowercase) for i in range(10))
TOKEN_DEFAULT_PATH = "/tokens"
TOKEN_V1_PATH = "/v1/tokens"
TOKEN_VERIFY_PATH = "/v1/tokens/validate"


class TestTokenController(FunctionalTest):
    @classmethod
    def setUpClass(cls, **kwargs):
        kwargs["extra_environ"] = {"REMOTE_USER": USERNAME}
        super(TestTokenController, cls).setUpClass(**kwargs)

    def test_token_model(self):
        dt = date_utils.get_datetime_utc_now()
        tk1 = TokenAPI(
            user="stanley",
            token=uuid.uuid4().hex,
            expiry=isotime.format(dt, offset=False),
        )
        tkdb1 = TokenAPI.to_model(tk1)
        self.assertIsNotNone(tkdb1)
        self.assertIsInstance(tkdb1, TokenDB)
        self.assertEqual(tkdb1.user, tk1.user)
        self.assertEqual(tkdb1.token, tk1.token)
        self.assertEqual(tkdb1.expiry, isotime.parse(tk1.expiry))
        tkdb2 = Token.add_or_update(tkdb1)
        self.assertEqual(tkdb1, tkdb2)
        self.assertIsNotNone(tkdb2.id)
        tk2 = TokenAPI.from_model(tkdb2)
        self.assertEqual(tk2.user, tk1.user)
        self.assertEqual(tk2.token, tk1.token)
        self.assertEqual(tk2.expiry, tk1.expiry)

    def test_token_model_null_token(self):
        dt = date_utils.get_datetime_utc_now()
        tk = TokenAPI(user="stanley", token=None, expiry=isotime.format(dt))
        self.assertRaises(ValueError, Token.add_or_update, TokenAPI.to_model(tk))

    def test_token_model_null_user(self):
        dt = date_utils.get_datetime_utc_now()
        tk = TokenAPI(user=None, token=uuid.uuid4().hex, expiry=isotime.format(dt))
        self.assertRaises(ValueError, Token.add_or_update, TokenAPI.to_model(tk))

    def test_token_model_null_expiry(self):
        tk = TokenAPI(user="stanley", token=uuid.uuid4().hex, expiry=None)
        self.assertRaises(ValueError, Token.add_or_update, TokenAPI.to_model(tk))

    def _test_token_post(self, path=TOKEN_V1_PATH):
        ttl = cfg.CONF.auth.token_ttl
        timestamp = date_utils.get_datetime_utc_now()
        response = self.app.post_json(path, {}, expect_errors=False)
        expected_expiry = date_utils.get_datetime_utc_now() + datetime.timedelta(
            seconds=ttl
        )
        expected_expiry = date_utils.add_utc_tz(expected_expiry)
        self.assertEqual(response.status_int, 201)
        self.assertIsNotNone(response.json["token"])
        self.assertEqual(response.json["user"], USERNAME)
        actual_expiry = isotime.parse(response.json["expiry"])
        self.assertLess(timestamp, actual_expiry)
        self.assertLess(actual_expiry, expected_expiry)
        return response

    def test_token_post_proxy_user(self):
        headers = {"X-Forwarded-For": "192.0.2.1", "X-Forwarded-User": "testuser"}
        response = self.app.post_json(
            TOKEN_V1_PATH,
            {},
            headers=headers,
            expect_errors=False,
            extra_environ={"REMOTE_USER": ""},
        )
        self.assertEqual(response.status_int, 201)
        self.assertIsNotNone(response.json["token"])
        self.assertEqual(response.json["user"], "testuser")

    def test_token_post_unauthorized(self):
        response = self.app.post_json(
            TOKEN_V1_PATH, {}, expect_errors=True, extra_environ={"REMOTE_USER": ""}
        )
        self.assertEqual(response.status_int, 401)

    @mock.patch.object(User, "get_by_name", mock.MagicMock(side_effect=Exception()))
    @mock.patch.object(
        User, "add_or_update", mock.Mock(return_value=UserDB(name=USERNAME))
    )
    def test_token_post_new_user(self):
        self._test_token_post()

    @mock.patch.object(
        User, "get_by_name", mock.MagicMock(return_value=UserDB(name=USERNAME))
    )
    def test_token_post_existing_user(self):
        self._test_token_post()

    @mock.patch.object(
        User, "get_by_name", mock.MagicMock(return_value=UserDB(name=USERNAME))
    )
    def test_token_post_success_x_api_url_header_value(self):
        # auth.api_url option is explicitly set
        cfg.CONF.set_override("api_url", override="https://example.com", group="auth")

        resp = self._test_token_post()
        self.assertEqual(resp.headers["X-API-URL"], "https://example.com")

        # auth.api_url option is not set, url is inferred from listen host and port
        cfg.CONF.set_override("api_url", override=None, group="auth")

        resp = self._test_token_post()
        self.assertEqual(resp.headers["X-API-URL"], "http://127.0.0.1:9101")

    @mock.patch.object(
        User, "get_by_name", mock.MagicMock(return_value=UserDB(name=USERNAME))
    )
    def test_token_post_default_url_path(self):
        self._test_token_post(path=TOKEN_DEFAULT_PATH)

    @mock.patch.object(
        User, "get_by_name", mock.MagicMock(return_value=UserDB(name=USERNAME))
    )
    def test_token_post_set_ttl(self):
        timestamp = date_utils.add_utc_tz(date_utils.get_datetime_utc_now())
        response = self.app.post_json(TOKEN_V1_PATH, {"ttl": 60}, expect_errors=False)
        expected_expiry = date_utils.get_datetime_utc_now() + datetime.timedelta(
            seconds=60
        )
        self.assertEqual(response.status_int, 201)
        actual_expiry = isotime.parse(response.json["expiry"])
        self.assertLess(timestamp, actual_expiry)
        self.assertLess(actual_expiry, expected_expiry)

    @mock.patch.object(
        User, "get_by_name", mock.MagicMock(return_value=UserDB(name=USERNAME))
    )
    def test_token_post_no_data_in_body_text_plain_context_type_used(self):
        response = self.app.post(
            TOKEN_V1_PATH, expect_errors=False, content_type="text/plain"
        )
        self.assertEqual(response.status_int, 201)

    @mock.patch.object(
        User, "get_by_name", mock.MagicMock(return_value=UserDB(name=USERNAME))
    )
    def test_token_post_set_ttl_over_policy(self):
        ttl = cfg.CONF.auth.token_ttl
        response = self.app.post_json(
            TOKEN_V1_PATH, {"ttl": ttl + 60}, expect_errors=True
        )
        self.assertEqual(response.status_int, 400)
        message = "TTL specified %s is greater than max allowed %s." % (ttl + 60, ttl)
        self.assertEqual(response.json["faultstring"], message)

    @mock.patch.object(
        User, "get_by_name", mock.MagicMock(return_value=UserDB(name=USERNAME))
    )
    def test_token_post_set_bad_ttl(self):
        response = self.app.post_json(TOKEN_V1_PATH, {"ttl": -1}, expect_errors=True)
        self.assertEqual(response.status_int, 400)
        response = self.app.post_json(TOKEN_V1_PATH, {"ttl": 0}, expect_errors=True)
        self.assertEqual(response.status_int, 400)

    @mock.patch.object(
        User, "get_by_name", mock.MagicMock(return_value=UserDB(name=USERNAME))
    )
    def test_token_get_unauthorized(self):
        # Create a new token.
        response = self.app.post_json(TOKEN_V1_PATH, expect_errors=False)

        # Verify the token. 401 is expected because an API key or token is not provided in header.
        data = {"token": str(response.json["token"])}
        response = self.app.post_json(TOKEN_VERIFY_PATH, data, expect_errors=True)
        self.assertEqual(response.status_int, 401)

    @mock.patch.object(
        User, "get_by_name", mock.MagicMock(return_value=UserDB(name=USERNAME))
    )
    def test_token_get_unauthorized_bad_api_key(self):
        # Create a new token.
        response = self.app.post_json(TOKEN_V1_PATH, expect_errors=False)

        # Verify the token. 401 is expected because the API key is bad.
        headers = {"St2-Api-Key": "foobar"}
        data = {"token": str(response.json["token"])}
        response = self.app.post_json(
            TOKEN_VERIFY_PATH, data, headers=headers, expect_errors=True
        )
        self.assertEqual(response.status_int, 401)

    @mock.patch.object(
        User, "get_by_name", mock.MagicMock(return_value=UserDB(name=USERNAME))
    )
    def test_token_get_unauthorized_bad_token(self):
        # Create a new token.
        response = self.app.post_json(TOKEN_V1_PATH, expect_errors=False)

        # Verify the token. 401 is expected because the token is bad.
        headers = {"X-Auth-Token": "foobar"}
        data = {"token": str(response.json["token"])}
        response = self.app.post_json(
            TOKEN_VERIFY_PATH, data, headers=headers, expect_errors=True
        )
        self.assertEqual(response.status_int, 401)

    @mock.patch.object(
        User, "get_by_name", mock.MagicMock(return_value=UserDB(name=USERNAME))
    )
    @mock.patch.object(
        ApiKey,
        "get",
        mock.MagicMock(return_value=ApiKeyDB(user=USERNAME, key_hash="foobar")),
    )
    def test_token_get_auth_with_api_key(self):
        # Create a new token.
        response = self.app.post_json(TOKEN_V1_PATH, expect_errors=False)

        # Verify the token. Use an API key to authenticate with the st2 auth get token endpoint.
        headers = {"St2-Api-Key": "foobar"}
        data = {"token": str(response.json["token"])}
        response = self.app.post_json(
            TOKEN_VERIFY_PATH, data, headers=headers, expect_errors=True
        )
        self.assertEqual(response.status_int, 200)
        self.assertTrue(response.json["valid"])

    @mock.patch.object(
        User, "get_by_name", mock.MagicMock(return_value=UserDB(name=USERNAME))
    )
    def test_token_get_auth_with_token(self):
        # Create a new token.
        response = self.app.post_json(TOKEN_V1_PATH, {}, expect_errors=False)

        # Verify the token. Use a token to authenticate with the st2 auth get token endpoint.
        headers = {"X-Auth-Token": str(response.json["token"])}
        data = {"token": str(response.json["token"])}
        response = self.app.post_json(
            TOKEN_VERIFY_PATH, data, headers=headers, expect_errors=True
        )
        self.assertEqual(response.status_int, 200)
        self.assertTrue(response.json["valid"])

    @mock.patch.object(
        User, "get_by_name", mock.MagicMock(return_value=UserDB(name=USERNAME))
    )
    @mock.patch.object(
        ApiKey,
        "get",
        mock.MagicMock(return_value=ApiKeyDB(user=USERNAME, key_hash="foobar")),
    )
    @mock.patch.object(
        Token,
        "get",
        mock.MagicMock(
            return_value=TokenDB(
                user=USERNAME,
                token="12345",
                expiry=date_utils.get_datetime_utc_now()
                - datetime.timedelta(minutes=1),
            )
        ),
    )
    def test_token_get_unauthorized_bad_ttl(self):
        # Verify the token. 400 is expected because the token has expired.
        headers = {"St2-Api-Key": "foobar"}
        data = {"token": "12345"}
        response = self.app.post_json(
            TOKEN_VERIFY_PATH, data, headers=headers, expect_errors=False
        )
        self.assertEqual(response.status_int, 200)
        self.assertFalse(response.json["valid"])

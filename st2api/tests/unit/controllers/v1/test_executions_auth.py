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

import bson
import copy
import datetime
import mock
import uuid

try:
    import simplejson as json
except ImportError:
    import json

import st2common.validators.api.action as action_validator
from st2common.constants.keyvalue import FULL_USER_SCOPE
from st2common.models.api.keyvalue import KeyValuePairAPI
from st2common.models.db.auth import TokenDB
from st2common.models.db.auth import UserDB
from st2common.models.db.auth import ApiKeyDB
from st2common.models.db.keyvalue import KeyValuePairDB
from st2common.persistence.auth import Token
from st2common.persistence.auth import User
from st2common.persistence.auth import ApiKey
from st2common.persistence.keyvalue import KeyValuePair
from st2common.transport.publishers import PoolPublisher
from st2common.util import crypto as crypto_utils
from st2common.util import date as date_utils
from st2tests.api import SUPER_SECRET_PARAMETER
from st2tests.fixtures.generic.fixture import PACK_NAME as FIXTURES_PACK
from st2tests.fixturesloader import FixturesLoader
from st2tests.api import FunctionalTest


ACTION_1 = {
    "name": "st2.dummy.action1",
    "description": "test description",
    "enabled": True,
    "entry_point": "/tmp/test/action1.sh",
    "pack": "sixpack",
    "runner_type": "remote-shell-cmd",
    "parameters": {
        "a": {"type": "string", "default": "abc"},
        "b": {"type": "number", "default": 123},
        "c": {"type": "number", "default": 123, "immutable": True},
        "d": {"type": "string", "secret": True},
    },
}
ACTION_DEFAULT_ENCRYPT = {
    "name": "st2.dummy.default_encrypted_value",
    "description": "An action that uses a jinja template with decrypt_kv filter "
    "in default parameter",
    "enabled": True,
    "pack": "starterpack",
    "runner_type": "local-shell-cmd",
    "parameters": {
        "encrypted_param": {
            "type": "string",
            "default": "{{ st2kv.system.secret | decrypt_kv }}",
        },
        "encrypted_user_param": {
            "type": "string",
            "default": "{{ st2kv.user.secret | decrypt_kv }}",
        },
    },
}

LIVE_ACTION_1 = {
    "action": "sixpack.st2.dummy.action1",
    "parameters": {
        "hosts": "localhost",
        "cmd": "uname -a",
        "d": SUPER_SECRET_PARAMETER,
    },
}
LIVE_ACTION_DEFAULT_ENCRYPT = {
    "action": "starterpack.st2.dummy.default_encrypted_value",
}

# NOTE: We use a longer expiry time because this variable is initialized on module import (aka
# when nosetests or similar imports this module before running the tests.
# Depending on when the import happens and when the tests actually run, token could already expire
# by that time and the tests would fail.
NOW = date_utils.get_datetime_utc_now()
EXPIRY = NOW + datetime.timedelta(seconds=1000)
SYS_TOKEN = TokenDB(
    id=bson.ObjectId(), user="system", token=uuid.uuid4().hex, expiry=EXPIRY
)
USR_TOKEN = TokenDB(
    id=bson.ObjectId(), user="tokenuser", token=uuid.uuid4().hex, expiry=EXPIRY
)

FIXTURES = {"users": ["system_user.yaml", "token_user.yaml"]}

# These parameters are used for the tests of getting value from datastore and decrypting it at
# Jinja expression in a action metadata definition.
TEST_USER = UserDB(name="user1")
TEST_TOKEN = TokenDB(
    id=bson.ObjectId(), user=TEST_USER, token=uuid.uuid4().hex, expiry=EXPIRY
)
TEST_APIKEY = ApiKeyDB(user=TEST_USER, key_hash="secret_key", enabled=True)


def mock_get_token(*args, **kwargs):
    if args[0] == SYS_TOKEN.token:
        return SYS_TOKEN
    return USR_TOKEN


def mock_get_by_name(name):
    return UserDB(name=name)


@mock.patch.object(PoolPublisher, "publish", mock.MagicMock())
class ActionExecutionControllerTestCaseAuthEnabled(FunctionalTest):

    enable_auth = True

    @classmethod
    @mock.patch.object(Token, "get", mock.MagicMock(side_effect=mock_get_token))
    @mock.patch.object(User, "get_by_name", mock.MagicMock(return_value=TEST_USER))
    @mock.patch.object(
        action_validator, "validate_action", mock.MagicMock(return_value=True)
    )
    def setUpClass(cls):
        super(ActionExecutionControllerTestCaseAuthEnabled, cls).setUpClass()
        cls.action = copy.deepcopy(ACTION_1)
        headers = {
            "content-type": "application/json",
            "X-Auth-Token": str(SYS_TOKEN.token),
        }
        post_resp = cls.app.post_json("/v1/actions", cls.action, headers=headers)
        cls.action["id"] = post_resp.json["id"]

        cls.action_encrypt = copy.deepcopy(ACTION_DEFAULT_ENCRYPT)
        post_resp = cls.app.post_json(
            "/v1/actions", cls.action_encrypt, headers=headers
        )
        cls.action_encrypt["id"] = post_resp.json["id"]

        FixturesLoader().save_fixtures_to_db(
            fixtures_pack=FIXTURES_PACK, fixtures_dict=FIXTURES
        )

        # register datastore values which are used in this tests
        KeyValuePairAPI._setup_crypto()
        register_items = [
            {
                "name": "secret",
                "secret": True,
                "value": crypto_utils.symmetric_encrypt(
                    KeyValuePairAPI.crypto_key, "foo"
                ),
            },
            {
                "name": "user1:secret",
                "secret": True,
                "scope": FULL_USER_SCOPE,
                "value": crypto_utils.symmetric_encrypt(
                    KeyValuePairAPI.crypto_key, "bar"
                ),
            },
        ]
        cls.kvps = [
            KeyValuePair.add_or_update(KeyValuePairDB(**x)) for x in register_items
        ]

    @classmethod
    @mock.patch.object(Token, "get", mock.MagicMock(side_effect=mock_get_token))
    def tearDownClass(cls):
        headers = {
            "content-type": "application/json",
            "X-Auth-Token": str(SYS_TOKEN.token),
        }
        cls.app.delete("/v1/actions/%s" % cls.action["id"], headers=headers)
        cls.app.delete("/v1/actions/%s" % cls.action_encrypt["id"], headers=headers)

        # unregister key-value pairs for tests
        [KeyValuePair.delete(x) for x in cls.kvps]

        super(ActionExecutionControllerTestCaseAuthEnabled, cls).tearDownClass()

    def _do_post(self, liveaction, *args, **kwargs):
        return self.app.post_json("/v1/executions", liveaction, *args, **kwargs)

    @mock.patch.object(Token, "get", mock.MagicMock(side_effect=mock_get_token))
    def test_post_with_st2_context_in_headers(self):
        headers = {
            "content-type": "application/json",
            "X-Auth-Token": str(USR_TOKEN.token),
        }
        resp = self._do_post(copy.deepcopy(LIVE_ACTION_1), headers=headers)
        self.assertEqual(resp.status_int, 201)
        token_user = resp.json["context"]["user"]
        self.assertEqual(token_user, "tokenuser")
        context = {"parent": {"execution_id": str(resp.json["id"]), "user": token_user}}
        headers = {
            "content-type": "application/json",
            "X-Auth-Token": str(SYS_TOKEN.token),
            "st2-context": json.dumps(context),
        }
        resp = self._do_post(copy.deepcopy(LIVE_ACTION_1), headers=headers)
        self.assertEqual(resp.status_int, 201)
        self.assertEqual(resp.json["context"]["user"], "tokenuser")
        self.assertEqual(resp.json["context"]["parent"], context["parent"])

    @mock.patch.object(ApiKey, "get", mock.Mock(return_value=TEST_APIKEY))
    @mock.patch.object(User, "get_by_name", mock.Mock(return_value=TEST_USER))
    def test_template_encrypted_params_with_apikey(self):
        resp = self._do_post(
            LIVE_ACTION_DEFAULT_ENCRYPT, headers={"St2-Api-key": "secret_key"}
        )
        self.assertEqual(resp.status_int, 201)
        self.assertEqual(resp.json["parameters"]["encrypted_param"], "foo")
        self.assertEqual(resp.json["parameters"]["encrypted_user_param"], "bar")

    @mock.patch.object(Token, "get", mock.Mock(return_value=TEST_TOKEN))
    @mock.patch.object(User, "get_by_name", mock.Mock(return_value=TEST_USER))
    def test_template_encrypted_params_with_access_token(self):
        resp = self._do_post(
            LIVE_ACTION_DEFAULT_ENCRYPT, headers={"X-Auth-Token": str(TEST_TOKEN.token)}
        )
        self.assertEqual(resp.status_int, 201)
        self.assertEqual(resp.json["parameters"]["encrypted_param"], "foo")
        self.assertEqual(resp.json["parameters"]["encrypted_user_param"], "bar")

    def test_template_encrypted_params_without_auth(self):
        resp = self._do_post(LIVE_ACTION_DEFAULT_ENCRYPT, expect_errors=True)

        self.assertEqual(resp.status_int, 401)
        self.assertEqual(
            resp.json["faultstring"], "Unauthorized - One of Token or API key required."
        )

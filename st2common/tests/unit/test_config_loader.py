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

from __future__ import absolute_import
from st2common.persistence.pack import Config
from st2common.models.db.pack import ConfigDB
from st2common.models.db.keyvalue import KeyValuePairDB
from st2common.exceptions.db import StackStormDBObjectNotFoundError
from st2common.persistence.keyvalue import KeyValuePair
from st2common.models.api.keyvalue import KeyValuePairAPI
from st2common.services.config import set_datastore_value_for_config_key
from st2common.util.config_loader import ContentPackConfigLoader
from st2common.util import crypto

from st2tests.base import CleanDbTestCase
from st2tests.fixtures.packs.dummy_pack_1.fixture import PACK_NAME as DUMMY_PACK_1
from st2tests.fixtures.packs.dummy_pack_4.fixture import PACK_NAME as DUMMY_PACK_4
from st2tests.fixtures.packs.dummy_pack_5.fixture import PACK_NAME as DUMMY_PACK_5
from st2tests.fixtures.packs.dummy_pack_17.fixture import PACK_DIR_NAME as DUMMY_PACK_17
from st2tests.fixtures.packs.dummy_pack_schema_with_additional_items_1.fixture import (
    PACK_NAME as DUMMY_PACK_SCHEMA_WITH_ADDITIONAL_ITEMS_1,
)
from st2tests.fixtures.packs.dummy_pack_schema_with_additional_properties_1.fixture import (
    PACK_NAME as DUMMY_PACK_SCHEMA_WITH_ADDITIONAL_PROPERTIES_1,
)
from st2tests.fixtures.packs.dummy_pack_schema_with_nested_object_1.fixture import (
    PACK_NAME as DUMMY_PACK_SCHEMA_WITH_NESTED_OBJECT_1,
)
from st2tests.fixtures.packs.dummy_pack_schema_with_nested_object_2.fixture import (
    PACK_NAME as DUMMY_PACK_SCHEMA_WITH_NESTED_OBJECT_2,
)
from st2tests.fixtures.packs.dummy_pack_schema_with_nested_object_3.fixture import (
    PACK_NAME as DUMMY_PACK_SCHEMA_WITH_NESTED_OBJECT_3,
)
from st2tests.fixtures.packs.dummy_pack_schema_with_nested_object_4.fixture import (
    PACK_NAME as DUMMY_PACK_SCHEMA_WITH_NESTED_OBJECT_4,
)
from st2tests.fixtures.packs.dummy_pack_schema_with_nested_object_5.fixture import (
    PACK_NAME as DUMMY_PACK_SCHEMA_WITH_NESTED_OBJECT_5,
)
from st2tests.fixtures.packs.dummy_pack_schema_with_pattern_and_additional_properties_1.fixture import (
    PACK_NAME as DUMMY_PACK_SCHEMA_WITH_PATTERN_AND_ADDITIONAL_PROPERTIES_1,
)
from st2tests.fixtures.packs.dummy_pack_schema_with_pattern_properties_1.fixture import (
    PACK_NAME as DUMMY_PACK_SCHEMA_WITH_PATTERN_PROPERTIES_1,
)

__all__ = ["ContentPackConfigLoaderTestCase"]


class ContentPackConfigLoaderTestCase(CleanDbTestCase):
    register_packs = True
    register_pack_configs = True

    def test_ensure_local_pack_config_feature_removed(self):
        # Test a scenario where all the values are loaded from pack local
        # config and pack global config (pack name.yaml) doesn't exist.
        # Test a scenario where no values are overridden in the datastore
        loader = ContentPackConfigLoader(pack_name=DUMMY_PACK_4)
        config = loader.get_config()
        expected_config = {}

        self.assertDictEqual(config, expected_config)

    def test_get_config_some_values_overriden_in_datastore(self):
        # Test a scenario where some values are overriden in datastore via pack
        # global config
        kvp_db = set_datastore_value_for_config_key(
            pack_name=DUMMY_PACK_5,
            key_name="api_secret",
            value="some_api_secret",
            secret=True,
            user="joe",
        )

        # This is a secret so a value should be encrypted
        self.assertTrue(kvp_db.value != "some_api_secret")
        self.assertTrue(len(kvp_db.value) > len("some_api_secret") * 2)
        self.assertTrue(kvp_db.secret)

        kvp_db = set_datastore_value_for_config_key(
            pack_name=DUMMY_PACK_5,
            key_name="private_key_path",
            value="some_private_key",
        )
        self.assertEqual(kvp_db.value, "some_private_key")
        self.assertFalse(kvp_db.secret)

        loader = ContentPackConfigLoader(pack_name=DUMMY_PACK_5, user="joe")
        config = loader.get_config()

        # regions is provided in the pack global config
        # api_secret is dynamically loaded from the datastore for a particular user
        expected_config = {
            "api_key": "some_api_key",
            "api_secret": "some_api_secret",
            "regions": ["us-west-1"],
            "region": "default-region-value",
            "private_key_path": "some_private_key",
            "non_required_with_default_value": "config value",
        }

        self.assertEqual(config, expected_config)

    def test_get_config_default_value_from_config_schema_is_used(self):
        # No value is provided for "region" in the config, default value from config schema
        # should be used
        loader = ContentPackConfigLoader(pack_name=DUMMY_PACK_5)
        config = loader.get_config()
        self.assertEqual(config["region"], "default-region-value")

        # Here a default value is specified in schema but an explicit value is provided in the
        # config
        loader = ContentPackConfigLoader(pack_name=DUMMY_PACK_1)
        config = loader.get_config()
        self.assertEqual(config["region"], "us-west-1")

        # Config item attribute has required: false
        # Value is provided in the config - it should be used as provided
        pack_name = DUMMY_PACK_5

        loader = ContentPackConfigLoader(pack_name=pack_name)
        config = loader.get_config()
        self.assertEqual(config["non_required_with_default_value"], "config value")

        config_db = Config.get_by_pack(pack_name)
        del config_db["values"]["non_required_with_default_value"]
        Config.add_or_update(config_db)

        # No value in the config - default value should be used
        config_db = Config.get_by_pack(pack_name)
        config_db.delete()

        # No config exists for that pack - default value should be used
        loader = ContentPackConfigLoader(pack_name=pack_name)
        config = loader.get_config()
        self.assertEqual(
            config["non_required_with_default_value"], "some default value"
        )

    def test_default_values_from_schema_are_used_when_no_config_exists(self):
        pack_name = DUMMY_PACK_5
        config_db = Config.get_by_pack(pack_name)

        # Delete the existing config loaded in setUp
        config_db = Config.get_by_pack(pack_name)
        config_db.delete()

        # Verify config has been deleted from the database
        self.assertRaises(
            StackStormDBObjectNotFoundError, Config.get_by_pack, pack_name
        )

        loader = ContentPackConfigLoader(pack_name=pack_name)
        config = loader.get_config()
        self.assertEqual(config["region"], "default-region-value")

    def test_default_values_are_used_when_default_values_are_falsey(self):
        pack_name = DUMMY_PACK_17

        loader = ContentPackConfigLoader(pack_name=pack_name)
        config = loader.get_config()

        # 1. Default values are used
        self.assertEqual(config["key_with_default_falsy_value_1"], False)
        self.assertEqual(config["key_with_default_falsy_value_2"], None)
        self.assertEqual(config["key_with_default_falsy_value_3"], {})
        self.assertEqual(config["key_with_default_falsy_value_4"], "")
        self.assertEqual(config["key_with_default_falsy_value_5"], 0)
        self.assertEqual(config["key_with_default_falsy_value_6"]["key_1"], False)
        self.assertEqual(config["key_with_default_falsy_value_6"]["key_2"], 0)

        # 2. Default values are overwrriten with config values which are also falsey
        values = {
            "key_with_default_falsy_value_1": 0,
            "key_with_default_falsy_value_2": "",
            "key_with_default_falsy_value_3": False,
            "key_with_default_falsy_value_4": None,
            "key_with_default_falsy_value_5": {},
            "key_with_default_falsy_value_6": {"key_2": False},
        }
        config_db = ConfigDB(pack=pack_name, values=values)
        config_db = Config.add_or_update(config_db)

        loader = ContentPackConfigLoader(pack_name=pack_name)
        config = loader.get_config()

        self.assertEqual(config["key_with_default_falsy_value_1"], 0)
        self.assertEqual(config["key_with_default_falsy_value_2"], "")
        self.assertEqual(config["key_with_default_falsy_value_3"], False)
        self.assertEqual(config["key_with_default_falsy_value_4"], None)
        self.assertEqual(config["key_with_default_falsy_value_5"], {})
        self.assertEqual(config["key_with_default_falsy_value_6"]["key_1"], False)
        self.assertEqual(config["key_with_default_falsy_value_6"]["key_2"], False)

    def test_get_config_nested_schema_default_values_from_config_schema_are_used(self):
        # Special case for more complex config schemas with attributes ntesting.
        # Validate that the default values are also used for one level nested object properties.
        pack_name = DUMMY_PACK_SCHEMA_WITH_NESTED_OBJECT_1

        # 1. None of the nested object values are provided
        loader = ContentPackConfigLoader(pack_name=pack_name)
        config = loader.get_config()

        expected_config = {
            "api_key": "",
            "api_secret": "",
            "regions": ["us-west-1", "us-east-1"],
            "auth_settings": {
                "host": "127.0.0.3",
                "port": 8080,
                "device_uids": ["a", "b", "c"],
            },
        }
        self.assertEqual(config, expected_config)

        # 2. Some of the nested object values are provided (host, port)
        pack_name = DUMMY_PACK_SCHEMA_WITH_NESTED_OBJECT_2

        loader = ContentPackConfigLoader(pack_name=pack_name)
        config = loader.get_config()

        expected_config = {
            "api_key": "",
            "api_secret": "",
            "regions": ["us-west-1", "us-east-1"],
            "auth_settings": {
                "host": "127.0.0.6",
                "port": 9090,
                "device_uids": ["a", "b", "c"],
            },
        }
        self.assertEqual(config, expected_config)

        # 3. Nested attribute (auth_settings.token) references a non-secret datastore value
        pack_name = DUMMY_PACK_SCHEMA_WITH_NESTED_OBJECT_3

        kvp_db = set_datastore_value_for_config_key(
            pack_name=pack_name,
            key_name="auth_settings_token",
            value="some_auth_settings_token",
        )
        self.assertEqual(kvp_db.value, "some_auth_settings_token")
        self.assertFalse(kvp_db.secret)

        loader = ContentPackConfigLoader(pack_name=pack_name)
        config = loader.get_config()

        expected_config = {
            "api_key": "",
            "api_secret": "",
            "regions": ["us-west-1", "us-east-1"],
            "auth_settings": {
                "host": "127.0.0.10",
                "port": 8080,
                "device_uids": ["a", "b", "c"],
                "token": "some_auth_settings_token",
            },
        }
        self.assertEqual(config, expected_config)

        # 4. Nested attribute (auth_settings.token) references a secret datastore value
        pack_name = DUMMY_PACK_SCHEMA_WITH_NESTED_OBJECT_4

        kvp_db = set_datastore_value_for_config_key(
            pack_name=pack_name,
            key_name="auth_settings_token",
            value="joe_token_secret",
            secret=True,
            user="joe",
        )
        self.assertTrue(kvp_db.value != "joe_token_secret")
        self.assertTrue(len(kvp_db.value) > len("joe_token_secret") * 2)
        self.assertTrue(kvp_db.secret)

        kvp_db = set_datastore_value_for_config_key(
            pack_name=pack_name,
            key_name="auth_settings_token",
            value="alice_token_secret",
            secret=True,
            user="alice",
        )
        self.assertTrue(kvp_db.value != "alice_token_secret")
        self.assertTrue(len(kvp_db.value) > len("alice_token_secret") * 2)
        self.assertTrue(kvp_db.secret)

        loader = ContentPackConfigLoader(pack_name=pack_name, user="joe")
        config = loader.get_config()

        expected_config = {
            "api_key": "",
            "api_secret": "",
            "regions": ["us-west-1", "us-east-1"],
            "auth_settings": {
                "host": "127.0.0.11",
                "port": 8080,
                "device_uids": ["a", "b", "c"],
                "token": "joe_token_secret",
            },
        }
        self.assertEqual(config, expected_config)

        loader = ContentPackConfigLoader(pack_name=pack_name, user="alice")
        config = loader.get_config()

        expected_config = {
            "api_key": "",
            "api_secret": "",
            "regions": ["us-west-1", "us-east-1"],
            "auth_settings": {
                "host": "127.0.0.11",
                "port": 8080,
                "device_uids": ["a", "b", "c"],
                "token": "alice_token_secret",
            },
        }
        self.assertEqual(config, expected_config)

    def test_get_config_dynamic_config_item_render_fails_user_friendly_exception_is_thrown(
        self,
    ):
        pack_name = DUMMY_PACK_SCHEMA_WITH_NESTED_OBJECT_5
        loader = ContentPackConfigLoader(pack_name=pack_name)

        # Render fails on top-level item
        values = {"level0_key": "{{st2kvXX.invalid}}"}
        config_db = ConfigDB(pack=pack_name, values=values)
        config_db = Config.add_or_update(config_db)

        expected_msg = (
            'Failed to render dynamic configuration value for key "level0_key" with '
            'value "{{st2kvXX.invalid}}" for pack ".*?" config: '
            "<class 'jinja2.exceptions.UndefinedError'> "
            "'st2kvXX' is undefined"
        )
        self.assertRaisesRegex(RuntimeError, expected_msg, loader.get_config)
        config_db.delete()

        # Renders fails on fist level item
        values = {"level0_object": {"level1_key": "{{st2kvXX.invalid}}"}}
        config_db = ConfigDB(pack=pack_name, values=values)
        Config.add_or_update(config_db)

        expected_msg = (
            "Failed to render dynamic configuration value for key "
            '"level0_object.level1_key" with value "{{st2kvXX.invalid}}"'
            " for pack \".*?\" config: <class 'jinja2.exceptions.UndefinedError'>"
            " 'st2kvXX' is undefined"
        )
        self.assertRaisesRegex(RuntimeError, expected_msg, loader.get_config)
        config_db.delete()

        # Renders fails on second level item
        values = {
            "level0_object": {"level1_object": {"level2_key": "{{st2kvXX.invalid}}"}}
        }
        config_db = ConfigDB(pack=pack_name, values=values)
        Config.add_or_update(config_db)

        expected_msg = (
            "Failed to render dynamic configuration value for key "
            '"level0_object.level1_object.level2_key" with value "{{st2kvXX.invalid}}"'
            " for pack \".*?\" config: <class 'jinja2.exceptions.UndefinedError'>"
            " 'st2kvXX' is undefined"
        )
        self.assertRaisesRegex(RuntimeError, expected_msg, loader.get_config)
        config_db.delete()

        # Renders fails on list item
        values = {"level0_object": ["abc", "{{st2kvXX.invalid}}"]}
        config_db = ConfigDB(pack=pack_name, values=values)
        Config.add_or_update(config_db)

        expected_msg = (
            "Failed to render dynamic configuration value for key "
            '"level0_object.1" with value "{{st2kvXX.invalid}}"'
            " for pack \".*?\" config: <class 'jinja2.exceptions.UndefinedError'>"
            " 'st2kvXX' is undefined"
        )
        self.assertRaisesRegex(RuntimeError, expected_msg, loader.get_config)
        config_db.delete()

        # Renders fails on nested object in list item
        values = {"level0_object": [{"level2_key": "{{st2kvXX.invalid}}"}]}
        config_db = ConfigDB(pack=pack_name, values=values)
        Config.add_or_update(config_db)

        expected_msg = (
            "Failed to render dynamic configuration value for key "
            '"level0_object.0.level2_key" with value "{{st2kvXX.invalid}}"'
            " for pack \".*?\" config: <class 'jinja2.exceptions.UndefinedError'>"
            " 'st2kvXX' is undefined"
        )
        self.assertRaisesRegex(RuntimeError, expected_msg, loader.get_config)
        config_db.delete()

        # Renders fails on invalid syntax
        values = {"level0_key": "{{ this is some invalid Jinja }}"}
        config_db = ConfigDB(pack=pack_name, values=values)
        Config.add_or_update(config_db)

        expected_msg = (
            "Failed to render dynamic configuration value for key "
            '"level0_key" with value "{{ this is some invalid Jinja }}"'
            " for pack \".*?\" config: <class 'jinja2.exceptions.TemplateSyntaxError'>"
            " expected token 'end of print statement', got 'Jinja'"
        )
        self.assertRaisesRegex(RuntimeError, expected_msg, loader.get_config)
        config_db.delete()

    def test_get_config_dynamic_config_item(self):
        pack_name = "dummy_pack_schema_with_nested_object_6"
        loader = ContentPackConfigLoader(pack_name=pack_name)

        ####################
        # value in top level item
        KeyValuePair.add_or_update(KeyValuePairDB(name="k1", value="v1"))
        values = {"level0_key": "{{st2kv.system.k1}}"}
        config_db = ConfigDB(pack=pack_name, values=values)
        config_db = Config.add_or_update(config_db)

        config_rendered = loader.get_config()

        self.assertEqual(config_rendered, {"level0_key": "v1"})

        config_db.delete()

    def test_get_config_dynamic_config_item_nested_dict(self):
        pack_name = "dummy_pack_schema_with_nested_object_7"
        loader = ContentPackConfigLoader(pack_name=pack_name)

        KeyValuePair.add_or_update(KeyValuePairDB(name="k0", value="v0"))
        KeyValuePair.add_or_update(KeyValuePairDB(name="k1", value="v1"))
        KeyValuePair.add_or_update(KeyValuePairDB(name="k2", value="v2"))

        ####################
        # values nested dictionaries
        values = {
            "level0_key": "{{st2kv.system.k0}}",
            "level0_object": {
                "level1_key": "{{st2kv.system.k1}}",
                "level1_object": {"level2_key": "{{st2kv.system.k2}}"},
            },
        }
        config_db = ConfigDB(pack=pack_name, values=values)
        config_db = Config.add_or_update(config_db)

        config_rendered = loader.get_config()

        self.assertEqual(
            config_rendered,
            {
                "level0_key": "v0",
                "level0_object": {
                    "level1_key": "v1",
                    "level1_object": {"level2_key": "v2"},
                },
            },
        )

        config_db.delete()

    def test_get_config_dynamic_config_item_list(self):
        pack_name = "dummy_pack_schema_with_nested_object_7"
        loader = ContentPackConfigLoader(pack_name=pack_name)

        KeyValuePair.add_or_update(KeyValuePairDB(name="k0", value="v0"))
        KeyValuePair.add_or_update(KeyValuePairDB(name="k1", value="v1"))

        ####################
        # values in list
        values = {
            "level0_key": [
                "a",
                "{{st2kv.system.k0}}",
                "b",
                "{{st2kv.system.k1}}",
            ]
        }
        config_db = ConfigDB(pack=pack_name, values=values)
        config_db = Config.add_or_update(config_db)

        config_rendered = loader.get_config()

        self.assertEqual(config_rendered, {"level0_key": ["a", "v0", "b", "v1"]})

        config_db.delete()

    def test_get_config_dynamic_config_item_nested_list(self):
        pack_name = "dummy_pack_schema_with_nested_object_8"
        loader = ContentPackConfigLoader(pack_name=pack_name)

        KeyValuePair.add_or_update(KeyValuePairDB(name="k0", value="v0"))
        KeyValuePair.add_or_update(KeyValuePairDB(name="k1", value="v1"))
        KeyValuePair.add_or_update(KeyValuePairDB(name="k2", value="v2"))

        ####################
        # values in objects embedded in lists and nested lists
        values = {
            "level0_key": [
                {"level1_key0": "{{st2kv.system.k0}}"},
                "{{st2kv.system.k1}}",
                [
                    "{{st2kv.system.k0}}",
                    "{{st2kv.system.k1}}",
                    "{{st2kv.system.k2}}",
                ],
                {
                    "level1_key2": [
                        "{{st2kv.system.k2}}",
                    ]
                },
            ]
        }
        config_db = ConfigDB(pack=pack_name, values=values)
        config_db = Config.add_or_update(config_db)

        config_rendered = loader.get_config()

        self.assertEqual(
            config_rendered,
            {
                "level0_key": [
                    {"level1_key0": "v0"},
                    "v1",
                    [
                        "v0",
                        "v1",
                        "v2",
                    ],
                    {
                        "level1_key2": [
                            "v2",
                        ]
                    },
                ]
            },
        )

        config_db.delete()

    def test_get_config_dynamic_config_item_under_additional_properties(self):
        pack_name = DUMMY_PACK_SCHEMA_WITH_ADDITIONAL_PROPERTIES_1
        loader = ContentPackConfigLoader(pack_name=pack_name)

        encrypted_value = crypto.symmetric_encrypt(
            KeyValuePairAPI.crypto_key, "v1_encrypted"
        )
        KeyValuePair.add_or_update(
            KeyValuePairDB(name="k1_encrypted", value=encrypted_value, secret=True)
        )

        ####################
        # values in objects under an object with additionalProperties
        values = {
            "profiles": {
                "dev": {
                    # no host or port to test default value
                    "token": "hard-coded-secret",
                },
                "prod": {
                    "host": "127.1.2.7",
                    "port": 8282,
                    # encrypted in datastore
                    "token": "{{st2kv.system.k1_encrypted}}",
                    # schema declares `secret: true` which triggers auto-decryption.
                    # If this were not encrypted, it would try to decrypt it and fail.
                },
            }
        }
        config_db = ConfigDB(pack=pack_name, values=values)
        config_db = Config.add_or_update(config_db)

        config_rendered = loader.get_config()

        self.assertEqual(
            config_rendered,
            {
                "region": "us-east-1",
                "profiles": {
                    "dev": {
                        "host": "127.0.0.3",
                        "port": 8080,
                        "token": "hard-coded-secret",
                    },
                    "prod": {
                        "host": "127.1.2.7",
                        "port": 8282,
                        "token": "v1_encrypted",
                    },
                },
            },
        )

        config_db.delete()

    def test_get_config_dynamic_config_item_under_pattern_properties(self):
        pack_name = DUMMY_PACK_SCHEMA_WITH_PATTERN_PROPERTIES_1
        loader = ContentPackConfigLoader(pack_name=pack_name)

        encrypted_value = crypto.symmetric_encrypt(
            KeyValuePairAPI.crypto_key, "v1_encrypted"
        )
        KeyValuePair.add_or_update(
            KeyValuePairDB(name="k1_encrypted", value=encrypted_value, secret=True)
        )

        ####################
        # values in objects under an object with patternProperties
        values = {
            "profiles": {
                "dev": {
                    # no host or port to test default value
                    "token": "hard-coded-secret",
                },
                "prod": {
                    "host": "127.1.2.7",
                    "port": 8282,
                    # encrypted in datastore
                    "token": "{{st2kv.system.k1_encrypted}}",
                    # schema declares `secret: true` which triggers auto-decryption.
                    # If this were not encrypted, it would try to decrypt it and fail.
                },
            }
        }
        config_db = ConfigDB(pack=pack_name, values=values)
        config_db = Config.add_or_update(config_db)

        config_rendered = loader.get_config()

        self.assertEqual(
            config_rendered,
            {
                "region": "us-east-1",
                "profiles": {
                    "dev": {
                        "host": "127.0.0.3",
                        "port": 8080,
                        "token": "hard-coded-secret",
                    },
                    "prod": {
                        "host": "127.1.2.7",
                        "port": 8282,
                        "token": "v1_encrypted",
                    },
                },
            },
        )

        config_db.delete()

    def test_get_config_dynamic_config_item_properties_order_of_precedence(self):
        pack_name = DUMMY_PACK_SCHEMA_WITH_PATTERN_AND_ADDITIONAL_PROPERTIES_1
        loader = ContentPackConfigLoader(pack_name=pack_name)

        encrypted_value_1 = crypto.symmetric_encrypt(
            KeyValuePairAPI.crypto_key, "v1_encrypted"
        )
        KeyValuePair.add_or_update(
            KeyValuePairDB(name="k1_encrypted", value=encrypted_value_1, secret=True)
        )
        encrypted_value_2 = crypto.symmetric_encrypt(
            KeyValuePairAPI.crypto_key, "v2_encrypted"
        )
        KeyValuePair.add_or_update(
            KeyValuePairDB(name="k2_encrypted", value=encrypted_value_2, secret=True)
        )
        encrypted_value_3 = crypto.symmetric_encrypt(
            KeyValuePairAPI.crypto_key, "v3_encrypted"
        )
        KeyValuePair.add_or_update(
            KeyValuePairDB(name="k3_encrypted", value=encrypted_value_3, secret=True)
        )

        ####################
        # values in objects under an object with additionalProperties
        values = {
            "profiles": {
                # properties
                "foo": {
                    "domain": "foo.example.com",
                    "token": "hard-coded-secret",
                },
                "bar": {
                    "domain": "bar.example.com",
                    "token": "{{st2kv.system.k1_encrypted}}",
                },
                # patternProperties start with env-
                "env-dev": {
                    "host": "127.0.0.127",
                    "token": "hard-coded-secret",
                },
                "env-prod": {
                    "host": "127.1.2.7",
                    "port": 8282,
                    # encrypted in datastore
                    "token": "{{st2kv.system.k2_encrypted}}",
                    # schema declares `secret: true` which triggers auto-decryption.
                    # If this were not encrypted, it would try to decrypt it and fail.
                },
                # additionalProperties
                "dev": {
                    "url": "https://example.com",
                    "token": "hard-coded-secret",
                },
                "prod": {
                    "url": "https://other.example.com",
                    "port": 2345,
                    "token": "{{st2kv.system.k3_encrypted}}",
                },
            }
        }
        config_db = ConfigDB(pack=pack_name, values=values)
        config_db = Config.add_or_update(config_db)

        config_rendered = loader.get_config()

        self.assertEqual(
            config_rendered,
            {
                "region": "us-east-1",
                "profiles": {
                    "foo": {
                        "domain": "foo.example.com",
                        "token": "hard-coded-secret",
                    },
                    "bar": {
                        "domain": "bar.example.com",
                        "token": "v1_encrypted",
                    },
                    "env-dev": {
                        "host": "127.0.0.127",
                        "port": 8080,
                        "token": "hard-coded-secret",
                    },
                    "env-prod": {
                        "host": "127.1.2.7",
                        "port": 8282,
                        "token": "v2_encrypted",
                    },
                    "dev": {
                        "url": "https://example.com",
                        "port": 1234,
                        "token": "hard-coded-secret",
                    },
                    "prod": {
                        "url": "https://other.example.com",
                        "port": 2345,
                        "token": "v3_encrypted",
                    },
                },
            },
        )

        config_db.delete()

    def test_get_config_dynamic_config_item_under_additional_items(self):
        pack_name = DUMMY_PACK_SCHEMA_WITH_ADDITIONAL_ITEMS_1
        loader = ContentPackConfigLoader(pack_name=pack_name)

        encrypted_value = crypto.symmetric_encrypt(
            KeyValuePairAPI.crypto_key, "v1_encrypted"
        )
        KeyValuePair.add_or_update(
            KeyValuePairDB(name="k1_encrypted", value=encrypted_value, secret=True)
        )

        ####################
        # values in objects under an object with additionalProperties
        values = {
            "profiles": [
                {
                    # no host or port to test default value
                    "token": "hard-coded-secret",
                },
                {
                    "host": "127.1.2.7",
                    "port": 8282,
                    # encrypted in datastore
                    "token": "{{st2kv.system.k1_encrypted}}",
                    # schema declares `secret: true` which triggers auto-decryption.
                    # If this were not encrypted, it would try to decrypt it and fail.
                },
            ],
            # foobar has additionalItems: true
            "foobar": [
                # there are no types to validate here
                5,
                "a string",
                {
                    # there are no defaults to interpolate here
                    "token": "hard-coded-secret",
                },
                {
                    # nothing is marked `secret: true` so no auto-decryption occurs.
                    "token": "{{st2kv.system.k1_encrypted|decrypt_kv}}",
                },
            ],
        }
        config_db = ConfigDB(pack=pack_name, values=values)
        config_db = Config.add_or_update(config_db)

        config_rendered = loader.get_config()

        self.assertEqual(
            config_rendered,
            {
                "region": "us-east-1",
                "profiles": [
                    {
                        "host": "127.0.0.3",
                        "port": 8080,
                        "token": "hard-coded-secret",
                    },
                    {
                        "host": "127.1.2.7",
                        "port": 8282,
                        "token": "v1_encrypted",
                    },
                ],
                "foobar": [
                    5,
                    "a string",
                    {
                        "token": "hard-coded-secret",
                    },
                    {
                        "token": "v1_encrypted",
                    },
                ],
            },
        )

        config_db.delete()

    def test_empty_config_object_in_the_database(self):
        pack_name = "dummy_pack_empty_config"

        config_db = ConfigDB(pack=pack_name)
        config_db = Config.add_or_update(config_db)

        loader = ContentPackConfigLoader(pack_name=pack_name)
        config = loader.get_config()
        self.assertEqual(config, {})

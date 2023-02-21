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

import mock

from oslo_config import cfg

from st2tests.base import CleanDbTestCase
from st2common.constants.keyvalue import FULL_SYSTEM_SCOPE, FULL_USER_SCOPE
from st2common.constants.keyvalue import SYSTEM_SCOPE, USER_SCOPE
from st2common.constants.types import ResourceType
from st2common.exceptions.rbac import ResourceAccessDeniedError
from st2common.models.db.auth import UserDB
from st2common.models.db.keyvalue import KeyValuePairDB
from st2common.persistence.keyvalue import KeyValuePair
from st2common.rbac.backends.noop import NoOpRBACUtils
from st2common.rbac.types import PermissionType
from st2common.services.keyvalues import KeyValueLookup, UserKeyValueLookup
from st2tests import config

USER = "stanley"
RESOURCE_UUID = "%s:%s:%s" % (
    ResourceType.KEY_VALUE_PAIR,
    FULL_USER_SCOPE,
    "stanley:foobar",
)


class TestKeyValueLookup(CleanDbTestCase):
    @classmethod
    def setUpClass(cls):
        super(TestKeyValueLookup, cls).setUpClass()
        config.parse_args()
        cfg.CONF.set_override(name="backend", override="noop", group="rbac")

    def test_lookup_with_key_prefix(self):
        KeyValuePair.add_or_update(
            KeyValuePairDB(
                name="some:prefix:stanley:k5", value="v5", scope=FULL_USER_SCOPE
            )
        )

        # No prefix provided, should return None
        lookup = UserKeyValueLookup(user="stanley", scope=FULL_USER_SCOPE)
        self.assertEqual(str(lookup.k5), "")

        # Prefix provided
        lookup = UserKeyValueLookup(
            prefix="some:prefix", user="stanley", scope=FULL_USER_SCOPE
        )
        self.assertEqual(str(lookup.k5), "v5")

    def test_non_hierarchical_lookup(self):
        k1 = KeyValuePair.add_or_update(KeyValuePairDB(name="k1", value="v1"))
        k2 = KeyValuePair.add_or_update(KeyValuePairDB(name="k2", value="v2"))
        k3 = KeyValuePair.add_or_update(KeyValuePairDB(name="k3", value="v3"))
        k4 = KeyValuePair.add_or_update(
            KeyValuePairDB(name="stanley:k4", value="v4", scope=FULL_USER_SCOPE)
        )

        lookup = KeyValueLookup()
        self.assertEqual(str(lookup.k1), k1.value)
        self.assertEqual(str(lookup.k2), k2.value)
        self.assertEqual(str(lookup.k3), k3.value)

        # Scoped lookup
        lookup = KeyValueLookup(scope=FULL_SYSTEM_SCOPE)
        self.assertEqual(str(lookup.k4), "")
        user_lookup = UserKeyValueLookup(scope=FULL_USER_SCOPE, user="stanley")
        self.assertEqual(str(user_lookup.k4), k4.value)

    def test_hierarchical_lookup_dotted(self):
        k1 = KeyValuePair.add_or_update(KeyValuePairDB(name="a.b", value="v1"))
        k2 = KeyValuePair.add_or_update(KeyValuePairDB(name="a.b.c", value="v2"))
        k3 = KeyValuePair.add_or_update(KeyValuePairDB(name="b.c", value="v3"))
        k4 = KeyValuePair.add_or_update(
            KeyValuePairDB(name="stanley:r.i.p", value="v4", scope=FULL_USER_SCOPE)
        )

        lookup = KeyValueLookup()
        self.assertEqual(str(lookup.a.b), k1.value)
        self.assertEqual(str(lookup.a.b.c), k2.value)
        self.assertEqual(str(lookup.b.c), k3.value)
        self.assertEqual(str(lookup.a), "")

        # Scoped lookup
        lookup = KeyValueLookup(scope=FULL_SYSTEM_SCOPE)
        self.assertEqual(str(lookup.r.i.p), "")
        user_lookup = UserKeyValueLookup(scope=FULL_USER_SCOPE, user="stanley")
        self.assertEqual(str(user_lookup.r.i.p), k4.value)

    def test_hierarchical_lookup_dict(self):
        k1 = KeyValuePair.add_or_update(KeyValuePairDB(name="a.b", value="v1"))
        k2 = KeyValuePair.add_or_update(KeyValuePairDB(name="a.b.c", value="v2"))
        k3 = KeyValuePair.add_or_update(KeyValuePairDB(name="b.c", value="v3"))
        k4 = KeyValuePair.add_or_update(
            KeyValuePairDB(name="stanley:r.i.p", value="v4", scope=FULL_USER_SCOPE)
        )

        lookup = KeyValueLookup()
        self.assertEqual(str(lookup["a"]["b"]), k1.value)
        self.assertEqual(str(lookup["a"]["b"]["c"]), k2.value)
        self.assertEqual(str(lookup["b"]["c"]), k3.value)
        self.assertEqual(str(lookup["a"]), "")

        # Scoped lookup
        lookup = KeyValueLookup(scope=FULL_SYSTEM_SCOPE)
        self.assertEqual(str(lookup["r"]["i"]["p"]), "")
        user_lookup = UserKeyValueLookup(scope=FULL_USER_SCOPE, user="stanley")
        self.assertEqual(str(user_lookup["r"]["i"]["p"]), k4.value)

    def test_lookups_older_scope_names_backward_compatibility(self):
        k1 = KeyValuePair.add_or_update(
            KeyValuePairDB(name="a.b", value="v1", scope=FULL_SYSTEM_SCOPE)
        )
        lookup = KeyValueLookup(scope=SYSTEM_SCOPE)
        self.assertEqual(str(lookup["a"]["b"]), k1.value)

        k2 = KeyValuePair.add_or_update(
            KeyValuePairDB(name="stanley:r.i.p", value="v4", scope=FULL_USER_SCOPE)
        )
        user_lookup = UserKeyValueLookup(scope=USER_SCOPE, user="stanley")
        self.assertEqual(str(user_lookup["r"]["i"]["p"]), k2.value)

    def test_user_scope_lookups_dot_in_user(self):
        KeyValuePair.add_or_update(
            KeyValuePairDB(name="first.last:r.i.p", value="v4", scope=FULL_USER_SCOPE)
        )
        lookup = UserKeyValueLookup(scope=FULL_USER_SCOPE, user="first.last")
        self.assertEqual(str(lookup.r.i.p), "v4")
        self.assertEqual(str(lookup["r"]["i"]["p"]), "v4")

    def test_user_scope_lookups_user_sep_in_name(self):
        KeyValuePair.add_or_update(
            KeyValuePairDB(name="stanley:r:i:p", value="v4", scope=FULL_USER_SCOPE)
        )
        lookup = UserKeyValueLookup(scope=FULL_USER_SCOPE, user="stanley")
        # This is the only way to lookup because USER_SEPARATOR (':') cannot be a part of
        # variable name in Python.
        self.assertEqual(str(lookup["r:i:p"]), "v4")

    def test_missing_key_lookup(self):
        lookup = KeyValueLookup(scope=FULL_SYSTEM_SCOPE)
        self.assertEqual(str(lookup.missing_key), "")
        self.assertTrue(lookup.missing_key, "Should be not none.")

        user_lookup = UserKeyValueLookup(scope=FULL_USER_SCOPE, user="stanley")
        self.assertEqual(str(user_lookup.missing_key), "")
        self.assertTrue(user_lookup.missing_key, "Should be not none.")

    def test_secret_lookup(self):
        secret_value = (
            "0055A2D9A09E1071931925933744965EEA7E23DCF59A8D1D7A3"
            + "64338294916D37E83C4796283C584751750E39844E2FD97A3727DB5D553F638"
        )
        k1 = KeyValuePair.add_or_update(
            KeyValuePairDB(name="k1", value=secret_value, secret=True)
        )
        k2 = KeyValuePair.add_or_update(KeyValuePairDB(name="k2", value="v2"))
        k3 = KeyValuePair.add_or_update(
            KeyValuePairDB(
                name="stanley:k3",
                value=secret_value,
                scope=FULL_USER_SCOPE,
                secret=True,
            )
        )

        lookup = KeyValueLookup()
        self.assertEqual(str(lookup.k1), k1.value)
        self.assertEqual(str(lookup.k2), k2.value)
        self.assertEqual(str(lookup.k3), "")

        user_lookup = UserKeyValueLookup(scope=FULL_USER_SCOPE, user="stanley")
        self.assertEqual(str(user_lookup.k3), k3.value)

    def test_lookup_cast(self):
        KeyValuePair.add_or_update(KeyValuePairDB(name="count", value="5.5"))

        lookup = KeyValueLookup(scope=FULL_SYSTEM_SCOPE)
        self.assertEqual(str(lookup.count), "5.5")
        self.assertEqual(float(lookup.count), 5.5)
        self.assertEqual(int(lookup.count), 5)

    @mock.patch.object(
        NoOpRBACUtils,
        "assert_user_has_resource_db_permission",
        mock.MagicMock(
            side_effect=ResourceAccessDeniedError(
                user_db=UserDB(name=USER),
                resource_api_or_db=KeyValuePairDB(uid=RESOURCE_UUID),
                permission_type=PermissionType.KEY_VALUE_PAIR_VIEW,
            )
        ),
    )
    def test_system_kvp_lookup_unauthorized(self):
        secret_value = (
            "0055A2D9A09E1071931925933744965EEA7E23DCF59A8D1D7A3"
            + "64338294916D37E83C4796283C584751750E39844E2FD97A3727DB5D553F638"
        )

        KeyValuePair.add_or_update(
            KeyValuePairDB(name="k1", value=secret_value, secret=True)
        )

        lookup = KeyValueLookup()
        self.assertRaises(ResourceAccessDeniedError, getattr, lookup, "k1")

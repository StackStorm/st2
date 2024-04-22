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

import six
import mock
from jsonschema import ValidationError

from st2common.content import utils as content_utils
from st2common.bootstrap.base import ResourceRegistrar
from st2common.persistence.pack import Pack
from st2common.persistence.pack import ConfigSchema

from st2tests.base import CleanDbTestCase
from st2tests.fixtures.packs.dummy_pack_1.fixture import (
    PACK_NAME as DUMMY_PACK_1,
    PACK_PATH as PACK_PATH_1,
)
from st2tests.fixtures.packs.dummy_pack_6.fixture import (
    PACK_NAME as DUMMY_PACK_6,
    PACK_PATH as PACK_PATH_6,
)
from st2tests.fixtures.packs.dummy_pack_7.fixture import (
    PACK_NAME as DUMMY_PACK_7_NAME,
    PACK_PATH as PACK_PATH_7,
)
from st2tests.fixtures.packs.dummy_pack_8.fixture import PACK_PATH as PACK_PATH_8
from st2tests.fixtures.packs.dummy_pack_9.fixture import (
    PACK_DIR_NAME as DUMMY_PACK_9,
    PACK_NAME as DUMMY_PACK_9_DEPS,
    PACK_PATH as PACK_PATH_9,
)
from st2tests.fixtures.packs.dummy_pack_10.fixture import PACK_PATH as PACK_PATH_10
from st2tests.fixtures.packs.dummy_pack_13.fixture import PACK_PATH as PACK_PATH_13
from st2tests.fixtures.packs.dummy_pack_14.fixture import PACK_PATH as PACK_PATH_14
from st2tests.fixtures.packs.dummy_pack_20.fixture import (
    PACK_NAME as DUMMY_PACK_20,
    PACK_PATH as PACK_PATH_20,
)
from st2tests.fixtures.packs.dummy_pack_21.fixture import (
    PACK_NAME as DUMMY_PACK_21,
    PACK_PATH as PACK_PATH_21,
)
from st2tests.fixtures.packs_invalid.dummy_pack_17.fixture import (
    PACK_NAME as DUMMY_PACK_17,
    PACK_PATH as PACK_PATH_17,
)
from st2tests.fixtures.packs_invalid.dummy_pack_18.fixture import (
    PACK_NAME as DUMMY_PACK_18,
    PACK_PATH as PACK_PATH_18,
)

# from st2tests.fixtures.packs.dummy_pack_12.fixture import (
#     PACK_PATH as PACK_PATH_12,
# )  # not used?


__all__ = ["ResourceRegistrarTestCase"]


class ResourceRegistrarTestCase(CleanDbTestCase):
    def test_register_packs(self):
        # Verify DB is empty
        pack_dbs = Pack.get_all()
        config_schema_dbs = ConfigSchema.get_all()

        self.assertEqual(len(pack_dbs), 0)
        self.assertEqual(len(config_schema_dbs), 0)

        registrar = ResourceRegistrar(use_pack_cache=False)
        registrar._pack_loader.get_packs = mock.Mock()
        registrar._pack_loader.get_packs.return_value = {DUMMY_PACK_1: PACK_PATH_1}
        packs_base_paths = content_utils.get_packs_base_paths()
        registrar.register_packs(base_dirs=packs_base_paths)

        # Verify pack and schema have been registered
        pack_dbs = Pack.get_all()
        config_schema_dbs = ConfigSchema.get_all()

        self.assertEqual(len(pack_dbs), 1)
        self.assertEqual(len(config_schema_dbs), 1)

        pack_db = pack_dbs[0]
        config_schema_db = config_schema_dbs[0]

        self.assertEqual(pack_db.name, DUMMY_PACK_1)
        self.assertEqual(len(pack_db.contributors), 2)
        self.assertEqual(pack_db.contributors[0], "John Doe1 <john.doe1@gmail.com>")
        self.assertEqual(pack_db.contributors[1], "John Doe2 <john.doe2@gmail.com>")
        self.assertIn("api_key", config_schema_db.attributes)
        self.assertIn("api_secret", config_schema_db.attributes)

        # Verify pack_db.files is correct and doesn't contain excluded files (*.pyc, .git/*, etc.)
        # Note: We can't test that .git/* files are excluded since git doesn't allow you to add
        # .git directory to existing repo index :/
        excluded_files = [
            "__init__.pyc",
            "actions/dummy1.pyc",
            "actions/dummy2.pyc",
        ]

        for excluded_file in excluded_files:
            self.assertNotIn(excluded_file, pack_db.files)

    def test_register_pack_arbitrary_properties_are_allowed(self):
        # Test registering a pack which has "arbitrary" properties in pack.yaml
        # We support this use-case (ignore properties which are not defined on the PackAPI model)
        # so we can add new attributes in a new version without breaking existing installations.
        registrar = ResourceRegistrar(use_pack_cache=False)
        registrar._pack_loader.get_packs = mock.Mock()
        registrar._pack_loader.get_packs.return_value = {
            DUMMY_PACK_20: PACK_PATH_20,
        }
        packs_base_paths = content_utils.get_packs_base_paths()
        registrar.register_packs(base_dirs=packs_base_paths)

        # Ref is provided
        pack_db = Pack.get_by_name(DUMMY_PACK_20)
        self.assertEqual(pack_db.ref, "dummy_pack_20_ref")
        self.assertEqual(len(pack_db.contributors), 0)

    def test_register_pack_pack_ref(self):
        # Verify DB is empty
        pack_dbs = Pack.get_all()

        self.assertEqual(len(pack_dbs), 0)

        registrar = ResourceRegistrar(use_pack_cache=False)
        registrar._pack_loader.get_packs = mock.Mock()
        registrar._pack_loader.get_packs.return_value = {
            DUMMY_PACK_1: PACK_PATH_1,
            DUMMY_PACK_6: PACK_PATH_6,
        }
        packs_base_paths = content_utils.get_packs_base_paths()
        registrar.register_packs(base_dirs=packs_base_paths)

        # Ref is provided
        pack_db = Pack.get_by_name(DUMMY_PACK_6)
        self.assertEqual(pack_db.ref, "dummy_pack_6_ref")
        self.assertEqual(len(pack_db.contributors), 0)

        # Ref is not provided, directory name should be used
        pack_db = Pack.get_by_name(DUMMY_PACK_1)
        self.assertEqual(pack_db.ref, DUMMY_PACK_1)

        # "ref" is not provided, but "name" is
        registrar._register_pack_db(pack_name=None, pack_dir=PACK_PATH_7)

        pack_db = Pack.get_by_name(DUMMY_PACK_7_NAME)
        self.assertEqual(pack_db.ref, DUMMY_PACK_7_NAME)

        # "ref" is not provided and "name" contains invalid characters
        expected_msg = "contains invalid characters"
        self.assertRaisesRegex(
            ValueError,
            expected_msg,
            registrar._register_pack_db,
            pack_name=None,
            pack_dir=PACK_PATH_8,
        )

    def test_register_pack_invalid_ref_name_friendly_error_message(self):
        registrar = ResourceRegistrar(use_pack_cache=False)

        # Invalid ref
        expected_msg = (
            r"Pack ref / name can only contain valid word characters .*?,"
            " dashes are not allowed."
        )
        self.assertRaisesRegex(
            ValidationError,
            expected_msg,
            registrar._register_pack_db,
            pack_name=None,
            pack_dir=PACK_PATH_13,
        )

        try:
            registrar._register_pack_db(pack_name=None, pack_dir=PACK_PATH_13)
        except ValidationError as e:
            self.assertIn(
                "'invalid-has-dash' does not match '^[a-z0-9_]+$'", six.text_type(e)
            )
        else:
            self.fail("Exception not thrown")

        # Pack ref not provided and name doesn't contain valid characters
        expected_msg = (
            r'Pack name "dummy pack 14" contains invalid characters and "ref" '
            "attribute is not available. You either need to add"
        )
        self.assertRaisesRegex(
            ValueError,
            expected_msg,
            registrar._register_pack_db,
            pack_name=None,
            pack_dir=PACK_PATH_14,
        )

    def test_register_pack_pack_stackstorm_version_and_future_parameters(self):
        # Verify DB is empty
        pack_dbs = Pack.get_all()
        self.assertEqual(len(pack_dbs), 0)

        registrar = ResourceRegistrar(use_pack_cache=False)
        registrar._pack_loader.get_packs = mock.Mock()
        registrar._pack_loader.get_packs.return_value = {DUMMY_PACK_9: PACK_PATH_9}
        packs_base_paths = content_utils.get_packs_base_paths()
        registrar.register_packs(base_dirs=packs_base_paths)

        # Dependencies, stackstorm_version and future values
        pack_db = Pack.get_by_name(DUMMY_PACK_9_DEPS)
        self.assertEqual(pack_db.dependencies, ["core=0.2.0"])
        self.assertEqual(pack_db.stackstorm_version, ">=1.6.0, <2.2.0")
        self.assertEqual(pack_db.system, {"centos": {"foo": ">= 1.0"}})
        self.assertEqual(pack_db.python_versions, ["2", "3"])

        # Note: We only store parameters which are defined in the schema, all other custom user
        # defined attributes are ignored
        self.assertTrue(not hasattr(pack_db, "future"))
        self.assertTrue(not hasattr(pack_db, "this"))

        # Wrong characters in the required st2 version
        expected_msg = "'wrongstackstormversion' does not match"
        self.assertRaisesRegex(
            ValidationError,
            expected_msg,
            registrar._register_pack_db,
            pack_name=None,
            pack_dir=PACK_PATH_10,
        )

    def test_register_pack_empty_and_invalid_config_schema(self):
        registrar = ResourceRegistrar(use_pack_cache=False, fail_on_failure=True)
        registrar._pack_loader.get_packs = mock.Mock()
        registrar._pack_loader.get_packs.return_value = {DUMMY_PACK_17: PACK_PATH_17}
        packs_base_paths = content_utils.get_packs_base_paths()

        expected_msg = (
            'Config schema ".*?dummy_pack_17/config.schema.yaml" is empty and invalid.'
        )
        self.assertRaisesRegex(
            ValueError,
            expected_msg,
            registrar.register_packs,
            base_dirs=packs_base_paths,
        )

    def test_register_pack_invalid_config_schema_invalid_attribute(self):
        registrar = ResourceRegistrar(use_pack_cache=False, fail_on_failure=True)
        registrar._pack_loader.get_packs = mock.Mock()
        registrar._pack_loader.get_packs.return_value = {DUMMY_PACK_18: PACK_PATH_18}
        packs_base_paths = content_utils.get_packs_base_paths()

        expected_msg = (
            r"Additional properties are not allowed \(\'invalid\' was unexpected\)"
        )
        self.assertRaisesRegex(
            ValueError,
            expected_msg,
            registrar.register_packs,
            base_dirs=packs_base_paths,
        )

    def test_register_pack_invalid_python_versions_attribute(self):
        registrar = ResourceRegistrar(use_pack_cache=False, fail_on_failure=True)
        registrar._pack_loader.get_packs = mock.Mock()
        registrar._pack_loader.get_packs.return_value = {DUMMY_PACK_21: PACK_PATH_21}
        packs_base_paths = content_utils.get_packs_base_paths()

        expected_msg = r"'4' is not one of \['2', '3'\]"
        self.assertRaisesRegex(
            ValueError,
            expected_msg,
            registrar.register_packs,
            base_dirs=packs_base_paths,
        )

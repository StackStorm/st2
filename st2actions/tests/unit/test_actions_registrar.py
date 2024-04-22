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
import jsonschema
import mock
import yaml

import st2common.bootstrap.actionsregistrar as actions_registrar
from st2common.persistence.action import Action
import st2common.validators.api.action as action_validator
from st2common.models.db.runner import RunnerTypeDB

import st2tests.base as tests_base
from st2tests.fixtures.generic.fixture import (
    PACK_NAME as GENERIC_PACK,
    PACK_PATH as GENERIC_PACK_PATH,
    PACK_BASE_PATH as PACKS_BASE_PATH,
)
import st2tests.fixturesloader as fixtures_loader

MOCK_RUNNER_TYPE_DB = RunnerTypeDB(name="run-local", runner_module="st2.runners.local")


# NOTE: We need to perform this patching because test fixtures are located outside of the packs
# base paths directory. This will never happen outside the context of test fixtures.
@mock.patch(
    "st2common.content.utils.get_pack_base_path",
    mock.Mock(return_value=GENERIC_PACK_PATH),
)
class ActionsRegistrarTest(tests_base.DbTestCase):
    @mock.patch.object(
        action_validator, "_is_valid_pack", mock.MagicMock(return_value=True)
    )
    @mock.patch.object(
        action_validator,
        "get_runner_model",
        mock.MagicMock(return_value=MOCK_RUNNER_TYPE_DB),
    )
    def test_register_all_actions(self):
        try:
            all_actions_in_db = Action.get_all()
            actions_registrar.register_actions(packs_base_paths=[PACKS_BASE_PATH])
        except Exception as e:
            print(six.text_type(e))
            self.fail("All actions must be registered without exceptions.")
        else:
            all_actions_in_db = Action.get_all()
            self.assertTrue(len(all_actions_in_db) > 0)

        # Assert metadata_file field is populated
        expected_path = "actions/action-with-no-parameters.yaml"
        self.assertEqual(all_actions_in_db[0].metadata_file, expected_path)

    def test_register_actions_from_bad_pack(self):
        packs_base_path = tests_base.get_fixtures_path()
        try:
            actions_registrar.register_actions(packs_base_paths=[packs_base_path])
            self.fail("Should have thrown.")
        except:
            pass

    @mock.patch.object(
        action_validator, "_is_valid_pack", mock.MagicMock(return_value=True)
    )
    @mock.patch.object(
        action_validator,
        "get_runner_model",
        mock.MagicMock(return_value=MOCK_RUNNER_TYPE_DB),
    )
    def test_pack_name_missing(self):
        registrar = actions_registrar.ActionsRegistrar()
        loader = fixtures_loader.FixturesLoader()
        action_file = loader.get_fixture_file_path_abs(
            GENERIC_PACK, "actions", "action_3_pack_missing.yaml"
        )
        registrar._register_action("dummy", action_file)
        action_name = None
        with open(action_file, "r") as fd:
            content = yaml.safe_load(fd)
            action_name = str(content["name"])
            action_db = Action.get_by_name(action_name)
            expected_msg = "Content pack must be set to dummy"
            self.assertEqual(action_db.pack, "dummy", expected_msg)
            Action.delete(action_db)

    @mock.patch.object(
        action_validator, "_is_valid_pack", mock.MagicMock(return_value=True)
    )
    @mock.patch.object(
        action_validator,
        "get_runner_model",
        mock.MagicMock(return_value=MOCK_RUNNER_TYPE_DB),
    )
    def test_register_action_with_no_params(self):
        registrar = actions_registrar.ActionsRegistrar()
        loader = fixtures_loader.FixturesLoader()
        action_file = loader.get_fixture_file_path_abs(
            GENERIC_PACK, "actions", "action-with-no-parameters.yaml"
        )

        self.assertEqual(registrar._register_action("dummy", action_file), False)

    @mock.patch.object(
        action_validator, "_is_valid_pack", mock.MagicMock(return_value=True)
    )
    @mock.patch.object(
        action_validator,
        "get_runner_model",
        mock.MagicMock(return_value=MOCK_RUNNER_TYPE_DB),
    )
    def test_register_action_invalid_parameter_type_attribute(self):
        registrar = actions_registrar.ActionsRegistrar()
        loader = fixtures_loader.FixturesLoader()
        action_file = loader.get_fixture_file_path_abs(
            GENERIC_PACK, "actions", "action_invalid_param_type.yaml"
        )

        # with jsonschema 2.6.0, the anyOf validator errors with:
        #   "'list' is not valid under any of the given schemas"
        # with jsonschema 3.2.0, the underlying enum (anyOf->enum) gets reported instead:
        expected_msg = r"'list' is not one of \['array', 'boolean', 'integer', 'null', 'number', 'object', 'string'\].*"
        self.assertRaisesRegex(
            jsonschema.ValidationError,
            expected_msg,
            registrar._register_action,
            "dummy",
            action_file,
        )

    @mock.patch.object(
        action_validator, "_is_valid_pack", mock.MagicMock(return_value=True)
    )
    @mock.patch.object(
        action_validator,
        "get_runner_model",
        mock.MagicMock(return_value=MOCK_RUNNER_TYPE_DB),
    )
    def test_register_action_invalid_parameter_name(self):
        registrar = actions_registrar.ActionsRegistrar()
        loader = fixtures_loader.FixturesLoader()
        action_file = loader.get_fixture_file_path_abs(
            GENERIC_PACK, "actions", "action_invalid_parameter_name.yaml"
        )

        expected_msg = (
            'Parameter name "action-name" is invalid. Valid characters for '
            "parameter name are"
        )
        self.assertRaisesRegex(
            jsonschema.ValidationError,
            expected_msg,
            registrar._register_action,
            GENERIC_PACK,
            action_file,
        )

    @mock.patch.object(
        action_validator, "_is_valid_pack", mock.MagicMock(return_value=True)
    )
    @mock.patch.object(
        action_validator,
        "get_runner_model",
        mock.MagicMock(return_value=MOCK_RUNNER_TYPE_DB),
    )
    def test_invalid_params_schema(self):
        registrar = actions_registrar.ActionsRegistrar()
        loader = fixtures_loader.FixturesLoader()
        action_file = loader.get_fixture_file_path_abs(
            GENERIC_PACK, "actions", "action-invalid-schema-params.yaml"
        )
        try:
            registrar._register_action(GENERIC_PACK, action_file)
            self.fail("Invalid action schema. Should have failed.")
        except jsonschema.ValidationError:
            pass

    @mock.patch.object(
        action_validator, "_is_valid_pack", mock.MagicMock(return_value=True)
    )
    @mock.patch.object(
        action_validator,
        "get_runner_model",
        mock.MagicMock(return_value=MOCK_RUNNER_TYPE_DB),
    )
    def test_action_update(self):
        registrar = actions_registrar.ActionsRegistrar()
        loader = fixtures_loader.FixturesLoader()
        action_file = loader.get_fixture_file_path_abs(
            GENERIC_PACK, "actions", "action1.yaml"
        )
        registrar._register_action("wolfpack", action_file)
        # try registering again. this should not throw errors.
        registrar._register_action("wolfpack", action_file)
        action_name = None
        with open(action_file, "r") as fd:
            content = yaml.safe_load(fd)
            action_name = str(content["name"])
            action_db = Action.get_by_name(action_name)
            expected_msg = "Content pack must be set to wolfpack"
            self.assertEqual(action_db.pack, "wolfpack", expected_msg)
            Action.delete(action_db)

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

try:
    import simplejson as json
except ImportError:
    import json

import six
import mock

from st2common.exceptions.apivalidation import ValueValidationException
from st2common.models.api.action import ActionAPI
from st2common.bootstrap import runnersregistrar as runners_registrar
import st2common.validators.api.action as action_validator
from st2tests import DbTestCase
from st2tests.fixtures.packs import executions as fixture

__all__ = ["TestActionAPIValidator"]


class TestActionAPIValidator(DbTestCase):
    @classmethod
    def setUpClass(cls):
        super(TestActionAPIValidator, cls).setUpClass()

        runners_registrar.register_runners()

    @mock.patch.object(
        action_validator, "_is_valid_pack", mock.MagicMock(return_value=True)
    )
    def test_validate_runner_type_happy_case(self):
        action_api_dict = fixture.ARTIFACTS["actions"]["local"]
        action_api = ActionAPI(**action_api_dict)
        try:
            action_validator.validate_action(action_api)
        except:
            self.fail("Exception validating action: %s" % json.dumps(action_api_dict))

    @mock.patch.object(
        action_validator, "_is_valid_pack", mock.MagicMock(return_value=True)
    )
    def test_validate_runner_type_invalid_runner(self):
        action_api_dict = fixture.ARTIFACTS["actions"]["action-with-invalid-runner"]
        action_api = ActionAPI(**action_api_dict)
        try:
            action_validator.validate_action(action_api)
            self.fail(
                "Action validation should not have passed. %s"
                % json.dumps(action_api_dict)
            )
        except ValueValidationException:
            pass

    @mock.patch.object(
        action_validator, "_is_valid_pack", mock.MagicMock(return_value=True)
    )
    def test_validate_override_immutable_runner_param(self):
        action_api_dict = fixture.ARTIFACTS["actions"][
            "remote-override-runner-immutable"
        ]
        action_api = ActionAPI(**action_api_dict)
        try:
            action_validator.validate_action(action_api)
            self.fail(
                "Action validation should not have passed. %s"
                % json.dumps(action_api_dict)
            )
        except ValueValidationException as e:
            self.assertIn("Cannot override in action.", six.text_type(e))

    @mock.patch.object(
        action_validator, "_is_valid_pack", mock.MagicMock(return_value=True)
    )
    def test_validate_action_param_immutable(self):
        action_api_dict = fixture.ARTIFACTS["actions"][
            "action-immutable-param-no-default"
        ]
        action_api = ActionAPI(**action_api_dict)
        try:
            action_validator.validate_action(action_api)
            self.fail(
                "Action validation should not have passed. %s"
                % json.dumps(action_api_dict)
            )
        except ValueValidationException as e:
            self.assertIn("requires a default value.", six.text_type(e))

    @mock.patch.object(
        action_validator, "_is_valid_pack", mock.MagicMock(return_value=True)
    )
    def test_validate_action_param_immutable_no_default(self):
        action_api_dict = fixture.ARTIFACTS["actions"][
            "action-immutable-runner-param-no-default"
        ]
        action_api = ActionAPI(**action_api_dict)

        # Runner param sudo is decalred immutable in action but no defualt value
        # supplied in action. We should pick up default value from runner.
        try:
            action_validator.validate_action(action_api)
        except ValueValidationException as e:
            print(e)
            self.fail(
                "Action validation should have passed. %s" % json.dumps(action_api_dict)
            )

    @mock.patch.object(
        action_validator, "_is_valid_pack", mock.MagicMock(return_value=True)
    )
    def test_validate_action_param_position_values_unique(self):
        action_api_dict = fixture.ARTIFACTS["actions"][
            "action-with-non-unique-positions"
        ]
        action_api = ActionAPI(**action_api_dict)

        try:
            action_validator.validate_action(action_api)
            self.fail(
                "Action validation should have failed "
                + "because position values are not unique."
                % json.dumps(action_api_dict)
            )
        except ValueValidationException as e:
            self.assertIn("have same position", six.text_type(e))

    @mock.patch.object(
        action_validator, "_is_valid_pack", mock.MagicMock(return_value=True)
    )
    def test_validate_action_param_position_values_contiguous(self):
        action_api_dict = fixture.ARTIFACTS["actions"][
            "action-with-non-contiguous-positions"
        ]
        action_api = ActionAPI(**action_api_dict)

        try:
            action_validator.validate_action(action_api)
            self.fail(
                "Action validation should have failed "
                + "because position values are not contiguous."
                % json.dumps(action_api_dict)
            )
        except ValueValidationException as e:
            self.assertIn("are not contiguous", six.text_type(e))

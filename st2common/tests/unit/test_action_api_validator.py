# Licensed to the StackStorm, Inc ('StackStorm') under one or more
# contributor license agreements.  See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.
# The ASF licenses this file to You under the Apache License, Version 2.0
# (the "License"); you may not use this file except in compliance with
# the License.  You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

try:
    import simplejson as json
except ImportError:
    import json

import mock

from st2common.exceptions.apivalidation import ValueValidationException
from st2common.models.api.action import (ActionAPI, RunnerTypeAPI)
from st2common.persistence.runner import RunnerType
import st2common.validators.api.action as action_validator
from st2tests import DbTestCase
from st2tests.fixtures.packs import executions as fixture


class TestActionAPIValidator(DbTestCase):

    @classmethod
    def setUpClass(cls):
        super(TestActionAPIValidator, cls).setUpClass()

        runner_api_dict = fixture.ARTIFACTS['runners']['run-local']
        runner_api = RunnerTypeAPI(**runner_api_dict)
        runner_model = RunnerTypeAPI.to_model(runner_api)

        RunnerType.add_or_update(runner_model)

    @mock.patch.object(action_validator, '_is_valid_pack', mock.MagicMock(
        return_value=True))
    def test_validate_runner_type_happy_case(self):
        action_api_dict = fixture.ARTIFACTS['actions']['local']
        action_api = ActionAPI(**action_api_dict)
        try:
            action_validator.validate_action(action_api)
        except:
            self.fail('Exception validating action: %s' % json.dumps(action_api_dict))

    @mock.patch.object(action_validator, '_is_valid_pack', mock.MagicMock(
        return_value=True))
    def test_validate_runner_type_invalid_runner(self):
        action_api_dict = fixture.ARTIFACTS['actions']['action-with-invalid-runner']
        action_api = ActionAPI(**action_api_dict)
        try:
            action_validator.validate_action(action_api)
            self.fail('Action validation should not have passed. %s' % json.dumps(action_api_dict))
        except ValueValidationException:
            pass

    @mock.patch.object(action_validator, '_is_valid_pack', mock.MagicMock(
        return_value=True))
    def test_validate_override_immutable_runner_param(self):
        action_api_dict = fixture.ARTIFACTS['actions']['local-override-runner-immutable']
        action_api = ActionAPI(**action_api_dict)
        try:
            action_validator.validate_action(action_api)
            self.fail('Action validation should not have passed. %s' % json.dumps(action_api_dict))
        except ValueValidationException as e:
            self.assertTrue('Cannot override in action.' in e.message)

    @mock.patch.object(action_validator, '_is_valid_pack', mock.MagicMock(
        return_value=True))
    def test_validate_action_param_immutable(self):
        action_api_dict = fixture.ARTIFACTS['actions']['action-immutable-param-no-default']
        action_api = ActionAPI(**action_api_dict)
        try:
            action_validator.validate_action(action_api)
            self.fail('Action validation should not have passed. %s' % json.dumps(action_api_dict))
        except ValueValidationException as e:
            self.assertTrue('requires a default value.' in e.message)

    @mock.patch.object(action_validator, '_is_valid_pack', mock.MagicMock(
        return_value=True))
    def test_validate_action_param_immutable_no_default(self):
        action_api_dict = fixture.ARTIFACTS['actions']['action-immutable-runner-param-no-default']
        action_api = ActionAPI(**action_api_dict)

        # Runner param sudo is decalred immutable in action but no defualt value
        # supplied in action. We should pick up default value from runner.
        try:
            action_validator.validate_action(action_api)
        except ValueValidationException as e:
            print(e)
            self.fail('Action validation should have passed. %s' % json.dumps(action_api_dict))

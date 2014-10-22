try:
    import simplejson as json
except ImportError:
    import json

import mock

from st2common.exceptions.apivalidation import ValueValidationException
from st2common.models.api.action import (ActionAPI, RunnerTypeAPI)
from st2common.persistence.action import RunnerType
import st2common.validators.api.action as action_validator
from st2tests import DbTestCase
from tests.fixtures import history as fixture


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
    def test_validate_action_param_required_missing_definition(self):
        action_api_dict = fixture.ARTIFACTS['actions']['action-missing-param-required']
        action_api = ActionAPI(**action_api_dict)
        try:
            action_validator.validate_action(action_api)
            self.fail('Action validation should not have passed. %s' % json.dumps(action_api_dict))
        except ValueValidationException as e:
            self.assertTrue('does not have a definition' in e.message)

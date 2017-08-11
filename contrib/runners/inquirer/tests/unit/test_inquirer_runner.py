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

import mock

import inquirer
from st2actions.container import service
from st2common.constants.action import LIVEACTION_STATUS_PENDING
from st2common.constants.pack import SYSTEM_PACK_NAME
from st2tests.base import RunnerTestCase


mock_liveaction_db = mock.Mock()
mock_liveaction_db.result = {"response": {}}

mock_action_utils = mock.Mock()
mock_action_utils.get_liveaction_by_id.return_value = mock_liveaction_db

mock_action_service = mock.Mock()

mock_trigger_dispatcher = mock.Mock()

test_user = 'st2admin'
test_parent_id = '1234567890'

runner_params = {
    "users": [],
    "roles": [],
    "tag": "developers",
    "schema": {}
}


class InquiryTestCase(RunnerTestCase):

    def test_runner_creation(self):
        runner = inquirer.get_runner()
        self.assertTrue(runner is not None, 'Creation failed. No instance.')
        self.assertEqual(type(runner), inquirer.Inquirer, 'Creation failed. No instance.')

    @mock.patch('inquirer.TriggerDispatcher', mock_trigger_dispatcher)
    @mock.patch('inquirer.action_utils', mock_action_utils)
    @mock.patch('inquirer.action_service', mock_action_service)
    def test_simple_inquiry(self):
        runner = inquirer.get_runner()
        runner.context = {
            'user': test_user
        }
        runner.action = self._get_mock_action_obj()
        runner.runner_parameters = runner_params
        runner.container_service = service.RunnerContainerService()
        runner.pre_run()
        mock_liveaction_db.context = {
            "parent": test_parent_id
        }
        (status, output, _) = runner.run({})
        self.assertEqual(status, LIVEACTION_STATUS_PENDING)
        self.assertTrue(output is not None)
        self.assertEqual(output, {"response": {}})
        mock_trigger_dispatcher.return_value.dispatch.assert_called_once_with(
            'core.st2.generic.inquiry',
            {
                'users': [],
                'roles': [],
                'id': None,
                'tag': "developers",
                'response': {},
                'schema': {}
            }
        )
        mock_action_service.request_pause.assert_called_once_with(
            test_parent_id,
            test_user
        )
        mock_trigger_dispatcher.reset_mock()
        mock_action_utils.reset_mock()
        mock_action_service.reset_mock()

    @mock.patch('inquirer.TriggerDispatcher', mock_trigger_dispatcher)
    @mock.patch('inquirer.action_utils', mock_action_utils)
    @mock.patch('inquirer.action_service', mock_action_service)
    def test_inquiry_no_parent(self):
        """Should behave like a regular execution, but without requesting a pause
        """

        runner = inquirer.get_runner()
        runner.context = {
            'user': 'st2admin'
        }
        runner.action = self._get_mock_action_obj()
        runner.runner_parameters = runner_params
        runner.container_service = service.RunnerContainerService()
        runner.pre_run()
        mock_liveaction_db.context = {
            "parent": None
        }
        (status, output, _) = runner.run({})
        self.assertEqual(status, LIVEACTION_STATUS_PENDING)
        self.assertTrue(output is not None)
        self.assertEqual(output, {"response": {}})
        mock_trigger_dispatcher.return_value.dispatch.assert_called_once_with(
            'core.st2.generic.inquiry',
            {
                'users': [],
                'roles': [],
                'id': None,
                'tag': "developers",
                'response': {},
                'schema': {}
            }
        )
        mock_action_service.request_pause.assert_not_called()
        mock_trigger_dispatcher.reset_mock()
        mock_action_utils.reset_mock()
        mock_action_service.reset_mock()

    def _get_mock_action_obj(self):
        action = mock.Mock()
        action.pack = SYSTEM_PACK_NAME
        action.users = []
        action.roles = []
        return action

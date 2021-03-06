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

from inquirer_runner import inquirer_runner
from st2common.constants import action as action_constants
from st2common.constants import pack as pack_constants
from st2common.persistence import execution as ex_db_access
from st2common.services import action as action_service
from st2common.transport import reactor as reactor_transport
from st2common.util import action_db as action_utils
from st2tests import base as st2tests


mock_exc_get = mock.Mock()
mock_exc_get.id = "abcdef"

mock_inquiry_liveaction_db = mock.Mock()
mock_inquiry_liveaction_db.result = {"response": {}}

mock_action_utils = mock.Mock()
mock_action_utils.return_value = mock_inquiry_liveaction_db

test_parent = mock.Mock()
test_parent.id = "1234567890"

mock_get_root = mock.Mock()
mock_get_root.return_value = test_parent

mock_trigger_dispatcher = mock.Mock()
mock_request_pause = mock.Mock()

test_user = "st2admin"

runner_params = {"users": [], "roles": [], "route": "developers", "schema": {}}


@mock.patch.object(reactor_transport, "TriggerDispatcher", mock_trigger_dispatcher)
@mock.patch.object(action_utils, "get_liveaction_by_id", mock_action_utils)
@mock.patch.object(action_service, "request_pause", mock_request_pause)
@mock.patch.object(action_service, "get_root_liveaction", mock_get_root)
@mock.patch.object(
    ex_db_access.ActionExecution, "get", mock.MagicMock(return_value=mock_exc_get)
)
class InquiryTestCase(st2tests.RunnerTestCase):
    def tearDown(self):
        mock_trigger_dispatcher.reset_mock()
        mock_action_utils.reset_mock()
        mock_get_root.reset_mock()
        mock_request_pause.reset_mock()

    def test_runner_creation(self):
        runner = inquirer_runner.get_runner()
        self.assertIsNotNone(runner, "Creation failed. No instance.")
        self.assertEqual(
            type(runner), inquirer_runner.Inquirer, "Creation failed. No instance."
        )

    def test_simple_inquiry(self):
        runner = inquirer_runner.get_runner()
        runner.context = {"user": test_user}
        runner.action = self._get_mock_action_obj()
        runner.runner_parameters = runner_params
        runner.pre_run()

        mock_inquiry_liveaction_db.context = {"parent": test_parent.id}
        runner.liveaction = mock_inquiry_liveaction_db

        (status, output, _) = runner.run({})

        self.assertEqual(status, action_constants.LIVEACTION_STATUS_PENDING)
        self.assertEqual(
            output,
            {
                "users": [],
                "roles": [],
                "route": "developers",
                "schema": {},
                "ttl": 1440,
            },
        )

        mock_trigger_dispatcher.return_value.dispatch.assert_called_once_with(
            "core.st2.generic.inquiry", {"id": mock_exc_get.id, "route": "developers"}
        )

        runner.post_run(action_constants.LIVEACTION_STATUS_PENDING, {})

        mock_request_pause.assert_called_once_with(test_parent, test_user)

    def test_inquiry_no_parent(self):
        """Should behave like a regular execution, but without requesting a pause"""

        runner = inquirer_runner.get_runner()
        runner.context = {"user": "st2admin"}
        runner.action = self._get_mock_action_obj()
        runner.runner_parameters = runner_params
        runner.pre_run()
        mock_inquiry_liveaction_db.context = {"parent": None}
        (status, output, _) = runner.run({})
        self.assertEqual(status, action_constants.LIVEACTION_STATUS_PENDING)
        self.assertEqual(
            output,
            {
                "users": [],
                "roles": [],
                "route": "developers",
                "schema": {},
                "ttl": 1440,
            },
        )
        mock_trigger_dispatcher.return_value.dispatch.assert_called_once_with(
            "core.st2.generic.inquiry", {"id": mock_exc_get.id, "route": "developers"}
        )
        mock_request_pause.assert_not_called()

    def _get_mock_action_obj(self):
        action = mock.Mock()
        action.pack = pack_constants.SYSTEM_PACK_NAME
        action.users = []
        action.roles = []
        return action

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

import uuid

import mock

from st2actions.query.mistral import v2 as mistral
from st2common.constants import action as action_constants
from st2common.services import action as action_service
from st2tests import DbTestCase


MOCK_WF_TASKS_SUCCEEDED = [
    {'name': 'task1', 'state': 'SUCCESS'},
    {'name': 'task2', 'state': 'SUCCESS'}
]

MOCK_WF_TASKS_ERRORED = [
    {'name': 'task1', 'state': 'SUCCESS'},
    {'name': 'task2', 'state': 'ERROR'}
]

MOCK_WF_TASKS_RUNNING = [
    {'name': 'task1', 'state': 'SUCCESS'},
    {'name': 'task2', 'state': 'RUNNING'}
]


class MistralQuerierTest(DbTestCase):

    def setUp(self):
        super(MistralQuerierTest, self).setUp()
        self.querier = mistral.get_query_instance()

    @mock.patch.object(
        action_service, 'is_action_canceled_or_canceling',
        mock.MagicMock(return_value=False))
    def test_determine_status_wf_running_tasks_running(self):
        status = self.querier._determine_execution_status(uuid.uuid4().hex,
                                                          'RUNNING',
                                                          MOCK_WF_TASKS_RUNNING)

        self.assertEqual(action_constants.LIVEACTION_STATUS_RUNNING, status)

    @mock.patch.object(
        action_service, 'is_action_canceled_or_canceling',
        mock.MagicMock(return_value=False))
    def test_determine_status_wf_running_tasks_completed(self):
        status = self.querier._determine_execution_status(uuid.uuid4().hex,
                                                          'RUNNING',
                                                          MOCK_WF_TASKS_SUCCEEDED)

        self.assertEqual(action_constants.LIVEACTION_STATUS_RUNNING, status)

    @mock.patch.object(
        action_service, 'is_action_canceled_or_canceling',
        mock.MagicMock(return_value=False))
    def test_determine_status_wf_succeeded_tasks_completed(self):
        status = self.querier._determine_execution_status(uuid.uuid4().hex,
                                                          'SUCCESS',
                                                          MOCK_WF_TASKS_SUCCEEDED)

        self.assertEqual(action_constants.LIVEACTION_STATUS_SUCCEEDED, status)

    @mock.patch.object(
        action_service, 'is_action_canceled_or_canceling',
        mock.MagicMock(return_value=False))
    def test_determine_status_wf_succeeded_tasks_running(self):
        status = self.querier._determine_execution_status(uuid.uuid4().hex,
                                                          'SUCCESS',
                                                          MOCK_WF_TASKS_RUNNING)

        self.assertEqual(action_constants.LIVEACTION_STATUS_RUNNING, status)

    @mock.patch.object(
        action_service, 'is_action_canceled_or_canceling',
        mock.MagicMock(return_value=False))
    def test_determine_status_wf_errored_tasks_completed(self):
        status = self.querier._determine_execution_status(uuid.uuid4().hex,
                                                          'ERROR',
                                                          MOCK_WF_TASKS_SUCCEEDED)

        self.assertEqual(action_constants.LIVEACTION_STATUS_FAILED, status)

    @mock.patch.object(
        action_service, 'is_action_canceled_or_canceling',
        mock.MagicMock(return_value=False))
    def test_determine_status_wf_errored_tasks_running(self):
        status = self.querier._determine_execution_status(uuid.uuid4().hex,
                                                          'ERROR',
                                                          MOCK_WF_TASKS_RUNNING)

        self.assertEqual(action_constants.LIVEACTION_STATUS_RUNNING, status)

    @mock.patch.object(
        action_service, 'is_action_canceled_or_canceling',
        mock.MagicMock(return_value=True))
    def test_determine_status_wf_incomplete_tasks_completed_exec_canceled(self):
        status = self.querier._determine_execution_status(uuid.uuid4().hex,
                                                          'PAUSED',
                                                          MOCK_WF_TASKS_SUCCEEDED)

        self.assertEqual(action_constants.LIVEACTION_STATUS_CANCELED, status)

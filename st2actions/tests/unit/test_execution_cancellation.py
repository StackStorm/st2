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

from __future__ import absolute_import
import mock
import six
import uuid
from collections import defaultdict

from oslo_config import cfg

# XXX: actionsensor import depends on config being setup.
import st2tests.config as tests_config
tests_config.parse_args()

from st2common.constants import action as action_constants
from st2common.models.api.action import ActionAPI
from st2common.models.api.action import RunnerTypeAPI
from st2common.models.db.liveaction import LiveActionDB
from st2common.persistence.action import Action
from st2common.persistence.action import LiveAction
from st2common.persistence.runner import RunnerType
from st2common.runners import base as runners
from st2common.services import action as action_service
from st2common.services import trace as trace_service
from st2common.transport.liveaction import LiveActionPublisher
from st2common.transport.publishers import CUDPublisher
from st2common.util import loader
from st2tests import DbTestCase
from st2tests.fixturesloader import FixturesLoader
from st2tests.mocks.execution import MockExecutionPublisher
from st2tests.mocks.liveaction import MockLiveActionPublisher


TEST_FIXTURES = {
    'runners': [
        'testrunner1.yaml'
    ],
    'actions': [
        'action1.yaml'
    ]
}

PACK = 'generic'
LOADER = FixturesLoader()
FIXTURES = LOADER.load_fixtures(fixtures_pack=PACK, fixtures_dict=TEST_FIXTURES)


class ExecutionCancellationTest(DbTestCase):

    @classmethod
    def setUpClass(cls):
        super(ExecutionCancellationTest, cls).setUpClass()

        for _, fixture in six.iteritems(FIXTURES['runners']):
            instance = RunnerTypeAPI(**fixture)
            RunnerType.add_or_update(RunnerTypeAPI.to_model(instance))

        for _, fixture in six.iteritems(FIXTURES['actions']):
            instance = ActionAPI(**fixture)
            Action.add_or_update(ActionAPI.to_model(instance))

    @classmethod
    def tearDownClass(cls):
        # Unset the cache for the runner modules
        loader.RUNNER_MODULES_CACHE = defaultdict(dict)

        super(ExecutionCancellationTest, cls).tearDownClass()

    def tearDown(self):
        # Ensure all liveactions are canceled at end of each test.
        for liveaction in LiveAction.get_all():
            action_service.update_status(
                liveaction, action_constants.LIVEACTION_STATUS_CANCELED)

    @classmethod
    def get_runner_class(cls, runner_name):
        return runners.get_runner(runner_name, runner_name).__class__

    @mock.patch.object(
        CUDPublisher, 'publish_create',
        mock.MagicMock(side_effect=MockLiveActionPublisher.publish_create))
    @mock.patch.object(
        CUDPublisher, 'publish_update',
        mock.MagicMock(side_effect=MockExecutionPublisher.publish_update))
    @mock.patch.object(
        LiveActionPublisher, 'publish_state',
        mock.MagicMock(side_effect=MockLiveActionPublisher.publish_state))
    def test_basic_cancel(self):
        runner_cls = self.get_runner_class('runner')
        runner_run_result = (action_constants.LIVEACTION_STATUS_RUNNING, 'foobar', None)
        runner_cls.run = mock.Mock(return_value=runner_run_result)

        liveaction = LiveActionDB(action='wolfpack.action-1', parameters={'actionstr': 'foo'})
        liveaction, _ = action_service.request(liveaction)
        liveaction = LiveAction.get_by_id(str(liveaction.id))
        self.assertEqual(liveaction.status, action_constants.LIVEACTION_STATUS_RUNNING)

        # Cancel execution.
        action_service.request_cancellation(liveaction, cfg.CONF.system_user.user)
        liveaction = LiveAction.get_by_id(str(liveaction.id))
        self.assertEqual(liveaction.status, action_constants.LIVEACTION_STATUS_CANCELED)

    @mock.patch.object(
        CUDPublisher, 'publish_create',
        mock.MagicMock(side_effect=MockLiveActionPublisher.publish_create))
    @mock.patch.object(
        CUDPublisher, 'publish_update',
        mock.MagicMock(side_effect=MockExecutionPublisher.publish_update))
    @mock.patch.object(
        LiveActionPublisher, 'publish_state',
        mock.MagicMock(side_effect=MockLiveActionPublisher.publish_state))
    @mock.patch.object(
        runners.ActionRunner, 'cancel',
        mock.MagicMock(side_effect=Exception('Mock cancellation failure.')))
    def test_failed_cancel(self):
        runner_cls = self.get_runner_class('runner')
        runner_run_result = (action_constants.LIVEACTION_STATUS_RUNNING, 'foobar', None)
        runner_cls.run = mock.Mock(return_value=runner_run_result)

        liveaction = LiveActionDB(action='wolfpack.action-1', parameters={'actionstr': 'foo'})
        liveaction, _ = action_service.request(liveaction)
        liveaction = LiveAction.get_by_id(str(liveaction.id))
        self.assertEqual(liveaction.status, action_constants.LIVEACTION_STATUS_RUNNING)

        # Cancel execution.
        action_service.request_cancellation(liveaction, cfg.CONF.system_user.user)

        # Cancellation failed and execution state remains "canceling".
        runners.ActionRunner.cancel.assert_called_once_with()
        liveaction = LiveAction.get_by_id(str(liveaction.id))
        self.assertEqual(liveaction.status, action_constants.LIVEACTION_STATUS_CANCELING)

    @mock.patch.object(
        CUDPublisher, 'publish_create',
        mock.MagicMock(return_value=None))
    @mock.patch.object(
        LiveActionPublisher, 'publish_state',
        mock.MagicMock(return_value=None))
    @mock.patch.object(
        runners.ActionRunner, 'cancel',
        mock.MagicMock(return_value=None))
    def test_noop_cancel(self):
        liveaction = LiveActionDB(action='wolfpack.action-1', parameters={'actionstr': 'foo'})
        liveaction, _ = action_service.request(liveaction)
        liveaction = LiveAction.get_by_id(str(liveaction.id))
        self.assertEqual(liveaction.status, action_constants.LIVEACTION_STATUS_REQUESTED)

        # Cancel execution.
        action_service.request_cancellation(liveaction, cfg.CONF.system_user.user)

        # Cancel is only called when liveaction is still in running state.
        # Otherwise, the cancellation is only a state change.
        self.assertFalse(runners.ActionRunner.cancel.called)
        liveaction = LiveAction.get_by_id(str(liveaction.id))
        self.assertEqual(liveaction.status, action_constants.LIVEACTION_STATUS_CANCELED)

    @mock.patch.object(
        CUDPublisher, 'publish_create',
        mock.MagicMock(return_value=None))
    @mock.patch.object(
        LiveActionPublisher, 'publish_state',
        mock.MagicMock(return_value=None))
    @mock.patch.object(
        runners.ActionRunner, 'cancel',
        mock.MagicMock(return_value=None))
    def test_cancel_delayed_execution(self):
        liveaction = LiveActionDB(action='wolfpack.action-1', parameters={'actionstr': 'foo'})
        liveaction, _ = action_service.request(liveaction)
        liveaction = LiveAction.get_by_id(str(liveaction.id))
        self.assertEqual(liveaction.status, action_constants.LIVEACTION_STATUS_REQUESTED)

        # Manually update the liveaction from requested to delayed to mock concurrency policy.
        action_service.update_status(liveaction, action_constants.LIVEACTION_STATUS_DELAYED)
        liveaction = LiveAction.get_by_id(str(liveaction.id))
        self.assertEqual(liveaction.status, action_constants.LIVEACTION_STATUS_DELAYED)

        # Cancel execution.
        action_service.request_cancellation(liveaction, cfg.CONF.system_user.user)

        # Cancel is only called when liveaction is still in running state.
        # Otherwise, the cancellation is only a state change.
        self.assertFalse(runners.ActionRunner.cancel.called)
        liveaction = LiveAction.get_by_id(str(liveaction.id))
        self.assertEqual(liveaction.status, action_constants.LIVEACTION_STATUS_CANCELED)

    @mock.patch.object(
        CUDPublisher, 'publish_create',
        mock.MagicMock(return_value=None))
    @mock.patch.object(
        LiveActionPublisher, 'publish_state',
        mock.MagicMock(return_value=None))
    @mock.patch.object(
        trace_service, 'get_trace_db_by_live_action',
        mock.MagicMock(return_value=(None, None)))
    def test_cancel_delayed_execution_with_parent(self):
        liveaction = LiveActionDB(
            action='wolfpack.action-1',
            parameters={'actionstr': 'foo'},
            context={'parent': {'execution_id': uuid.uuid4().hex}}
        )

        liveaction, _ = action_service.request(liveaction)
        liveaction = LiveAction.get_by_id(str(liveaction.id))
        self.assertEqual(liveaction.status, action_constants.LIVEACTION_STATUS_REQUESTED)

        # Manually update the liveaction from requested to delayed to mock concurrency policy.
        action_service.update_status(liveaction, action_constants.LIVEACTION_STATUS_DELAYED)
        liveaction = LiveAction.get_by_id(str(liveaction.id))
        self.assertEqual(liveaction.status, action_constants.LIVEACTION_STATUS_DELAYED)

        # Cancel execution.
        action_service.request_cancellation(liveaction, cfg.CONF.system_user.user)

        # Cancel is only called when liveaction is still in running state.
        # Otherwise, the cancellation is only a state change.
        liveaction = LiveAction.get_by_id(str(liveaction.id))
        self.assertEqual(liveaction.status, action_constants.LIVEACTION_STATUS_CANCELING)

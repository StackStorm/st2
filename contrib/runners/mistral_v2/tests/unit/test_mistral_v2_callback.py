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
from mock import call
import requests

from mistralclient.api.v2 import action_executions
from oslo_config import cfg

# XXX: actionsensor import depends on config being setup.
import st2tests.config as tests_config
tests_config.parse_args()

from st2common.bootstrap import actionsregistrar
from st2common.bootstrap import runnersregistrar
from st2common.constants import action as action_constants
from st2common.models.db.liveaction import LiveActionDB
from st2common.persistence.liveaction import LiveAction
from st2common.runners import base as runners
from st2common.services import action as action_service
from st2common.transport.liveaction import LiveActionPublisher
from st2common.transport.publishers import CUDPublisher
from st2common.util import loader
from st2tests import DbTestCase
from st2tests import fixturesloader
from st2tests.mocks.liveaction import MockLiveActionPublisher


MISTRAL_RUNNER_NAME = 'mistral_v2'
TEST_PACK = 'mistral_tests'
TEST_PACK_PATH = fixturesloader.get_fixtures_packs_base_path() + '/' + TEST_PACK

PACKS = [
    TEST_PACK_PATH,
    fixturesloader.get_fixtures_packs_base_path() + '/core'
]

NON_EMPTY_RESULT = 'non-empty'


@mock.patch.object(
    CUDPublisher,
    'publish_update',
    mock.MagicMock(return_value=None))
@mock.patch.object(
    CUDPublisher,
    'publish_create',
    mock.MagicMock(side_effect=MockLiveActionPublisher.publish_create))
@mock.patch.object(
    LiveActionPublisher,
    'publish_state',
    mock.MagicMock(side_effect=MockLiveActionPublisher.publish_state))
class MistralRunnerCallbackTest(DbTestCase):

    @classmethod
    def setUpClass(cls):
        super(MistralRunnerCallbackTest, cls).setUpClass()

        # Override the retry configuration here otherwise st2tests.config.parse_args
        # in DbTestCase.setUpClass will reset these overrides.
        cfg.CONF.set_override('retry_exp_msec', 100, group='mistral')
        cfg.CONF.set_override('retry_exp_max_msec', 200, group='mistral')
        cfg.CONF.set_override('retry_stop_max_msec', 200, group='mistral')
        cfg.CONF.set_override('api_url', 'http://0.0.0.0:9101', group='auth')

        # Register runners.
        runnersregistrar.register_runners()

        # Register test pack(s).
        actions_registrar = actionsregistrar.ActionsRegistrar(
            use_pack_cache=False,
            fail_on_failure=True
        )

        for pack in PACKS:
            actions_registrar.register_from_pack(pack)

        # Get an instance of the callback module and reference to mistral status map
        cls.callback_module = loader.register_callback_module(MISTRAL_RUNNER_NAME)
        cls.callback_class = cls.callback_module.get_instance()
        cls.status_map = cls.callback_module.STATUS_MAP

    @classmethod
    def get_runner_class(cls, runner_name):
        return runners.get_runner(runner_name).__class__

    def test_callback_handler_status_map(self):
        # Ensure all StackStorm status are mapped otherwise leads to zombie workflow.
        self.assertListEqual(sorted(self.status_map.keys()),
                             sorted(action_constants.LIVEACTION_STATUSES))

    @mock.patch.object(
        action_executions.ActionExecutionManager, 'update',
        mock.MagicMock(return_value=None))
    def test_callback_handler_with_result_as_text(self):
        self.callback_class.callback('http://127.0.0.1:8989/v2/action_executions/12345', {},
                                     action_constants.LIVEACTION_STATUS_SUCCEEDED,
                                     '<html></html>')

    @mock.patch.object(
        action_executions.ActionExecutionManager, 'update',
        mock.MagicMock(return_value=None))
    def test_callback_handler_with_result_as_dict(self):
        self.callback_class.callback('http://127.0.0.1:8989/v2/action_executions/12345', {},
                                     action_constants.LIVEACTION_STATUS_SUCCEEDED, {'a': 1})

    @mock.patch.object(
        action_executions.ActionExecutionManager, 'update',
        mock.MagicMock(return_value=None))
    def test_callback_handler_with_result_as_json_str(self):
        self.callback_class.callback('http://127.0.0.1:8989/v2/action_executions/12345', {},
                                     action_constants.LIVEACTION_STATUS_SUCCEEDED, '{"a": 1}')
        self.callback_class.callback('http://127.0.0.1:8989/v2/action_executions/12345', {},
                                     action_constants.LIVEACTION_STATUS_SUCCEEDED, "{'a': 1}")

    @mock.patch.object(
        action_executions.ActionExecutionManager, 'update',
        mock.MagicMock(return_value=None))
    def test_callback_handler_with_result_as_list(self):
        self.callback_class.callback('http://127.0.0.1:8989/v2/action_executions/12345', {},
                                     action_constants.LIVEACTION_STATUS_SUCCEEDED,
                                     ["a", "b", "c"])

    @mock.patch.object(
        action_executions.ActionExecutionManager, 'update',
        mock.MagicMock(return_value=None))
    def test_callback_handler_with_result_as_list_str(self):
        self.callback_class.callback('http://127.0.0.1:8989/v2/action_executions/12345', {},
                                     action_constants.LIVEACTION_STATUS_SUCCEEDED,
                                     '["a", "b", "c"]')

    @mock.patch.object(
        action_executions.ActionExecutionManager, 'update',
        mock.MagicMock(return_value=None))
    def test_callback(self):
        local_runner_cls = self.get_runner_class('local_runner')

        liveaction = LiveActionDB(
            action='core.local', parameters={'cmd': 'uname -a'},
            callback={
                'source': MISTRAL_RUNNER_NAME,
                'url': 'http://127.0.0.1:8989/v2/action_executions/12345'
            }
        )

        for status in action_constants.LIVEACTION_COMPLETED_STATES:
            expected_mistral_status = self.status_map[status]
            local_runner_cls.run = mock.Mock(return_value=(status, NON_EMPTY_RESULT, None))
            liveaction, execution = action_service.request(liveaction)
            liveaction = LiveAction.get_by_id(str(liveaction.id))
            self.assertEqual(liveaction.status, status)
            action_executions.ActionExecutionManager.update.assert_called_with(
                '12345', state=expected_mistral_status, output=NON_EMPTY_RESULT)

    @mock.patch.object(
        action_executions.ActionExecutionManager, 'update',
        mock.MagicMock(return_value=None))
    def test_callback_incomplete_state(self):
        local_runner_cls = self.get_runner_class('local_runner')
        local_run_result = (action_constants.LIVEACTION_STATUS_RUNNING, NON_EMPTY_RESULT, None)
        local_runner_cls.run = mock.Mock(return_value=local_run_result)

        liveaction = LiveActionDB(
            action='core.local', parameters={'cmd': 'uname -a'},
            callback={
                'source': MISTRAL_RUNNER_NAME,
                'url': 'http://127.0.0.1:8989/v2/action_executions/12345'
            }
        )

        liveaction, execution = action_service.request(liveaction)
        liveaction = LiveAction.get_by_id(str(liveaction.id))
        self.assertEqual(liveaction.status, action_constants.LIVEACTION_STATUS_RUNNING)
        self.assertFalse(action_executions.ActionExecutionManager.update.called)

    @mock.patch.object(
        action_executions.ActionExecutionManager, 'update',
        mock.MagicMock(side_effect=[
            requests.exceptions.ConnectionError(),
            None]))
    def test_callback_retry(self):
        local_runner_cls = self.get_runner_class('local_runner')
        local_run_result = (action_constants.LIVEACTION_STATUS_SUCCEEDED, NON_EMPTY_RESULT, None)
        local_runner_cls.run = mock.Mock(return_value=local_run_result)

        liveaction = LiveActionDB(
            action='core.local', parameters={'cmd': 'uname -a'},
            callback={
                'source': MISTRAL_RUNNER_NAME,
                'url': 'http://127.0.0.1:8989/v2/action_executions/12345'
            }
        )

        liveaction, execution = action_service.request(liveaction)
        liveaction = LiveAction.get_by_id(str(liveaction.id))
        self.assertEqual(liveaction.status, action_constants.LIVEACTION_STATUS_SUCCEEDED)

        calls = [call('12345', state='SUCCESS', output=NON_EMPTY_RESULT) for i in range(0, 2)]
        action_executions.ActionExecutionManager.update.assert_has_calls(calls)

    @mock.patch.object(
        action_executions.ActionExecutionManager, 'update',
        mock.MagicMock(side_effect=[
            requests.exceptions.ConnectionError(),
            requests.exceptions.ConnectionError(),
            requests.exceptions.ConnectionError(),
            requests.exceptions.ConnectionError(),
            None]))
    def test_callback_retry_exhausted(self):
        local_runner_cls = self.get_runner_class('local_runner')
        local_run_result = (action_constants.LIVEACTION_STATUS_SUCCEEDED, NON_EMPTY_RESULT, None)
        local_runner_cls.run = mock.Mock(return_value=local_run_result)

        liveaction = LiveActionDB(
            action='core.local', parameters={'cmd': 'uname -a'},
            callback={
                'source': MISTRAL_RUNNER_NAME,
                'url': 'http://127.0.0.1:8989/v2/action_executions/12345'
            }
        )

        liveaction, execution = action_service.request(liveaction)
        liveaction = LiveAction.get_by_id(str(liveaction.id))
        self.assertEqual(liveaction.status, action_constants.LIVEACTION_STATUS_SUCCEEDED)

        # This test initially setup mock for action_executions.ActionExecutionManager.update
        # to fail the first 4 times and return success on the 5th times. The max attempts
        # is set to 3. We expect only 3 calls to pass thru the update method.
        calls = [call('12345', state='SUCCESS', output=NON_EMPTY_RESULT) for i in range(0, 2)]
        action_executions.ActionExecutionManager.update.assert_has_calls(calls)

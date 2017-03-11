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

import copy
import uuid

import mock
import yaml

from mistralclient.api.v2 import action_executions
from mistralclient.api.v2 import executions
from mistralclient.api.v2 import workflows
from oslo_config import cfg

# XXX: actionsensor import depends on config being setup.
import st2tests.config as tests_config
tests_config.parse_args()

from mistral_v2 import MistralRunner
import st2common
from st2common.bootstrap import actionsregistrar
from st2common.bootstrap import policiesregistrar
from st2common.bootstrap import runnersregistrar
from st2common.constants import action as action_constants
from st2common.models.db.liveaction import LiveActionDB
from st2common.persistence.liveaction import LiveAction
from st2common.persistence.policy import Policy
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

# Non-workbook with a single workflow
WF1_META_FILE_NAME = 'workflow_v2.yaml'
WF1_META_FILE_PATH = TEST_PACK_PATH + '/actions/' + WF1_META_FILE_NAME
WF1_META_CONTENT = loader.load_meta_file(WF1_META_FILE_PATH)
WF1_NAME = WF1_META_CONTENT['pack'] + '.' + WF1_META_CONTENT['name']
WF1_ENTRY_POINT = TEST_PACK_PATH + '/actions/' + WF1_META_CONTENT['entry_point']
WF1_ENTRY_POINT_X = WF1_ENTRY_POINT.replace(WF1_META_FILE_NAME, 'xformed_' + WF1_META_FILE_NAME)
WF1_SPEC = yaml.safe_load(MistralRunner.get_workflow_definition(WF1_ENTRY_POINT_X))
WF1_YAML = yaml.safe_dump(WF1_SPEC, default_flow_style=False)
WF1 = workflows.Workflow(None, {'name': WF1_NAME, 'definition': WF1_YAML})
MISTRAL_EXECUTION = {'id': str(uuid.uuid4()), 'state': 'RUNNING', 'workflow_name': WF1_NAME}
WF1_EXEC = copy.deepcopy(MISTRAL_EXECUTION)


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
class MistralRunnerPolicyTest(DbTestCase):

    @classmethod
    def setUpClass(cls):
        super(MistralRunnerPolicyTest, cls).setUpClass()

        # Override the retry configuration here otherwise st2tests.config.parse_args
        # in DbTestCase.setUpClass will reset these overrides.
        cfg.CONF.set_override('retry_exp_msec', 100, group='mistral')
        cfg.CONF.set_override('retry_exp_max_msec', 200, group='mistral')
        cfg.CONF.set_override('retry_stop_max_msec', 200, group='mistral')
        cfg.CONF.set_override('api_url', 'http://0.0.0.0:9101', group='auth')

    def setUp(self):
        super(MistralRunnerPolicyTest, self).setUp()

        # Start with a clean database for each test.
        self._establish_connection_and_re_create_db()

        # Register runners.
        runnersregistrar.register_runners()

        actions_registrar = actionsregistrar.ActionsRegistrar(
            use_pack_cache=False,
            fail_on_failure=True
        )

        for pack in PACKS:
            actions_registrar.register_from_pack(pack)

        # Register policies required for the tests.
        policiesregistrar.register_policy_types(st2common)

        policies_registrar = policiesregistrar.PolicyRegistrar(
            use_pack_cache=False,
            fail_on_failure=True
        )

        for pack in PACKS:
            policies_registrar.register_from_pack(pack)

    @classmethod
    def get_runner_class(cls, runner_name):
        return runners.get_runner(runner_name).__class__

    def _drop_all_other_policies(self, test_policy):
        policy_dbs = [policy_db for policy_db in Policy.get_all() if policy_db.ref != test_policy]

        for policy_db in policy_dbs:
            Policy.delete(policy_db, publish=False)

    @mock.patch.object(
        workflows.WorkflowManager, 'list',
        mock.MagicMock(return_value=[]))
    @mock.patch.object(
        workflows.WorkflowManager, 'get',
        mock.MagicMock(return_value=WF1))
    @mock.patch.object(
        workflows.WorkflowManager, 'create',
        mock.MagicMock(return_value=[WF1]))
    @mock.patch.object(
        executions.ExecutionManager, 'create',
        mock.MagicMock(return_value=executions.Execution(None, WF1_EXEC)))
    @mock.patch.object(
        action_executions.ActionExecutionManager, 'update',
        mock.MagicMock(return_value=None))
    def test_cancel_on_task_action_concurrency(self):
        # Delete other policies in the test pack to avoid conflicts.
        required_policy = 'mistral_tests.cancel_on_concurrency'
        self._drop_all_other_policies(required_policy)

        # Get threshold from the policy.
        policy = Policy.get_by_ref(required_policy)
        threshold = policy.parameters.get('threshold', 0)
        self.assertGreater(threshold, 0)

        # Launch instances of the workflow up to threshold.
        for i in range(0, threshold):
            liveaction = LiveActionDB(action=WF1_NAME, parameters={'friend': 'friend' + str(i)})
            liveaction, execution1 = action_service.request(liveaction)
            liveaction = LiveAction.get_by_id(str(liveaction.id))
            self.assertEqual(liveaction.status, action_constants.LIVEACTION_STATUS_RUNNING)

        # Check number of running instances
        running = LiveAction.count(
            action=WF1_NAME, status=action_constants.LIVEACTION_STATUS_RUNNING)

        self.assertEqual(running, threshold)

        # Mock the mistral runner cancel method to assert cancel is called.
        mistral_runner_cls = self.get_runner_class('mistral_v2')

        with mock.patch.object(mistral_runner_cls, 'cancel', mock.MagicMock(return_value=None)):
            # Launch another instance of the workflow with mistral callback defined
            # to indicate that this is executed under a workflow.
            callback = {
                'source': MISTRAL_RUNNER_NAME,
                'url': 'http://127.0.0.1:8989/v2/action_executions/12345'
            }

            params = {'friend': 'grande animalerie'}

            liveaction2 = LiveActionDB(action=WF1_NAME, parameters=params, callback=callback)
            liveaction2, execution2 = action_service.request(liveaction2)

            action_executions.ActionExecutionManager.update.assert_called_once_with(
                '12345',
                output='{"error": "Execution canceled by user."}',
                state='CANCELLED'
            )

            liveaction2 = LiveAction.get_by_id(str(liveaction2.id))
            self.assertEqual(liveaction2.status, action_constants.LIVEACTION_STATUS_CANCELED)

            # Assert cancel has been called.
            mistral_runner_cls.cancel.assert_called_once_with()

    @mock.patch.object(
        workflows.WorkflowManager, 'list',
        mock.MagicMock(return_value=[]))
    @mock.patch.object(
        workflows.WorkflowManager, 'get',
        mock.MagicMock(return_value=WF1))
    @mock.patch.object(
        workflows.WorkflowManager, 'create',
        mock.MagicMock(return_value=[WF1]))
    @mock.patch.object(
        executions.ExecutionManager, 'create',
        mock.MagicMock(return_value=executions.Execution(None, WF1_EXEC)))
    @mock.patch.object(
        action_executions.ActionExecutionManager, 'update',
        mock.MagicMock(return_value=None))
    def test_cancel_on_task_action_concurrency_by_attr(self):
        # Delete other policies in the test pack to avoid conflicts.
        required_policy = 'mistral_tests.cancel_on_concurrency_by_attr'
        self._drop_all_other_policies(required_policy)

        # Get threshold from the policy.
        policy = Policy.get_by_ref(required_policy)
        threshold = policy.parameters.get('threshold', 0)
        self.assertGreater(threshold, 0)

        params = {'friend': 'grande animalerie'}

        # Launch instances of the workflow up to threshold.
        for i in range(0, threshold):
            liveaction = LiveActionDB(action=WF1_NAME, parameters=params)
            liveaction, execution1 = action_service.request(liveaction)
            liveaction = LiveAction.get_by_id(str(liveaction.id))
            self.assertEqual(liveaction.status, action_constants.LIVEACTION_STATUS_RUNNING)

        # Check number of running instances
        running = LiveAction.count(
            action=WF1_NAME, status=action_constants.LIVEACTION_STATUS_RUNNING,
            parameters__friend=params['friend'])

        self.assertEqual(running, threshold)

        # Mock the mistral runner cancel method to assert cancel is called.
        mistral_runner_cls = self.get_runner_class('mistral_v2')

        with mock.patch.object(mistral_runner_cls, 'cancel', mock.MagicMock(return_value=None)):
            # Launch another instance of the workflow with mistral callback defined
            # to indicate that this is executed under a workflow.
            callback = {
                'source': MISTRAL_RUNNER_NAME,
                'url': 'http://127.0.0.1:8989/v2/action_executions/12345'
            }

            liveaction2 = LiveActionDB(action=WF1_NAME, parameters=params, callback=callback)
            liveaction2, execution2 = action_service.request(liveaction2)

            action_executions.ActionExecutionManager.update.assert_called_once_with(
                '12345',
                output='{"error": "Execution canceled by user."}',
                state='CANCELLED'
            )

            liveaction2 = LiveAction.get_by_id(str(liveaction2.id))
            self.assertEqual(liveaction2.status, action_constants.LIVEACTION_STATUS_CANCELED)

            # Assert cancel has been called.
            mistral_runner_cls.cancel.assert_called_once_with()

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

from mistralclient.api.v2 import executions
from mistralclient.api.v2 import workflows
from oslo_config import cfg

# XXX: actionsensor import depends on config being setup.
import st2tests.config as tests_config
tests_config.parse_args()

from mistral_v2 import MistralRunner
from st2common.bootstrap import actionsregistrar
from st2common.bootstrap import runnersregistrar
from st2common.constants import action as action_constants
from st2common.models.db.execution import ActionExecutionDB
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


TEST_PACK = 'mistral_tests'
TEST_PACK_PATH = fixturesloader.get_fixtures_packs_base_path() + '/' + TEST_PACK

PACKS = [
    TEST_PACK_PATH,
    fixturesloader.get_fixtures_packs_base_path() + '/core'
]

# Action executions requirements
ACTION_PARAMS = {'friend': 'Rocky'}
NON_EMPTY_RESULT = 'non-empty'

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
WF1_OLD = workflows.Workflow(None, {'name': WF1_NAME, 'definition': ''})
WF1_EXEC = {'id': str(uuid.uuid4()), 'state': 'RUNNING', 'workflow_name': WF1_NAME}
WF1_EXEC_PAUSED = copy.deepcopy(WF1_EXEC)
WF1_EXEC_PAUSED['state'] = 'PAUSED'

# Workflow with a subworkflow action
WF2_META_FILE_NAME = 'workflow_v2_call_workflow_action.yaml'
WF2_META_FILE_PATH = TEST_PACK_PATH + '/actions/' + WF2_META_FILE_NAME
WF2_META_CONTENT = loader.load_meta_file(WF2_META_FILE_PATH)
WF2_NAME = WF2_META_CONTENT['pack'] + '.' + WF2_META_CONTENT['name']
WF2_ENTRY_POINT = TEST_PACK_PATH + '/actions/' + WF2_META_CONTENT['entry_point']
WF2_ENTRY_POINT_X = WF2_ENTRY_POINT.replace(WF2_META_FILE_NAME, 'xformed_' + WF2_META_FILE_NAME)
WF2_SPEC = yaml.safe_load(MistralRunner.get_workflow_definition(WF2_ENTRY_POINT_X))
WF2_YAML = yaml.safe_dump(WF2_SPEC, default_flow_style=False)
WF2 = workflows.Workflow(None, {'name': WF2_NAME, 'definition': WF2_YAML})
WF2_EXEC = {'id': str(uuid.uuid4()), 'state': 'RUNNING', 'workflow_name': WF2_NAME}
WF2_EXEC_PAUSED = copy.deepcopy(WF2_EXEC)
WF2_EXEC_PAUSED['state'] = 'PAUSED'


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
class MistralRunnerPauseResumeTest(DbTestCase):

    @classmethod
    def setUpClass(cls):
        super(MistralRunnerPauseResumeTest, cls).setUpClass()

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

    @classmethod
    def get_runner_class(cls, runner_name):
        return runners.get_runner(runner_name).__class__

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
        executions.ExecutionManager, 'update',
        mock.MagicMock(return_value=executions.Execution(None, WF1_EXEC_PAUSED)))
    def test_pause(self):
        # Launch the workflow execution.
        liveaction = LiveActionDB(action=WF1_NAME, parameters=ACTION_PARAMS)
        liveaction, execution = action_service.request(liveaction)
        liveaction = LiveAction.get_by_id(str(liveaction.id))
        self.assertEqual(liveaction.status, action_constants.LIVEACTION_STATUS_RUNNING)

        mistral_context = liveaction.context.get('mistral', None)
        self.assertIsNotNone(mistral_context)
        self.assertEqual(mistral_context['execution_id'], WF1_EXEC.get('id'))
        self.assertEqual(mistral_context['workflow_name'], WF1_EXEC.get('workflow_name'))

        # Pause the workflow execution.
        requester = cfg.CONF.system_user.user
        liveaction, execution = action_service.request_pause(liveaction, requester)
        executions.ExecutionManager.update.assert_called_with(WF1_EXEC.get('id'), 'PAUSED')
        liveaction = LiveAction.get_by_id(str(liveaction.id))
        self.assertEqual(liveaction.status, action_constants.LIVEACTION_STATUS_PAUSING)

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
        executions.ExecutionManager, 'update',
        mock.MagicMock(side_effect=[
            executions.Execution(None, WF1_EXEC_PAUSED),
            executions.Execution(None, WF1_EXEC)]))
    def test_resume(self):
        # Launch the workflow execution.
        liveaction = LiveActionDB(action=WF1_NAME, parameters=ACTION_PARAMS)
        liveaction, execution = action_service.request(liveaction)
        liveaction = LiveAction.get_by_id(str(liveaction.id))
        self.assertEqual(liveaction.status, action_constants.LIVEACTION_STATUS_RUNNING)

        mistral_context = liveaction.context.get('mistral', None)
        self.assertIsNotNone(mistral_context)
        self.assertEqual(mistral_context['execution_id'], WF1_EXEC.get('id'))
        self.assertEqual(mistral_context['workflow_name'], WF1_EXEC.get('workflow_name'))

        # Pause the workflow execution.
        requester = cfg.CONF.system_user.user
        liveaction, execution = action_service.request_pause(liveaction, requester)
        executions.ExecutionManager.update.assert_called_with(WF1_EXEC.get('id'), 'PAUSED')
        liveaction = LiveAction.get_by_id(str(liveaction.id))
        self.assertEqual(liveaction.status, action_constants.LIVEACTION_STATUS_PAUSING)

        # Manually update the liveaction from pausing to paused. The paused state
        # is usually updated by the mistral querier.
        action_service.update_status(liveaction, action_constants.LIVEACTION_STATUS_PAUSED)
        liveaction = LiveAction.get_by_id(str(liveaction.id))
        self.assertEqual(liveaction.status, action_constants.LIVEACTION_STATUS_PAUSED)

        # Resume the workflow execution.
        liveaction, execution = action_service.request_resume(liveaction, requester)
        executions.ExecutionManager.update.assert_called_with(WF1_EXEC.get('id'), 'RUNNING')
        liveaction = LiveAction.get_by_id(str(liveaction.id))
        self.assertEqual(liveaction.status, action_constants.LIVEACTION_STATUS_RUNNING)

    @mock.patch.object(
        workflows.WorkflowManager, 'list',
        mock.MagicMock(return_value=[]))
    @mock.patch.object(
        workflows.WorkflowManager, 'get',
        mock.MagicMock(side_effect=[WF2, WF1]))
    @mock.patch.object(
        workflows.WorkflowManager, 'create',
        mock.MagicMock(side_effect=[[WF2], [WF1]]))
    @mock.patch.object(
        executions.ExecutionManager, 'create',
        mock.MagicMock(side_effect=[
            executions.Execution(None, WF2_EXEC),
            executions.Execution(None, WF1_EXEC)]))
    @mock.patch.object(
        executions.ExecutionManager, 'update',
        mock.MagicMock(side_effect=[
            executions.Execution(None, WF2_EXEC_PAUSED),
            executions.Execution(None, WF1_EXEC_PAUSED),
            executions.Execution(None, WF2_EXEC),
            executions.Execution(None, WF1_EXEC)]))
    def test_resume_subworkflow_action(self):
        requester = cfg.CONF.system_user.user

        liveaction1 = LiveActionDB(action=WF2_NAME, parameters=ACTION_PARAMS)
        liveaction1, execution1 = action_service.request(liveaction1)
        liveaction1 = LiveAction.get_by_id(str(liveaction1.id))
        self.assertEqual(liveaction1.status, action_constants.LIVEACTION_STATUS_RUNNING)

        liveaction2 = LiveActionDB(action=WF1_NAME, parameters=ACTION_PARAMS)
        liveaction2, execution2 = action_service.request(liveaction2)
        liveaction2 = LiveAction.get_by_id(str(liveaction2.id))
        self.assertEqual(liveaction2.status, action_constants.LIVEACTION_STATUS_RUNNING)

        # Mock the children of the parent execution to make this
        # test case has subworkflow execution.
        with mock.patch.object(
                ActionExecutionDB, 'children',
                new_callable=mock.PropertyMock) as action_ex_children_mock:
            action_ex_children_mock.return_value = [execution2.id]

            mistral_context = liveaction1.context.get('mistral', None)
            self.assertIsNotNone(mistral_context)
            self.assertEqual(mistral_context['execution_id'], WF2_EXEC.get('id'))
            self.assertEqual(mistral_context['workflow_name'], WF2_EXEC.get('workflow_name'))

            # Pause the parent liveaction and check that the request is cascaded down.
            liveaction1, execution1 = action_service.request_pause(liveaction1, requester)

            self.assertTrue(executions.ExecutionManager.update.called)
            self.assertEqual(executions.ExecutionManager.update.call_count, 2)

            calls = [
                mock.call(WF2_EXEC.get('id'), 'PAUSED'),
                mock.call(WF1_EXEC.get('id'), 'PAUSED')
            ]

            executions.ExecutionManager.update.assert_has_calls(calls, any_order=False)

            liveaction1 = LiveAction.get_by_id(str(liveaction1.id))
            self.assertEqual(liveaction1.status, action_constants.LIVEACTION_STATUS_PAUSING)

            liveaction2 = LiveAction.get_by_id(str(liveaction2.id))
            self.assertEqual(liveaction2.status, action_constants.LIVEACTION_STATUS_PAUSING)

            # Manually set the liveaction status to PAUSED.
            action_service.update_status(liveaction2, action_constants.LIVEACTION_STATUS_PAUSED)
            action_service.update_status(liveaction1, action_constants.LIVEACTION_STATUS_PAUSED)

            liveaction1 = LiveAction.get_by_id(str(liveaction1.id))
            self.assertEqual(liveaction1.status, action_constants.LIVEACTION_STATUS_PAUSED)

            liveaction2 = LiveAction.get_by_id(str(liveaction2.id))
            self.assertEqual(liveaction2.status, action_constants.LIVEACTION_STATUS_PAUSED)

            # Resume the parent liveaction and check that the request is cascaded down.
            liveaction1, execution1 = action_service.request_resume(liveaction1, requester)

            # Includes the previous calls.
            self.assertTrue(executions.ExecutionManager.update.called)
            self.assertEqual(executions.ExecutionManager.update.call_count, 4)

            calls = [
                mock.call(WF2_EXEC.get('id'), 'PAUSED'),
                mock.call(WF1_EXEC.get('id'), 'PAUSED'),
                mock.call(WF2_EXEC.get('id'), 'RUNNING'),
                mock.call(WF1_EXEC.get('id'), 'RUNNING')
            ]

            executions.ExecutionManager.update.assert_has_calls(calls, any_order=False)

            liveaction1 = LiveAction.get_by_id(str(liveaction1.id))
            self.assertEqual(liveaction1.status, action_constants.LIVEACTION_STATUS_RUNNING)

            liveaction2 = LiveAction.get_by_id(str(liveaction2.id))
            self.assertEqual(liveaction2.status, action_constants.LIVEACTION_STATUS_RUNNING)

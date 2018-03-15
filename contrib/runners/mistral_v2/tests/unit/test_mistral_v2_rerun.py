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
import copy
import uuid

import mock
import yaml

from mistralclient.api.v2 import executions
from mistralclient.api.v2 import tasks
from mistralclient.api.v2 import workbooks
from mistralclient.api.v2 import workflows
from oslo_config import cfg

# XXX: actionsensor import depends on config being setup.
import st2tests.config as tests_config
tests_config.parse_args()

from mistral_v2.mistral_v2 import MistralRunner
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


TEST_FIXTURES = {
    'workflows': [
        'workflow_v2.yaml',
        'workbook_v2_many_workflows.yaml'
    ],
    'actions': [
        'workflow_v2.yaml',
        'workbook_v2_many_workflows.yaml'
    ]
}

TEST_PACK = 'mistral_tests'
TEST_PACK_PATH = fixturesloader.get_fixtures_packs_base_path() + '/' + TEST_PACK

PACKS = [
    TEST_PACK_PATH,
    fixturesloader.get_fixtures_packs_base_path() + '/core'
]

# Action executions requirements
ACTION_PARAMS = {'friend': 'Rocky'}
NON_EMPTY_RESULT = 'non-empty'

# Workbook with multiple workflows
WB1_META_FILE_NAME = TEST_FIXTURES['workflows'][1]
WB1_META_FILE_PATH = TEST_PACK_PATH + '/actions/' + WB1_META_FILE_NAME
WB1_META_CONTENT = loader.load_meta_file(WB1_META_FILE_PATH)
WB1_NAME = WB1_META_CONTENT['pack'] + '.' + WB1_META_CONTENT['name']
WB1_ENTRY_POINT = TEST_PACK_PATH + '/actions/' + WB1_META_CONTENT['entry_point']
WB1_ENTRY_POINT_X = WB1_ENTRY_POINT.replace(WB1_META_FILE_NAME, 'xformed_' + WB1_META_FILE_NAME)
WB1_SPEC = yaml.safe_load(MistralRunner.get_workflow_definition(WB1_ENTRY_POINT_X))
WB1_YAML = yaml.safe_dump(WB1_SPEC, default_flow_style=False)
WB1 = workbooks.Workbook(None, {'name': WB1_NAME, 'definition': WB1_YAML})
WB1_MAIN_EXEC = {'id': str(uuid.uuid4()), 'state': 'RUNNING'}
WB1_MAIN_EXEC['workflow_name'] = WB1_NAME + '.main'
WB1_MAIN_EXEC_ERRORED = copy.deepcopy(WB1_MAIN_EXEC)
WB1_MAIN_EXEC_ERRORED['state'] = 'ERROR'
WB1_MAIN_TASK1 = {'id': str(uuid.uuid4()), 'name': 'greet', 'state': 'ERROR'}
WB1_MAIN_TASKS = [tasks.Task(None, WB1_MAIN_TASK1)]
WB1_MAIN_TASK_ID = WB1_MAIN_TASK1['id']
WB1_SUB1_EXEC = {'id': str(uuid.uuid4()), 'state': 'RUNNING', 'task_execution_id': WB1_MAIN_TASK_ID}
WB1_SUB1_EXEC['workflow_name'] = WB1_NAME + '.subflow1'
WB1_SUB1_EXEC_ERRORED = copy.deepcopy(WB1_SUB1_EXEC)
WB1_SUB1_EXEC_ERRORED['state'] = 'ERROR'
WB1_SUB1_TASK1 = {'id': str(uuid.uuid4()), 'name': 'say-greeting', 'state': 'SUCCESS'}
WB1_SUB1_TASK2 = {'id': str(uuid.uuid4()), 'name': 'say-friend', 'state': 'ERROR'}
WB1_SUB1_TASKS = [tasks.Task(None, WB1_SUB1_TASK1), tasks.Task(None, WB1_SUB1_TASK2)]

# Non-workbook with a single workflow
WF1_META_FILE_NAME = TEST_FIXTURES['workflows'][0]
WF1_META_FILE_PATH = TEST_PACK_PATH + '/actions/' + WF1_META_FILE_NAME
WF1_META_CONTENT = loader.load_meta_file(WF1_META_FILE_PATH)
WF1_NAME = WF1_META_CONTENT['pack'] + '.' + WF1_META_CONTENT['name']
WF1_ENTRY_POINT = TEST_PACK_PATH + '/actions/' + WF1_META_CONTENT['entry_point']
WF1_ENTRY_POINT_X = WF1_ENTRY_POINT.replace(WF1_META_FILE_NAME, 'xformed_' + WF1_META_FILE_NAME)
WF1_SPEC = yaml.safe_load(MistralRunner.get_workflow_definition(WF1_ENTRY_POINT_X))
WF1_YAML = yaml.safe_dump(WF1_SPEC, default_flow_style=False)
WF1 = workflows.Workflow(None, {'name': WF1_NAME, 'definition': WF1_YAML})
WF1_EXEC = {'id': str(uuid.uuid4()), 'state': 'ERROR', 'workflow_name': WF1_NAME}
WF1_EXEC_NOT_RERUNABLE = copy.deepcopy(WF1_EXEC)
WF1_EXEC_NOT_RERUNABLE['state'] = 'PAUSED'
WF1_TASK1 = {'id': str(uuid.uuid4()), 'name': 'say-greeting', 'state': 'SUCCESS'}
WF1_TASK2 = {'id': str(uuid.uuid4()), 'name': 'say-friend', 'state': 'SUCCESS'}
WF1_TASKS = [tasks.Task(None, WF1_TASK1), tasks.Task(None, WF1_TASK2)]


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
class MistralRunnerTest(DbTestCase):

    @classmethod
    def setUpClass(cls):
        super(MistralRunnerTest, cls).setUpClass()

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

    def setUp(self):
        super(MistralRunnerTest, self).setUp()

        # Mock the local runner run method.
        local_runner_cls = self.get_runner_class('local_runner', 'local_shell_command_runner')
        local_run_result = (action_constants.LIVEACTION_STATUS_SUCCEEDED, NON_EMPTY_RESULT, None)
        local_runner_cls.run = mock.Mock(return_value=local_run_result)

    @classmethod
    def get_runner_class(cls, package_name, module_name):
        return runners.get_runner(package_name, module_name).__class__

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
    def test_resume_option(self):
        patched_mistral_runner = self.get_runner_class('mistral_v2', 'mistral_v2')

        mock_resume_result = (
            action_constants.LIVEACTION_STATUS_RUNNING,
            {'tasks': []},
            {'execution_id': str(uuid.uuid4())}
        )

        with mock.patch.object(patched_mistral_runner, 'resume_workflow',
                               mock.MagicMock(return_value=mock_resume_result)):

            liveaction1 = LiveActionDB(action=WF1_NAME, parameters=ACTION_PARAMS)
            liveaction1, execution1 = action_service.request(liveaction1)
            self.assertFalse(patched_mistral_runner.resume_workflow.called)

            # Rerun the execution.
            context = {
                're-run': {
                    'ref': execution1.id,
                    'tasks': ['x']
                }
            }

            liveaction2 = LiveActionDB(action=WF1_NAME, parameters=ACTION_PARAMS, context=context)
            liveaction2, execution2 = action_service.request(liveaction2)
            liveaction2 = LiveAction.get_by_id(str(liveaction2.id))
            self.assertEqual(liveaction2.status, action_constants.LIVEACTION_STATUS_RUNNING)

            task_specs = {
                'x': {
                    'reset': False
                }
            }

            patched_mistral_runner.resume_workflow.assert_called_with(
                ex_ref=execution1,
                task_specs=task_specs
            )

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
    def test_resume_option_reset_tasks(self):
        patched_mistral_runner = self.get_runner_class('mistral_v2', 'mistral_v2')

        mock_resume_result = (
            action_constants.LIVEACTION_STATUS_RUNNING,
            {'tasks': []},
            {'execution_id': str(uuid.uuid4())}
        )

        with mock.patch.object(patched_mistral_runner, 'resume_workflow',
                               mock.MagicMock(return_value=mock_resume_result)):

            liveaction1 = LiveActionDB(action=WF1_NAME, parameters=ACTION_PARAMS)
            liveaction1, execution1 = action_service.request(liveaction1)
            self.assertFalse(patched_mistral_runner.resume_workflow.called)

            # Rerun the execution.
            context = {
                're-run': {
                    'ref': execution1.id,
                    'tasks': ['x', 'y'],
                    'reset': ['y']
                }
            }

            liveaction2 = LiveActionDB(action=WF1_NAME, parameters=ACTION_PARAMS, context=context)
            liveaction2, execution2 = action_service.request(liveaction2)
            liveaction2 = LiveAction.get_by_id(str(liveaction2.id))
            self.assertEqual(liveaction2.status, action_constants.LIVEACTION_STATUS_RUNNING)

            task_specs = {
                'x': {
                    'reset': False
                },
                'y': {
                    'reset': True
                }
            }

            patched_mistral_runner.resume_workflow.assert_called_with(
                ex_ref=execution1,
                task_specs=task_specs
            )

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
        mock.MagicMock(return_value=executions.Execution(None, WF1_EXEC_NOT_RERUNABLE)))
    @mock.patch.object(
        executions.ExecutionManager, 'get',
        mock.MagicMock(return_value=executions.Execution(None, WF1_EXEC_NOT_RERUNABLE)))
    @mock.patch.object(
        tasks.TaskManager, 'list',
        mock.MagicMock(return_value=WF1_TASKS))
    def test_resume_workflow_not_in_rerunable_state(self):
        liveaction1 = LiveActionDB(action=WF1_NAME, parameters=ACTION_PARAMS)
        liveaction1, execution1 = action_service.request(liveaction1)

        # Rerun the execution.
        context = {
            're-run': {
                'ref': execution1.id,
                'tasks': ['say-friend']
            }
        }

        liveaction2 = LiveActionDB(action=WF1_NAME, parameters=ACTION_PARAMS, context=context)
        liveaction2, execution2 = action_service.request(liveaction2)
        liveaction2 = LiveAction.get_by_id(str(liveaction2.id))
        self.assertEqual(liveaction2.status, action_constants.LIVEACTION_STATUS_FAILED)
        self.assertIn('not in a rerunable state', liveaction2.result.get('error'))

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
        executions.ExecutionManager, 'list',
        mock.MagicMock(return_value=[executions.Execution(None, WF1_EXEC)]))
    @mock.patch.object(
        executions.ExecutionManager, 'create',
        mock.MagicMock(return_value=executions.Execution(None, WF1_EXEC)))
    @mock.patch.object(
        executions.ExecutionManager, 'get',
        mock.MagicMock(return_value=executions.Execution(None, WF1_EXEC)))
    @mock.patch.object(
        tasks.TaskManager, 'list',
        mock.MagicMock(return_value=WF1_TASKS))
    def test_resume_tasks_not_in_rerunable_state(self):
        liveaction1 = LiveActionDB(action=WF1_NAME, parameters=ACTION_PARAMS)
        liveaction1, execution1 = action_service.request(liveaction1)

        # Rerun the execution.
        context = {
            're-run': {
                'ref': execution1.id,
                'tasks': ['say-friend']
            }
        }

        liveaction2 = LiveActionDB(action=WF1_NAME, parameters=ACTION_PARAMS, context=context)
        liveaction2, execution2 = action_service.request(liveaction2)
        liveaction2 = LiveAction.get_by_id(str(liveaction2.id))
        self.assertEqual(liveaction2.status, action_constants.LIVEACTION_STATUS_FAILED)
        self.assertIn('Unable to identify rerunable', liveaction2.result.get('error'))

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
        executions.ExecutionManager, 'list',
        mock.MagicMock(return_value=[executions.Execution(None, WF1_EXEC)]))
    @mock.patch.object(
        executions.ExecutionManager, 'create',
        mock.MagicMock(return_value=executions.Execution(None, WF1_EXEC)))
    @mock.patch.object(
        executions.ExecutionManager, 'get',
        mock.MagicMock(return_value=executions.Execution(None, WF1_EXEC)))
    @mock.patch.object(
        tasks.TaskManager, 'list',
        mock.MagicMock(return_value=WF1_TASKS))
    def test_resume_unidentified_tasks(self):
        liveaction1 = LiveActionDB(action=WF1_NAME, parameters=ACTION_PARAMS)
        liveaction1, execution1 = action_service.request(liveaction1)

        # Rerun the execution.
        context = {
            're-run': {
                'ref': execution1.id,
                'tasks': ['x']
            }
        }

        liveaction2 = LiveActionDB(action=WF1_NAME, parameters=ACTION_PARAMS, context=context)
        liveaction2, execution2 = action_service.request(liveaction2)
        liveaction2 = LiveAction.get_by_id(str(liveaction2.id))
        self.assertEqual(liveaction2.status, action_constants.LIVEACTION_STATUS_FAILED)
        self.assertIn('Unable to identify', liveaction2.result.get('error'))

    @mock.patch.object(
        workflows.WorkflowManager, 'list',
        mock.MagicMock(return_value=[]))
    @mock.patch.object(
        workflows.WorkflowManager, 'get',
        mock.MagicMock(return_value=WF1))
    @mock.patch.object(
        workbooks.WorkbookManager, 'create',
        mock.MagicMock(return_value=WB1))
    @mock.patch.object(
        executions.ExecutionManager, 'create',
        mock.MagicMock(return_value=executions.Execution(None, WB1_MAIN_EXEC)))
    @mock.patch.object(
        executions.ExecutionManager, 'update',
        mock.MagicMock(side_effect=[
            executions.Execution(None, WB1_MAIN_EXEC),
            executions.Execution(None, WB1_SUB1_EXEC)
        ]))
    @mock.patch.object(
        executions.ExecutionManager, 'get',
        mock.MagicMock(return_value=executions.Execution(None, WB1_MAIN_EXEC_ERRORED)))
    @mock.patch.object(
        executions.ExecutionManager, 'list',
        mock.MagicMock(side_effect=[
            [
                executions.Execution(None, WB1_MAIN_EXEC_ERRORED),
                executions.Execution(None, WB1_SUB1_EXEC_ERRORED)
            ],
            [
                executions.Execution(None, WB1_SUB1_EXEC_ERRORED)
            ]
        ]))
    @mock.patch.object(
        tasks.TaskManager, 'list',
        mock.MagicMock(side_effect=[
            WB1_MAIN_TASKS,     # First call of _get_tasks at mistral_v2 runner
            WB1_SUB1_TASKS,     # Recursive call of the first _get_tasks
            WB1_MAIN_TASKS,     # tasks.list in _update_workflow_env at mistral_v2 runner
            []                  # Resursive call of _update_workflow_env
        ]))
    @mock.patch.object(
        tasks.TaskManager, 'rerun',
        mock.MagicMock(return_value=None))
    def test_resume_subworkflow_task(self):
        liveaction1 = LiveActionDB(action=WB1_NAME, parameters=ACTION_PARAMS)
        liveaction1, execution1 = action_service.request(liveaction1)

        # Rerun the execution.
        context = {
            're-run': {
                'ref': execution1.id,
                'tasks': ['greet.say-friend']
            }
        }

        liveaction2 = LiveActionDB(action=WB1_NAME, parameters=ACTION_PARAMS, context=context)
        liveaction2, execution2 = action_service.request(liveaction2)
        liveaction2 = LiveAction.get_by_id(str(liveaction2.id))

        self.assertEqual(liveaction2.status, action_constants.LIVEACTION_STATUS_RUNNING)

        expected_env = {
            'st2_liveaction_id': str(liveaction2.id),
            'st2_execution_id': str(execution2.id),
            '__actions': {
                'st2.action': {
                    'st2_context': {
                        'api_url': 'http://0.0.0.0:9101/v1',
                        'endpoint': 'http://0.0.0.0:9101/v1/actionexecutions',
                        'notify': {},
                        'parent': {
                            'pack': 'mistral_tests',
                            're-run': context['re-run'],
                            'execution_id': str(execution2.id)
                        },
                        'skip_notify_tasks': []
                    }
                }
            },
            'st2_action_api_url': 'http://0.0.0.0:9101/v1'
        }

        tasks.TaskManager.rerun.assert_called_with(
            WB1_SUB1_TASK2['id'],
            reset=False,
            env=expected_env
        )

    @mock.patch.object(
        workflows.WorkflowManager, 'list',
        mock.MagicMock(return_value=[]))
    @mock.patch.object(
        workflows.WorkflowManager, 'get',
        mock.MagicMock(return_value=WF1))
    @mock.patch.object(
        workbooks.WorkbookManager, 'create',
        mock.MagicMock(return_value=WB1))
    @mock.patch.object(
        executions.ExecutionManager, 'create',
        mock.MagicMock(return_value=executions.Execution(None, WB1_MAIN_EXEC)))
    @mock.patch.object(
        executions.ExecutionManager, 'get',
        mock.MagicMock(return_value=executions.Execution(None, WB1_MAIN_EXEC_ERRORED)))
    @mock.patch.object(
        executions.ExecutionManager, 'list',
        mock.MagicMock(
            return_value=[
                executions.Execution(None, WB1_MAIN_EXEC_ERRORED),
                executions.Execution(None, WB1_SUB1_EXEC_ERRORED)]))
    @mock.patch.object(
        tasks.TaskManager, 'list',
        mock.MagicMock(side_effect=[WB1_MAIN_TASKS, WB1_SUB1_TASKS]))
    def test_resume_unidentified_subworkflow_task(self):
        liveaction1 = LiveActionDB(action=WB1_NAME, parameters=ACTION_PARAMS)
        liveaction1, execution1 = action_service.request(liveaction1)

        # Rerun the execution.
        context = {
            're-run': {
                'ref': execution1.id,
                'tasks': ['greet.x']
            }
        }

        liveaction2 = LiveActionDB(action=WB1_NAME, parameters=ACTION_PARAMS, context=context)
        liveaction2, execution2 = action_service.request(liveaction2)
        liveaction2 = LiveAction.get_by_id(str(liveaction2.id))
        self.assertEqual(liveaction2.status, action_constants.LIVEACTION_STATUS_FAILED)
        self.assertIn('Unable to identify', liveaction2.result.get('error'))

    @mock.patch.object(
        workflows.WorkflowManager, 'list',
        mock.MagicMock(return_value=[]))
    @mock.patch.object(
        workflows.WorkflowManager, 'get',
        mock.MagicMock(return_value=WF1))
    @mock.patch.object(
        workbooks.WorkbookManager, 'create',
        mock.MagicMock(return_value=WB1))
    @mock.patch.object(
        executions.ExecutionManager, 'create',
        mock.MagicMock(return_value=executions.Execution(None, WB1_MAIN_EXEC)))
    @mock.patch.object(
        executions.ExecutionManager, 'update',
        mock.MagicMock(side_effect=[
            executions.Execution(None, WB1_MAIN_EXEC),
            executions.Execution(None, WB1_SUB1_EXEC)
        ]))
    @mock.patch.object(
        executions.ExecutionManager, 'get',
        mock.MagicMock(return_value=executions.Execution(None, WB1_MAIN_EXEC_ERRORED)))
    @mock.patch.object(
        executions.ExecutionManager, 'list',
        mock.MagicMock(side_effect=[
            [
                executions.Execution(None, WB1_MAIN_EXEC_ERRORED),
                executions.Execution(None, WB1_SUB1_EXEC_ERRORED)
            ],
            [
                executions.Execution(None, WB1_SUB1_EXEC_ERRORED)
            ]
        ]))
    @mock.patch.object(
        tasks.TaskManager, 'list',
        mock.MagicMock(side_effect=[
            WB1_MAIN_TASKS,     # First call of _get_tasks at mistral_v2 runner
            WB1_SUB1_TASKS,     # Recursive call of the first _get_tasks
            WB1_MAIN_TASKS,     # tasks.list in _update_workflow_env at mistral_v2 runner
            []                  # Resursive call of _update_workflow_env
        ]))
    @mock.patch.object(
        tasks.TaskManager, 'rerun',
        mock.MagicMock(return_value=None))
    def test_resume_and_reset_subworkflow_task(self):
        liveaction1 = LiveActionDB(action=WB1_NAME, parameters=ACTION_PARAMS)
        liveaction1, execution1 = action_service.request(liveaction1)

        # Rerun the execution.
        context = {
            're-run': {
                'ref': execution1.id,
                'tasks': ['greet.say-friend'],
                'reset': ['greet.say-friend']
            }
        }

        liveaction2 = LiveActionDB(action=WB1_NAME, parameters=ACTION_PARAMS, context=context)
        liveaction2, execution2 = action_service.request(liveaction2)
        liveaction2 = LiveAction.get_by_id(str(liveaction2.id))

        self.assertEqual(liveaction2.status, action_constants.LIVEACTION_STATUS_RUNNING)

        expected_env = {
            'st2_liveaction_id': str(liveaction2.id),
            'st2_execution_id': str(execution2.id),
            '__actions': {
                'st2.action': {
                    'st2_context': {
                        'api_url': 'http://0.0.0.0:9101/v1',
                        'endpoint': 'http://0.0.0.0:9101/v1/actionexecutions',
                        'notify': {},
                        'parent': {
                            'pack': 'mistral_tests',
                            're-run': context['re-run'],
                            'execution_id': str(execution2.id)
                        },
                        'skip_notify_tasks': []
                    }
                }
            },
            'st2_action_api_url': 'http://0.0.0.0:9101/v1'
        }

        tasks.TaskManager.rerun.assert_called_with(
            WB1_SUB1_TASK2['id'],
            reset=True,
            env=expected_env
        )

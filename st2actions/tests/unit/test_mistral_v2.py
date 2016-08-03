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
from mock import call
import requests
import six
import yaml

from mistralclient.api.base import APIException
from mistralclient.api.v2 import action_executions
from mistralclient.api.v2 import executions
from mistralclient.api.v2 import workbooks
from mistralclient.api.v2 import workflows
from oslo_config import cfg

# XXX: actionsensor import depends on config being setup.
import st2tests.config as tests_config
tests_config.parse_args()

# Set defaults for retry options.
cfg.CONF.set_override('retry_exp_msec', 100, group='mistral')
cfg.CONF.set_override('retry_exp_max_msec', 200, group='mistral')
cfg.CONF.set_override('retry_stop_max_msec', 200, group='mistral')

import st2common.bootstrap.runnersregistrar as runners_registrar
from st2actions.handlers.mistral import MistralCallbackHandler
from st2actions.handlers.mistral import STATUS_MAP as mistral_status_map
from st2actions.runners.localrunner import LocalShellRunner
from st2actions.runners.mistral.v2 import MistralRunner
from st2common.constants import action as action_constants
from st2common.models.api.action import ActionAPI
from st2common.models.api.notification import NotificationsHelper
from st2common.models.db.liveaction import LiveActionDB
from st2common.persistence.action import Action
from st2common.persistence.liveaction import LiveAction
from st2common.services import action as action_service
from st2common.transport.liveaction import LiveActionPublisher
from st2common.transport.publishers import CUDPublisher
from st2tests import DbTestCase
from st2tests.fixturesloader import FixturesLoader
from tests.unit.base import MockLiveActionPublisher


TEST_FIXTURES = {
    'workflows': [
        'workbook_v2.yaml',
        'workbook_v2_many_workflows.yaml',
        'workbook_v2_many_workflows_no_default.yaml',
        'workflow_v2.yaml',
        'workflow_v2_many_workflows.yaml'
    ],
    'actions': [
        'workbook_v2.yaml',
        'workbook_v2_many_workflows.yaml',
        'workbook_v2_many_workflows_no_default.yaml',
        'workflow_v2.yaml',
        'workflow_v2_many_workflows.yaml',
        'workbook_v2_name_mismatch.yaml',
        'workflow_v2_name_mismatch.yaml',
        'local.yaml'
    ]
}

PACK = 'generic'
LOADER = FixturesLoader()
FIXTURES = LOADER.load_fixtures(fixtures_pack=PACK, fixtures_dict=TEST_FIXTURES)

MISTRAL_EXECUTION = {'id': str(uuid.uuid4()), 'state': 'RUNNING', 'workflow_name': None}

# Workbook with a single workflow
WB1_YAML_FILE_NAME = TEST_FIXTURES['workflows'][0]
WB1_YAML_FILE_PATH = LOADER.get_fixture_file_path_abs(PACK, 'workflows', WB1_YAML_FILE_NAME)
WB1_SPEC = FIXTURES['workflows'][WB1_YAML_FILE_NAME]
WB1_YAML = yaml.safe_dump(WB1_SPEC, default_flow_style=False)
WB1_NAME = '%s.%s' % (PACK, WB1_YAML_FILE_NAME.replace('.yaml', ''))
WB1 = workbooks.Workbook(None, {'name': WB1_NAME, 'definition': WB1_YAML})
WB1_OLD = workbooks.Workbook(None, {'name': WB1_NAME, 'definition': ''})
WB1_EXEC = copy.deepcopy(MISTRAL_EXECUTION)
WB1_EXEC['workflow_name'] = WB1_NAME

# Workbook with many workflows
WB2_YAML_FILE_NAME = TEST_FIXTURES['workflows'][1]
WB2_YAML_FILE_PATH = LOADER.get_fixture_file_path_abs(PACK, 'workflows', WB2_YAML_FILE_NAME)
WB2_SPEC = FIXTURES['workflows'][WB2_YAML_FILE_NAME]
WB2_YAML = yaml.safe_dump(WB2_SPEC, default_flow_style=False)
WB2_NAME = '%s.%s' % (PACK, WB2_YAML_FILE_NAME.replace('.yaml', ''))
WB2 = workbooks.Workbook(None, {'name': WB2_NAME, 'definition': WB2_YAML})
WB2_EXEC = copy.deepcopy(MISTRAL_EXECUTION)
WB2_EXEC['workflow_name'] = WB2_NAME

# Workbook with many workflows but no default workflow is defined
WB3_YAML_FILE_NAME = TEST_FIXTURES['workflows'][2]
WB3_YAML_FILE_PATH = LOADER.get_fixture_file_path_abs(PACK, 'workflows', WB3_YAML_FILE_NAME)
WB3_SPEC = FIXTURES['workflows'][WB3_YAML_FILE_NAME]
WB3_YAML = yaml.safe_dump(WB3_SPEC, default_flow_style=False)
WB3_NAME = '%s.%s' % (PACK, WB3_YAML_FILE_NAME.replace('.yaml', ''))
WB3 = workbooks.Workbook(None, {'name': WB3_NAME, 'definition': WB3_YAML})
WB3_EXEC = copy.deepcopy(MISTRAL_EXECUTION)
WB3_EXEC['workflow_name'] = WB3_NAME

# Non-workbook with a single workflow
WF1_YAML_FILE_NAME = TEST_FIXTURES['workflows'][3]
WF1_YAML_FILE_PATH = LOADER.get_fixture_file_path_abs(PACK, 'workflows', WF1_YAML_FILE_NAME)
WF1_SPEC = FIXTURES['workflows'][WF1_YAML_FILE_NAME]
WF1_YAML = yaml.safe_dump(WF1_SPEC, default_flow_style=False)
WF1_NAME = '%s.%s' % (PACK, WF1_YAML_FILE_NAME.replace('.yaml', ''))
WF1 = workflows.Workflow(None, {'name': WF1_NAME, 'definition': WF1_YAML})
WF1_OLD = workflows.Workflow(None, {'name': WF1_NAME, 'definition': ''})
WF1_EXEC = copy.deepcopy(MISTRAL_EXECUTION)
WF1_EXEC['workflow_name'] = WF1_NAME
WF1_EXEC_PAUSED = copy.deepcopy(WF1_EXEC)
WF1_EXEC_PAUSED['state'] = 'PAUSED'

# Non-workbook with a many workflows
WF2_YAML_FILE_NAME = TEST_FIXTURES['workflows'][4]
WF2_YAML_FILE_PATH = LOADER.get_fixture_file_path_abs(PACK, 'workflows', WF2_YAML_FILE_NAME)
WF2_SPEC = FIXTURES['workflows'][WF2_YAML_FILE_NAME]
WF2_YAML = yaml.safe_dump(WF2_SPEC, default_flow_style=False)
WF2_NAME = '%s.%s' % (PACK, WF2_YAML_FILE_NAME.replace('.yaml', ''))
WF2 = workflows.Workflow(None, {'name': WF2_NAME, 'definition': WF2_YAML})
WF2_EXEC = copy.deepcopy(MISTRAL_EXECUTION)
WF2_EXEC['workflow_name'] = WF2_NAME

# Action executions requirements
ACTION_PARAMS = {'friend': 'Rocky'}

NON_EMPTY_RESULT = 'non-empty'


@mock.patch.object(CUDPublisher, 'publish_update', mock.MagicMock(return_value=None))
@mock.patch.object(CUDPublisher, 'publish_create',
                   mock.MagicMock(side_effect=MockLiveActionPublisher.publish_create))
@mock.patch.object(LiveActionPublisher, 'publish_state',
                   mock.MagicMock(side_effect=MockLiveActionPublisher.publish_state))
class MistralRunnerTest(DbTestCase):

    @classmethod
    def setUpClass(cls):
        super(MistralRunnerTest, cls).setUpClass()
        runners_registrar.register_runner_types()

        for _, fixture in six.iteritems(FIXTURES['actions']):
            instance = ActionAPI(**fixture)
            Action.add_or_update(ActionAPI.to_model(instance))

    def setUp(self):
        super(MistralRunnerTest, self).setUp()
        cfg.CONF.set_override('api_url', 'http://0.0.0.0:9101', group='auth')

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
    def test_launch_workflow(self):
        MistralRunner.entry_point = mock.PropertyMock(return_value=WF1_YAML_FILE_PATH)
        liveaction = LiveActionDB(action=WF1_NAME, parameters=ACTION_PARAMS)
        liveaction, execution = action_service.request(liveaction)
        liveaction = LiveAction.get_by_id(str(liveaction.id))
        self.assertEqual(liveaction.status, action_constants.LIVEACTION_STATUS_RUNNING)

        mistral_context = liveaction.context.get('mistral', None)
        self.assertIsNotNone(mistral_context)
        self.assertEqual(mistral_context['execution_id'], WF1_EXEC.get('id'))
        self.assertEqual(mistral_context['workflow_name'], WF1_EXEC.get('workflow_name'))

        workflow_input = copy.deepcopy(ACTION_PARAMS)
        workflow_input.update({'count': '3'})

        env = {
            'st2_execution_id': str(execution.id),
            'st2_liveaction_id': str(liveaction.id),
            'st2_action_api_url': 'http://0.0.0.0:9101/v1',
            '__actions': {
                'st2.action': {
                    'st2_context': {
                        'api_url': 'http://0.0.0.0:9101/v1',
                        'endpoint': 'http://0.0.0.0:9101/v1/actionexecutions',
                        'parent': {
                            'execution_id': str(execution.id)
                        },
                        'notify': {},
                        'skip_notify_tasks': []
                    }
                }
            }
        }

        executions.ExecutionManager.create.assert_called_with(
            WF1_NAME, workflow_input=workflow_input, env=env)

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
    def test_launch_workflow_with_st2_https(self):
        cfg.CONF.set_override('api_url', 'https://0.0.0.0:9101', group='auth')

        MistralRunner.entry_point = mock.PropertyMock(return_value=WF1_YAML_FILE_PATH)
        liveaction = LiveActionDB(action=WF1_NAME, parameters=ACTION_PARAMS)
        liveaction, execution = action_service.request(liveaction)
        liveaction = LiveAction.get_by_id(str(liveaction.id))
        self.assertEqual(liveaction.status, action_constants.LIVEACTION_STATUS_RUNNING)

        mistral_context = liveaction.context.get('mistral', None)
        self.assertIsNotNone(mistral_context)
        self.assertEqual(mistral_context['execution_id'], WF1_EXEC.get('id'))
        self.assertEqual(mistral_context['workflow_name'], WF1_EXEC.get('workflow_name'))

        workflow_input = copy.deepcopy(ACTION_PARAMS)
        workflow_input.update({'count': '3'})

        env = {
            'st2_execution_id': str(execution.id),
            'st2_liveaction_id': str(liveaction.id),
            'st2_action_api_url': 'https://0.0.0.0:9101/v1',
            '__actions': {
                'st2.action': {
                    'st2_context': {
                        'api_url': 'https://0.0.0.0:9101/v1',
                        'endpoint': 'https://0.0.0.0:9101/v1/actionexecutions',
                        'parent': {
                            'execution_id': str(execution.id)
                        },
                        'notify': {},
                        'skip_notify_tasks': []
                    }
                }
            }
        }

        executions.ExecutionManager.create.assert_called_with(
            WF1_NAME, workflow_input=workflow_input, env=env)

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
    def test_launch_workflow_with_notifications(self):
        notify_data = {'on_complete': {'routes': ['slack'],
                       'message': '"@channel: Action succeeded."', 'data': {}}}

        MistralRunner.entry_point = mock.PropertyMock(return_value=WF1_YAML_FILE_PATH)
        liveaction = LiveActionDB(action=WF1_NAME, parameters=ACTION_PARAMS, notify=notify_data)
        liveaction, execution = action_service.request(liveaction)
        liveaction = LiveAction.get_by_id(str(liveaction.id))
        self.assertEqual(liveaction.status, action_constants.LIVEACTION_STATUS_RUNNING)

        mistral_context = liveaction.context.get('mistral', None)
        self.assertIsNotNone(mistral_context)
        self.assertEqual(mistral_context['execution_id'], WF1_EXEC.get('id'))
        self.assertEqual(mistral_context['workflow_name'], WF1_EXEC.get('workflow_name'))

        workflow_input = copy.deepcopy(ACTION_PARAMS)
        workflow_input.update({'count': '3'})

        env = {
            'st2_execution_id': str(execution.id),
            'st2_liveaction_id': str(liveaction.id),
            'st2_action_api_url': 'http://0.0.0.0:9101/v1',
            '__actions': {
                'st2.action': {
                    'st2_context': {
                        'api_url': 'http://0.0.0.0:9101/v1',
                        'endpoint': 'http://0.0.0.0:9101/v1/actionexecutions',
                        'parent': {
                            'execution_id': str(execution.id)
                        },
                        'notify': NotificationsHelper.from_model(liveaction.notify),
                        'skip_notify_tasks': []
                    }
                }
            }
        }

        executions.ExecutionManager.create.assert_called_with(
            WF1_NAME, workflow_input=workflow_input, env=env)

    @mock.patch.object(
        workflows.WorkflowManager, 'list',
        mock.MagicMock(side_effect=requests.exceptions.ConnectionError('Connection refused')))
    def test_launch_workflow_mistral_offline(self):
        MistralRunner.entry_point = mock.PropertyMock(return_value=WF1_YAML_FILE_PATH)
        liveaction = LiveActionDB(action=WF1_NAME, parameters=ACTION_PARAMS)
        liveaction, execution = action_service.request(liveaction)
        liveaction = LiveAction.get_by_id(str(liveaction.id))
        self.assertEqual(liveaction.status, action_constants.LIVEACTION_STATUS_FAILED)
        self.assertIn('Connection refused', liveaction.result['error'])

    @mock.patch.object(
        workflows.WorkflowManager, 'list',
        mock.MagicMock(side_effect=[requests.exceptions.ConnectionError(), []]))
    @mock.patch.object(
        workflows.WorkflowManager, 'get',
        mock.MagicMock(return_value=WF1))
    @mock.patch.object(
        workflows.WorkflowManager, 'create',
        mock.MagicMock(return_value=[WF1]))
    @mock.patch.object(
        executions.ExecutionManager, 'create',
        mock.MagicMock(return_value=executions.Execution(None, WF1_EXEC)))
    def test_launch_workflow_mistral_retry(self):
        MistralRunner.entry_point = mock.PropertyMock(return_value=WF1_YAML_FILE_PATH)
        liveaction = LiveActionDB(action=WF1_NAME, parameters=ACTION_PARAMS)
        liveaction, execution = action_service.request(liveaction)
        liveaction = LiveAction.get_by_id(str(liveaction.id))
        self.assertEqual(liveaction.status, action_constants.LIVEACTION_STATUS_RUNNING)

        mistral_context = liveaction.context.get('mistral', None)
        self.assertIsNotNone(mistral_context)
        self.assertEqual(mistral_context['execution_id'], WF1_EXEC.get('id'))
        self.assertEqual(mistral_context['workflow_name'], WF1_EXEC.get('workflow_name'))

    @mock.patch.object(
        workflows.WorkflowManager, 'list',
        mock.MagicMock(return_value=[]))
    @mock.patch.object(
        workflows.WorkflowManager, 'get',
        mock.MagicMock(return_value=WF1))
    @mock.patch.object(
        workflows.WorkflowManager, 'create',
        mock.MagicMock(side_effect=[APIException(error_message='Duplicate entry.'), WF1]))
    @mock.patch.object(
        executions.ExecutionManager, 'create',
        mock.MagicMock(return_value=executions.Execution(None, WF1_EXEC)))
    def test_launch_workflow_duplicate_error(self):
        MistralRunner.entry_point = mock.PropertyMock(return_value=WF1_YAML_FILE_PATH)
        liveaction = LiveActionDB(action=WF1_NAME, parameters=ACTION_PARAMS)
        liveaction, execution = action_service.request(liveaction)
        liveaction = LiveAction.get_by_id(str(liveaction.id))
        self.assertEqual(liveaction.status, action_constants.LIVEACTION_STATUS_RUNNING)

        mistral_context = liveaction.context.get('mistral', None)
        self.assertIsNotNone(mistral_context)
        self.assertEqual(mistral_context['execution_id'], WF1_EXEC.get('id'))
        self.assertEqual(mistral_context['workflow_name'], WF1_EXEC.get('workflow_name'))

    @mock.patch.object(
        workflows.WorkflowManager, 'list',
        mock.MagicMock(return_value=[]))
    @mock.patch.object(
        workflows.WorkflowManager, 'get',
        mock.MagicMock(return_value=WF1_OLD))
    @mock.patch.object(
        workflows.WorkflowManager, 'create',
        mock.MagicMock(return_value=[WF1]))
    @mock.patch.object(
        workflows.WorkflowManager, 'update',
        mock.MagicMock(return_value=[WF1]))
    @mock.patch.object(
        executions.ExecutionManager, 'create',
        mock.MagicMock(return_value=executions.Execution(None, WF1_EXEC)))
    def test_launch_when_workflow_definition_changed(self):
        MistralRunner.entry_point = mock.PropertyMock(return_value=WF1_YAML_FILE_PATH)
        liveaction = LiveActionDB(action=WF1_NAME, parameters=ACTION_PARAMS)
        liveaction, execution = action_service.request(liveaction)
        liveaction = LiveAction.get_by_id(str(liveaction.id))
        self.assertEqual(liveaction.status, action_constants.LIVEACTION_STATUS_RUNNING)

        mistral_context = liveaction.context.get('mistral', None)
        self.assertIsNotNone(mistral_context)
        self.assertEqual(mistral_context['execution_id'], WF1_EXEC.get('id'))
        self.assertEqual(mistral_context['workflow_name'], WF1_EXEC.get('workflow_name'))

    @mock.patch.object(
        workflows.WorkflowManager, 'list',
        mock.MagicMock(return_value=[]))
    @mock.patch.object(
        workflows.WorkflowManager, 'get',
        mock.MagicMock(side_effect=Exception()))
    @mock.patch.object(
        workbooks.WorkbookManager, 'delete',
        mock.MagicMock(side_effect=Exception()))
    @mock.patch.object(
        workflows.WorkflowManager, 'create',
        mock.MagicMock(return_value=[WF1]))
    @mock.patch.object(
        executions.ExecutionManager, 'create',
        mock.MagicMock(return_value=executions.Execution(None, WF1_EXEC)))
    def test_launch_when_workflow_not_exists(self):
        liveaction = LiveActionDB(action=WF1_NAME, parameters=ACTION_PARAMS)
        liveaction, execution = action_service.request(liveaction)
        liveaction = LiveAction.get_by_id(str(liveaction.id))
        self.assertEqual(liveaction.status, action_constants.LIVEACTION_STATUS_RUNNING)

        mistral_context = liveaction.context.get('mistral', None)
        self.assertIsNotNone(mistral_context)
        self.assertEqual(mistral_context['execution_id'], WF1_EXEC.get('id'))
        self.assertEqual(mistral_context['workflow_name'], WF1_EXEC.get('workflow_name'))

    @mock.patch.object(
        workflows.WorkflowManager, 'list',
        mock.MagicMock(return_value=[]))
    @mock.patch.object(
        workflows.WorkflowManager, 'get',
        mock.MagicMock(return_value=WF2))
    def test_launch_workflow_with_many_workflows(self):
        MistralRunner.entry_point = mock.PropertyMock(return_value=WF2_YAML_FILE_PATH)
        liveaction = LiveActionDB(action=WF2_NAME, parameters=ACTION_PARAMS)
        liveaction, execution = action_service.request(liveaction)
        liveaction = LiveAction.get_by_id(str(liveaction.id))
        self.assertEqual(liveaction.status, action_constants.LIVEACTION_STATUS_FAILED)
        self.assertIn('Multiple workflows is not supported.', liveaction.result['error'])

    @mock.patch.object(
        workflows.WorkflowManager, 'list',
        mock.MagicMock(return_value=[]))
    @mock.patch.object(
        workflows.WorkflowManager, 'get',
        mock.MagicMock(side_effect=Exception()))
    def test_launch_workflow_name_mistmatch(self):
        action_ref = 'generic.workflow_v2_name_mismatch'
        MistralRunner.entry_point = mock.PropertyMock(return_value=WF1_YAML_FILE_PATH)
        liveaction = LiveActionDB(action=action_ref, parameters=ACTION_PARAMS)
        liveaction, execution = action_service.request(liveaction)
        liveaction = LiveAction.get_by_id(str(liveaction.id))
        self.assertEqual(liveaction.status, action_constants.LIVEACTION_STATUS_FAILED)
        self.assertIn('Name of the workflow must be the same', liveaction.result['error'])

    @mock.patch.object(
        workflows.WorkflowManager, 'list',
        mock.MagicMock(return_value=[]))
    @mock.patch.object(
        workbooks.WorkbookManager, 'get',
        mock.MagicMock(return_value=WB1))
    @mock.patch.object(
        workbooks.WorkbookManager, 'create',
        mock.MagicMock(return_value=WB1))
    @mock.patch.object(
        workbooks.WorkbookManager, 'update',
        mock.MagicMock(return_value=WB1))
    @mock.patch.object(
        executions.ExecutionManager, 'create',
        mock.MagicMock(return_value=executions.Execution(None, WB1_EXEC)))
    def test_launch_workbook(self):
        MistralRunner.entry_point = mock.PropertyMock(return_value=WB1_YAML_FILE_PATH)
        liveaction = LiveActionDB(action=WB1_NAME, parameters=ACTION_PARAMS)
        liveaction, execution = action_service.request(liveaction)
        liveaction = LiveAction.get_by_id(str(liveaction.id))
        self.assertEqual(liveaction.status, action_constants.LIVEACTION_STATUS_RUNNING)

        mistral_context = liveaction.context.get('mistral', None)
        self.assertIsNotNone(mistral_context)
        self.assertEqual(mistral_context['execution_id'], WB1_EXEC.get('id'))
        self.assertEqual(mistral_context['workflow_name'], WB1_EXEC.get('workflow_name'))

    @mock.patch.object(
        workflows.WorkflowManager, 'list',
        mock.MagicMock(return_value=[]))
    @mock.patch.object(
        workbooks.WorkbookManager, 'get',
        mock.MagicMock(return_value=WB2))
    @mock.patch.object(
        workbooks.WorkbookManager, 'create',
        mock.MagicMock(return_value=WB2))
    @mock.patch.object(
        workbooks.WorkbookManager, 'update',
        mock.MagicMock(return_value=WB2))
    @mock.patch.object(
        executions.ExecutionManager, 'create',
        mock.MagicMock(return_value=executions.Execution(None, WB2_EXEC)))
    def test_launch_workbook_with_many_workflows(self):
        MistralRunner.entry_point = mock.PropertyMock(return_value=WB2_YAML_FILE_PATH)
        liveaction = LiveActionDB(action=WB2_NAME, parameters=ACTION_PARAMS)
        liveaction, execution = action_service.request(liveaction)
        liveaction = LiveAction.get_by_id(str(liveaction.id))
        self.assertEqual(liveaction.status, action_constants.LIVEACTION_STATUS_RUNNING)

        mistral_context = liveaction.context.get('mistral', None)
        self.assertIsNotNone(mistral_context)
        self.assertEqual(mistral_context['execution_id'], WB2_EXEC.get('id'))
        self.assertEqual(mistral_context['workflow_name'], WB2_EXEC.get('workflow_name'))

    @mock.patch.object(
        workflows.WorkflowManager, 'list',
        mock.MagicMock(return_value=[]))
    @mock.patch.object(
        workbooks.WorkbookManager, 'get',
        mock.MagicMock(return_value=WB3))
    @mock.patch.object(
        workbooks.WorkbookManager, 'create',
        mock.MagicMock(return_value=WB3))
    @mock.patch.object(
        workbooks.WorkbookManager, 'update',
        mock.MagicMock(return_value=WB3))
    @mock.patch.object(
        executions.ExecutionManager, 'create',
        mock.MagicMock(return_value=executions.Execution(None, WB3_EXEC)))
    def test_launch_workbook_with_many_workflows_no_default(self):
        MistralRunner.entry_point = mock.PropertyMock(return_value=WB3_YAML_FILE_PATH)
        liveaction = LiveActionDB(action=WB3_NAME, parameters=ACTION_PARAMS)
        liveaction, execution = action_service.request(liveaction)
        liveaction = LiveAction.get_by_id(str(liveaction.id))
        self.assertEqual(liveaction.status, action_constants.LIVEACTION_STATUS_FAILED)
        self.assertIn('Default workflow cannot be determined.', liveaction.result['error'])

    @mock.patch.object(
        workflows.WorkflowManager, 'list',
        mock.MagicMock(return_value=[]))
    @mock.patch.object(
        workbooks.WorkbookManager, 'get',
        mock.MagicMock(return_value=WB1_OLD))
    @mock.patch.object(
        workbooks.WorkbookManager, 'create',
        mock.MagicMock(return_value=WB1))
    @mock.patch.object(
        workbooks.WorkbookManager, 'update',
        mock.MagicMock(return_value=WB1))
    @mock.patch.object(
        executions.ExecutionManager, 'create',
        mock.MagicMock(return_value=executions.Execution(None, WB1_EXEC)))
    def test_launch_when_workbook_definition_changed(self):
        MistralRunner.entry_point = mock.PropertyMock(return_value=WB1_YAML_FILE_PATH)
        liveaction = LiveActionDB(action=WB1_NAME, parameters=ACTION_PARAMS)
        liveaction, execution = action_service.request(liveaction)
        liveaction = LiveAction.get_by_id(str(liveaction.id))
        self.assertEqual(liveaction.status, action_constants.LIVEACTION_STATUS_RUNNING)

        mistral_context = liveaction.context.get('mistral', None)
        self.assertIsNotNone(mistral_context)
        self.assertEqual(mistral_context['execution_id'], WB1_EXEC.get('id'))
        self.assertEqual(mistral_context['workflow_name'], WB1_EXEC.get('workflow_name'))

    @mock.patch.object(
        workflows.WorkflowManager, 'list',
        mock.MagicMock(return_value=[]))
    @mock.patch.object(
        workbooks.WorkbookManager, 'get',
        mock.MagicMock(side_effect=Exception()))
    @mock.patch.object(
        workflows.WorkflowManager, 'delete',
        mock.MagicMock(side_effect=Exception()))
    @mock.patch.object(
        workbooks.WorkbookManager, 'create',
        mock.MagicMock(return_value=WB1))
    @mock.patch.object(
        executions.ExecutionManager, 'create',
        mock.MagicMock(return_value=executions.Execution(None, WB1_EXEC)))
    def test_launch_when_workbook_not_exists(self):
        liveaction = LiveActionDB(action=WB1_NAME, parameters=ACTION_PARAMS)
        liveaction, execution = action_service.request(liveaction)
        liveaction = LiveAction.get_by_id(str(liveaction.id))
        self.assertEqual(liveaction.status, action_constants.LIVEACTION_STATUS_RUNNING)

        mistral_context = liveaction.context.get('mistral', None)
        self.assertIsNotNone(mistral_context)
        self.assertEqual(mistral_context['execution_id'], WB1_EXEC.get('id'))
        self.assertEqual(mistral_context['workflow_name'], WB1_EXEC.get('workflow_name'))

    @mock.patch.object(
        workflows.WorkflowManager, 'list',
        mock.MagicMock(return_value=[]))
    @mock.patch.object(
        workbooks.WorkbookManager, 'get',
        mock.MagicMock(side_effect=Exception()))
    def test_launch_workbook_name_mismatch(self):
        action_ref = 'generic.workbook_v2_name_mismatch'
        MistralRunner.entry_point = mock.PropertyMock(return_value=WB1_YAML_FILE_PATH)
        liveaction = LiveActionDB(action=action_ref, parameters=ACTION_PARAMS)
        liveaction, execution = action_service.request(liveaction)
        liveaction = LiveAction.get_by_id(str(liveaction.id))
        self.assertEqual(liveaction.status, action_constants.LIVEACTION_STATUS_FAILED)
        self.assertIn('Name of the workbook must be the same', liveaction.result['error'])

    def test_callback_handler_status_map(self):
        # Ensure all StackStorm status are mapped otherwise leads to zombie workflow.
        self.assertListEqual(sorted(mistral_status_map.keys()),
                             sorted(action_constants.LIVEACTION_STATUSES))

    @mock.patch.object(
        action_executions.ActionExecutionManager, 'update',
        mock.MagicMock(return_value=None))
    def test_callback_handler_with_result_as_text(self):
        MistralCallbackHandler.callback('http://127.0.0.1:8989/v2/action_executions/12345', {},
                                        action_constants.LIVEACTION_STATUS_SUCCEEDED,
                                        '<html></html>')

    @mock.patch.object(
        action_executions.ActionExecutionManager, 'update',
        mock.MagicMock(return_value=None))
    def test_callback_handler_with_result_as_dict(self):
        MistralCallbackHandler.callback('http://127.0.0.1:8989/v2/action_executions/12345', {},
                                        action_constants.LIVEACTION_STATUS_SUCCEEDED, {'a': 1})

    @mock.patch.object(
        action_executions.ActionExecutionManager, 'update',
        mock.MagicMock(return_value=None))
    def test_callback_handler_with_result_as_json_str(self):
        MistralCallbackHandler.callback('http://127.0.0.1:8989/v2/action_executions/12345', {},
                                        action_constants.LIVEACTION_STATUS_SUCCEEDED, '{"a": 1}')
        MistralCallbackHandler.callback('http://127.0.0.1:8989/v2/action_executions/12345', {},
                                        action_constants.LIVEACTION_STATUS_SUCCEEDED, "{'a': 1}")

    @mock.patch.object(
        action_executions.ActionExecutionManager, 'update',
        mock.MagicMock(return_value=None))
    def test_callback_handler_with_result_as_list(self):
        MistralCallbackHandler.callback('http://127.0.0.1:8989/v2/action_executions/12345', {},
                                        action_constants.LIVEACTION_STATUS_SUCCEEDED,
                                        ["a", "b", "c"])

    @mock.patch.object(
        action_executions.ActionExecutionManager, 'update',
        mock.MagicMock(return_value=None))
    def test_callback_handler_with_result_as_list_str(self):
        MistralCallbackHandler.callback('http://127.0.0.1:8989/v2/action_executions/12345', {},
                                        action_constants.LIVEACTION_STATUS_SUCCEEDED,
                                        '["a", "b", "c"]')

    @mock.patch.object(
        action_executions.ActionExecutionManager, 'update',
        mock.MagicMock(return_value=None))
    def test_callback(self):
        liveaction = LiveActionDB(
            action='core.local', parameters={'cmd': 'uname -a'},
            callback={
                'source': 'mistral',
                'url': 'http://127.0.0.1:8989/v2/action_executions/12345'
            }
        )

        for status in action_constants.LIVEACTION_COMPLETED_STATES:
            expected_mistral_status = mistral_status_map[status]
            LocalShellRunner.run = mock.Mock(return_value=(status, NON_EMPTY_RESULT, None))
            liveaction, execution = action_service.request(liveaction)
            liveaction = LiveAction.get_by_id(str(liveaction.id))
            self.assertEqual(liveaction.status, status)
            action_executions.ActionExecutionManager.update.assert_called_with(
                '12345', state=expected_mistral_status, output=NON_EMPTY_RESULT)

    @mock.patch.object(
        LocalShellRunner, 'run',
        mock.MagicMock(return_value=(action_constants.LIVEACTION_STATUS_RUNNING,
                                     NON_EMPTY_RESULT, None)))
    @mock.patch.object(
        action_executions.ActionExecutionManager, 'update',
        mock.MagicMock(return_value=None))
    def test_callback_incomplete_state(self):
        liveaction = LiveActionDB(
            action='core.local', parameters={'cmd': 'uname -a'},
            callback={
                'source': 'mistral',
                'url': 'http://127.0.0.1:8989/v2/action_executions/12345'
            }
        )

        liveaction, execution = action_service.request(liveaction)
        liveaction = LiveAction.get_by_id(str(liveaction.id))
        self.assertEqual(liveaction.status, action_constants.LIVEACTION_STATUS_RUNNING)
        self.assertFalse(action_executions.ActionExecutionManager.update.called)

    @mock.patch.object(
        LocalShellRunner, 'run',
        mock.MagicMock(return_value=(action_constants.LIVEACTION_STATUS_SUCCEEDED,
                                     NON_EMPTY_RESULT, None)))
    @mock.patch.object(
        action_executions.ActionExecutionManager, 'update',
        mock.MagicMock(side_effect=[
            requests.exceptions.ConnectionError(),
            None]))
    def test_callback_retry(self):
        liveaction = LiveActionDB(
            action='core.local', parameters={'cmd': 'uname -a'},
            callback={
                'source': 'mistral',
                'url': 'http://127.0.0.1:8989/v2/action_executions/12345'
            }
        )

        liveaction, execution = action_service.request(liveaction)
        liveaction = LiveAction.get_by_id(str(liveaction.id))
        self.assertEqual(liveaction.status, action_constants.LIVEACTION_STATUS_SUCCEEDED)

        calls = [call('12345', state='SUCCESS', output=NON_EMPTY_RESULT) for i in range(0, 2)]
        action_executions.ActionExecutionManager.update.assert_has_calls(calls)

    @mock.patch.object(
        LocalShellRunner, 'run',
        mock.MagicMock(return_value=(action_constants.LIVEACTION_STATUS_SUCCEEDED,
                                     NON_EMPTY_RESULT, None)))
    @mock.patch.object(
        action_executions.ActionExecutionManager, 'update',
        mock.MagicMock(side_effect=[
            requests.exceptions.ConnectionError(),
            requests.exceptions.ConnectionError(),
            requests.exceptions.ConnectionError(),
            requests.exceptions.ConnectionError(),
            None]))
    def test_callback_retry_exhausted(self):
        liveaction = LiveActionDB(
            action='core.local', parameters={'cmd': 'uname -a'},
            callback={
                'source': 'mistral',
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
    def test_cancel(self):
        MistralRunner.entry_point = mock.PropertyMock(return_value=WF1_YAML_FILE_PATH)
        liveaction = LiveActionDB(action=WF1_NAME, parameters=ACTION_PARAMS)
        liveaction, execution = action_service.request(liveaction)
        liveaction = LiveAction.get_by_id(str(liveaction.id))
        self.assertEqual(liveaction.status, action_constants.LIVEACTION_STATUS_RUNNING)

        mistral_context = liveaction.context.get('mistral', None)
        self.assertIsNotNone(mistral_context)
        self.assertEqual(mistral_context['execution_id'], WF1_EXEC.get('id'))
        self.assertEqual(mistral_context['workflow_name'], WF1_EXEC.get('workflow_name'))

        requester = cfg.CONF.system_user.user
        liveaction, execution = action_service.request_cancellation(liveaction, requester)
        executions.ExecutionManager.update.assert_called_with(WF1_EXEC.get('id'), 'PAUSED')
        liveaction = LiveAction.get_by_id(str(liveaction.id))
        self.assertEqual(liveaction.status, action_constants.LIVEACTION_STATUS_CANCELED)

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
        mock.MagicMock(side_effect=[requests.exceptions.ConnectionError(),
                                    executions.Execution(None, WF1_EXEC_PAUSED)]))
    def test_cancel_retry(self):
        MistralRunner.entry_point = mock.PropertyMock(return_value=WF1_YAML_FILE_PATH)
        liveaction = LiveActionDB(action=WF1_NAME, parameters=ACTION_PARAMS)
        liveaction, execution = action_service.request(liveaction)
        liveaction = LiveAction.get_by_id(str(liveaction.id))
        self.assertEqual(liveaction.status, action_constants.LIVEACTION_STATUS_RUNNING)

        mistral_context = liveaction.context.get('mistral', None)
        self.assertIsNotNone(mistral_context)
        self.assertEqual(mistral_context['execution_id'], WF1_EXEC.get('id'))
        self.assertEqual(mistral_context['workflow_name'], WF1_EXEC.get('workflow_name'))

        requester = cfg.CONF.system_user.user
        liveaction, execution = action_service.request_cancellation(liveaction, requester)
        executions.ExecutionManager.update.assert_called_with(WF1_EXEC.get('id'), 'PAUSED')
        liveaction = LiveAction.get_by_id(str(liveaction.id))
        self.assertEqual(liveaction.status, action_constants.LIVEACTION_STATUS_CANCELED)

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
        mock.MagicMock(side_effect=requests.exceptions.ConnectionError('Connection refused')))
    def test_cancel_retry_exhausted(self):
        MistralRunner.entry_point = mock.PropertyMock(return_value=WF1_YAML_FILE_PATH)
        liveaction = LiveActionDB(action=WF1_NAME, parameters=ACTION_PARAMS)
        liveaction, execution = action_service.request(liveaction)
        liveaction = LiveAction.get_by_id(str(liveaction.id))
        self.assertEqual(liveaction.status, action_constants.LIVEACTION_STATUS_RUNNING)

        mistral_context = liveaction.context.get('mistral', None)
        self.assertIsNotNone(mistral_context)
        self.assertEqual(mistral_context['execution_id'], WF1_EXEC.get('id'))
        self.assertEqual(mistral_context['workflow_name'], WF1_EXEC.get('workflow_name'))

        requester = cfg.CONF.system_user.user
        liveaction, execution = action_service.request_cancellation(liveaction, requester)

        calls = [call(WF1_EXEC.get('id'), 'PAUSED') for i in range(0, 2)]
        executions.ExecutionManager.update.assert_has_calls(calls)

        liveaction = LiveAction.get_by_id(str(liveaction.id))
        self.assertEqual(liveaction.status, action_constants.LIVEACTION_STATUS_CANCELING)

    def test_build_context(self):
        parent = {
            'mistral': {
                'workflow_name': 'foo',
                'workflow_execution_id': 'b222b934-7473-4cd4-a2ec-e204a8c93848',
                'task_tags': None,
                'task_name': 'some_fancy_wf_task',
                'task_id': '6c7d4334-3e7d-49c6-918d-698e846affaf',
                'action_execution_id': '24da5c88-834c-4a65-8b56-4ddbd654eb68'
            }
        }

        current = {
            'workflow_name': 'foo.subwf',
            'workflow_execution_id': '135e3446-4c89-4afe-821f-6ec6a0849b27'
        }

        context = MistralRunner._build_mistral_context(parent, current)
        self.assertTrue(context is not None)
        self.assertTrue('parent' in context['mistral'].keys())

        parent_dict = {
            'workflow_name': parent['mistral']['workflow_name'],
            'workflow_execution_id': parent['mistral']['workflow_execution_id']
        }

        self.assertDictEqual(context['mistral']['parent'], parent_dict)
        self.assertEqual(context['mistral']['workflow_execution_id'],
                         current['workflow_execution_id'])

        parent = None
        context = MistralRunner._build_mistral_context(parent, current)
        self.assertDictEqual(context['mistral'], current)

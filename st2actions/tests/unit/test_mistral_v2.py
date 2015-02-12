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
import json
import uuid

import mock
import requests
import six
import yaml

from mistralclient.api.v2 import workbooks
from mistralclient.api.v2 import workflows
from mistralclient.api.v2 import executions

# XXX: actionsensor import depends on config being setup.
import st2tests.config as tests_config
tests_config.parse_args()

from st2tests.fixturesloader import FixturesLoader
from st2tests import http
from st2tests import DbTestCase
import st2actions.bootstrap.runnersregistrar as runners_registrar
from st2actions import worker
from st2actions.runners.mistral.v2 import MistralRunner
from st2actions.runners.localrunner import LocalShellRunner
from st2actions.handlers.mistral import MistralCallbackHandler
from st2common.transport.publishers import CUDPublisher
from st2common.services import action as action_service
from st2common.models.db.action import ActionExecutionDB
from st2common.constants.action import ACTIONEXEC_STATUS_SUCCEEDED
from st2common.constants.action import ACTIONEXEC_STATUS_RUNNING
from st2common.constants.action import ACTIONEXEC_STATUS_FAILED
from st2common.models.api.action import ActionAPI
from st2common.persistence.action import Action, ActionExecution


TEST_FIXTURES = {
    'workflows': [
        'workbook_v2.yaml',
        'workbook_v2_many_workflows.yaml',
        'workbook_v2_many_workflows_no_default.yaml',
        'workflow_v2.yaml',
        'workflow_v2_many_workflows.yaml'
    ],
    'actions': [
        'workbook_v2.json',
        'workbook_v2_many_workflows.json',
        'workbook_v2_many_workflows_no_default.json',
        'workflow_v2.json',
        'workflow_v2_many_workflows.json',
        'workbook_v2_name_mismatch.json',
        'workflow_v2_name_mismatch.json',
        'local.json'
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

# Non-workbook with a many workflows
WF2_YAML_FILE_NAME = TEST_FIXTURES['workflows'][4]
WF2_YAML_FILE_PATH = LOADER.get_fixture_file_path_abs(PACK, 'workflows', WF2_YAML_FILE_NAME)
WF2_SPEC = FIXTURES['workflows'][WF2_YAML_FILE_NAME]
WF2_YAML = yaml.safe_dump(WF2_SPEC, default_flow_style=False)
WF2_NAME = '%s.%s' % (PACK, WF2_YAML_FILE_NAME.replace('.yaml', ''))
WF2 = workflows.Workflow(None, {'name': WF2_NAME, 'definition': WF2_YAML})
WF2_EXEC = copy.deepcopy(MISTRAL_EXECUTION)
WF2_EXEC['workflow_name'] = WF2_NAME

# Action executions' requirements
ACTION_PARAMS = {'friend': 'Rocky'}
CHAMPION = worker.Worker(None)


def process_create(payload):
    if isinstance(payload, ActionExecutionDB):
        CHAMPION.execute_action(payload)


@mock.patch.object(LocalShellRunner, 'run', mock.
                   MagicMock(return_value=(ACTIONEXEC_STATUS_SUCCEEDED, {}, None)))
@mock.patch.object(CUDPublisher, 'publish_create', mock.MagicMock(side_effect=process_create))
@mock.patch.object(CUDPublisher, 'publish_update', mock.MagicMock(return_value=None))
class TestMistralRunner(DbTestCase):

    @classmethod
    def setUpClass(cls):
        super(TestMistralRunner, cls).setUpClass()
        runners_registrar.register_runner_types()

        for name, fixture in six.iteritems(FIXTURES['actions']):
            instance = ActionAPI(**fixture)
            Action.add_or_update(ActionAPI.to_model(instance))

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
        execution = ActionExecutionDB(action=WF1_NAME, parameters=ACTION_PARAMS)
        execution = action_service.schedule(execution)
        execution = ActionExecution.get_by_id(str(execution.id))
        self.assertEqual(execution.status, ACTIONEXEC_STATUS_RUNNING)

        mistral_context = execution.context.get('mistral', None)
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
        execution = ActionExecutionDB(action=WF1_NAME, parameters=ACTION_PARAMS)
        execution = action_service.schedule(execution)
        execution = ActionExecution.get_by_id(str(execution.id))
        self.assertEqual(execution.status, ACTIONEXEC_STATUS_RUNNING)

        mistral_context = execution.context.get('mistral', None)
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
        execution = ActionExecutionDB(action=WF1_NAME, parameters=ACTION_PARAMS)
        execution = action_service.schedule(execution)
        execution = ActionExecution.get_by_id(str(execution.id))
        self.assertEqual(execution.status, ACTIONEXEC_STATUS_RUNNING)

        mistral_context = execution.context.get('mistral', None)
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
        execution = ActionExecutionDB(action=WF2_NAME, parameters=ACTION_PARAMS)
        execution = action_service.schedule(execution)
        execution = ActionExecution.get_by_id(str(execution.id))
        self.assertEqual(execution.status, ACTIONEXEC_STATUS_FAILED)
        self.assertIn('Multiple workflows is not supported.', execution.result['message'])

    @mock.patch.object(
        workflows.WorkflowManager, 'list',
        mock.MagicMock(return_value=[]))
    @mock.patch.object(
        workflows.WorkflowManager, 'get',
        mock.MagicMock(side_effect=Exception()))
    def test_launch_workflow_name_mistmatch(self):
        action_ref = 'generic.workflow_v2_name_mismatch'
        MistralRunner.entry_point = mock.PropertyMock(return_value=WF1_YAML_FILE_PATH)
        execution = ActionExecutionDB(action=action_ref, parameters=ACTION_PARAMS)
        execution = action_service.schedule(execution)
        execution = ActionExecution.get_by_id(str(execution.id))
        self.assertEqual(execution.status, ACTIONEXEC_STATUS_FAILED)
        self.assertIn('Name of the workflow must be the same', execution.result['message'])

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
        execution = ActionExecutionDB(action=WB1_NAME, parameters=ACTION_PARAMS)
        execution = action_service.schedule(execution)
        execution = ActionExecution.get_by_id(str(execution.id))
        self.assertEqual(execution.status, ACTIONEXEC_STATUS_RUNNING)

        mistral_context = execution.context.get('mistral', None)
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
        execution = ActionExecutionDB(action=WB2_NAME, parameters=ACTION_PARAMS)
        execution = action_service.schedule(execution)
        execution = ActionExecution.get_by_id(str(execution.id))
        self.assertEqual(execution.status, ACTIONEXEC_STATUS_RUNNING)

        mistral_context = execution.context.get('mistral', None)
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
        execution = ActionExecutionDB(action=WB3_NAME, parameters=ACTION_PARAMS)
        execution = action_service.schedule(execution)
        execution = ActionExecution.get_by_id(str(execution.id))
        self.assertEqual(execution.status, ACTIONEXEC_STATUS_FAILED)
        self.assertIn('Default workflow cannot be determined.', execution.result['message'])

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
        execution = ActionExecutionDB(action=WB1_NAME, parameters=ACTION_PARAMS)
        execution = action_service.schedule(execution)
        execution = ActionExecution.get_by_id(str(execution.id))
        self.assertEqual(execution.status, ACTIONEXEC_STATUS_RUNNING)

        mistral_context = execution.context.get('mistral', None)
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
        execution = ActionExecutionDB(action=WB1_NAME, parameters=ACTION_PARAMS)
        execution = action_service.schedule(execution)
        execution = ActionExecution.get_by_id(str(execution.id))
        self.assertEqual(execution.status, ACTIONEXEC_STATUS_RUNNING)

        mistral_context = execution.context.get('mistral', None)
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
        execution = ActionExecutionDB(action=action_ref, parameters=ACTION_PARAMS)
        execution = action_service.schedule(execution)
        execution = ActionExecution.get_by_id(str(execution.id))
        self.assertEqual(execution.status, ACTIONEXEC_STATUS_FAILED)
        self.assertIn('Name of the workbook must be the same', execution.result['message'])

    @mock.patch.object(
        requests, 'request',
        mock.MagicMock(return_value=http.FakeResponse({}, 200, 'OK')))
    def test_callback_handler_with_result_as_text(self):
        MistralCallbackHandler.callback('http://localhost:8989/v2/tasks/12345', {},
                                        ACTIONEXEC_STATUS_SUCCEEDED, '<html></html>')

    @mock.patch.object(
        requests, 'request',
        mock.MagicMock(return_value=http.FakeResponse({}, 200, 'OK')))
    def test_callback_handler_with_result_as_dict(self):
        MistralCallbackHandler.callback('http://localhost:8989/v2/tasks/12345', {},
                                        ACTIONEXEC_STATUS_SUCCEEDED, {'a': 1})

    @mock.patch.object(
        requests, 'request',
        mock.MagicMock(return_value=http.FakeResponse({}, 200, 'OK')))
    def test_callback_handler_with_result_as_json_str(self):
        MistralCallbackHandler.callback('http://localhost:8989/v2/tasks/12345', {},
                                        ACTIONEXEC_STATUS_SUCCEEDED, '{"a": 1}')
        MistralCallbackHandler.callback('http://localhost:8989/v2/tasks/12345', {},
                                        ACTIONEXEC_STATUS_SUCCEEDED, "{'a': 1}")

    @mock.patch.object(
        requests, 'request',
        mock.MagicMock(return_value=http.FakeResponse({}, 200, 'OK')))
    def test_callback_handler_with_result_as_list(self):
        MistralCallbackHandler.callback('http://localhost:8989/v2/tasks/12345', {},
                                        ACTIONEXEC_STATUS_SUCCEEDED, ["a", "b", "c"])

    @mock.patch.object(
        requests, 'request',
        mock.MagicMock(return_value=http.FakeResponse({}, 200, 'OK')))
    def test_callback_handler_with_result_as_list_str(self):
        MistralCallbackHandler.callback('http://localhost:8989/v2/tasks/12345', {},
                                        ACTIONEXEC_STATUS_SUCCEEDED, '["a", "b", "c"]')

    @mock.patch.object(
        requests, 'request',
        mock.MagicMock(return_value=http.FakeResponse({}, 200, 'OK')))
    def test_callback(self):
        execution = ActionExecutionDB(
            action='core.local', parameters={'cmd': 'uname -a'},
            callback={'source': 'mistral', 'url': 'http://localhost:8989/v2/tasks/12345'})
        execution = action_service.schedule(execution)
        execution = ActionExecution.get_by_id(str(execution.id))
        self.assertEqual(execution.status, ACTIONEXEC_STATUS_SUCCEEDED)
        requests.request.assert_called_with('PUT', execution.callback['url'],
                                            data=json.dumps({'state': 'SUCCESS', 'result': '{}'}),
                                            headers={'content-type': 'application/json'})

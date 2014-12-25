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

from mistralclient.api.v2 import workbooks
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
    'workflows': ['workflow-v2.yaml'],
    'actions': ['local.json', 'workflow-v2.json']
}

PACK = 'generic'
FIXTURES = FixturesLoader().load_fixtures(fixtures_pack=PACK, fixtures_dict=TEST_FIXTURES)
WORKFLOW_YAML = FixturesLoader().get_fixture_file_path_abs(PACK, 'workflows', 'workflow-v2.yaml')
WORKBOOK_SPEC = FIXTURES['workflows']['workflow-v2.yaml']
WORKBOOK = workbooks.Workbook(None, {'name': 'workflow-v2', 'definition': WORKBOOK_SPEC})
WORKBOOK_OLD = workbooks.Workbook(None, {'name': 'workflow-v2', 'definition': ''})
EXECUTION = executions.Execution(None, {'id': str(uuid.uuid4()), 'state': 'RUNNING'})
CHAMPION = worker.Worker(None)


def process_create(payload):
    if isinstance(payload, ActionExecutionDB):
        CHAMPION.execute_action(payload)


@mock.patch.object(LocalShellRunner, 'run', mock.MagicMock(return_value=(True, None, {})))
@mock.patch.object(CUDPublisher, 'publish_create', mock.MagicMock(side_effect=process_create))
@mock.patch.object(CUDPublisher, 'publish_update', mock.MagicMock(return_value=None))
class TestMistralRunner(DbTestCase):

    @classmethod
    def setUpClass(cls):
        super(TestMistralRunner, cls).setUpClass()
        runners_registrar.register_runner_types()
        action_local = ActionAPI(**copy.deepcopy(FIXTURES['actions']['local.json']))
        Action.add_or_update(ActionAPI.to_model(action_local))
        action_wkflow = ActionAPI(**copy.deepcopy(FIXTURES['actions']['workflow-v2.json']))
        Action.add_or_update(ActionAPI.to_model(action_wkflow))

    @mock.patch.object(
        workbooks.WorkbookManager, 'get',
        mock.MagicMock(return_value=WORKBOOK))
    @mock.patch.object(
        workbooks.WorkbookManager, 'create',
        mock.MagicMock(return_value=WORKBOOK))
    @mock.patch.object(
        workbooks.WorkbookManager, 'update',
        mock.MagicMock(return_value=WORKBOOK))
    @mock.patch.object(
        executions.ExecutionManager, 'create',
        mock.MagicMock(return_value=EXECUTION))
    def test_launch_workflow(self):
        MistralRunner.entry_point = mock.PropertyMock(return_value=WORKFLOW_YAML)
        execution = ActionExecutionDB(action='generic.workflow-v2', parameters={'friend': 'Rocky'})
        execution = action_service.schedule(execution)
        execution = ActionExecution.get_by_id(str(execution.id))
        self.assertEqual(execution.status, ACTIONEXEC_STATUS_RUNNING)

    @mock.patch.object(
        workbooks.WorkbookManager, 'get',
        mock.MagicMock(return_value=WORKBOOK_OLD))
    @mock.patch.object(
        workbooks.WorkbookManager, 'create',
        mock.MagicMock(return_value=WORKBOOK))
    @mock.patch.object(
        workbooks.WorkbookManager, 'update',
        mock.MagicMock(return_value=WORKBOOK))
    @mock.patch.object(
        executions.ExecutionManager, 'create',
        mock.MagicMock(return_value=EXECUTION))
    def test_launch_workflow_when_definition_changed(self):
        MistralRunner.entry_point = mock.PropertyMock(return_value=WORKFLOW_YAML)
        execution = ActionExecutionDB(action='generic.workflow-v2', parameters={'friend': 'Rocky'})
        execution = action_service.schedule(execution)
        execution = ActionExecution.get_by_id(str(execution.id))
        self.assertEqual(execution.status, ACTIONEXEC_STATUS_RUNNING)

    @mock.patch.object(
        workbooks.WorkbookManager, 'get',
        mock.MagicMock(return_value=Exception()))
    @mock.patch.object(
        workbooks.WorkbookManager, 'create',
        mock.MagicMock(return_value=None))
    @mock.patch.object(
        executions.ExecutionManager, 'create',
        mock.MagicMock(return_value=EXECUTION))
    def test_launch_workflow_when_workbook_not_exists(self):
        execution = ActionExecutionDB(action='generic.workflow-v2', parameters={'friend': 'Rocky'})
        execution = action_service.schedule(execution)
        execution = ActionExecution.get_by_id(str(execution.id))
        self.assertEqual(execution.status, ACTIONEXEC_STATUS_RUNNING)

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
        self.assertEqual(execution.status, ACTIONEXEC_STATUS_FAILED)
        requests.request.assert_called_with('PUT', execution.callback['url'],
                                            data=json.dumps({'state': 'ERROR', 'result': 'None'}),
                                            headers={'content-type': 'application/json'})

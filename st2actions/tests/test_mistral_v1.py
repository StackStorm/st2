import copy
import json
import uuid

import mock
import requests

from mistralclient.api.v1 import workbooks
from mistralclient.api.v1 import executions

# XXX: actionsensor import depends on config being setup.
import st2tests.config as tests_config
tests_config.parse_args()

from tests.fixtures import mistral as fixture
from st2tests import http
from st2tests import DbTestCase
import st2actions.bootstrap.runnersregistrar as runners_registrar
from st2actions import worker
from st2actions.runners.mistral.v1 import MistralRunner
from st2actions.runners.fabricrunner import FabricRunner
from st2common.transport.publishers import CUDPublisher
from st2common.services import action as action_service
from st2common.models.db.action import ActionExecutionDB
from st2common.constants.action import ACTIONEXEC_STATUS_SUCCEEDED, ACTIONEXEC_STATUS_RUNNING
from st2common.models.api.action import ActionAPI
from st2common.persistence.action import Action, ActionExecution


CHAMPION = worker.Worker(None)
WORKFLOW_YAML = [f for f in fixture.WORKFLOW_YAMLS if 'workflow-v1.yaml' in f][0]
WORKBOOK_SPEC = fixture.ARTIFACTS['workflows']['workflow-v1']
WORKBOOK = workbooks.Workbook(None, {'name': 'workflow-v1'})
EXECUTION = executions.Execution(None, {'id': str(uuid.uuid4()), 'state': 'RUNNING'})


def process_create(payload):
    if isinstance(payload, ActionExecutionDB):
        CHAMPION.execute_action(payload)


@mock.patch.object(FabricRunner, '_run', mock.MagicMock(return_value={}))
@mock.patch.object(CUDPublisher, 'publish_create', mock.MagicMock(side_effect=process_create))
@mock.patch.object(CUDPublisher, 'publish_update', mock.MagicMock(return_value=None))
class TestMistralRunner(DbTestCase):

    @classmethod
    def setUpClass(cls):
        super(TestMistralRunner, cls).setUpClass()
        runners_registrar.register_runner_types()
        metadata = fixture.ARTIFACTS['metadata']
        action_local = ActionAPI(**copy.deepcopy(metadata['actions']['local']))
        Action.add_or_update(ActionAPI.to_model(action_local))
        action_wkflow = ActionAPI(**copy.deepcopy(metadata['actions']['workflow-v1']))
        Action.add_or_update(ActionAPI.to_model(action_wkflow))

    @mock.patch.object(
        workbooks.WorkbookManager, 'list',
        mock.MagicMock(return_value=[WORKBOOK]))
    @mock.patch.object(
        workbooks.WorkbookManager, 'get_definition',
        mock.MagicMock(return_value=WORKBOOK_SPEC))
    @mock.patch.object(
        executions.ExecutionManager, 'create',
        mock.MagicMock(return_value=EXECUTION))
    def test_launch_workflow(self):
        MistralRunner.entry_point = mock.PropertyMock(return_value=WORKFLOW_YAML)
        execution = ActionExecutionDB(action='core.workflow-v1', parameters={'friend': 'Rocky'})
        execution = action_service.schedule(execution)
        execution = ActionExecution.get_by_id(str(execution.id))
        self.assertEqual(execution.status, ACTIONEXEC_STATUS_RUNNING)

    @mock.patch.object(
        workbooks.WorkbookManager, 'list',
        mock.MagicMock(return_value=[WORKBOOK]))
    @mock.patch.object(
        workbooks.WorkbookManager, 'get_definition',
        mock.MagicMock(return_value=None))
    @mock.patch.object(
        workbooks.WorkbookManager, 'upload_definition',
        mock.MagicMock(return_value=None))
    @mock.patch.object(
        executions.ExecutionManager, 'create',
        mock.MagicMock(return_value=EXECUTION))
    def test_launch_workflow_when_definition_changed(self):
        MistralRunner.entry_point = mock.PropertyMock(return_value=WORKFLOW_YAML)
        execution = ActionExecutionDB(action='core.workflow-v1', parameters={'friend': 'Rocky'})
        execution = action_service.schedule(execution)
        execution = ActionExecution.get_by_id(str(execution.id))
        self.assertEqual(execution.status, ACTIONEXEC_STATUS_RUNNING)

    @mock.patch.object(
        workbooks.WorkbookManager, 'list',
        mock.MagicMock(return_value=[]))
    @mock.patch.object(
        workbooks.WorkbookManager, 'create',
        mock.MagicMock(return_value=None))
    @mock.patch.object(
        workbooks.WorkbookManager, 'get_definition',
        mock.MagicMock(return_value=None))
    @mock.patch.object(
        workbooks.WorkbookManager, 'upload_definition',
        mock.MagicMock(return_value=None))
    @mock.patch.object(
        executions.ExecutionManager, 'create',
        mock.MagicMock(return_value=EXECUTION))
    def test_launch_workflow_when_workbook_not_exists(self):
        MistralRunner.entry_point = mock.PropertyMock(return_value=WORKFLOW_YAML)
        execution = ActionExecutionDB(action='core.workflow-v1', parameters={'friend': 'Rocky'})
        execution = action_service.schedule(execution)
        execution = ActionExecution.get_by_id(str(execution.id))
        self.assertEqual(execution.status, ACTIONEXEC_STATUS_RUNNING)

    @mock.patch.object(
        requests, 'request',
        mock.MagicMock(return_value=http.FakeResponse({}, 200, 'OK')))
    def test_callback(self):
        execution = ActionExecutionDB(
            action='core.local', parameters={'cmd': 'uname -a'},
            callback={'source': 'mistral', 'url': 'http://localhost:8989/v1/tasks/12345'})
        execution = action_service.schedule(execution)
        execution = ActionExecution.get_by_id(str(execution.id))
        self.assertEqual(execution.status, ACTIONEXEC_STATUS_SUCCEEDED)
        requests.request.assert_called_with('PUT', execution.callback['url'],
                                            data=json.dumps({'state': 'SUCCESS', 'output': '{}'}),
                                            headers={'content-type': 'application/json'})

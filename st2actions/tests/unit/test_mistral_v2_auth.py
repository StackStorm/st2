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
import six
import yaml

from mistralclient.api.v2 import client
from mistralclient.api.v2 import executions
from mistralclient.api.v2 import workflows
from oslo_config import cfg

# XXX: actionsensor import depends on config being setup.
import st2tests.config as tests_config
tests_config.parse_args()

import st2common.bootstrap.runnersregistrar as runners_registrar
from st2actions.runners.localrunner import LocalShellRunner
from st2actions.runners.mistral.v2 import MistralRunner
from st2common.constants import action as action_constants
from st2common.models.api.auth import TokenAPI
from st2common.models.api.action import ActionAPI
from st2common.models.db.liveaction import LiveActionDB
from st2common.persistence.action import Action
from st2common.persistence.liveaction import LiveAction
from st2common.services import access as access_service
from st2common.services import action as action_service
from st2common.transport.liveaction import LiveActionPublisher
from st2common.transport.publishers import CUDPublisher
from st2common.util import isotime
from st2common.util import date as date_utils
from st2tests import DbTestCase
from st2tests.fixturesloader import FixturesLoader
from tests.unit.base import MockLiveActionPublisher


TEST_FIXTURES = {
    'workflows': [
        'workflow_v2.yaml'
    ],
    'actions': [
        'workflow_v2.yaml',
        'local.yaml'
    ]
}

PACK = 'generic'
LOADER = FixturesLoader()
FIXTURES = LOADER.load_fixtures(fixtures_pack=PACK, fixtures_dict=TEST_FIXTURES)

MISTRAL_EXECUTION = {'id': str(uuid.uuid4()), 'state': 'RUNNING', 'workflow_name': None}

# Non-workbook with a single workflow
WF1_YAML_FILE_NAME = TEST_FIXTURES['workflows'][0]
WF1_YAML_FILE_PATH = LOADER.get_fixture_file_path_abs(PACK, 'workflows', WF1_YAML_FILE_NAME)
WF1_SPEC = FIXTURES['workflows'][WF1_YAML_FILE_NAME]
WF1_YAML = yaml.safe_dump(WF1_SPEC, default_flow_style=False)
WF1_NAME = '%s.%s' % (PACK, WF1_YAML_FILE_NAME.replace('.yaml', ''))
WF1 = workflows.Workflow(None, {'name': WF1_NAME, 'definition': WF1_YAML})
WF1_OLD = workflows.Workflow(None, {'name': WF1_NAME, 'definition': ''})
WF1_EXEC = copy.deepcopy(MISTRAL_EXECUTION)
WF1_EXEC['workflow_name'] = WF1_NAME

# Action executions requirements
ACTION_CONTEXT = {'user': 'stanley'}
ACTION_PARAMS = {'friend': 'Rocky'}

# Token for auth test cases
TOKEN_API = TokenAPI(
    user=ACTION_CONTEXT['user'], token=uuid.uuid4().hex,
    expiry=isotime.format(date_utils.get_datetime_utc_now(), offset=False))
TOKEN_DB = TokenAPI.to_model(TOKEN_API)

NON_EMPTY_RESULT = 'non-empty'


@mock.patch.object(LocalShellRunner, 'run', mock.
                   MagicMock(return_value=(action_constants.LIVEACTION_STATUS_SUCCEEDED,
                                           NON_EMPTY_RESULT, None)))
@mock.patch.object(CUDPublisher, 'publish_update', mock.MagicMock(return_value=None))
@mock.patch.object(CUDPublisher, 'publish_create',
                   mock.MagicMock(side_effect=MockLiveActionPublisher.publish_create))
@mock.patch.object(LiveActionPublisher, 'publish_state',
                   mock.MagicMock(side_effect=MockLiveActionPublisher.publish_state))
class MistralAuthTest(DbTestCase):

    @classmethod
    def setUpClass(cls):
        super(MistralAuthTest, cls).setUpClass()
        runners_registrar.register_runner_types()

        for _, fixture in six.iteritems(FIXTURES['actions']):
            instance = ActionAPI(**fixture)
            Action.add_or_update(ActionAPI.to_model(instance))

    def setUp(self):
        super(MistralAuthTest, self).setUp()
        cfg.CONF.set_override('api_url', 'http://0.0.0.0:9101', group='auth')

    def tearDown(self):
        super(MistralAuthTest, self).tearDown()
        cfg.CONF.set_default('keystone_username', None, group='mistral')
        cfg.CONF.set_default('keystone_password', None, group='mistral')
        cfg.CONF.set_default('keystone_project_name', None, group='mistral')
        cfg.CONF.set_default('keystone_auth_url', None, group='mistral')

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
        access_service, 'create_token',
        mock.MagicMock(return_value=TOKEN_DB))
    def test_launch_workflow_with_st2_auth(self):
        MistralRunner.entry_point = mock.PropertyMock(return_value=WF1_YAML_FILE_PATH)
        liveaction = LiveActionDB(action=WF1_NAME, parameters=ACTION_PARAMS, context=ACTION_CONTEXT)
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
                        'auth_token': TOKEN_DB.token,
                        'api_url': 'http://0.0.0.0:9101/v1',
                        'endpoint': 'http://0.0.0.0:9101/v1/actionexecutions',
                        'parent': {
                            'user': liveaction.context['user'],
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
        client.Client, 'authenticate',
        mock.MagicMock(return_value=(cfg.CONF.mistral.v2_base_url, '123', 'abc', 'xyz')))
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
    def test_launch_workflow_with_mistral_auth(self):
        cfg.CONF.set_default('keystone_username', 'foo', group='mistral')
        cfg.CONF.set_default('keystone_password', 'bar', group='mistral')
        cfg.CONF.set_default('keystone_project_name', 'admin', group='mistral')
        cfg.CONF.set_default('keystone_auth_url', 'http://127.0.0.1:5000/v3', group='mistral')

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

        client.Client.authenticate.assert_called_with(
            cfg.CONF.mistral.v2_base_url,
            cfg.CONF.mistral.keystone_username,
            cfg.CONF.mistral.keystone_password,
            cfg.CONF.mistral.keystone_project_name,
            cfg.CONF.mistral.keystone_auth_url,
            None, 'publicURL', 'workflow', None, None, None, False)

        executions.ExecutionManager.create.assert_called_with(
            WF1_NAME, workflow_input=workflow_input, env=env)

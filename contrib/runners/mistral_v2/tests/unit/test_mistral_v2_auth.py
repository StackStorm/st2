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
from mistralclient.api.v2 import workflows
from mistralclient.auth import keystone
from oslo_config import cfg

# XXX: actionsensor import depends on config being setup.
import st2tests.config as tests_config
tests_config.parse_args()

from mistral_v2.mistral_v2 import MistralRunner
from st2common.bootstrap import actionsregistrar
from st2common.bootstrap import runnersregistrar
from st2common.constants import action as action_constants
from st2common.models.api.auth import TokenAPI
from st2common.models.db.liveaction import LiveActionDB
from st2common.persistence.liveaction import LiveAction
from st2common.runners import base as runners
from st2common.services import access as access_service
from st2common.services import action as action_service
from st2common.transport.liveaction import LiveActionPublisher
from st2common.transport.publishers import CUDPublisher
from st2common.util import isotime
from st2common.util import date as date_utils
from st2common.util import loader
from st2tests import DbTestCase
from st2tests import fixturesloader
from st2tests.mocks.liveaction import MockLiveActionPublisher


TEST_FIXTURES = {
    'workflows': [
        'workflow_v2.yaml'
    ],
    'actions': [
        'workflow_v2.yaml'
    ]
}

TEST_PACK = 'mistral_tests'
TEST_PACK_PATH = fixturesloader.get_fixtures_packs_base_path() + '/' + TEST_PACK

PACKS = [
    TEST_PACK_PATH,
    fixturesloader.get_fixtures_packs_base_path() + '/core'
]

# Action executions requirements
MISTRAL_EXECUTION = {'id': str(uuid.uuid4()), 'state': 'RUNNING', 'workflow_name': None}
ACTION_CONTEXT = {'user': 'stanley'}
ACTION_PARAMS = {'friend': 'Rocky'}
NON_EMPTY_RESULT = 'non-empty'

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
WF1_OLD = workflows.Workflow(None, {'name': WF1_NAME, 'definition': ''})
WF1_EXEC = copy.deepcopy(MISTRAL_EXECUTION)
WF1_EXEC['workflow_name'] = WF1_NAME

# Data for the notify param
NOTIFY = [{'type': 'st2'}]

# Token for auth test cases
TOKEN_API = TokenAPI(
    user=ACTION_CONTEXT['user'], token=uuid.uuid4().hex,
    expiry=isotime.format(date_utils.get_datetime_utc_now(), offset=False))
TOKEN_DB = TokenAPI.to_model(TOKEN_API)


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
class MistralAuthTest(DbTestCase):

    @classmethod
    def setUpClass(cls):
        super(MistralAuthTest, cls).setUpClass()

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
        super(MistralAuthTest, self).setUp()

        # Mock the local runner run method.
        local_runner_cls = self.get_runner_class('local_runner', 'local_shell_command_runner')
        local_run_result = (action_constants.LIVEACTION_STATUS_SUCCEEDED, NON_EMPTY_RESULT, None)
        local_runner_cls.run = mock.Mock(return_value=local_run_result)

    @classmethod
    def get_runner_class(cls, package_name, module_name):
        return runners.get_runner(package_name, module_name).__class__

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
                            'pack': 'mistral_tests',
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
            WF1_NAME, workflow_input=workflow_input, env=env, notify=NOTIFY)

    @mock.patch.object(
        keystone.KeystoneAuthHandler, 'authenticate',
        mock.MagicMock(return_value={}))
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
                            'pack': 'mistral_tests',
                            'execution_id': str(execution.id)
                        },
                        'notify': {},
                        'skip_notify_tasks': []
                    }
                }
            }
        }

        auth_req = {
            'auth_url': cfg.CONF.mistral.keystone_auth_url,
            'mistral_url': cfg.CONF.mistral.v2_base_url,
            'project_name': cfg.CONF.mistral.keystone_project_name,
            'username': cfg.CONF.mistral.keystone_username,
            'api_key': cfg.CONF.mistral.keystone_password,
            'insecure': False,
            'cacert': None
        }

        keystone.KeystoneAuthHandler.authenticate.assert_called_with(auth_req, session=None)

        executions.ExecutionManager.create.assert_called_with(
            WF1_NAME, workflow_input=workflow_input, env=env, notify=NOTIFY)

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

from mistralclient.api.v2 import executions
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
from st2actions.runners.localrunner import LocalShellRunner
from st2actions.runners.mistral.v2 import MistralRunner
from st2common.constants import action as action_constants
from st2common.models.api.action import ActionAPI
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
        'workflow_v2.yaml',
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
WF1_EXEC_PAUSED = copy.deepcopy(WF1_EXEC)
WF1_EXEC_PAUSED['state'] = 'PAUSED'

# Action executions requirements
ACTION_PARAMS = {'friend': 'Rocky'}

NON_EMPTY_RESULT = 'non-empty'


@mock.patch.object(LocalShellRunner, 'run', mock.
                   MagicMock(return_value=(action_constants.LIVEACTION_STATUS_SUCCEEDED,
                                           NON_EMPTY_RESULT, None)))
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
    @mock.patch.object(
        MistralRunner, 'resume',
        mock.MagicMock(
            return_value=(action_constants.LIVEACTION_STATUS_RUNNING,
                          {'tasks': []},
                          {'execution_id': str(uuid.uuid4())})
        )
    )
    def test_resume_option(self):
        MistralRunner.entry_point = mock.PropertyMock(return_value=WF1_YAML_FILE_PATH)
        liveaction1 = LiveActionDB(action=WF1_NAME, parameters=ACTION_PARAMS)
        liveaction1, execution1 = action_service.request(liveaction1)
        self.assertFalse(MistralRunner.resume.called)

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
        MistralRunner.resume.assert_called_with(execution1, context['re-run']['tasks'])

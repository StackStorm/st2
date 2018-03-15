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
import requests
import yaml

from mistralclient.api.base import APIException
from mistralclient.api.v2 import executions
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
from st2common.models.api.notification import NotificationsHelper
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
        'workflow_v2_name_mismatch.yaml'
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
ACTION_PARAMS = {'friend': 'Rocky'}
NON_EMPTY_RESULT = 'non-empty'

# Workbook with a single workflow
WB1_META_FILE_NAME = TEST_FIXTURES['workflows'][0]
WB1_META_FILE_PATH = TEST_PACK_PATH + '/actions/' + WB1_META_FILE_NAME
WB1_META_CONTENT = loader.load_meta_file(WB1_META_FILE_PATH)
WB1_NAME = WB1_META_CONTENT['pack'] + '.' + WB1_META_CONTENT['name']
WB1_ENTRY_POINT = TEST_PACK_PATH + '/actions/' + WB1_META_CONTENT['entry_point']
WB1_ENTRY_POINT_X = WB1_ENTRY_POINT.replace(WB1_META_FILE_NAME, 'xformed_' + WB1_META_FILE_NAME)
WB1_SPEC = yaml.safe_load(MistralRunner.get_workflow_definition(WB1_ENTRY_POINT_X))
WB1_YAML = yaml.safe_dump(WB1_SPEC, default_flow_style=False)
WB1 = workbooks.Workbook(None, {'name': WB1_NAME, 'definition': WB1_YAML})
WB1_OLD = workbooks.Workbook(None, {'name': WB1_NAME, 'definition': ''})
WB1_EXEC = copy.deepcopy(MISTRAL_EXECUTION)
WB1_EXEC['workflow_name'] = WB1_NAME

# Workbook with many workflows
WB2_META_FILE_NAME = TEST_FIXTURES['workflows'][1]
WB2_META_FILE_PATH = TEST_PACK_PATH + '/actions/' + WB2_META_FILE_NAME
WB2_META_CONTENT = loader.load_meta_file(WB2_META_FILE_PATH)
WB2_NAME = WB2_META_CONTENT['pack'] + '.' + WB2_META_CONTENT['name']
WB2_ENTRY_POINT = TEST_PACK_PATH + '/actions/' + WB2_META_CONTENT['entry_point']
WB2_ENTRY_POINT_X = WB2_ENTRY_POINT.replace(WB2_META_FILE_NAME, 'xformed_' + WB2_META_FILE_NAME)
WB2_SPEC = yaml.safe_load(MistralRunner.get_workflow_definition(WB2_ENTRY_POINT_X))
WB2_YAML = yaml.safe_dump(WB2_SPEC, default_flow_style=False)
WB2 = workbooks.Workbook(None, {'name': WB2_NAME, 'definition': WB2_YAML})
WB2_EXEC = copy.deepcopy(MISTRAL_EXECUTION)
WB2_EXEC['workflow_name'] = WB2_NAME

# Workbook with many workflows but no default workflow is defined
WB3_META_FILE_NAME = TEST_FIXTURES['workflows'][2]
WB3_META_FILE_PATH = TEST_PACK_PATH + '/actions/' + WB3_META_FILE_NAME
WB3_META_CONTENT = loader.load_meta_file(WB3_META_FILE_PATH)
WB3_NAME = WB3_META_CONTENT['pack'] + '.' + WB3_META_CONTENT['name']
WB3_ENTRY_POINT = TEST_PACK_PATH + '/actions/' + WB3_META_CONTENT['entry_point']
WB3_ENTRY_POINT_X = WB3_ENTRY_POINT.replace(WB3_META_FILE_NAME, 'xformed_' + WB3_META_FILE_NAME)
WB3_SPEC = yaml.safe_load(MistralRunner.get_workflow_definition(WB3_ENTRY_POINT_X))
WB3_YAML = yaml.safe_dump(WB3_SPEC, default_flow_style=False)
WB3 = workbooks.Workbook(None, {'name': WB3_NAME, 'definition': WB3_YAML})
WB3_EXEC = copy.deepcopy(MISTRAL_EXECUTION)
WB3_EXEC['workflow_name'] = WB3_NAME

# Non-workbook with a single workflow
WF1_META_FILE_NAME = TEST_FIXTURES['workflows'][3]
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

# Non-workbook with a many workflows
WF2_META_FILE_NAME = TEST_FIXTURES['workflows'][4]
WF2_META_FILE_PATH = TEST_PACK_PATH + '/actions/' + WF2_META_FILE_NAME
WF2_META_CONTENT = loader.load_meta_file(WF2_META_FILE_PATH)
WF2_NAME = WF2_META_CONTENT['pack'] + '.' + WF2_META_CONTENT['name']
WF2_ENTRY_POINT = TEST_PACK_PATH + '/actions/' + WF2_META_CONTENT['entry_point']
WF2_ENTRY_POINT_X = WF2_ENTRY_POINT.replace(WF2_META_FILE_NAME, 'xformed_' + WF2_META_FILE_NAME)
WF2_SPEC = yaml.safe_load(MistralRunner.get_workflow_definition(WF2_ENTRY_POINT_X))
WF2_YAML = yaml.safe_dump(WF2_SPEC, default_flow_style=False)
WF2 = workflows.Workflow(None, {'name': WF2_NAME, 'definition': WF2_YAML})
WF2_EXEC = copy.deepcopy(MISTRAL_EXECUTION)
WF2_EXEC['workflow_name'] = WF2_NAME

# Data for the notify param
NOTIFY = [{'type': 'st2'}]


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

    @classmethod
    def get_runner_class(cls, runner_name):
        return runners.get_runner(runner_name, runner_name).__class__

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
        self.assertTrue('parent' in list(context['mistral'].keys()))

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

        executions.ExecutionManager.create.assert_called_with(
            WF1_NAME, workflow_input=workflow_input, env=env, notify=NOTIFY)

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
    def test_launch_workflow_under_parent_chain_with_jinja_params(self):
        ac_ctx = {
            'chain': {
                'params': {
                    'var1': 'foobar',
                    'var2': '{{foobar}}',
                    'var3': ['{{foo}}', '{{bar}}'],
                    'var4': {
                        'foobar': '{{foobar}}'
                    },
                    'var5': {
                        'foobar': '{% for item in items %}foobar{% end for %}'
                    }
                }
            }
        }

        liveaction = LiveActionDB(action=WF1_NAME, parameters=ACTION_PARAMS, context=ac_ctx)
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
                            'execution_id': str(execution.id),
                            'chain': {
                                'params': {
                                    'var1': 'foobar',
                                    'var2': '{% raw %}{{foobar}}{% endraw %}',
                                    'var3': [
                                        '{% raw %}{{foo}}{% endraw %}',
                                        '{% raw %}{{bar}}{% endraw %}'
                                    ],
                                    'var4': {
                                        'foobar': '{% raw %}{{foobar}}{% endraw %}'
                                    },
                                    'var5': {
                                        'foobar': (
                                            '{% raw %}{% for item in items %}'
                                            'foobar{% end for %}{% endraw %}'
                                        )
                                    }
                                }
                            }
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
    def test_launch_workflow_under_parent_chain_with_jinja_parameters(self):
        ac_ctx = {
            'chain': {
                'parameters': {
                    'var1': 'foobar',
                    'var2': '{{foobar}}',
                    'var3': ['{{foo}}', '{{bar}}'],
                    'var4': {
                        'foobar': '{{foobar}}'
                    },
                }
            }
        }

        liveaction = LiveActionDB(action=WF1_NAME, parameters=ACTION_PARAMS, context=ac_ctx)
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
                            'execution_id': str(execution.id),
                            'chain': {
                                'parameters': {
                                    'var1': 'foobar',
                                    'var2': '{% raw %}{{foobar}}{% endraw %}',
                                    'var3': [
                                        '{% raw %}{{foo}}{% endraw %}',
                                        '{% raw %}{{bar}}{% endraw %}'
                                    ],
                                    'var4': {
                                        'foobar': '{% raw %}{{foobar}}{% endraw %}'
                                    }
                                }
                            }
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
    def test_launch_workflow_under_parent_chain_with_nonetype_in_chain_context(self):
        ac_ctx = {'chain': None}

        liveaction = LiveActionDB(action=WF1_NAME, parameters=ACTION_PARAMS, context=ac_ctx)
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
                            'execution_id': str(execution.id),
                            'chain': None
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
    def test_launch_workflow_under_parent_chain_with_nonetype_in_params_context(self):
        ac_ctx = {'chain': {'params': None}}

        liveaction = LiveActionDB(action=WF1_NAME, parameters=ACTION_PARAMS, context=ac_ctx)
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
                            'execution_id': str(execution.id),
                            'chain': {
                                'params': None
                            }
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
                            'pack': 'mistral_tests',
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
                            'pack': 'mistral_tests',
                            'execution_id': str(execution.id)
                        },
                        'notify': NotificationsHelper.from_model(liveaction.notify),
                        'skip_notify_tasks': []
                    }
                }
            }
        }

        executions.ExecutionManager.create.assert_called_with(
            WF1_NAME, workflow_input=workflow_input, env=env, notify=NOTIFY)

    @mock.patch.object(
        workflows.WorkflowManager, 'list',
        mock.MagicMock(side_effect=requests.exceptions.ConnectionError('Connection refused')))
    def test_launch_workflow_mistral_offline(self):
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
        action_ref = TEST_PACK + '.workflow_v2_name_mismatch'
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
        action_ref = TEST_PACK + '.workbook_v2_name_mismatch'
        liveaction = LiveActionDB(action=action_ref, parameters=ACTION_PARAMS)
        liveaction, execution = action_service.request(liveaction)
        liveaction = LiveAction.get_by_id(str(liveaction.id))
        self.assertEqual(liveaction.status, action_constants.LIVEACTION_STATUS_FAILED)
        self.assertIn('Name of the workbook must be the same', liveaction.result['error'])

# Licensed to the StackStorm, Inc ('StackStorm') under one or more
# contributor license agreements.  See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.
# The ASF licenses this file to You under the Apache License, Version 2.0
# (the 'License'); you may not use this file except in compliance with
# the License.  You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an 'AS IS' BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import absolute_import

import mock
import os

from orchestra import states as wf_lib_states

import st2tests

import st2tests.config as tests_config
tests_config.parse_args()

from st2actions.workflows import workflows
from st2common.bootstrap import actionsregistrar
from st2common.bootstrap import runnersregistrar
from st2common.models.db import liveaction as lv_db_models
from st2common.persistence import execution as ex_db_access
from st2common.persistence import workflow as wf_db_access
from st2common.services import action as ac_svc
from st2common.transport import liveaction as lv_ac_xport
from st2common.transport import publishers
from st2common.util import loader
from st2tests.mocks import liveaction as mock_lv_ac_xport


TEST_FIXTURES = {
    'workflows': [
        'sequential.yaml'
    ],
    'actions': [
        'sequential.yaml'
    ]
}

TEST_PACK = 'orchestra_tests'
TEST_PACK_PATH = st2tests.fixturesloader.get_fixtures_packs_base_path() + '/' + TEST_PACK

PACKS = [
    TEST_PACK_PATH,
    st2tests.fixturesloader.get_fixtures_packs_base_path() + '/core'
]


def get_wf_fixture_meta_data(fixture_pack_path, wf_meta_file_name):
    wf_meta_file_path = fixture_pack_path + '/actions/' + wf_meta_file_name
    wf_meta_content = loader.load_meta_file(wf_meta_file_path)
    wf_name = wf_meta_content['pack'] + '.' + wf_meta_content['name']

    return {
        'file_name': wf_meta_file_name,
        'file_path': wf_meta_file_path,
        'content': wf_meta_content,
        'name': wf_name
    }


def get_wf_def(wf_meta):
    rel_wf_def_path = wf_meta['content']['entry_point']
    abs_wf_def_path = os.path.join(TEST_PACK_PATH, 'actions', rel_wf_def_path)

    with open(abs_wf_def_path, 'r') as def_file:
        return def_file.read()


@mock.patch.object(
    publishers.CUDPublisher,
    'publish_update',
    mock.MagicMock(return_value=None))
@mock.patch.object(
    publishers.CUDPublisher,
    'publish_create',
    mock.MagicMock(side_effect=mock_lv_ac_xport.MockLiveActionPublisher.publish_create))
@mock.patch.object(
    lv_ac_xport.LiveActionPublisher,
    'publish_state',
    mock.MagicMock(side_effect=mock_lv_ac_xport.MockLiveActionPublisher.publish_state))
class WorkflowEngineTest(st2tests.DbTestCase):

    @classmethod
    def setUpClass(cls):
        super(WorkflowEngineTest, cls).setUpClass()

        # Register runners.
        runnersregistrar.register_runners()

        # Register test pack(s).
        actions_registrar = actionsregistrar.ActionsRegistrar(
            use_pack_cache=False,
            fail_on_failure=True
        )

        for pack in PACKS:
            actions_registrar.register_from_pack(pack)

    def __init__(self, *args, **kwargs):
        super(WorkflowEngineTest, self).__init__(*args, **kwargs)
        self.wf_engine = workflows.get_engine()

    def test_process_request(self):
        # Request action execution for the workflow definition.
        wf_meta = get_wf_fixture_meta_data(TEST_PACK_PATH, TEST_FIXTURES['workflows'][0])
        lv_ac_db = lv_db_models.LiveActionDB(action=wf_meta['name'])
        lv_ac_db, ac_ex_db = ac_svc.request(lv_ac_db)

        # Identify the corresponding workflow execution and process the request.
        wf_ex_db = wf_db_access.WorkflowExecution.query(action_execution=str(ac_ex_db.id))[0]
        self.wf_engine.process(wf_ex_db)

        # Check workflow execution internal state.
        wf_ex_db = wf_db_access.WorkflowExecution.query(action_execution=str(ac_ex_db.id))[0]
        self.assertGreater(wf_ex_db.rev, 1)
        self.assertEqual(wf_ex_db.status, wf_lib_states.RUNNING)

        expected_flow = {
            'ready': [],
            'tasks': {
                'task1': 0
            },
            'sequence': [
                {
                    'state': 'running',
                    'id': 'task1'
                }
            ]
        }

        self.assertDictEqual(wf_ex_db.flow, expected_flow)

        # Workflow is sequential. Check that there is only one task execution.
        task_ex_dbs = wf_db_access.TaskExecution.query(workflow_execution=str(wf_ex_db.id))
        self.assertEqual(len(task_ex_dbs), len(expected_flow['tasks'].values()))

        # Check task execution attributes.
        task_ex_db = task_ex_dbs[0]
        self.assertGreater(task_ex_db.rev, 1)
        self.assertEqual(task_ex_db.status, wf_lib_states.RUNNING)

        # Check action execution for the task query with task execution ID.
        ac_ex_dbs = ex_db_access.ActionExecution.query(task_execution=str(task_ex_db.id))
        self.assertEqual(len(ac_ex_dbs), 1)

        # Check action execution for the task query with workflow execution ID.
        ac_ex_dbs = ex_db_access.ActionExecution.query(workflow_execution=str(wf_ex_db.id))
        self.assertEqual(len(ac_ex_dbs), 1)

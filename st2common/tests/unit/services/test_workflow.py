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
import mock
import os

from orchestra.specs import loader as specs_loader
from orchestra import states as wf_lib_states

import st2tests

from st2common.bootstrap import actionsregistrar
from st2common.bootstrap import runnersregistrar
from st2common.exceptions import action as ac_exc
from st2common.models.db import liveaction as lv_db_models
from st2common.models.db import execution as ex_db_models
from st2common.persistence import execution as ex_db_access
from st2common.persistence import workflow as wf_db_access
from st2common.services import action as ac_svc
from st2common.services import workflows as wf_svc
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
class WorkflowExecutionServiceTest(st2tests.DbTestCase):

    @classmethod
    def setUpClass(cls):
        super(WorkflowExecutionServiceTest, cls).setUpClass()

        # Register runners.
        runnersregistrar.register_runners()

        # Register test pack(s).
        actions_registrar = actionsregistrar.ActionsRegistrar(
            use_pack_cache=False,
            fail_on_failure=True
        )

        for pack in PACKS:
            actions_registrar.register_from_pack(pack)

    def test_request(self):
        wf_meta = get_wf_fixture_meta_data(TEST_PACK_PATH, TEST_FIXTURES['workflows'][0])

        # Manually create the liveaction and action execution objects without publishing.
        lv_ac_db = lv_db_models.LiveActionDB(action=wf_meta['name'])
        lv_ac_db, ac_ex_db = ac_svc.create_request(lv_ac_db)

        # Request the workflow execution.
        wf_def = get_wf_def(wf_meta)
        wf_ex_db = wf_svc.request(wf_def, ac_ex_db)

        # Check workflow execution is saved to the database..
        wf_ex_dbs = wf_db_access.WorkflowExecution.query(action_execution=str(ac_ex_db.id))
        self.assertEqual(len(wf_ex_dbs), 1)

        # Check required attributes.
        wf_ex_db = wf_ex_dbs[0]
        self.assertIsNotNone(wf_ex_db.id)
        self.assertGreater(wf_ex_db.rev, 0)
        self.assertEqual(wf_ex_db.action_execution, str(ac_ex_db.id))
        self.assertEqual(wf_ex_db.status, wf_lib_states.REQUESTED)

    def test_request_with_inputs(self):
        wf_meta = get_wf_fixture_meta_data(TEST_PACK_PATH, TEST_FIXTURES['workflows'][0])

        # Manually create the liveaction and action execution objects without publishing.
        lv_ac_db = lv_db_models.LiveActionDB(action=wf_meta['name'], parameters={'who': 'stan'})
        lv_ac_db, ac_ex_db = ac_svc.create_request(lv_ac_db)

        # Request the workflow execution.
        wf_def = get_wf_def(wf_meta)
        wf_ex_db = wf_svc.request(wf_def, ac_ex_db)

        # Check workflow execution is saved to the database..
        wf_ex_dbs = wf_db_access.WorkflowExecution.query(action_execution=str(ac_ex_db.id))
        self.assertEqual(len(wf_ex_dbs), 1)

        # Check required attributes.
        wf_ex_db = wf_ex_dbs[0]
        self.assertIsNotNone(wf_ex_db.id)
        self.assertGreater(wf_ex_db.rev, 0)
        self.assertEqual(wf_ex_db.action_execution, str(ac_ex_db.id))
        self.assertEqual(wf_ex_db.status, wf_lib_states.REQUESTED)

        # Check inputs and context.
        expected_inputs = {
            'who': 'stan'
        }

        expected_context = {
            'who': 'stan',
            'msg1': 'Veni, vidi, vici.',
            'msg2': 'Resistance is futile!',
            'msg3': 'All your base are belong to us!'
        }

        self.assertDictEqual(wf_ex_db.inputs, expected_inputs)
        self.assertDictEqual(wf_ex_db.context, expected_context)

    def test_request_bad_action(self):
        wf_meta = get_wf_fixture_meta_data(TEST_PACK_PATH, TEST_FIXTURES['workflows'][0])

        # Manually create the action execution object with the bad action.
        ac_ex_db = ex_db_models.ActionExecutionDB(action={'ref': 'mock.foobar'})

        # Request the workflow execution.
        self.assertRaises(
            ac_exc.InvalidActionReferencedException,
            wf_svc.request,
            get_wf_def(wf_meta),
            ac_ex_db
        )

    def test_request_task_execution(self):
        wf_meta = get_wf_fixture_meta_data(TEST_PACK_PATH, TEST_FIXTURES['workflows'][0])

        # Manually create the liveaction and action execution objects without publishing.
        lv_ac_db = lv_db_models.LiveActionDB(action=wf_meta['name'])
        lv_ac_db, ac_ex_db = ac_svc.create_request(lv_ac_db)

        # Request the workflow execution.
        wf_def = get_wf_def(wf_meta)
        wf_ex_db = wf_svc.request(wf_def, ac_ex_db)

        # Manually request task execution.
        task_id = 'task1'
        spec_module = specs_loader.get_spec_module(wf_ex_db.spec['catalog'])
        wf_spec = spec_module.WorkflowSpec.deserialize(wf_ex_db.spec)
        task_spec = wf_spec.tasks.get_task(task_id)
        task_ctx = copy.deepcopy(wf_ex_db.context)
        st2_ctx = {'execution_id': wf_ex_db.action_execution}
        wf_svc.request_task_execution(wf_ex_db, task_id, task_spec, task_ctx, st2_ctx)

        # Check task execution is saved to the database..
        task_ex_dbs = wf_db_access.TaskExecution.query(workflow_execution=str(wf_ex_db.id))
        self.assertEqual(len(task_ex_dbs), 1)

        # Check required attributes.
        task_ex_db = task_ex_dbs[0]
        self.assertIsNotNone(task_ex_db.id)
        self.assertGreater(task_ex_db.rev, 0)
        self.assertEqual(task_ex_db.workflow_execution, str(wf_ex_db.id))
        self.assertEqual(task_ex_db.status, wf_lib_states.REQUESTED)

        # Check action execution for the task query with task execution ID.
        ac_ex_dbs = ex_db_access.ActionExecution.query(task_execution=str(task_ex_db.id))
        self.assertEqual(len(ac_ex_dbs), 1) 

        # Check action execution for the task query with workflow execution ID.
        ac_ex_dbs = ex_db_access.ActionExecution.query(workflow_execution=str(wf_ex_db.id))
        self.assertEqual(len(ac_ex_dbs), 1)

    def test_request_task_execution_bad_action(self):
        wf_meta = get_wf_fixture_meta_data(TEST_PACK_PATH, TEST_FIXTURES['workflows'][0])

        # Manually create the liveaction and action execution objects without publishing.
        lv_ac_db = lv_db_models.LiveActionDB(action=wf_meta['name'])
        lv_ac_db, ac_ex_db = ac_svc.create_request(lv_ac_db)

        # Request the workflow execution.
        wf_def = get_wf_def(wf_meta)
        wf_ex_db = wf_svc.request(wf_def, ac_ex_db)

        # Manually request task execution.
        task_id = 'task1'
        spec_module = specs_loader.get_spec_module(wf_ex_db.spec['catalog'])
        wf_spec = spec_module.WorkflowSpec.deserialize(wf_ex_db.spec)
        task_spec = wf_spec.tasks.get_task(task_id)
        task_ctx = copy.deepcopy(wf_ex_db.context)
        st2_ctx = {'execution_id': wf_ex_db.action_execution}

        task_spec.action = 'mock.foobar'

        self.assertRaises(
            ac_exc.InvalidActionReferencedException,
            wf_svc.request_task_execution,
            wf_ex_db,
            task_id,
            task_spec,
            task_ctx,
            st2_ctx
        )

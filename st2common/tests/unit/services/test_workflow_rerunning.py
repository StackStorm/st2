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

import mock
import os
import shutil

from orquesta import events
from orquesta import statuses as wf_statuses

import st2tests

import st2tests.config as tests_config
tests_config.parse_args()

from st2common.bootstrap import actionsregistrar
from st2common.bootstrap import runnersregistrar
from st2common.constants import action as ac_const
from st2common.exceptions import workflow as wf_exc
from st2common.models.db import liveaction as lv_db_models
from st2common.persistence import workflow as wf_db_access
from st2common.services import action as ac_svc
from st2common.services import workflows as wf_svc
from st2common.transport import liveaction as lv_ac_xport
from st2common.transport import publishers
from st2tests.mocks import liveaction as mock_lv_ac_xport


TEST_FIXTURES = {
    'workflows': [
        'rerun.yaml'
    ],
    'actions': [
        'rerun.yaml'
    ]
}

TEST_PACK = 'orquesta_tests'
TEST_PACK_PATH = st2tests.fixturesloader.get_fixtures_packs_base_path() + '/' + TEST_PACK

PACKS = [
    TEST_PACK_PATH,
    st2tests.fixturesloader.get_fixtures_packs_base_path() + '/core'
]

RERUN_TASK = 'task1'
OPTIONS = {
    'tasks': [RERUN_TASK],
}

TEMPFILE = '/tmp/rerun.txt'


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
class WorkflowExecutionRerunTest(st2tests.WorkflowTestCase, st2tests.ExecutionDbTestCase):

    @classmethod
    def setUpClass(cls):
        super(WorkflowExecutionRerunTest, cls).setUpClass()

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
        super(WorkflowExecutionRerunTest, self).setUp()

        with open(TEMPFILE, 'w') as f:
            f.write('1')

    def tearDown(self):
        if TEMPFILE and os.path.exists(TEMPFILE):
            if os.path.isdir(TEMPFILE):
                shutil.rmtree(TEMPFILE)
            else:
                os.remove(TEMPFILE)

    def test_rerun(self):
        task_route = 0

        # 1. Fail task1 and workflow
        # Manually create the liveaction and action execution objects without publishing.
        wf_meta = self.get_wf_fixture_meta_data(TEST_PACK_PATH, TEST_FIXTURES['workflows'][0])
        lv_ac_db = lv_db_models.LiveActionDB(action=wf_meta['name'])
        lv_ac_db, ac_ex_db = ac_svc.create_request(lv_ac_db)

        # Request and pre-process the workflow execution.
        wf_def = self.get_wf_def(TEST_PACK_PATH, wf_meta)
        st2_ctx = self.mock_st2_context(ac_ex_db)
        wf_ex_db = wf_svc.request(wf_def, ac_ex_db, st2_ctx)
        wf_ex_db = self.prep_wf_ex(wf_ex_db)

        self.run_workflow_step(wf_ex_db, RERUN_TASK, task_route,
                               expected_ac_ex_db_status=ac_const.LIVEACTION_STATUS_FAILED,
                               expected_tk_ex_db_status=wf_statuses.FAILED)

        # Check workflow status.
        conductor, wf_ex_db = wf_svc.refresh_conductor(str(wf_ex_db.id))
        self.assertEqual(conductor.get_workflow_status(), wf_statuses.FAILED)
        self.assertEqual(wf_ex_db.status, wf_statuses.FAILED)

        # Manually create the liveaction and action execution objects without publishing.
        # prepare rerun.
        with open(TEMPFILE, 'w') as f:
            f.write('0')

        lv_ac_db1 = lv_db_models.LiveActionDB(action=wf_meta['name'])
        lv_ac_db1, ac_ex_db1 = ac_svc.create_request(lv_ac_db1)

        st2_ctx = self.mock_st2_context(ac_ex_db1, ac_ex_db1.context)
        st2_ctx['workflow_execution_id'] = wf_ex_db.id

        # Request workflow rerun execution.
        wf_ex_db = wf_svc.request_rerun(ac_ex_db, st2_ctx, OPTIONS)
        conductor = wf_svc.deserialize_conductor(wf_ex_db)

        task = conductor.get_task(RERUN_TASK, 0)
        ac_ex_event = events.ActionExecutionEvent(wf_statuses.RUNNING)
        conductor.update_task_state(task['id'], task['route'], ac_ex_event)

        wf_ex_db.status = conductor.get_workflow_status()
        wf_ex_db.state = conductor.workflow_state.serialize()
        wf_ex_db = wf_db_access.WorkflowExecution.update(wf_ex_db, publish=False)

        self.run_workflow_step(wf_ex_db, RERUN_TASK, 0)

        conductor, wf_ex_db = wf_svc.refresh_conductor(str(wf_ex_db.id))
        self.assertEqual(wf_ex_db.status, wf_statuses.SUCCEEDED)

    def test_rerun_with_running_status(self):
        with open(TEMPFILE, 'w') as f:
            f.write('0')

        # 1. Fail task1 and workflow
        # Manually create the liveaction and action execution objects without publishing.
        wf_meta = self.get_wf_fixture_meta_data(TEST_PACK_PATH, TEST_FIXTURES['workflows'][0])
        lv_ac_db = lv_db_models.LiveActionDB(action=wf_meta['name'])
        lv_ac_db, ac_ex_db = ac_svc.create_request(lv_ac_db)

        # Request and pre-process the workflow execution.
        wf_def = self.get_wf_def(TEST_PACK_PATH, wf_meta)
        st2_ctx = self.mock_st2_context(ac_ex_db)
        wf_ex_db = wf_svc.request(wf_def, ac_ex_db, st2_ctx)
        wf_ex_db = self.prep_wf_ex(wf_ex_db)

        # Check workflow status.
        conductor, wf_ex_db = wf_svc.refresh_conductor(str(wf_ex_db.id))
        self.assertEqual(conductor.get_workflow_status(), wf_statuses.RUNNING)
        self.assertEqual(wf_ex_db.status, wf_statuses.RUNNING)

        # 2. Rerun workflow
        # Manually create the liveaction and action execution objects without publishing.
        lv_ac_db = lv_db_models.LiveActionDB(action=wf_meta['name'])
        lv_ac_db, ac_ex_db = ac_svc.create_request(lv_ac_db)

        st2_ctx = self.mock_st2_context(ac_ex_db)
        st2_ctx['workflow_execution_id'] = wf_ex_db.id
        st2_ctx['parent'] = ac_ex_db.context
        # Request workflow rerun execution.
        self.assertRaises(
            wf_exc.WorkflowExecutionRerunException,
            wf_svc.request_rerun,
            ac_ex_db,
            st2_ctx,
            OPTIONS
        )

    def test_rerun_with_completed_status(self):
        with open(TEMPFILE, 'w') as f:
            f.write('0')

        # 1. Cancel and workflow
        # Manually create the liveaction and action execution objects without publishing.
        wf_meta = self.get_wf_fixture_meta_data(TEST_PACK_PATH, TEST_FIXTURES['workflows'][0])
        lv_ac_db = lv_db_models.LiveActionDB(action=wf_meta['name'])
        lv_ac_db, ac_ex_db = ac_svc.create_request(lv_ac_db)

        # Request and pre-process the workflow execution.
        wf_def = self.get_wf_def(TEST_PACK_PATH, wf_meta)
        st2_ctx = self.mock_st2_context(ac_ex_db)
        wf_svc.request(wf_def, ac_ex_db, st2_ctx)

        # Cancel workflow
        wf_ex_db = wf_svc.request_cancellation(ac_ex_db)
        conductor, wf_ex_db = wf_svc.refresh_conductor(str(wf_ex_db.id))
        self.assertEqual(conductor.get_workflow_status(), wf_statuses.CANCELED)
        self.assertEqual(wf_ex_db.status, wf_statuses.CANCELED)

        # 2. Rerun workflow
        # Manually create the liveaction and action execution objects without publishing.
        lv_ac_db = lv_db_models.LiveActionDB(action=wf_meta['name'])
        lv_ac_db, ac_ex_db = ac_svc.create_request(lv_ac_db)

        st2_ctx = self.mock_st2_context(ac_ex_db)
        st2_ctx['workflow_execution_id'] = wf_ex_db.id
        st2_ctx['parent'] = ac_ex_db.context

        # Request workflow rerun execution.
        self.assertRaises(
            wf_exc.WorkflowExecutionRerunException,
            wf_svc.request_rerun,
            ac_ex_db,
            st2_ctx,
            OPTIONS
        )

    def test_rerun_when_rerunning_is_active(self):
        task_route = 0

        # 1. Fail task1 and workflow
        # Manually create the liveaction and action execution objects without publishing.
        wf_meta = self.get_wf_fixture_meta_data(TEST_PACK_PATH, TEST_FIXTURES['workflows'][0])
        lv_ac_db = lv_db_models.LiveActionDB(action=wf_meta['name'])
        lv_ac_db, ac_ex_db = ac_svc.create_request(lv_ac_db)

        # Request and pre-process the workflow execution.
        wf_def = self.get_wf_def(TEST_PACK_PATH, wf_meta)
        st2_ctx = self.mock_st2_context(ac_ex_db)
        wf_ex_db = wf_svc.request(wf_def, ac_ex_db, st2_ctx)
        wf_ex_db = self.prep_wf_ex(wf_ex_db)

        self.run_workflow_step(wf_ex_db, RERUN_TASK, task_route,
                               expected_ac_ex_db_status=ac_const.LIVEACTION_STATUS_FAILED,
                               expected_tk_ex_db_status=wf_statuses.FAILED)

        # Check workflow status.
        conductor, wf_ex_db = wf_svc.refresh_conductor(str(wf_ex_db.id))
        self.assertEqual(conductor.get_workflow_status(), wf_statuses.FAILED)
        self.assertEqual(wf_ex_db.status, wf_statuses.FAILED)

        # 2. Rerun workflow
        # Manually create the liveaction and action execution objects without publishing.
        lv_ac_db = lv_db_models.LiveActionDB(action=wf_meta['name'])
        lv_ac_db, ac_ex_db = ac_svc.create_request(lv_ac_db)

        # prepare rerun.
        with open(TEMPFILE, 'w') as f:
            f.write('0')

        st2_ctx = self.mock_st2_context(ac_ex_db, st2_ctx)
        st2_ctx['workflow_execution_id'] = wf_ex_db.id

        # Request workflow rerun execution.
        wf_ex_db = wf_svc.request_rerun(ac_ex_db, st2_ctx, OPTIONS)
        self.assertIsNotNone(wf_ex_db.id)
        self.assertGreater(wf_ex_db.rev, 0)
        self.assertEqual(wf_ex_db.action_execution, str(ac_ex_db.id))
        self.assertEqual(wf_ex_db.status, wf_statuses.RESUMING)

        wf_svc.request_next_tasks(wf_ex_db)
        wf_ex_db = wf_db_access.WorkflowExecution.get_by_id(str(wf_ex_db.id))
        self.assertEqual(wf_ex_db.status, wf_statuses.RUNNING)

        # 3. Retry Rerun workflow again
        # Manually create the liveaction and action execution objects without publishing.
        lv_ac_db2 = lv_db_models.LiveActionDB(action=wf_meta['name'])
        lv_ac_db2, ac_ex_db2 = ac_svc.create_request(lv_ac_db2)

        st2_ctx = self.mock_st2_context(ac_ex_db2, st2_ctx)
        st2_ctx['workflow_execution_id'] = wf_ex_db.id

        # Request workflow rerun execution.
        self.assertRaises(
            wf_exc.WorkflowExecutionRerunException,
            wf_svc.request_rerun,
            ac_ex_db2,
            st2_ctx,
            OPTIONS
        )

    def test_rerun_with_status_not_running_after_conducting(self):
        task_route = 0

        # 1. Fail task1 and workflow
        # Manually create the liveaction and action execution objects without publishing.
        wf_meta = self.get_wf_fixture_meta_data(TEST_PACK_PATH, TEST_FIXTURES['workflows'][0])
        lv_ac_db = lv_db_models.LiveActionDB(action=wf_meta['name'])
        lv_ac_db, ac_ex_db = ac_svc.create_request(lv_ac_db)

        # Request and pre-process the workflow execution.
        wf_def = self.get_wf_def(TEST_PACK_PATH, wf_meta)
        st2_ctx = self.mock_st2_context(ac_ex_db)
        wf_ex_db = wf_svc.request(wf_def, ac_ex_db, st2_ctx)
        wf_ex_db = self.prep_wf_ex(wf_ex_db)

        self.run_workflow_step(wf_ex_db, RERUN_TASK, task_route,
                               expected_ac_ex_db_status=ac_const.LIVEACTION_STATUS_FAILED,
                               expected_tk_ex_db_status=wf_statuses.FAILED)

        # Check workflow status.
        conductor, wf_ex_db = wf_svc.refresh_conductor(str(wf_ex_db.id))
        self.assertEqual(conductor.get_workflow_status(), wf_statuses.FAILED)
        self.assertEqual(wf_ex_db.status, wf_statuses.FAILED)

        # 2. Rerun workflow
        # Manually create the liveaction and action execution objects without publishing.
        lv_ac_db = lv_db_models.LiveActionDB(action=wf_meta['name'])
        lv_ac_db, ac_ex_db = ac_svc.create_request(lv_ac_db)

        # prepare rerun.
        with open(TEMPFILE, 'w') as f:
            f.write('0')

        st2_ctx = self.mock_st2_context(ac_ex_db, st2_ctx)
        st2_ctx['workflow_execution_id'] = wf_ex_db.id

        # With invalid rerun task ids, the orquesta conductor will raise exception.
        options = {'tasks': ['task2', 'task3']}
        # Request workflow rerun execution.
        self.assertRaises(
            wf_exc.WorkflowExecutionRerunException,
            wf_svc.request_rerun,
            ac_ex_db,
            st2_ctx,
            options
        )

    def test_rerun_with_workflow_execution_does_not_exist(self):
        # 1. Fail task1 and workflow
        # Manually create the liveaction and action execution objects without publishing.
        wf_meta = self.get_wf_fixture_meta_data(TEST_PACK_PATH, TEST_FIXTURES['workflows'][0])
        lv_ac_db = lv_db_models.LiveActionDB(action=wf_meta['name'])
        lv_ac_db, ac_ex_db = ac_svc.create_request(lv_ac_db)

        st2_ctx = self.mock_st2_context(ac_ex_db)
        # Mock workflow execution ID
        st2_ctx['workflow_execution_id'] = '5ca7dbe307612960d7b1d878'

        self.assertRaises(
            wf_exc.WorkflowExecutionRerunException,
            wf_svc.request_rerun,
            ac_ex_db,
            st2_ctx,
            OPTIONS
        )

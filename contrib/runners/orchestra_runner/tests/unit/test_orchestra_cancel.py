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

import st2tests

from oslo_config import cfg

# XXX: actionsensor import depends on config being setup.
import st2tests.config as tests_config
tests_config.parse_args()

from tests.unit import base

from st2common.bootstrap import actionsregistrar
from st2common.bootstrap import runnersregistrar
from st2common.constants import action as ac_const
from st2common.models.db import liveaction as lv_db_models
from st2common.persistence import execution as ex_db_access
from st2common.persistence import liveaction as lv_db_access
from st2common.persistence import workflow as wf_db_access
from st2common.runners import base as runners
from st2common.services import action as ac_svc
from st2common.services import workflows as wf_svc
from st2common.transport import liveaction as lv_ac_xport
from st2common.transport import workflow as wf_ex_xport
from st2common.transport import publishers
from st2tests.mocks import liveaction as mock_lv_ac_xport
from st2tests.mocks import workflow as mock_wf_ex_xport


TEST_PACK = 'orchestra_tests'
TEST_PACK_PATH = st2tests.fixturesloader.get_fixtures_packs_base_path() + '/' + TEST_PACK

PACKS = [
    TEST_PACK_PATH,
    st2tests.fixturesloader.get_fixtures_packs_base_path() + '/core'
]


@mock.patch.object(
    publishers.CUDPublisher,
    'publish_update',
    mock.MagicMock(return_value=None))
@mock.patch.object(
    lv_ac_xport.LiveActionPublisher,
    'publish_create',
    mock.MagicMock(side_effect=mock_lv_ac_xport.MockLiveActionPublisher.publish_create))
@mock.patch.object(
    lv_ac_xport.LiveActionPublisher,
    'publish_state',
    mock.MagicMock(side_effect=mock_lv_ac_xport.MockLiveActionPublisher.publish_state))
@mock.patch.object(
    wf_ex_xport.WorkflowExecutionPublisher,
    'publish_create',
    mock.MagicMock(side_effect=mock_wf_ex_xport.MockWorkflowExecutionPublisher.publish_create))
@mock.patch.object(
    wf_ex_xport.WorkflowExecutionPublisher,
    'publish_state',
    mock.MagicMock(side_effect=mock_wf_ex_xport.MockWorkflowExecutionPublisher.publish_state))
class OrchestraRunnerCancelTest(st2tests.DbTestCase):

    @classmethod
    def setUpClass(cls):
        super(OrchestraRunnerCancelTest, cls).setUpClass()

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

    @mock.patch.object(
        ac_svc, 'is_children_active',
        mock.MagicMock(return_value=True))
    def test_cancel(self):
        wf_meta = base.get_wf_fixture_meta_data(TEST_PACK_PATH, 'sequential.yaml')
        lv_ac_db = lv_db_models.LiveActionDB(action=wf_meta['name'])
        lv_ac_db, ac_ex_db = ac_svc.request(lv_ac_db)
        lv_ac_db = lv_db_access.LiveAction.get_by_id(str(lv_ac_db.id))
        self.assertEqual(lv_ac_db.status, ac_const.LIVEACTION_STATUS_RUNNING, lv_ac_db.result)

        requester = cfg.CONF.system_user.user
        lv_ac_db, ac_ex_db = ac_svc.request_cancellation(lv_ac_db, requester)
        lv_ac_db = lv_db_access.LiveAction.get_by_id(str(lv_ac_db.id))
        self.assertEqual(lv_ac_db.status, ac_const.LIVEACTION_STATUS_CANCELING)

    def test_cancel_workflow_cascade_down_to_subworkflow(self):
        wf_meta = base.get_wf_fixture_meta_data(TEST_PACK_PATH, 'subworkflow.yaml')
        lv_ac_db = lv_db_models.LiveActionDB(action=wf_meta['name'])
        lv_ac_db, ac_ex_db = ac_svc.request(lv_ac_db)
        lv_ac_db = lv_db_access.LiveAction.get_by_id(str(lv_ac_db.id))
        self.assertEqual(lv_ac_db.status, ac_const.LIVEACTION_STATUS_RUNNING, lv_ac_db.result)

        # Identify the records for the subworkflow.
        wf_ex_dbs = wf_db_access.WorkflowExecution.query(action_execution=str(ac_ex_db.id))
        self.assertEqual(len(wf_ex_dbs), 1)

        tk_ex_dbs = wf_db_access.TaskExecution.query(workflow_execution=str(wf_ex_dbs[0].id))
        self.assertEqual(len(tk_ex_dbs), 1)

        tk_ac_ex_dbs = ex_db_access.ActionExecution.query(task_execution=str(tk_ex_dbs[0].id))
        self.assertEqual(len(tk_ac_ex_dbs), 1)

        tk_lv_ac_db = lv_db_access.LiveAction.get_by_id(tk_ac_ex_dbs[0].liveaction['id'])
        self.assertEqual(tk_lv_ac_db.status, ac_const.LIVEACTION_STATUS_RUNNING)

        # Cancel the main workflow.
        requester = cfg.CONF.system_user.user
        lv_ac_db, ac_ex_db = ac_svc.request_cancellation(lv_ac_db, requester)
        self.assertEqual(lv_ac_db.status, ac_const.LIVEACTION_STATUS_CANCELING)

        # Assert the subworkflow is canceled.
        tk_lv_ac_db = lv_db_access.LiveAction.get_by_id(str(tk_lv_ac_db.id))
        self.assertEqual(tk_lv_ac_db.status, ac_const.LIVEACTION_STATUS_CANCELED)

        # Assert the main workflow is canceled.
        lv_ac_db = lv_db_access.LiveAction.get_by_id(str(lv_ac_db.id))
        self.assertEqual(lv_ac_db.status, ac_const.LIVEACTION_STATUS_CANCELED)

    def test_cancel_subworkflow_cascade_up_to_workflow(self):
        wf_meta = base.get_wf_fixture_meta_data(TEST_PACK_PATH, 'subworkflow.yaml')
        lv_ac_db = lv_db_models.LiveActionDB(action=wf_meta['name'])
        lv_ac_db, ac_ex_db = ac_svc.request(lv_ac_db)
        lv_ac_db = lv_db_access.LiveAction.get_by_id(str(lv_ac_db.id))
        self.assertEqual(lv_ac_db.status, ac_const.LIVEACTION_STATUS_RUNNING, lv_ac_db.result)

        # Identify the records for the subworkflow.
        wf_ex_dbs = wf_db_access.WorkflowExecution.query(action_execution=str(ac_ex_db.id))
        self.assertEqual(len(wf_ex_dbs), 1)

        tk_ex_dbs = wf_db_access.TaskExecution.query(workflow_execution=str(wf_ex_dbs[0].id))
        self.assertEqual(len(tk_ex_dbs), 1)

        tk_ac_ex_dbs = ex_db_access.ActionExecution.query(task_execution=str(tk_ex_dbs[0].id))
        self.assertEqual(len(tk_ac_ex_dbs), 1)

        tk_lv_ac_db = lv_db_access.LiveAction.get_by_id(tk_ac_ex_dbs[0].liveaction['id'])
        self.assertEqual(tk_lv_ac_db.status, ac_const.LIVEACTION_STATUS_RUNNING)

        # Cancel the subworkflow.
        requester = cfg.CONF.system_user.user
        tk_lv_ac_db, tk_ac_ex_db = ac_svc.request_cancellation(tk_lv_ac_db, requester)
        self.assertEqual(tk_lv_ac_db.status, ac_const.LIVEACTION_STATUS_CANCELING)

        # Assert the subworkflow is canceled.
        tk_lv_ac_db = lv_db_access.LiveAction.get_by_id(str(tk_lv_ac_db.id))
        self.assertEqual(tk_lv_ac_db.status, ac_const.LIVEACTION_STATUS_CANCELED)

        # Manually handle action execution completion for the task.
        tk_ac_ex_db = ex_db_access.ActionExecution.get_by_id(str(tk_ac_ex_db.id))
        self.assertEqual(tk_ac_ex_db.status, ac_const.LIVEACTION_STATUS_CANCELED)
        wf_svc.handle_action_execution_completion(tk_ac_ex_db)

        # Assert the main workflow is canceled.
        lv_ac_db = lv_db_access.LiveAction.get_by_id(str(lv_ac_db.id))
        self.assertEqual(lv_ac_db.status, ac_const.LIVEACTION_STATUS_CANCELED)

    def test_cancel_subworkflow_cascade_up_to_workflow_with_other_subworkflows(self):
        wf_meta = base.get_wf_fixture_meta_data(TEST_PACK_PATH, 'subworkflows.yaml')
        lv_ac_db = lv_db_models.LiveActionDB(action=wf_meta['name'])
        lv_ac_db, ac_ex_db = ac_svc.request(lv_ac_db)
        lv_ac_db = lv_db_access.LiveAction.get_by_id(str(lv_ac_db.id))
        self.assertEqual(lv_ac_db.status, ac_const.LIVEACTION_STATUS_RUNNING, lv_ac_db.result)

        # Identify the records for the subworkflow.
        wf_ex_dbs = wf_db_access.WorkflowExecution.query(action_execution=str(ac_ex_db.id))
        self.assertEqual(len(wf_ex_dbs), 1)

        tk_ex_dbs = wf_db_access.TaskExecution.query(workflow_execution=str(wf_ex_dbs[0].id))
        self.assertEqual(len(tk_ex_dbs), 2)

        tk1_ac_ex_dbs = ex_db_access.ActionExecution.query(task_execution=str(tk_ex_dbs[0].id))
        self.assertEqual(len(tk1_ac_ex_dbs), 1)

        tk1_lv_ac_db = lv_db_access.LiveAction.get_by_id(tk1_ac_ex_dbs[0].liveaction['id'])
        self.assertEqual(tk1_lv_ac_db.status, ac_const.LIVEACTION_STATUS_RUNNING)

        tk2_ac_ex_dbs = ex_db_access.ActionExecution.query(task_execution=str(tk_ex_dbs[1].id))
        self.assertEqual(len(tk2_ac_ex_dbs), 1)

        tk2_lv_ac_db = lv_db_access.LiveAction.get_by_id(tk2_ac_ex_dbs[0].liveaction['id'])
        self.assertEqual(tk2_lv_ac_db.status, ac_const.LIVEACTION_STATUS_RUNNING)

        # Cancel the subworkflow which should cascade up to the root.
        requester = cfg.CONF.system_user.user
        tk1_lv_ac_db, tk1_ac_ex_db = ac_svc.request_cancellation(tk1_lv_ac_db, requester)
        self.assertEqual(tk1_lv_ac_db.status, ac_const.LIVEACTION_STATUS_CANCELING)

        # Assert the main workflow is canceling.
        lv_ac_db = lv_db_access.LiveAction.get_by_id(str(lv_ac_db.id))
        self.assertEqual(lv_ac_db.status, ac_const.LIVEACTION_STATUS_CANCELING)

        # Assert both subworkflows are canceled.
        tk1_lv_ac_db = lv_db_access.LiveAction.get_by_id(str(tk1_lv_ac_db.id))
        self.assertEqual(tk1_lv_ac_db.status, ac_const.LIVEACTION_STATUS_CANCELED)
        tk2_lv_ac_db = lv_db_access.LiveAction.get_by_id(str(tk2_lv_ac_db.id))
        self.assertEqual(tk2_lv_ac_db.status, ac_const.LIVEACTION_STATUS_CANCELED)

        # Manually handle action execution completion for one of the tasks.
        tk1_ac_ex_db = ex_db_access.ActionExecution.get_by_id(str(tk1_ac_ex_db.id))
        self.assertEqual(tk1_ac_ex_db.status, ac_const.LIVEACTION_STATUS_CANCELED)
        wf_svc.handle_action_execution_completion(tk1_ac_ex_db)

        # Manually handle action execution completion for the other task.
        tk2_ac_ex_db = tk2_ac_ex_dbs[0]
        tk2_ac_ex_db = ex_db_access.ActionExecution.get_by_id(str(tk2_ac_ex_db.id))
        self.assertEqual(tk2_ac_ex_db.status, ac_const.LIVEACTION_STATUS_CANCELED)
        wf_svc.handle_action_execution_completion(tk2_ac_ex_db)

        # Assert the main workflow is canceling.
        lv_ac_db = lv_db_access.LiveAction.get_by_id(str(lv_ac_db.id))
        self.assertEqual(lv_ac_db.status, ac_const.LIVEACTION_STATUS_CANCELED)

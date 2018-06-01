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

from orchestra import states as wf_states
from oslo_config import cfg

# XXX: actionsensor import depends on config being setup.
import st2tests.config as tests_config
tests_config.parse_args()

from tests.unit import base

from st2actions.notifier import notifier
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
class OrchestraRunnerPauseResumeTest(st2tests.DbTestCase):

    @classmethod
    def setUpClass(cls):
        super(OrchestraRunnerPauseResumeTest, cls).setUpClass()

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
        mock.MagicMock(return_value=False))
    def test_pause(self):
        wf_meta = base.get_wf_fixture_meta_data(TEST_PACK_PATH, 'sequential.yaml')
        lv_ac_db = lv_db_models.LiveActionDB(action=wf_meta['name'])
        lv_ac_db, ac_ex_db = ac_svc.request(lv_ac_db)
        lv_ac_db = lv_db_access.LiveAction.get_by_id(str(lv_ac_db.id))
        self.assertEqual(lv_ac_db.status, ac_const.LIVEACTION_STATUS_RUNNING, lv_ac_db.result)

        lv_ac_db, ac_ex_db = ac_svc.request_pause(lv_ac_db, cfg.CONF.system_user.user)
        lv_ac_db = lv_db_access.LiveAction.get_by_id(str(lv_ac_db.id))
        self.assertEqual(lv_ac_db.status, ac_const.LIVEACTION_STATUS_PAUSING)

    @mock.patch.object(
        ac_svc, 'is_children_active',
        mock.MagicMock(return_value=True))
    def test_pause_with_active_children(self):
        wf_meta = base.get_wf_fixture_meta_data(TEST_PACK_PATH, 'sequential.yaml')
        lv_ac_db = lv_db_models.LiveActionDB(action=wf_meta['name'])
        lv_ac_db, ac_ex_db = ac_svc.request(lv_ac_db)
        lv_ac_db = lv_db_access.LiveAction.get_by_id(str(lv_ac_db.id))
        self.assertEqual(lv_ac_db.status, ac_const.LIVEACTION_STATUS_RUNNING, lv_ac_db.result)

        lv_ac_db, ac_ex_db = ac_svc.request_pause(lv_ac_db, cfg.CONF.system_user.user)
        lv_ac_db = lv_db_access.LiveAction.get_by_id(str(lv_ac_db.id))
        self.assertEqual(lv_ac_db.status, ac_const.LIVEACTION_STATUS_PAUSING)

    def test_pause_subworkflow_not_cascade_up_to_workflow(self):
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

        # Pause the subworkflow.
        tk_lv_ac_db, tk_ac_ex_db = ac_svc.request_pause(tk_lv_ac_db, cfg.CONF.system_user.user)
        self.assertEqual(tk_lv_ac_db.status, ac_const.LIVEACTION_STATUS_PAUSING)

        # Assert the main workflow is still running.
        lv_ac_db = lv_db_access.LiveAction.get_by_id(str(lv_ac_db.id))
        self.assertEqual(lv_ac_db.status, ac_const.LIVEACTION_STATUS_RUNNING)

    def test_pause_workflow_cascade_down_to_subworkflow(self):
        wf_meta = base.get_wf_fixture_meta_data(TEST_PACK_PATH, 'subworkflow.yaml')
        lv_ac_db = lv_db_models.LiveActionDB(action=wf_meta['name'])
        lv_ac_db, ac_ex_db = ac_svc.request(lv_ac_db)
        lv_ac_db = lv_db_access.LiveAction.get_by_id(str(lv_ac_db.id))
        self.assertEqual(lv_ac_db.status, ac_const.LIVEACTION_STATUS_RUNNING, lv_ac_db.result)

        # Identify the records for the main workflow.
        wf_ex_dbs = wf_db_access.WorkflowExecution.query(action_execution=str(ac_ex_db.id))
        self.assertEqual(len(wf_ex_dbs), 1)

        wf_ex_db = wf_ex_dbs[0]
        tk_ex_dbs = wf_db_access.TaskExecution.query(workflow_execution=str(wf_ex_db.id))
        self.assertEqual(len(tk_ex_dbs), 1)

        tk_ex_db = tk_ex_dbs[0]
        tk_ac_ex_dbs = ex_db_access.ActionExecution.query(task_execution=str(tk_ex_db.id))
        self.assertEqual(len(tk_ac_ex_dbs), 1)

        tk_ac_ex_db = tk_ac_ex_dbs[0]
        tk_lv_ac_db = lv_db_access.LiveAction.get_by_id(tk_ac_ex_db.liveaction['id'])
        self.assertEqual(tk_lv_ac_db.status, ac_const.LIVEACTION_STATUS_RUNNING)

        # Identify the records for the subworkflow.
        sub_wf_ex_dbs = wf_db_access.WorkflowExecution.query(action_execution=str(tk_ac_ex_db.id))
        self.assertEqual(len(sub_wf_ex_dbs), 1)

        sub_wf_ex_db = sub_wf_ex_dbs[0]
        sub_tk_ex_dbs = wf_db_access.TaskExecution.query(workflow_execution=str(sub_wf_ex_db.id))
        self.assertEqual(len(sub_tk_ex_dbs), 1)

        sub_tk_ex_db = sub_tk_ex_dbs[0]
        sub_tk_ac_ex_dbs = ex_db_access.ActionExecution.query(task_execution=str(sub_tk_ex_db.id))
        self.assertEqual(len(sub_tk_ac_ex_dbs), 1)

        # Pause the main workflow and assert it is pausing because subworkflow is still running.
        lv_ac_db, ac_ex_db = ac_svc.request_pause(lv_ac_db, cfg.CONF.system_user.user)
        self.assertEqual(lv_ac_db.status, ac_const.LIVEACTION_STATUS_PAUSING)

        # Assert the subworkflow is pausing.
        tk_lv_ac_db = lv_db_access.LiveAction.get_by_id(str(tk_lv_ac_db.id))
        self.assertEqual(tk_lv_ac_db.status, ac_const.LIVEACTION_STATUS_PAUSING)

        # Manually handle action execution completion for the task in the subworkflow.
        sub_tk_ac_ex_db = sub_tk_ac_ex_dbs[0]
        self.assertEqual(sub_tk_ac_ex_db.status, ac_const.LIVEACTION_STATUS_SUCCEEDED)
        notifier.get_notifier().process(sub_tk_ac_ex_db)

        # Assert the subworkflow is paused and manually process the execution update.
        tk_lv_ac_db = lv_db_access.LiveAction.get_by_id(str(tk_lv_ac_db.id))
        self.assertEqual(tk_lv_ac_db.status, ac_const.LIVEACTION_STATUS_PAUSED)
        tk_ac_ex_db = ex_db_access.ActionExecution.get_by_id(str(tk_ac_ex_db.id))
        self.assertEqual(tk_ac_ex_db.status, ac_const.LIVEACTION_STATUS_PAUSED)
        notifier.get_notifier().process(tk_ac_ex_db)

        # Assert the main workflow is paused.
        lv_ac_db = lv_db_access.LiveAction.get_by_id(str(lv_ac_db.id))
        self.assertEqual(lv_ac_db.status, ac_const.LIVEACTION_STATUS_PAUSED)

    def test_pause_subworkflow_while_another_subworkflow_running(self):
        wf_meta = base.get_wf_fixture_meta_data(TEST_PACK_PATH, 'subworkflows.yaml')
        lv_ac_db = lv_db_models.LiveActionDB(action=wf_meta['name'])
        lv_ac_db, ac_ex_db = ac_svc.request(lv_ac_db)
        lv_ac_db = lv_db_access.LiveAction.get_by_id(str(lv_ac_db.id))
        self.assertEqual(lv_ac_db.status, ac_const.LIVEACTION_STATUS_RUNNING, lv_ac_db.result)

        # Identify the records for the main workflow.
        wf_ex_db = wf_db_access.WorkflowExecution.query(action_execution=str(ac_ex_db.id))[0]
        tk_ex_dbs = wf_db_access.TaskExecution.query(workflow_execution=str(wf_ex_db.id))
        self.assertEqual(len(tk_ex_dbs), 2)

        # Identify the records for the subworkflows.
        t1_ac_ex_db = ex_db_access.ActionExecution.query(task_execution=str(tk_ex_dbs[0].id))[0]
        t1_lv_ac_db = lv_db_access.LiveAction.get_by_id(t1_ac_ex_db.liveaction['id'])
        t1_wf_ex_db = wf_db_access.WorkflowExecution.query(action_execution=str(t1_ac_ex_db.id))[0]
        self.assertEqual(t1_lv_ac_db.status, ac_const.LIVEACTION_STATUS_RUNNING)
        self.assertEqual(t1_wf_ex_db.status, wf_states.RUNNING)

        t2_ac_ex_db = ex_db_access.ActionExecution.query(task_execution=str(tk_ex_dbs[1].id))[0]
        t2_lv_ac_db = lv_db_access.LiveAction.get_by_id(t2_ac_ex_db.liveaction['id'])
        t2_wf_ex_db = wf_db_access.WorkflowExecution.query(action_execution=str(t2_ac_ex_db.id))[0]
        self.assertEqual(t2_lv_ac_db.status, ac_const.LIVEACTION_STATUS_RUNNING)
        self.assertEqual(t2_wf_ex_db.status, wf_states.RUNNING)

        # Pause the subworkflow.
        t1_lv_ac_db, t1_ac_ex_db = ac_svc.request_pause(t1_lv_ac_db, cfg.CONF.system_user.user)
        self.assertEqual(t1_lv_ac_db.status, ac_const.LIVEACTION_STATUS_PAUSING)

        # Assert the main workflow is still running.
        lv_ac_db = lv_db_access.LiveAction.get_by_id(str(lv_ac_db.id))
        self.assertEqual(lv_ac_db.status, ac_const.LIVEACTION_STATUS_RUNNING)

        # Assert the other subworkflow is still running.
        t2_lv_ac_db = lv_db_access.LiveAction.get_by_id(t2_ac_ex_db.liveaction['id'])
        self.assertEqual(t2_lv_ac_db.status, ac_const.LIVEACTION_STATUS_RUNNING)

        # Manually notify action execution completion for the task in the subworkflow.
        t1_t1_ex_db = wf_db_access.TaskExecution.query(workflow_execution=str(t1_wf_ex_db.id))[0]
        t1_t1_ac_ex_db = ex_db_access.ActionExecution.query(task_execution=str(t1_t1_ex_db.id))[0]
        notifier.get_notifier().process(t1_t1_ac_ex_db)

        # Assert the subworkflow is paused and manually notify the paused of the
        # corresponding action execution in the main workflow.
        t1_lv_ac_db = lv_db_access.LiveAction.get_by_id(str(t1_lv_ac_db.id))
        self.assertEqual(t1_lv_ac_db.status, ac_const.LIVEACTION_STATUS_PAUSED)
        t1_ac_ex_db = ex_db_access.ActionExecution.get_by_id(t1_ac_ex_db.id)
        self.assertEqual(t1_ac_ex_db.status, ac_const.LIVEACTION_STATUS_PAUSED)
        notifier.get_notifier().process(t1_ac_ex_db)

        # Assert the main workflow is still running.
        lv_ac_db = lv_db_access.LiveAction.get_by_id(str(lv_ac_db.id))
        self.assertEqual(lv_ac_db.status, ac_const.LIVEACTION_STATUS_RUNNING)

        # Assert the other subworkflow is still running.
        t2_lv_ac_db = lv_db_access.LiveAction.get_by_id(t2_ac_ex_db.liveaction['id'])
        self.assertEqual(t2_lv_ac_db.status, ac_const.LIVEACTION_STATUS_RUNNING)

        # Manually notify action execution completion for the tasks in the other subworkflow.
        t2_t1_ex_db = wf_db_access.TaskExecution.query(workflow_execution=str(t2_wf_ex_db.id))[0]
        t2_t1_ac_ex_db = ex_db_access.ActionExecution.query(task_execution=str(t2_t1_ex_db.id))[0]
        notifier.get_notifier().process(t2_t1_ac_ex_db)
        t2_t2_ex_db = wf_db_access.TaskExecution.query(workflow_execution=str(t2_wf_ex_db.id))[1]
        t2_t2_ac_ex_db = ex_db_access.ActionExecution.query(task_execution=str(t2_t2_ex_db.id))[0]
        notifier.get_notifier().process(t2_t2_ac_ex_db)
        t2_t3_ex_db = wf_db_access.TaskExecution.query(workflow_execution=str(t2_wf_ex_db.id))[2]
        t2_t3_ac_ex_db = ex_db_access.ActionExecution.query(task_execution=str(t2_t3_ex_db.id))[0]
        notifier.get_notifier().process(t2_t3_ac_ex_db)
        t2_lv_ac_db = lv_db_access.LiveAction.get_by_id(str(t2_lv_ac_db.id))
        self.assertEqual(t2_lv_ac_db.status, ac_const.LIVEACTION_STATUS_SUCCEEDED)

        # Assert this other subworkflow is completed and manually notify the
        # completion to the corresponding action execution in the main workflow.
        t2_ac_ex_db = ex_db_access.ActionExecution.get_by_id(t2_ac_ex_db.id)
        notifier.get_notifier().process(t2_ac_ex_db)

        # Assert the main workflow is paused because no other tasks is running.
        lv_ac_db = lv_db_access.LiveAction.get_by_id(str(lv_ac_db.id))
        self.assertEqual(lv_ac_db.status, ac_const.LIVEACTION_STATUS_PAUSED)

    def test_pause_subworkflow_while_another_subworkflow_completed(self):
        wf_meta = base.get_wf_fixture_meta_data(TEST_PACK_PATH, 'subworkflows.yaml')
        lv_ac_db = lv_db_models.LiveActionDB(action=wf_meta['name'])
        lv_ac_db, ac_ex_db = ac_svc.request(lv_ac_db)
        lv_ac_db = lv_db_access.LiveAction.get_by_id(str(lv_ac_db.id))
        self.assertEqual(lv_ac_db.status, ac_const.LIVEACTION_STATUS_RUNNING, lv_ac_db.result)

        # Identify the records for the main workflow.
        wf_ex_db = wf_db_access.WorkflowExecution.query(action_execution=str(ac_ex_db.id))[0]
        tk_ex_dbs = wf_db_access.TaskExecution.query(workflow_execution=str(wf_ex_db.id))
        self.assertEqual(len(tk_ex_dbs), 2)

        # Identify the records for the subworkflows.
        t1_ac_ex_db = ex_db_access.ActionExecution.query(task_execution=str(tk_ex_dbs[0].id))[0]
        t1_lv_ac_db = lv_db_access.LiveAction.get_by_id(t1_ac_ex_db.liveaction['id'])
        t1_wf_ex_db = wf_db_access.WorkflowExecution.query(action_execution=str(t1_ac_ex_db.id))[0]
        self.assertEqual(t1_lv_ac_db.status, ac_const.LIVEACTION_STATUS_RUNNING)
        self.assertEqual(t1_wf_ex_db.status, wf_states.RUNNING)

        t2_ac_ex_db = ex_db_access.ActionExecution.query(task_execution=str(tk_ex_dbs[1].id))[0]
        t2_lv_ac_db = lv_db_access.LiveAction.get_by_id(t2_ac_ex_db.liveaction['id'])
        t2_wf_ex_db = wf_db_access.WorkflowExecution.query(action_execution=str(t2_ac_ex_db.id))[0]
        self.assertEqual(t2_lv_ac_db.status, ac_const.LIVEACTION_STATUS_RUNNING)
        self.assertEqual(t2_wf_ex_db.status, wf_states.RUNNING)

        # Pause the subworkflow.
        t1_lv_ac_db, t1_ac_ex_db = ac_svc.request_pause(t1_lv_ac_db, cfg.CONF.system_user.user)
        self.assertEqual(t1_lv_ac_db.status, ac_const.LIVEACTION_STATUS_PAUSING)

        # Assert the main workflow is still running.
        lv_ac_db = lv_db_access.LiveAction.get_by_id(str(lv_ac_db.id))
        self.assertEqual(lv_ac_db.status, ac_const.LIVEACTION_STATUS_RUNNING)

        # Assert the other subworkflow is still running.
        t2_lv_ac_db = lv_db_access.LiveAction.get_by_id(t2_ac_ex_db.liveaction['id'])
        self.assertEqual(t2_lv_ac_db.status, ac_const.LIVEACTION_STATUS_RUNNING)

        # Manually notify action execution completion for the tasks in the other subworkflow.
        t2_t1_ex_db = wf_db_access.TaskExecution.query(workflow_execution=str(t2_wf_ex_db.id))[0]
        t2_t1_ac_ex_db = ex_db_access.ActionExecution.query(task_execution=str(t2_t1_ex_db.id))[0]
        notifier.get_notifier().process(t2_t1_ac_ex_db)
        t2_t2_ex_db = wf_db_access.TaskExecution.query(workflow_execution=str(t2_wf_ex_db.id))[1]
        t2_t2_ac_ex_db = ex_db_access.ActionExecution.query(task_execution=str(t2_t2_ex_db.id))[0]
        notifier.get_notifier().process(t2_t2_ac_ex_db)
        t2_t3_ex_db = wf_db_access.TaskExecution.query(workflow_execution=str(t2_wf_ex_db.id))[2]
        t2_t3_ac_ex_db = ex_db_access.ActionExecution.query(task_execution=str(t2_t3_ex_db.id))[0]
        notifier.get_notifier().process(t2_t3_ac_ex_db)
        t2_lv_ac_db = lv_db_access.LiveAction.get_by_id(str(t2_lv_ac_db.id))
        self.assertEqual(t2_lv_ac_db.status, ac_const.LIVEACTION_STATUS_SUCCEEDED)

        # Assert this other subworkflow is completed and manually notify the
        # completion to the corresponding action execution in the main workflow.
        t2_ac_ex_db = ex_db_access.ActionExecution.get_by_id(t2_ac_ex_db.id)
        notifier.get_notifier().process(t2_ac_ex_db)

        # Assert the main workflow is pausing.
        lv_ac_db = lv_db_access.LiveAction.get_by_id(str(lv_ac_db.id))
        self.assertEqual(lv_ac_db.status, ac_const.LIVEACTION_STATUS_RUNNING)

        # Assert the target subworkflow is still pausing.
        t1_lv_ac_db = lv_db_access.LiveAction.get_by_id(t1_ac_ex_db.liveaction['id'])
        self.assertEqual(t1_lv_ac_db.status, ac_const.LIVEACTION_STATUS_PAUSING)

        # Manually notify action execution completion for the task in the subworkflow.
        t1_t1_ex_db = wf_db_access.TaskExecution.query(workflow_execution=str(t1_wf_ex_db.id))[0]
        t1_t1_ac_ex_db = ex_db_access.ActionExecution.query(task_execution=str(t1_t1_ex_db.id))[0]
        notifier.get_notifier().process(t1_t1_ac_ex_db)

        # Assert the subworkflow is paused and manually notify the paused of the
        # corresponding action execution in the main workflow.
        t1_lv_ac_db = lv_db_access.LiveAction.get_by_id(str(t1_lv_ac_db.id))
        self.assertEqual(t1_lv_ac_db.status, ac_const.LIVEACTION_STATUS_PAUSED)
        t1_ac_ex_db = ex_db_access.ActionExecution.get_by_id(t1_ac_ex_db.id)
        self.assertEqual(t1_ac_ex_db.status, ac_const.LIVEACTION_STATUS_PAUSED)
        notifier.get_notifier().process(t1_ac_ex_db)

        # Assert the main workflow is paused because no other tasks is running.
        lv_ac_db = lv_db_access.LiveAction.get_by_id(str(lv_ac_db.id))
        self.assertEqual(lv_ac_db.status, ac_const.LIVEACTION_STATUS_PAUSED)

    @mock.patch.object(
        ac_svc, 'is_children_active',
        mock.MagicMock(return_value=False))
    def test_resume(self):
        wf_meta = base.get_wf_fixture_meta_data(TEST_PACK_PATH, 'sequential.yaml')
        lv_ac_db = lv_db_models.LiveActionDB(action=wf_meta['name'])
        lv_ac_db, ac_ex_db = ac_svc.request(lv_ac_db)
        lv_ac_db = lv_db_access.LiveAction.get_by_id(str(lv_ac_db.id))
        self.assertEqual(lv_ac_db.status, ac_const.LIVEACTION_STATUS_RUNNING, lv_ac_db.result)

        # Pause the workflow.
        lv_ac_db, ac_ex_db = ac_svc.request_pause(lv_ac_db, cfg.CONF.system_user.user)
        lv_ac_db = lv_db_access.LiveAction.get_by_id(str(lv_ac_db.id))
        self.assertEqual(lv_ac_db.status, ac_const.LIVEACTION_STATUS_PAUSING)

        # Identify the records for the running task(s) and manually complete it.
        wf_ex_dbs = wf_db_access.WorkflowExecution.query(action_execution=str(ac_ex_db.id))
        tk_ex_dbs = wf_db_access.TaskExecution.query(workflow_execution=str(wf_ex_dbs[0].id))
        self.assertEqual(len(tk_ex_dbs), 1)
        tk_ac_ex_dbs = ex_db_access.ActionExecution.query(task_execution=str(tk_ex_dbs[0].id))
        tk_lv_ac_db = lv_db_access.LiveAction.get_by_id(tk_ac_ex_dbs[0].liveaction['id'])
        self.assertEqual(tk_ac_ex_dbs[0].status, ac_const.LIVEACTION_STATUS_SUCCEEDED)
        self.assertEqual(tk_lv_ac_db.status, ac_const.LIVEACTION_STATUS_SUCCEEDED)
        wf_svc.handle_action_execution_completion(tk_ac_ex_dbs[0])

        # Ensure the workflow is paused.
        lv_ac_db = lv_db_access.LiveAction.get_by_id(str(lv_ac_db.id))
        self.assertEqual(lv_ac_db.status, ac_const.LIVEACTION_STATUS_PAUSED, lv_ac_db.result)
        wf_ex_dbs = wf_db_access.WorkflowExecution.query(action_execution=str(ac_ex_db.id))
        self.assertEqual(wf_ex_dbs[0].status, wf_states.PAUSED)

        # Resume the workflow.
        lv_ac_db, ac_ex_db = ac_svc.request_resume(lv_ac_db, cfg.CONF.system_user.user)
        lv_ac_db = lv_db_access.LiveAction.get_by_id(str(lv_ac_db.id))
        self.assertEqual(lv_ac_db.status, ac_const.LIVEACTION_STATUS_RUNNING)
        wf_ex_dbs = wf_db_access.WorkflowExecution.query(action_execution=str(ac_ex_db.id))
        self.assertEqual(wf_ex_dbs[0].status, wf_states.RUNNING)
        tk_ex_dbs = wf_db_access.TaskExecution.query(workflow_execution=str(wf_ex_dbs[0].id))
        self.assertEqual(len(tk_ex_dbs), 2)

    def test_resume_cascade_to_subworkflow(self):
        wf_meta = base.get_wf_fixture_meta_data(TEST_PACK_PATH, 'subworkflow.yaml')
        lv_ac_db = lv_db_models.LiveActionDB(action=wf_meta['name'])
        lv_ac_db, ac_ex_db = ac_svc.request(lv_ac_db)
        lv_ac_db = lv_db_access.LiveAction.get_by_id(str(lv_ac_db.id))
        self.assertEqual(lv_ac_db.status, ac_const.LIVEACTION_STATUS_RUNNING, lv_ac_db.result)

        # Identify the records for the main workflow.
        wf_ex_dbs = wf_db_access.WorkflowExecution.query(action_execution=str(ac_ex_db.id))
        self.assertEqual(len(wf_ex_dbs), 1)

        wf_ex_db = wf_ex_dbs[0]
        tk_ex_dbs = wf_db_access.TaskExecution.query(workflow_execution=str(wf_ex_db.id))
        self.assertEqual(len(tk_ex_dbs), 1)

        tk_ex_db = tk_ex_dbs[0]
        tk_ac_ex_dbs = ex_db_access.ActionExecution.query(task_execution=str(tk_ex_db.id))
        self.assertEqual(len(tk_ac_ex_dbs), 1)

        tk_ac_ex_db = tk_ac_ex_dbs[0]
        tk_lv_ac_db = lv_db_access.LiveAction.get_by_id(tk_ac_ex_db.liveaction['id'])
        self.assertEqual(tk_lv_ac_db.status, ac_const.LIVEACTION_STATUS_RUNNING)

        # Identify the records for the subworkflow.
        sub_wf_ex_dbs = wf_db_access.WorkflowExecution.query(action_execution=str(tk_ac_ex_db.id))
        self.assertEqual(len(sub_wf_ex_dbs), 1)

        sub_wf_ex_db = sub_wf_ex_dbs[0]
        sub_tk_ex_dbs = wf_db_access.TaskExecution.query(workflow_execution=str(sub_wf_ex_db.id))
        self.assertEqual(len(sub_tk_ex_dbs), 1)

        sub_tk_ex_db = sub_tk_ex_dbs[0]
        sub_tk_ac_ex_dbs = ex_db_access.ActionExecution.query(task_execution=str(sub_tk_ex_db.id))
        self.assertEqual(len(sub_tk_ac_ex_dbs), 1)

        # Pause the main workflow and assert it is pausing because subworkflow is still running.
        lv_ac_db, ac_ex_db = ac_svc.request_pause(lv_ac_db, cfg.CONF.system_user.user)
        self.assertEqual(lv_ac_db.status, ac_const.LIVEACTION_STATUS_PAUSING)

        # Assert the subworkflow is pausing.
        tk_lv_ac_db = lv_db_access.LiveAction.get_by_id(str(tk_lv_ac_db.id))
        self.assertEqual(tk_lv_ac_db.status, ac_const.LIVEACTION_STATUS_PAUSING)

        # Manually handle action execution completion for the task in the subworkflow.
        sub_tk_ac_ex_db = sub_tk_ac_ex_dbs[0]
        self.assertEqual(sub_tk_ac_ex_db.status, ac_const.LIVEACTION_STATUS_SUCCEEDED)
        notifier.get_notifier().process(sub_tk_ac_ex_db)

        # Assert the subworkflow is paused and manually process the execution update.
        tk_lv_ac_db = lv_db_access.LiveAction.get_by_id(str(tk_lv_ac_db.id))
        self.assertEqual(tk_lv_ac_db.status, ac_const.LIVEACTION_STATUS_PAUSED)
        tk_ac_ex_db = ex_db_access.ActionExecution.get_by_id(str(tk_ac_ex_db.id))
        self.assertEqual(tk_ac_ex_db.status, ac_const.LIVEACTION_STATUS_PAUSED)
        notifier.get_notifier().process(tk_ac_ex_db)

        # Assert the main workflow is paused.
        lv_ac_db = lv_db_access.LiveAction.get_by_id(str(lv_ac_db.id))
        self.assertEqual(lv_ac_db.status, ac_const.LIVEACTION_STATUS_PAUSED)

        # Resume the main workflow and assert it is running.
        lv_ac_db, ac_ex_db = ac_svc.request_resume(lv_ac_db, cfg.CONF.system_user.user)
        lv_ac_db = lv_db_access.LiveAction.get_by_id(str(lv_ac_db.id))
        self.assertEqual(lv_ac_db.status, ac_const.LIVEACTION_STATUS_RUNNING)

        # Assert the subworkflow is running.
        tk_lv_ac_db = lv_db_access.LiveAction.get_by_id(str(tk_lv_ac_db.id))
        self.assertEqual(tk_lv_ac_db.status, ac_const.LIVEACTION_STATUS_RUNNING)

    def test_resume_from_subworkflow_when_parent_is_paused(self):
        wf_meta = base.get_wf_fixture_meta_data(TEST_PACK_PATH, 'subworkflows.yaml')
        lv_ac_db = lv_db_models.LiveActionDB(action=wf_meta['name'])
        lv_ac_db, ac_ex_db = ac_svc.request(lv_ac_db)
        lv_ac_db = lv_db_access.LiveAction.get_by_id(str(lv_ac_db.id))
        self.assertEqual(lv_ac_db.status, ac_const.LIVEACTION_STATUS_RUNNING, lv_ac_db.result)

        # Identify the records for the main workflow.
        wf_ex_db = wf_db_access.WorkflowExecution.query(action_execution=str(ac_ex_db.id))[0]
        tk_ex_dbs = wf_db_access.TaskExecution.query(workflow_execution=str(wf_ex_db.id))
        self.assertEqual(len(tk_ex_dbs), 2)

        # Identify the records for the subworkflows.
        t1_ac_ex_db = ex_db_access.ActionExecution.query(task_execution=str(tk_ex_dbs[0].id))[0]
        t1_lv_ac_db = lv_db_access.LiveAction.get_by_id(t1_ac_ex_db.liveaction['id'])
        t1_wf_ex_db = wf_db_access.WorkflowExecution.query(action_execution=str(t1_ac_ex_db.id))[0]
        self.assertEqual(t1_lv_ac_db.status, ac_const.LIVEACTION_STATUS_RUNNING)
        self.assertEqual(t1_wf_ex_db.status, wf_states.RUNNING)

        t2_ac_ex_db = ex_db_access.ActionExecution.query(task_execution=str(tk_ex_dbs[1].id))[0]
        t2_lv_ac_db = lv_db_access.LiveAction.get_by_id(t2_ac_ex_db.liveaction['id'])
        t2_wf_ex_db = wf_db_access.WorkflowExecution.query(action_execution=str(t2_ac_ex_db.id))[0]
        self.assertEqual(t2_lv_ac_db.status, ac_const.LIVEACTION_STATUS_RUNNING)
        self.assertEqual(t2_wf_ex_db.status, wf_states.RUNNING)

        # Pause the subworkflow.
        t1_lv_ac_db, t1_ac_ex_db = ac_svc.request_pause(t1_lv_ac_db, cfg.CONF.system_user.user)
        self.assertEqual(t1_lv_ac_db.status, ac_const.LIVEACTION_STATUS_PAUSING)

        # Assert the main workflow is still running.
        lv_ac_db = lv_db_access.LiveAction.get_by_id(str(lv_ac_db.id))
        self.assertEqual(lv_ac_db.status, ac_const.LIVEACTION_STATUS_RUNNING)

        # Assert the other subworkflow is still running.
        t2_lv_ac_db = lv_db_access.LiveAction.get_by_id(t2_ac_ex_db.liveaction['id'])
        self.assertEqual(t2_lv_ac_db.status, ac_const.LIVEACTION_STATUS_RUNNING)

        # Manually notify action execution completion for the task in the subworkflow.
        t1_t1_ex_db = wf_db_access.TaskExecution.query(workflow_execution=str(t1_wf_ex_db.id))[0]
        t1_t1_ac_ex_db = ex_db_access.ActionExecution.query(task_execution=str(t1_t1_ex_db.id))[0]
        notifier.get_notifier().process(t1_t1_ac_ex_db)

        # Assert the subworkflow is paused and manually notify the paused of the
        # corresponding action execution in the main workflow.
        t1_lv_ac_db = lv_db_access.LiveAction.get_by_id(str(t1_lv_ac_db.id))
        self.assertEqual(t1_lv_ac_db.status, ac_const.LIVEACTION_STATUS_PAUSED)
        t1_ac_ex_db = ex_db_access.ActionExecution.get_by_id(t1_ac_ex_db.id)
        self.assertEqual(t1_ac_ex_db.status, ac_const.LIVEACTION_STATUS_PAUSED)
        notifier.get_notifier().process(t1_ac_ex_db)

        # Assert the main workflow is pausing.
        lv_ac_db = lv_db_access.LiveAction.get_by_id(str(lv_ac_db.id))
        self.assertEqual(lv_ac_db.status, ac_const.LIVEACTION_STATUS_RUNNING)

        # Assert the other subworkflow is still running.
        t2_lv_ac_db = lv_db_access.LiveAction.get_by_id(t2_ac_ex_db.liveaction['id'])
        self.assertEqual(t2_lv_ac_db.status, ac_const.LIVEACTION_STATUS_RUNNING)

        # Manually notify action execution completion for the tasks in the other subworkflow.
        t2_t1_ex_db = wf_db_access.TaskExecution.query(workflow_execution=str(t2_wf_ex_db.id))[0]
        t2_t1_ac_ex_db = ex_db_access.ActionExecution.query(task_execution=str(t2_t1_ex_db.id))[0]
        notifier.get_notifier().process(t2_t1_ac_ex_db)
        t2_t2_ex_db = wf_db_access.TaskExecution.query(workflow_execution=str(t2_wf_ex_db.id))[1]
        t2_t2_ac_ex_db = ex_db_access.ActionExecution.query(task_execution=str(t2_t2_ex_db.id))[0]
        notifier.get_notifier().process(t2_t2_ac_ex_db)
        t2_t3_ex_db = wf_db_access.TaskExecution.query(workflow_execution=str(t2_wf_ex_db.id))[2]
        t2_t3_ac_ex_db = ex_db_access.ActionExecution.query(task_execution=str(t2_t3_ex_db.id))[0]
        notifier.get_notifier().process(t2_t3_ac_ex_db)
        t2_lv_ac_db = lv_db_access.LiveAction.get_by_id(str(t2_lv_ac_db.id))
        self.assertEqual(t2_lv_ac_db.status, ac_const.LIVEACTION_STATUS_SUCCEEDED)

        # Assert this other subworkflow is completed and manually notify the
        # completion to the corresponding action execution in the main workflow.
        t2_ac_ex_db = ex_db_access.ActionExecution.get_by_id(t2_ac_ex_db.id)
        notifier.get_notifier().process(t2_ac_ex_db)

        # Assert the main workflow is paused because no other tasks is running.
        lv_ac_db = lv_db_access.LiveAction.get_by_id(str(lv_ac_db.id))
        self.assertEqual(lv_ac_db.status, ac_const.LIVEACTION_STATUS_PAUSED)

        # Resume the subworkflow and assert it is running.
        t1_lv_ac_db, t1_ac_ex_db = ac_svc.request_resume(t1_lv_ac_db, cfg.CONF.system_user.user)
        t1_lv_ac_db = lv_db_access.LiveAction.get_by_id(str(t1_lv_ac_db.id))
        self.assertEqual(t1_lv_ac_db.status, ac_const.LIVEACTION_STATUS_RUNNING)

        # Assert the main workflow is running.
        lv_ac_db = lv_db_access.LiveAction.get_by_id(str(lv_ac_db.id))
        self.assertEqual(lv_ac_db.status, ac_const.LIVEACTION_STATUS_RUNNING)

        # Manually notify action execution completion for the tasks in the subworkflow.
        t1_t2_ex_db = wf_db_access.TaskExecution.query(workflow_execution=str(t1_wf_ex_db.id))[1]
        t1_t2_ac_ex_db = ex_db_access.ActionExecution.query(task_execution=str(t1_t2_ex_db.id))[0]
        notifier.get_notifier().process(t1_t2_ac_ex_db)
        t1_t3_ex_db = wf_db_access.TaskExecution.query(workflow_execution=str(t1_wf_ex_db.id))[2]
        t1_t3_ac_ex_db = ex_db_access.ActionExecution.query(task_execution=str(t1_t3_ex_db.id))[0]
        notifier.get_notifier().process(t1_t3_ac_ex_db)
        t1_lv_ac_db = lv_db_access.LiveAction.get_by_id(str(t1_lv_ac_db.id))
        self.assertEqual(t1_lv_ac_db.status, ac_const.LIVEACTION_STATUS_SUCCEEDED)

        # Assert the subworkflow is completed and manually notify the
        # completion to the corresponding action execution in the main workflow.
        t1_ac_ex_db = ex_db_access.ActionExecution.get_by_id(t1_ac_ex_db.id)
        notifier.get_notifier().process(t1_ac_ex_db)

        # Assert the main workflow is completed.
        lv_ac_db = lv_db_access.LiveAction.get_by_id(str(lv_ac_db.id))
        self.assertEqual(lv_ac_db.status, ac_const.LIVEACTION_STATUS_SUCCEEDED)

    def test_resume_from_subworkflow_when_parent_is_running(self):
        wf_meta = base.get_wf_fixture_meta_data(TEST_PACK_PATH, 'subworkflows.yaml')
        lv_ac_db = lv_db_models.LiveActionDB(action=wf_meta['name'])
        lv_ac_db, ac_ex_db = ac_svc.request(lv_ac_db)
        lv_ac_db = lv_db_access.LiveAction.get_by_id(str(lv_ac_db.id))
        self.assertEqual(lv_ac_db.status, ac_const.LIVEACTION_STATUS_RUNNING, lv_ac_db.result)

        # Identify the records for the main workflow.
        wf_ex_db = wf_db_access.WorkflowExecution.query(action_execution=str(ac_ex_db.id))[0]
        tk_ex_dbs = wf_db_access.TaskExecution.query(workflow_execution=str(wf_ex_db.id))
        self.assertEqual(len(tk_ex_dbs), 2)

        # Identify the records for the subworkflows.
        t1_ac_ex_db = ex_db_access.ActionExecution.query(task_execution=str(tk_ex_dbs[0].id))[0]
        t1_lv_ac_db = lv_db_access.LiveAction.get_by_id(t1_ac_ex_db.liveaction['id'])
        t1_wf_ex_db = wf_db_access.WorkflowExecution.query(action_execution=str(t1_ac_ex_db.id))[0]
        self.assertEqual(t1_lv_ac_db.status, ac_const.LIVEACTION_STATUS_RUNNING)
        self.assertEqual(t1_wf_ex_db.status, wf_states.RUNNING)

        t2_ac_ex_db = ex_db_access.ActionExecution.query(task_execution=str(tk_ex_dbs[1].id))[0]
        t2_lv_ac_db = lv_db_access.LiveAction.get_by_id(t2_ac_ex_db.liveaction['id'])
        t2_wf_ex_db = wf_db_access.WorkflowExecution.query(action_execution=str(t2_ac_ex_db.id))[0]
        self.assertEqual(t2_lv_ac_db.status, ac_const.LIVEACTION_STATUS_RUNNING)
        self.assertEqual(t2_wf_ex_db.status, wf_states.RUNNING)

        # Pause the subworkflow.
        t1_lv_ac_db, t1_ac_ex_db = ac_svc.request_pause(t1_lv_ac_db, cfg.CONF.system_user.user)
        self.assertEqual(t1_lv_ac_db.status, ac_const.LIVEACTION_STATUS_PAUSING)

        # Assert the main workflow is still running.
        lv_ac_db = lv_db_access.LiveAction.get_by_id(str(lv_ac_db.id))
        self.assertEqual(lv_ac_db.status, ac_const.LIVEACTION_STATUS_RUNNING)

        # Assert the other subworkflow is still running.
        t2_lv_ac_db = lv_db_access.LiveAction.get_by_id(t2_ac_ex_db.liveaction['id'])
        self.assertEqual(t2_lv_ac_db.status, ac_const.LIVEACTION_STATUS_RUNNING)

        # Manually notify action execution completion for the task in the subworkflow.
        t1_t1_ex_db = wf_db_access.TaskExecution.query(workflow_execution=str(t1_wf_ex_db.id))[0]
        t1_t1_ac_ex_db = ex_db_access.ActionExecution.query(task_execution=str(t1_t1_ex_db.id))[0]
        notifier.get_notifier().process(t1_t1_ac_ex_db)

        # Assert the subworkflow is paused and manually notify the paused of the
        # corresponding action execution in the main workflow.
        t1_lv_ac_db = lv_db_access.LiveAction.get_by_id(str(t1_lv_ac_db.id))
        self.assertEqual(t1_lv_ac_db.status, ac_const.LIVEACTION_STATUS_PAUSED)
        t1_ac_ex_db = ex_db_access.ActionExecution.get_by_id(t1_ac_ex_db.id)
        self.assertEqual(t1_ac_ex_db.status, ac_const.LIVEACTION_STATUS_PAUSED)
        notifier.get_notifier().process(t1_ac_ex_db)

        # Assert the main workflow is still running.
        lv_ac_db = lv_db_access.LiveAction.get_by_id(str(lv_ac_db.id))
        self.assertEqual(lv_ac_db.status, ac_const.LIVEACTION_STATUS_RUNNING)

        # Assert the other subworkflow is still running.
        t2_lv_ac_db = lv_db_access.LiveAction.get_by_id(t2_ac_ex_db.liveaction['id'])
        self.assertEqual(t2_lv_ac_db.status, ac_const.LIVEACTION_STATUS_RUNNING)

        # Resume the subworkflow and assert it is running.
        t1_lv_ac_db, t1_ac_ex_db = ac_svc.request_resume(t1_lv_ac_db, cfg.CONF.system_user.user)
        t1_lv_ac_db = lv_db_access.LiveAction.get_by_id(str(t1_lv_ac_db.id))
        self.assertEqual(t1_lv_ac_db.status, ac_const.LIVEACTION_STATUS_RUNNING)

        # Assert the main workflow is running.
        lv_ac_db = lv_db_access.LiveAction.get_by_id(str(lv_ac_db.id))
        self.assertEqual(lv_ac_db.status, ac_const.LIVEACTION_STATUS_RUNNING)

        # Assert the other subworkflow is still running.
        t2_lv_ac_db = lv_db_access.LiveAction.get_by_id(t2_ac_ex_db.liveaction['id'])
        self.assertEqual(t2_lv_ac_db.status, ac_const.LIVEACTION_STATUS_RUNNING)

        # Manually notify action execution completion for the tasks in the subworkflow.
        t1_t2_ex_db = wf_db_access.TaskExecution.query(workflow_execution=str(t1_wf_ex_db.id))[1]
        t1_t2_ac_ex_db = ex_db_access.ActionExecution.query(task_execution=str(t1_t2_ex_db.id))[0]
        notifier.get_notifier().process(t1_t2_ac_ex_db)
        t1_t3_ex_db = wf_db_access.TaskExecution.query(workflow_execution=str(t1_wf_ex_db.id))[2]
        t1_t3_ac_ex_db = ex_db_access.ActionExecution.query(task_execution=str(t1_t3_ex_db.id))[0]
        notifier.get_notifier().process(t1_t3_ac_ex_db)
        t1_lv_ac_db = lv_db_access.LiveAction.get_by_id(str(t1_lv_ac_db.id))
        self.assertEqual(t1_lv_ac_db.status, ac_const.LIVEACTION_STATUS_SUCCEEDED)

        # Assert the subworkflow is completed and manually notify the
        # completion to the corresponding action execution in the main workflow.
        t1_ac_ex_db = ex_db_access.ActionExecution.get_by_id(t1_ac_ex_db.id)
        notifier.get_notifier().process(t1_ac_ex_db)

        # Manually notify action execution completion for the tasks in the other subworkflow.
        t2_t1_ex_db = wf_db_access.TaskExecution.query(workflow_execution=str(t2_wf_ex_db.id))[0]
        t2_t1_ac_ex_db = ex_db_access.ActionExecution.query(task_execution=str(t2_t1_ex_db.id))[0]
        notifier.get_notifier().process(t2_t1_ac_ex_db)
        t2_t2_ex_db = wf_db_access.TaskExecution.query(workflow_execution=str(t2_wf_ex_db.id))[1]
        t2_t2_ac_ex_db = ex_db_access.ActionExecution.query(task_execution=str(t2_t2_ex_db.id))[0]
        notifier.get_notifier().process(t2_t2_ac_ex_db)
        t2_t3_ex_db = wf_db_access.TaskExecution.query(workflow_execution=str(t2_wf_ex_db.id))[2]
        t2_t3_ac_ex_db = ex_db_access.ActionExecution.query(task_execution=str(t2_t3_ex_db.id))[0]
        notifier.get_notifier().process(t2_t3_ac_ex_db)
        t2_lv_ac_db = lv_db_access.LiveAction.get_by_id(str(t2_lv_ac_db.id))
        self.assertEqual(t2_lv_ac_db.status, ac_const.LIVEACTION_STATUS_SUCCEEDED)

        # Assert this other subworkflow is completed and manually notify the
        # completion to the corresponding action execution in the main workflow.
        t2_ac_ex_db = ex_db_access.ActionExecution.get_by_id(t2_ac_ex_db.id)
        notifier.get_notifier().process(t2_ac_ex_db)

        # Assert the main workflow is completed.
        lv_ac_db = lv_db_access.LiveAction.get_by_id(str(lv_ac_db.id))
        self.assertEqual(lv_ac_db.status, ac_const.LIVEACTION_STATUS_SUCCEEDED)

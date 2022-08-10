# Copyright 2020 The StackStorm Authors.
# Copyright 2019 Extreme Networks, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
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

from orquesta import statuses as wf_statuses

import st2tests

# XXX: actionsensor import depends on config being setup.
import st2tests.config as tests_config

tests_config.parse_args()

from tests.unit import base

import st2common
from local_runner import local_shell_command_runner
from st2actions.notifier import notifier
from st2actions.workflows import workflows
from st2common.bootstrap import actionsregistrar
from st2common.bootstrap import policiesregistrar
from st2common.bootstrap import runnersregistrar
from st2common.constants import action as ac_const
from st2common.models.db import liveaction as lv_db_models
from st2common.persistence import execution as ex_db_access
from st2common.persistence import liveaction as lv_db_access
from st2common.persistence import workflow as wf_db_access
from st2common.services import action as ac_svc
from st2common.transport import liveaction as lv_ac_xport
from st2common.transport import workflow as wf_ex_xport
from st2common.transport import publishers
from st2tests.fixtures.packs.core.fixture import PACK_PATH as CORE_PACK_PATH
from st2tests.fixtures.packs.orquesta_tests.fixture import (
    PACK_NAME as TEST_PACK,
    PACK_PATH as TEST_PACK_PATH,
)
from st2tests.mocks import liveaction as mock_lv_ac_xport
from st2tests.mocks import workflow as mock_wf_ex_xport


PACKS = [TEST_PACK_PATH, CORE_PACK_PATH]

RUNNER_RESULT_FAILED = (ac_const.LIVEACTION_STATUS_FAILED, {"stderror": "..."}, {})


@mock.patch.object(
    publishers.CUDPublisher, "publish_update", mock.MagicMock(return_value=None)
)
@mock.patch.object(
    lv_ac_xport.LiveActionPublisher,
    "publish_create",
    mock.MagicMock(side_effect=mock_lv_ac_xport.MockLiveActionPublisher.publish_create),
)
@mock.patch.object(
    lv_ac_xport.LiveActionPublisher,
    "publish_state",
    mock.MagicMock(side_effect=mock_lv_ac_xport.MockLiveActionPublisher.publish_state),
)
@mock.patch.object(
    wf_ex_xport.WorkflowExecutionPublisher,
    "publish_create",
    mock.MagicMock(
        side_effect=mock_wf_ex_xport.MockWorkflowExecutionPublisher.publish_create
    ),
)
@mock.patch.object(
    wf_ex_xport.WorkflowExecutionPublisher,
    "publish_state",
    mock.MagicMock(
        side_effect=mock_wf_ex_xport.MockWorkflowExecutionPublisher.publish_state
    ),
)
class OrquestaRunnerTest(st2tests.ExecutionDbTestCase):
    @classmethod
    def setUpClass(cls):
        super(OrquestaRunnerTest, cls).setUpClass()

        # Register runners and policy types.
        runnersregistrar.register_runners()
        policiesregistrar.register_policy_types(st2common)

        # Register test pack(s).
        registrar_options = {"use_pack_cache": False, "fail_on_failure": True}
        actions_registrar = actionsregistrar.ActionsRegistrar(**registrar_options)
        policies_registrar = policiesregistrar.PolicyRegistrar(**registrar_options)

        for pack in PACKS:
            actions_registrar.register_from_pack(pack)
            policies_registrar.register_from_pack(pack)

    def tearDown(self):
        super(OrquestaRunnerTest, self).tearDown()

        # Remove all liveactions before running each test.
        for lv_ac_db in lv_db_access.LiveAction.get_all():
            lv_ac_db.delete()

        # Remove all action executions before running each test.
        for ac_ex_db in ex_db_access.ActionExecution.get_all():
            ac_ex_db.delete()

    @mock.patch.object(
        local_shell_command_runner.LocalShellCommandRunner,
        "run",
        mock.MagicMock(side_effect=[RUNNER_RESULT_FAILED]),
    )
    def test_retry_policy_applied_on_workflow_failure(self):
        wf_name = "sequential"
        wf_ac_ref = TEST_PACK + "." + wf_name
        wf_meta = base.get_wf_fixture_meta_data(TEST_PACK_PATH, wf_name + ".yaml")
        lv_ac_db = lv_db_models.LiveActionDB(action=wf_meta["name"])
        lv_ac_db, ac_ex_db = ac_svc.request(lv_ac_db)
        lv_ac_db = lv_db_access.LiveAction.get_by_id(str(lv_ac_db.id))
        self.assertEqual(
            lv_ac_db.status, ac_const.LIVEACTION_STATUS_RUNNING, lv_ac_db.result
        )

        # Ensure there is only one execution recorded.
        self.assertEqual(len(lv_db_access.LiveAction.query(action=wf_ac_ref)), 1)

        # Identify the records for the workflow and task.
        wf_ex_db = wf_db_access.WorkflowExecution.query(
            action_execution=str(ac_ex_db.id)
        )[0]
        t1_ex_db = wf_db_access.TaskExecution.query(
            workflow_execution=str(wf_ex_db.id)
        )[0]
        t1_lv_ac_db = lv_db_access.LiveAction.query(task_execution=str(t1_ex_db.id))[0]
        self.assertEqual(t1_lv_ac_db.status, ac_const.LIVEACTION_STATUS_FAILED)
        t1_ac_ex_db = ex_db_access.ActionExecution.query(
            task_execution=str(t1_ex_db.id)
        )[0]

        self.assertEqual(t1_ac_ex_db.status, ac_const.LIVEACTION_STATUS_FAILED)
        notifier.get_notifier().process(t1_ac_ex_db)
        workflows.get_engine().process(t1_ac_ex_db)

        # Assert the main workflow is completed.
        ac_ex_db = ex_db_access.ActionExecution.get_by_id(str(ac_ex_db.id))
        self.assertEqual(ac_ex_db.status, ac_const.LIVEACTION_STATUS_FAILED)
        notifier.get_notifier().process(ac_ex_db)

        # Ensure execution is retried.
        self.assertEqual(len(lv_db_access.LiveAction.query(action=wf_ac_ref)), 2)

    @mock.patch.object(
        local_shell_command_runner.LocalShellCommandRunner,
        "run",
        mock.MagicMock(side_effect=[RUNNER_RESULT_FAILED]),
    )
    def test_no_retry_policy_applied_on_task_failure(self):
        wf_meta = base.get_wf_fixture_meta_data(TEST_PACK_PATH, "subworkflow.yaml")
        lv_ac_db = lv_db_models.LiveActionDB(action=wf_meta["name"])
        lv_ac_db, ac_ex_db = ac_svc.request(lv_ac_db)
        lv_ac_db = lv_db_access.LiveAction.get_by_id(str(lv_ac_db.id))
        self.assertEqual(
            lv_ac_db.status, ac_const.LIVEACTION_STATUS_RUNNING, lv_ac_db.result
        )

        # Identify the records for the main workflow.
        wf_ex_db = wf_db_access.WorkflowExecution.query(
            action_execution=str(ac_ex_db.id)
        )[0]
        tk_ex_dbs = wf_db_access.TaskExecution.query(
            workflow_execution=str(wf_ex_db.id)
        )
        self.assertEqual(len(tk_ex_dbs), 1)

        # Identify the records for the tasks.
        t1_ac_ex_db = ex_db_access.ActionExecution.query(
            task_execution=str(tk_ex_dbs[0].id)
        )[0]
        t1_wf_ex_db = wf_db_access.WorkflowExecution.query(
            action_execution=str(t1_ac_ex_db.id)
        )[0]
        self.assertEqual(t1_ac_ex_db.status, ac_const.LIVEACTION_STATUS_RUNNING)
        self.assertEqual(t1_wf_ex_db.status, wf_statuses.RUNNING)

        # Ensure there is only one execution for the task.
        tk_ac_ref = TEST_PACK + "." + "sequential"
        self.assertEqual(len(lv_db_access.LiveAction.query(action=tk_ac_ref)), 1)

        # Fail the subtask of the subworkflow.
        t1_t1_ex_db = wf_db_access.TaskExecution.query(
            workflow_execution=str(t1_wf_ex_db.id)
        )[0]
        t1_t1_lv_ac_db = lv_db_access.LiveAction.query(
            task_execution=str(t1_t1_ex_db.id)
        )[0]
        self.assertEqual(t1_t1_lv_ac_db.status, ac_const.LIVEACTION_STATUS_FAILED)
        t1_t1_ac_ex_db = ex_db_access.ActionExecution.query(
            task_execution=str(t1_t1_ex_db.id)
        )[0]
        self.assertEqual(t1_t1_ac_ex_db.status, ac_const.LIVEACTION_STATUS_FAILED)
        notifier.get_notifier().process(t1_t1_ac_ex_db)
        workflows.get_engine().process(t1_t1_ac_ex_db)

        # Ensure the task execution is not retried.
        self.assertEqual(len(lv_db_access.LiveAction.query(action=tk_ac_ref)), 1)

        # Process the failure of the subworkflow.
        t1_ac_ex_db = ex_db_access.ActionExecution.get_by_id(str(t1_ac_ex_db.id))
        self.assertEqual(t1_ac_ex_db.status, ac_const.LIVEACTION_STATUS_FAILED)
        workflows.get_engine().process(t1_ac_ex_db)

        # Assert the main workflow is completed.
        ac_ex_db = ex_db_access.ActionExecution.get_by_id(str(ac_ex_db.id))
        self.assertEqual(ac_ex_db.status, ac_const.LIVEACTION_STATUS_FAILED)

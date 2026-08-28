# -*- coding: utf-8 -*-

# Copyright 2020 The StackStorm Authors.
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

from st2common.bootstrap import actionsregistrar
from st2common.bootstrap import runnersregistrar
from st2common.constants import action as ac_const
from st2common.models.db import liveaction as lv_db_models
from st2common.persistence import execution as ex_db_access
from st2common.persistence import liveaction as lv_db_access
from st2common.persistence import workflow as wf_db_access
from st2common.runners import utils as runners_utils
from st2common.services import action as ac_svc
from st2common.services import workflows as wf_svc
from st2common.transport import liveaction as lv_ac_xport
from st2common.transport import workflow as wf_ex_xport
from st2common.transport import publishers
from st2tests.fixtures.packs.core.fixture import PACK_PATH as CORE_PACK_PATH
from st2tests.fixtures.packs.orquesta_tests.fixture import PACK_PATH as TEST_PACK_PATH
from st2tests.mocks import liveaction as mock_lv_ac_xport
from st2tests.mocks import workflow as mock_wf_ex_xport


PACKS = [TEST_PACK_PATH, CORE_PACK_PATH]


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
class ReconcileRunningWorkflowTest(st2tests.ExecutionDbTestCase):
    @classmethod
    def setUpClass(cls):
        super(ReconcileRunningWorkflowTest, cls).setUpClass()

        # Register runners.
        runnersregistrar.register_runners()

        # Register test pack(s).
        actions_registrar = actionsregistrar.ActionsRegistrar(
            use_pack_cache=False, fail_on_failure=True
        )

        for pack in PACKS:
            actions_registrar.register_from_pack(pack)

    @mock.patch.object(
        runners_utils, "invoke_post_run", mock.MagicMock(return_value=None)
    )
    def test_reconcile_recovers_workflow_with_lost_completion_message(self):
        # Start the sequential workflow (task1 -> task2 -> task3).
        wf_meta = base.get_wf_fixture_meta_data(TEST_PACK_PATH, "sequential.yaml")
        wf_input = {"who": "Thanos"}
        lv_ac_db = lv_db_models.LiveActionDB(
            action=wf_meta["name"], parameters=wf_input
        )
        lv_ac_db, ac_ex_db = ac_svc.request(lv_ac_db)

        lv_ac_db = lv_db_access.LiveAction.get_by_id(str(lv_ac_db.id))
        self.assertEqual(lv_ac_db.status, ac_const.LIVEACTION_STATUS_RUNNING)

        wf_ex_db = wf_db_access.WorkflowExecution.query(
            action_execution=str(ac_ex_db.id)
        )[0]

        # task1's child action execution has already run to completion, but we
        # deliberately do NOT call handle_action_execution_completion. This
        # simulates an engine being hard-killed (e.g. OOM) after the message
        # was acked but before it was processed: the completion message is lost
        # and RabbitMQ will not redeliver it.
        tk1_ex_db = wf_db_access.TaskExecution.query(
            workflow_execution=str(wf_ex_db.id), task_id="task1"
        )[0]
        tk1_ac_ex_db = ex_db_access.ActionExecution.query(
            task_execution=str(tk1_ex_db.id)
        )[0]
        tk1_lv_ac_db = lv_db_access.LiveAction.get_by_id(tk1_ac_ex_db.liveaction_id)

        # The child action finished...
        self.assertEqual(tk1_lv_ac_db.status, ac_const.LIVEACTION_STATUS_SUCCEEDED)
        # ...but its task execution was never advanced (the lost message),...
        self.assertEqual(tk1_ex_db.status, wf_statuses.RUNNING)
        # ...so no downstream task was created,...
        self.assertEqual(
            len(
                wf_db_access.TaskExecution.query(
                    workflow_execution=str(wf_ex_db.id), task_id="task2"
                )
            ),
            0,
        )
        # ...and the whole workflow is wedged in RUNNING.
        wf_ex_db = wf_db_access.WorkflowExecution.get_by_id(wf_ex_db.id)
        self.assertEqual(wf_ex_db.status, wf_statuses.RUNNING)

        # Confirm bootstrap_resume_execution (the PAUSED path) is a no-op here:
        # request_resume early-returns for anything already in a RUNNING status,
        # which is exactly why a separate reconcile path is needed.
        wf_svc.bootstrap_resume_execution(lv_ac_db)
        self.assertEqual(
            len(
                wf_db_access.TaskExecution.query(
                    workflow_execution=str(wf_ex_db.id), task_id="task2"
                )
            ),
            0,
        )

        # Operator-initiated reconcile: replays the lost completion(s) and
        # re-drives the workflow. In this synchronous test harness requesting a
        # task runs its child action to completion, so the reconcile cascades
        # through task2 and task3 and the workflow finishes.
        wf_svc.reconcile_running_execution(lv_ac_db)

        # task1 is now properly marked completed.
        tk1_ex_db = wf_db_access.TaskExecution.get_by_id(tk1_ex_db.id)
        self.assertEqual(tk1_ex_db.status, wf_statuses.SUCCEEDED)

        # The workflow advanced and ran to completion.
        wf_ex_db = wf_db_access.WorkflowExecution.get_by_id(wf_ex_db.id)
        self.assertEqual(wf_ex_db.status, wf_statuses.SUCCEEDED)

        lv_ac_db = lv_db_access.LiveAction.get_by_id(str(lv_ac_db.id))
        self.assertEqual(lv_ac_db.status, ac_const.LIVEACTION_STATUS_SUCCEEDED)
        ac_ex_db = ex_db_access.ActionExecution.get_by_id(str(ac_ex_db.id))
        self.assertEqual(ac_ex_db.status, ac_const.LIVEACTION_STATUS_SUCCEEDED)

        # And it produced the expected output, proving every task really ran.
        expected_output = {
            "msg": "%s, All your base are belong to us!" % wf_input["who"]
        }
        self.assertDictEqual(wf_ex_db.output, expected_output)

    @mock.patch.object(
        runners_utils, "invoke_post_run", mock.MagicMock(return_value=None)
    )
    def test_reconcile_is_noop_for_healthy_running_workflow(self):
        # A workflow that is genuinely still mid-flight (task1 running, its
        # child action NOT yet complete) must not be disturbed by a reconcile.
        wf_meta = base.get_wf_fixture_meta_data(TEST_PACK_PATH, "sequential.yaml")
        lv_ac_db = lv_db_models.LiveActionDB(
            action=wf_meta["name"], parameters={"who": "Thanos"}
        )
        lv_ac_db, ac_ex_db = ac_svc.request(lv_ac_db)

        wf_ex_db = wf_db_access.WorkflowExecution.query(
            action_execution=str(ac_ex_db.id)
        )[0]

        tk1_ex_db = wf_db_access.TaskExecution.query(
            workflow_execution=str(wf_ex_db.id), task_id="task1"
        )[0]
        tk1_ac_ex_db = ex_db_access.ActionExecution.query(
            task_execution=str(tk1_ex_db.id)
        )[0]
        tk1_lv_ac_db = lv_db_access.LiveAction.get_by_id(tk1_ac_ex_db.liveaction_id)

        # Force task1's child action back to RUNNING to model a task that is
        # still executing (no completion has occurred, lost or otherwise).
        tk1_ac_ex_db.status = ac_const.LIVEACTION_STATUS_RUNNING
        tk1_ac_ex_db = ex_db_access.ActionExecution.add_or_update(
            tk1_ac_ex_db, publish=False
        )
        tk1_lv_ac_db.status = ac_const.LIVEACTION_STATUS_RUNNING
        lv_db_access.LiveAction.add_or_update(tk1_lv_ac_db, publish=False)

        lv_ac_db = lv_db_access.LiveAction.get_by_id(str(lv_ac_db.id))
        wf_svc.reconcile_running_execution(lv_ac_db)

        # No completion was replayed: task1 is still running and no downstream
        # task was created.
        tk1_ex_db = wf_db_access.TaskExecution.get_by_id(tk1_ex_db.id)
        self.assertEqual(tk1_ex_db.status, wf_statuses.RUNNING)
        self.assertEqual(
            len(
                wf_db_access.TaskExecution.query(
                    workflow_execution=str(wf_ex_db.id), task_id="task2"
                )
            ),
            0,
        )
        wf_ex_db = wf_db_access.WorkflowExecution.get_by_id(wf_ex_db.id)
        self.assertEqual(wf_ex_db.status, wf_statuses.RUNNING)

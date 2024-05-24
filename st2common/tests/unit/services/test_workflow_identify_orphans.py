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

import datetime
import mock

from oslo_config import cfg

import st2tests

from st2common.bootstrap import actionsregistrar
from st2common.bootstrap import runnersregistrar
from st2common.constants import action as ac_const
from st2common.garbage_collection import executions as ex_gc
from st2common import log as logging
from st2common.models.db import execution as ex_db_models
from st2common.models.db import liveaction as lv_db_models
from st2common.models.db import workflow as wf_db_models
from st2common.persistence import execution as ex_db_access
from st2common.persistence import liveaction as lv_db_access
from st2common.persistence import workflow as wf_db_access
from st2common.services import workflows as wf_svc
from st2common.transport import liveaction as lv_ac_xport
from st2common.transport import workflow as wf_ex_xport
from st2common.transport import publishers
from st2common.util import date as date_utils
from st2tests.fixtures.packs.core.fixture import PACK_PATH as CORE_PACK_PATH
from st2tests.fixtures.packs.orquesta_tests.fixture import PACK_PATH as TEST_PACK_PATH
from st2tests.mocks import liveaction as mock_lv_ac_xport
from st2tests.mocks import workflow as mock_wf_ex_xport


LOG = logging.getLogger(__name__)

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
class WorkflowServiceIdentifyOrphansTest(st2tests.WorkflowTestCase):
    ensure_indexes = True
    ensure_indexes_models = [
        ex_db_models.ActionExecutionDB,
        lv_db_models.LiveActionDB,
        wf_db_models.WorkflowExecutionDB,
        wf_db_models.TaskExecutionDB,
    ]

    @classmethod
    def setUpClass(cls):
        super(WorkflowServiceIdentifyOrphansTest, cls).setUpClass()

        # Register runners.
        runnersregistrar.register_runners()

        # Register test pack(s).
        actions_registrar = actionsregistrar.ActionsRegistrar(
            use_pack_cache=False, fail_on_failure=True
        )

        for pack in PACKS:
            actions_registrar.register_from_pack(pack)

    def tearDown(self):
        super(WorkflowServiceIdentifyOrphansTest, self).tearDown()

        for tk_ex_db in wf_db_access.TaskExecution.get_all():
            wf_db_access.TaskExecution.delete(tk_ex_db)

        for wf_ex_db in wf_db_access.WorkflowExecution.get_all():
            wf_db_access.WorkflowExecution.delete(wf_ex_db)

        for lv_ac_db in lv_db_access.LiveAction.get_all():
            lv_db_access.LiveAction.delete(lv_ac_db)

        for ac_ex_db in ex_db_access.ActionExecution.get_all():
            ex_db_access.ActionExecution.delete(ac_ex_db)

    def mock_workflow_records(self, completed=False, expired=True, log=True):
        status = (
            ac_const.LIVEACTION_STATUS_SUCCEEDED
            if completed
            else ac_const.LIVEACTION_STATUS_RUNNING
        )

        # Identify start and end timestamp
        gc_max_idle = cfg.CONF.workflow_engine.gc_max_idle_sec
        utc_now_dt = date_utils.get_datetime_utc_now()
        expiry_dt = utc_now_dt - datetime.timedelta(seconds=gc_max_idle + 30)
        start_timestamp = expiry_dt if expired else utc_now_dt
        end_timestamp = utc_now_dt if completed else None

        # Assign metadata.
        action_ref = "orquesta_tests.sequential"
        runner = "orquesta"
        user = "stanley"

        # Create the WorkflowExecutionDB record first since the ID needs to be
        # included in the LiveActionDB and ActionExecutionDB records.
        st2_ctx = {
            "st2": {
                "action_execution_id": "123",
                "action": "foobar",
                "runner": "orquesta",
            }
        }
        wf_ex_db = wf_db_models.WorkflowExecutionDB(
            context=st2_ctx,
            status=status,
            start_timestamp=start_timestamp,
            end_timestamp=end_timestamp,
        )

        wf_ex_db = wf_db_access.WorkflowExecution.insert(wf_ex_db, publish=False)

        # Create the LiveActionDB record.
        lv_ac_db = lv_db_models.LiveActionDB(
            workflow_execution=str(wf_ex_db.id),
            action=action_ref,
            action_is_workflow=True,
            context={"user": user, "workflow_execution": str(wf_ex_db.id)},
            status=status,
            start_timestamp=start_timestamp,
            end_timestamp=end_timestamp,
        )

        lv_ac_db = lv_db_access.LiveAction.insert(lv_ac_db, publish=False)

        # Create the ActionExecutionDB record.
        ac_ex_db = ex_db_models.ActionExecutionDB(
            workflow_execution=str(wf_ex_db.id),
            action={"runner_type": runner, "ref": action_ref},
            runner={"name": runner},
            liveaction={"id": str(lv_ac_db.id)},
            context={"user": user, "workflow_execution": str(wf_ex_db.id)},
            status=status,
            start_timestamp=start_timestamp,
            end_timestamp=end_timestamp,
        )

        if log:
            ac_ex_db.log = [{"status": "running", "timestamp": start_timestamp}]

        if log and status in ac_const.LIVEACTION_COMPLETED_STATES:
            ac_ex_db.log.append({"status": status, "timestamp": end_timestamp})

        ac_ex_db = ex_db_access.ActionExecution.insert(ac_ex_db, publish=False)

        # Update the WorkflowExecutionDB record with cross reference to the ActionExecutionDB.
        wf_ex_db.action_execution = str(ac_ex_db.id)
        wf_ex_db = wf_db_access.WorkflowExecution.update(wf_ex_db, publish=False)

        return wf_ex_db, lv_ac_db, ac_ex_db

    def mock_task_records(
        self, parent, task_id, task_route=0, completed=True, expired=False, log=True
    ):
        if not completed and expired:
            raise ValueError("Task must be set completed=True if expired=True.")

        status = (
            ac_const.LIVEACTION_STATUS_SUCCEEDED
            if completed
            else ac_const.LIVEACTION_STATUS_RUNNING
        )

        parent_wf_ex_db, parent_ac_ex_db = parent[0], parent[2]

        # Identify end timestamp
        gc_max_idle = cfg.CONF.workflow_engine.gc_max_idle_sec
        utc_now_dt = date_utils.get_datetime_utc_now()
        expiry_dt = utc_now_dt - datetime.timedelta(seconds=gc_max_idle + 10)
        end_timestamp = expiry_dt if expired else utc_now_dt

        # Assign metadata.
        action_ref = "core.local"
        runner = "local-shell-cmd"
        user = "stanley"

        # Create the TaskExecutionDB record first since the ID needs to be
        # included in the LiveActionDB and ActionExecutionDB records.
        tk_ex_db = wf_db_models.TaskExecutionDB(
            workflow_execution=str(parent_wf_ex_db.id),
            task_id=task_id,
            task_route=0,
            status=status,
            start_timestamp=parent_wf_ex_db.start_timestamp,
        )

        if status in ac_const.LIVEACTION_COMPLETED_STATES:
            tk_ex_db.end_timestamp = end_timestamp if expired else utc_now_dt

        tk_ex_db = wf_db_access.TaskExecution.insert(tk_ex_db, publish=False)

        # Build context for LiveActionDB and ActionExecutionDB.
        context = {
            "user": user,
            "orquesta": {
                "task_id": tk_ex_db.task_id,
                "task_name": tk_ex_db.task_id,
                "workflow_execution_id": str(parent_wf_ex_db.id),
                "task_execution_id": str(tk_ex_db.id),
                "task_route": tk_ex_db.task_route,
            },
            "parent": {"user": user, "execution_id": str(parent_ac_ex_db.id)},
        }

        # Create the LiveActionDB record.
        lv_ac_db = lv_db_models.LiveActionDB(
            workflow_execution=str(parent_wf_ex_db.id),
            task_execution=str(tk_ex_db.id),
            action=action_ref,
            action_is_workflow=False,
            context=context,
            status=status,
            start_timestamp=tk_ex_db.start_timestamp,
            end_timestamp=tk_ex_db.end_timestamp,
        )

        lv_ac_db = lv_db_access.LiveAction.insert(lv_ac_db, publish=False)

        # Create the ActionExecutionDB record.
        ac_ex_db = ex_db_models.ActionExecutionDB(
            workflow_execution=str(parent_wf_ex_db.id),
            task_execution=str(tk_ex_db.id),
            action={"runner_type": runner, "ref": action_ref},
            runner={"name": runner},
            liveaction={"id": str(lv_ac_db.id)},
            context=context,
            status=status,
            start_timestamp=tk_ex_db.start_timestamp,
            end_timestamp=tk_ex_db.end_timestamp,
        )

        if log:
            ac_ex_db.log = [
                {"status": "running", "timestamp": tk_ex_db.start_timestamp}
            ]

        if log and status in ac_const.LIVEACTION_COMPLETED_STATES:
            ac_ex_db.log.append({"status": status, "timestamp": tk_ex_db.end_timestamp})

        ac_ex_db = ex_db_access.ActionExecution.insert(ac_ex_db, publish=False)

        return tk_ex_db, lv_ac_db, ac_ex_db

    def test_no_orphans(self):
        # Workflow that is still running and not expired.
        self.mock_workflow_records(completed=False, expired=False)

        # Workflow that is still running with task completed and not expired.
        wf_ex_set_2 = self.mock_workflow_records(completed=False, expired=False)
        self.mock_task_records(wf_ex_set_2, "task1", completed=True, expired=False)

        # Workflow that is still running with task running and not expired.
        wf_ex_set_3 = self.mock_workflow_records(completed=False, expired=False)
        self.mock_task_records(wf_ex_set_3, "task1", completed=False, expired=False)

        # Workflow that is completed and not expired.
        self.mock_workflow_records(completed=True, expired=False)

        # Workflow that is completed with task completed and not expired.
        wf_ex_set_5 = self.mock_workflow_records(completed=True, expired=False)
        self.mock_task_records(wf_ex_set_5, "task1", completed=True, expired=False)

        orphaned_ac_ex_dbs = wf_svc.identify_orphaned_workflows()
        self.assertEqual(len(orphaned_ac_ex_dbs), 0)

    def test_identify_orphans_with_no_task_executions(self):
        # Workflow that is still running and expired.
        wf_ex_set_1 = self.mock_workflow_records(completed=False, expired=True)

        # Workflow that is completed and expired.
        self.mock_workflow_records(completed=True, expired=True)

        # Workflow that is still running and not expired.
        self.mock_workflow_records(completed=False, expired=False)

        # Workflow that is completed and not expired.
        self.mock_workflow_records(completed=True, expired=False)

        orphaned_ac_ex_dbs = wf_svc.identify_orphaned_workflows()
        self.assertEqual(len(orphaned_ac_ex_dbs), 1)
        self.assertEqual(orphaned_ac_ex_dbs[0].id, wf_ex_set_1[2].id)

    def test_identify_orphans_with_task_executions(self):
        # Workflow that is still running with task completed and expired.
        wf_ex_set_1 = self.mock_workflow_records(completed=False, expired=True)
        self.mock_task_records(wf_ex_set_1, "task1", completed=True, expired=True)

        # Workflow that is still running with task completed and not expired.
        wf_ex_set_2 = self.mock_workflow_records(completed=False, expired=False)
        self.mock_task_records(wf_ex_set_2, "task1", completed=True, expired=False)

        # Workflow that is still running with task running and not expired.
        wf_ex_set_3 = self.mock_workflow_records(completed=False, expired=False)
        self.mock_task_records(wf_ex_set_3, "task1", completed=False, expired=False)

        # Workflow that is still running with multiple tasks and not expired.
        # One of the task completed passed expiry date but another task is still running.
        wf_ex_set_4 = self.mock_workflow_records(completed=False, expired=False)
        self.mock_task_records(wf_ex_set_4, "task1", completed=True, expired=True)
        self.mock_task_records(wf_ex_set_4, "task2", completed=False, expired=False)

        # Workflow that is still running with multiple tasks and not expired.
        # Both of the tasks are completed with one completed only recently.
        wf_ex_set_5 = self.mock_workflow_records(completed=False, expired=False)
        self.mock_task_records(wf_ex_set_5, "task1", completed=True, expired=True)
        self.mock_task_records(wf_ex_set_5, "task2", completed=True, expired=False)

        # Workflow that is still running with multiple tasks and not expired.
        # One of the task completed recently and another task is still running.
        wf_ex_set_6 = self.mock_workflow_records(completed=False, expired=False)
        self.mock_task_records(wf_ex_set_6, "task1", completed=True, expired=False)
        self.mock_task_records(wf_ex_set_6, "task2", completed=False, expired=False)

        orphaned_ac_ex_dbs = wf_svc.identify_orphaned_workflows()
        self.assertEqual(len(orphaned_ac_ex_dbs), 1)
        self.assertEqual(orphaned_ac_ex_dbs[0].id, wf_ex_set_1[2].id)

    def test_action_execution_with_missing_log_entries(self):
        # Workflow that is still running and expired. However the state change logs are missing.
        wf_ex_set_1 = self.mock_workflow_records(
            completed=False, expired=True, log=False
        )
        self.mock_task_records(wf_ex_set_1, "task1", completed=True, expired=True)

        orphaned_ac_ex_dbs = wf_svc.identify_orphaned_workflows()
        self.assertEqual(len(orphaned_ac_ex_dbs), 0)

    def test_garbage_collection(self):
        # Workflow that is still running with no task and expired.
        wf_ex_set_1 = self.mock_workflow_records(completed=False, expired=True)

        # Workflow that is still running with task completed and expired.
        wf_ex_set_2 = self.mock_workflow_records(completed=False, expired=True)
        self.mock_task_records(wf_ex_set_2, "task1", completed=True, expired=True)

        # Ensure these workflows are identified as orphans.
        orphaned_ac_ex_dbs = wf_svc.identify_orphaned_workflows()
        self.assertEqual(len(orphaned_ac_ex_dbs), 2)
        self.assertIn(orphaned_ac_ex_dbs[0].id, [wf_ex_set_1[2].id, wf_ex_set_2[2].id])
        self.assertIn(orphaned_ac_ex_dbs[1].id, [wf_ex_set_1[2].id, wf_ex_set_2[2].id])

        # Run garbage collection.
        ex_gc.purge_orphaned_workflow_executions(logger=LOG)

        # Ensure these workflows are processed and not returned as orphans.
        orphaned_ac_ex_dbs = wf_svc.identify_orphaned_workflows()
        self.assertEqual(len(orphaned_ac_ex_dbs), 0)

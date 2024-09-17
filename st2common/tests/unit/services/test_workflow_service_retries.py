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

from st2common.util.monkey_patch import monkey_patch

monkey_patch()


import mock
import mongoengine
import os
import tempfile

from orquesta import statuses as wf_statuses
from tooz import coordination
from tooz.drivers.redis import RedisDriver

import st2tests

from st2common.bootstrap import actionsregistrar
from st2common.bootstrap import runnersregistrar
from st2common.constants import action as ac_const
from st2common.exceptions import db as db_exc
from st2common.models.db import execution_queue as ex_q_db_models
from st2common.models.db import liveaction as lv_db_models
from st2common.models.db import workflow as wf_db_models
from st2common.persistence import execution as ex_db_access
from st2common.persistence import liveaction as lv_db_access
from st2common.persistence import workflow as wf_db_access
from st2common.services import action as ac_svc
from st2common.services import coordination as coord_svc
from st2common.services import workflows as wf_svc
from st2common.transport import liveaction as lv_ac_xport
from st2common.transport import workflow as wf_ex_xport
from st2common.transport import publishers
from st2tests.fixtures.packs.core.fixture import PACK_PATH as CORE_PACK_PATH
from st2tests.fixtures.packs.orquesta_tests.fixture import PACK_PATH as TEST_PACK_PATH
from st2tests.mocks import liveaction as mock_lv_ac_xport
from st2tests.mocks import workflow as mock_wf_ex_xport


PACKS = [TEST_PACK_PATH, CORE_PACK_PATH]


# Temporary directory used by the tests.
TEMP_DIR_PATH = tempfile.mkdtemp()


def mock_wf_db_update_conflict(wf_ex_db, publish=True, dispatch_trigger=True, **kwargs):
    seq_len = len(wf_ex_db.state["sequence"])

    if seq_len > 0:
        current_task_id = wf_ex_db.state["sequence"][seq_len - 1 :][0]["id"]
        temp_file_path = TEMP_DIR_PATH + "/" + current_task_id

        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)
            raise db_exc.StackStormDBObjectWriteConflictError(wf_ex_db)

    return wf_db_access.WorkflowExecution._get_impl().update(wf_ex_db, **kwargs)


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
class OrquestaServiceRetryTest(st2tests.WorkflowTestCase):
    ensure_indexes = True
    ensure_indexes_models = [
        wf_db_models.WorkflowExecutionDB,
        wf_db_models.TaskExecutionDB,
        ex_q_db_models.ActionExecutionSchedulingQueueItemDB,
    ]

    @classmethod
    def setUpClass(cls):
        super(OrquestaServiceRetryTest, cls).setUpClass()

        # Register runners.
        runnersregistrar.register_runners()

        # Register test pack(s).
        actions_registrar = actionsregistrar.ActionsRegistrar(
            use_pack_cache=False, fail_on_failure=True
        )

        for pack in PACKS:
            actions_registrar.register_from_pack(pack)

    @mock.patch.object(RedisDriver, "get_lock")
    def test_recover_from_coordinator_connection_error(self, mock_get_lock):
        mock_get_lock.side_effect = coord_svc.NoOpLock(name="noop")
        wf_meta = self.get_wf_fixture_meta_data(TEST_PACK_PATH, "sequential.yaml")
        lv_ac_db = lv_db_models.LiveActionDB(action=wf_meta["name"])
        lv_ac_db, ac_ex_db = ac_svc.request(lv_ac_db)
        wf_ex_db = wf_db_access.WorkflowExecution.query(
            action_execution=str(ac_ex_db.id)
        )[0]

        # Process task1 and expect acquiring lock returns a few connection errors.
        query_filters = {"workflow_execution": str(wf_ex_db.id), "task_id": "task1"}
        tk1_ex_db = wf_db_access.TaskExecution.query(**query_filters)[0]
        tk1_ac_ex_db = ex_db_access.ActionExecution.query(
            task_execution=str(tk1_ex_db.id)
        )[0]
        tk1_lv_ac_db = lv_db_access.LiveAction.get_by_id(tk1_ac_ex_db.liveaction["id"])
        self.assertEqual(tk1_lv_ac_db.status, ac_const.LIVEACTION_STATUS_SUCCEEDED)
        mock_get_lock.side_effect = [
            coordination.ToozConnectionError("foobar"),
            coordination.ToozConnectionError("foobar"),
            coord_svc.NoOpLock(name="noop"),
            coord_svc.NoOpLock(name="noop"),
            coord_svc.NoOpLock(name="noop"),
            coord_svc.NoOpLock(name="noop"),
            coord_svc.NoOpLock(name="noop"),
        ]
        wf_svc.handle_action_execution_completion(tk1_ac_ex_db)

        mock_get_lock.side_effect = coord_svc.NoOpLock(name="noop")
        # Workflow service should recover from retries and task1 should succeed.
        tk1_ex_db = wf_db_access.TaskExecution.get_by_id(tk1_ex_db.id)
        self.assertEqual(tk1_ex_db.status, wf_statuses.SUCCEEDED)

    @mock.patch.object(RedisDriver, "get_lock")
    def test_retries_exhausted_from_coordinator_connection_error(self, mock_get_lock):
        mock_get_lock.side_effect = coord_svc.NoOpLock(name="noop")
        wf_meta = self.get_wf_fixture_meta_data(TEST_PACK_PATH, "sequential.yaml")
        lv_ac_db = lv_db_models.LiveActionDB(action=wf_meta["name"])
        lv_ac_db, ac_ex_db = ac_svc.request(lv_ac_db)
        wf_ex_db = wf_db_access.WorkflowExecution.query(
            action_execution=str(ac_ex_db.id)
        )[0]

        # Process task1 but retries exhaused with connection errors.
        query_filters = {"workflow_execution": str(wf_ex_db.id), "task_id": "task1"}
        tk1_ex_db = wf_db_access.TaskExecution.query(**query_filters)[0]
        tk1_ac_ex_db = ex_db_access.ActionExecution.query(
            task_execution=str(tk1_ex_db.id)
        )[0]
        tk1_lv_ac_db = lv_db_access.LiveAction.get_by_id(tk1_ac_ex_db.liveaction["id"])
        self.assertEqual(tk1_lv_ac_db.status, ac_const.LIVEACTION_STATUS_SUCCEEDED)

        mock_get_lock.side_effect = [
            coordination.ToozConnectionError("foobar"),
            coordination.ToozConnectionError("foobar"),
            coordination.ToozConnectionError("foobar"),
            coordination.ToozConnectionError("foobar"),
            coordination.ToozConnectionError("foobar"),
        ]
        # The connection error should raise if retries are exhaused.
        self.assertRaises(
            coordination.ToozConnectionError,
            wf_svc.handle_action_execution_completion,
            tk1_ac_ex_db,
        )

    @mock.patch.object(
        wf_svc,
        "update_task_state",
        mock.MagicMock(
            side_effect=[
                mongoengine.connection.ConnectionFailure(),
                None,
            ]
        ),
    )
    def test_recover_from_database_connection_error(self):
        wf_meta = self.get_wf_fixture_meta_data(TEST_PACK_PATH, "sequential.yaml")
        lv_ac_db = lv_db_models.LiveActionDB(action=wf_meta["name"])
        lv_ac_db, ac_ex_db = ac_svc.request(lv_ac_db)
        wf_ex_db = wf_db_access.WorkflowExecution.query(
            action_execution=str(ac_ex_db.id)
        )[0]

        # Process task1 and expect acquiring lock returns a few connection errors.
        query_filters = {"workflow_execution": str(wf_ex_db.id), "task_id": "task1"}
        tk1_ex_db = wf_db_access.TaskExecution.query(**query_filters)[0]
        tk1_ac_ex_db = ex_db_access.ActionExecution.query(
            task_execution=str(tk1_ex_db.id)
        )[0]
        tk1_lv_ac_db = lv_db_access.LiveAction.get_by_id(tk1_ac_ex_db.liveaction["id"])
        self.assertEqual(tk1_lv_ac_db.status, ac_const.LIVEACTION_STATUS_SUCCEEDED)
        wf_svc.handle_action_execution_completion(tk1_ac_ex_db)

        # Workflow service should recover from retries and task1 should succeed.
        tk1_ex_db = wf_db_access.TaskExecution.get_by_id(tk1_ex_db.id)
        self.assertEqual(tk1_ex_db.status, wf_statuses.SUCCEEDED)

    @mock.patch.object(
        wf_svc,
        "update_task_state",
        mock.MagicMock(side_effect=mongoengine.connection.ConnectionFailure()),
    )
    def test_retries_exhausted_from_database_connection_error(self):
        wf_meta = self.get_wf_fixture_meta_data(TEST_PACK_PATH, "sequential.yaml")
        lv_ac_db = lv_db_models.LiveActionDB(action=wf_meta["name"])
        lv_ac_db, ac_ex_db = ac_svc.request(lv_ac_db)
        wf_ex_db = wf_db_access.WorkflowExecution.query(
            action_execution=str(ac_ex_db.id)
        )[0]

        # Process task1 but retries exhaused with connection errors.
        query_filters = {"workflow_execution": str(wf_ex_db.id), "task_id": "task1"}
        tk1_ex_db = wf_db_access.TaskExecution.query(**query_filters)[0]
        tk1_ac_ex_db = ex_db_access.ActionExecution.query(
            task_execution=str(tk1_ex_db.id)
        )[0]
        tk1_lv_ac_db = lv_db_access.LiveAction.get_by_id(tk1_ac_ex_db.liveaction["id"])
        self.assertEqual(tk1_lv_ac_db.status, ac_const.LIVEACTION_STATUS_SUCCEEDED)

        # The connection error should raise if retries are exhaused.
        self.assertRaises(
            mongoengine.connection.ConnectionFailure,
            wf_svc.handle_action_execution_completion,
            tk1_ac_ex_db,
        )

    @mock.patch.object(
        wf_db_access.WorkflowExecution,
        "update",
        mock.MagicMock(side_effect=mock_wf_db_update_conflict),
    )
    def test_recover_from_database_write_conflicts(self):
        # Create a temporary file which will be used to signal
        # which task(s) to mock the DB write conflict.
        temp_file_path = TEMP_DIR_PATH + "/task4"
        if not os.path.exists(temp_file_path):
            with open(temp_file_path, "w"):
                pass

        # Manually create the liveaction and action execution objects without publishing.
        wf_meta = self.get_wf_fixture_meta_data(TEST_PACK_PATH, "join.yaml")
        lv_ac_db = lv_db_models.LiveActionDB(action=wf_meta["name"])
        lv_ac_db, ac_ex_db = ac_svc.request(lv_ac_db)
        wf_ex_db = wf_db_access.WorkflowExecution.query(
            action_execution=str(ac_ex_db.id)
        )[0]

        # Manually request task executions.
        task_route = 0
        self.run_workflow_step(wf_ex_db, "task1", task_route)
        self.assert_task_running("task2", task_route)
        self.assert_task_running("task4", task_route)
        self.run_workflow_step(wf_ex_db, "task2", task_route)
        self.assert_task_running("task3", task_route)
        self.run_workflow_step(wf_ex_db, "task4", task_route)
        self.assert_task_running("task5", task_route)
        self.run_workflow_step(wf_ex_db, "task3", task_route)
        self.assert_task_not_started("task6", task_route)
        self.run_workflow_step(wf_ex_db, "task5", task_route)
        self.assert_task_running("task6", task_route)
        self.run_workflow_step(wf_ex_db, "task6", task_route)
        self.assert_task_running("task7", task_route)
        self.run_workflow_step(wf_ex_db, "task7", task_route)
        self.assert_workflow_completed(str(wf_ex_db.id), status=wf_statuses.SUCCEEDED)

        # Ensure retry happened.
        self.assertFalse(os.path.exists(temp_file_path))

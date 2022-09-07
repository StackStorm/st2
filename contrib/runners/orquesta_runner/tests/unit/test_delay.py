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

from st2actions.workflows import workflows
from st2common.bootstrap import actionsregistrar
from st2common.bootstrap import runnersregistrar
from st2common.constants import action as action_constants
from st2common.models.db import liveaction as lv_db_models
from st2common.persistence import execution as ex_db_access
from st2common.persistence import liveaction as lv_db_access
from st2common.persistence import workflow as wf_db_access
from st2common.services import action as action_service
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
class OrquestaRunnerDelayTest(st2tests.ExecutionDbTestCase):
    @classmethod
    def setUpClass(cls):
        super(OrquestaRunnerDelayTest, cls).setUpClass()

        # Register runners.
        runnersregistrar.register_runners()

        # Register test pack(s).
        actions_registrar = actionsregistrar.ActionsRegistrar(
            use_pack_cache=False, fail_on_failure=True
        )

        for pack in PACKS:
            actions_registrar.register_from_pack(pack)

    def test_delay(self):
        expected_delay_sec = 1
        expected_delay_msec = expected_delay_sec * 1000

        wf_meta = base.get_wf_fixture_meta_data(TEST_PACK_PATH, "delay.yaml")
        wf_input = {"delay": expected_delay_sec}
        lv_ac_db = lv_db_models.LiveActionDB(
            action=wf_meta["name"], parameters=wf_input
        )
        lv_ac_db, ac_ex_db = action_service.request(lv_ac_db)
        lv_ac_db = self._wait_on_status(
            lv_ac_db, action_constants.LIVEACTION_STATUS_RUNNING
        )

        # Identify records for the main workflow.
        wf_ex_db = wf_db_access.WorkflowExecution.query(
            action_execution=str(ac_ex_db.id)
        )[0]
        query_filters = {"workflow_execution": str(wf_ex_db.id), "task_id": "task1"}
        t1_ex_db = wf_db_access.TaskExecution.query(**query_filters)[0]
        t1_ac_ex_db = ex_db_access.ActionExecution.query(
            task_execution=str(t1_ex_db.id)
        )[0]
        t1_lv_ac_db = lv_db_access.LiveAction.query(task_execution=str(t1_ex_db.id))[0]

        # Assert delay value is rendered and assigned.
        self.assertEqual(t1_ex_db.delay, expected_delay_sec)
        self.assertEqual(t1_lv_ac_db.delay, expected_delay_msec)
        self.assertEqual(t1_ac_ex_db.delay, expected_delay_msec)

    def test_delay_for_with_items(self):
        expected_delay_sec = 1
        expected_delay_msec = expected_delay_sec * 1000

        wf_meta = base.get_wf_fixture_meta_data(TEST_PACK_PATH, "with-items-delay.yaml")
        wf_input = {"delay": expected_delay_sec}
        lv_ac_db = lv_db_models.LiveActionDB(
            action=wf_meta["name"], parameters=wf_input
        )
        lv_ac_db, ac_ex_db = action_service.request(lv_ac_db)

        # Assert action execution is running.
        lv_ac_db = self._wait_on_status(
            lv_ac_db, action_constants.LIVEACTION_STATUS_RUNNING
        )
        wf_ex_db = wf_db_access.WorkflowExecution.query(
            action_execution=str(ac_ex_db.id)
        )[0]
        self.assertEqual(wf_ex_db.status, action_constants.LIVEACTION_STATUS_RUNNING)

        # Process the with items task.
        query_filters = {"workflow_execution": str(wf_ex_db.id), "task_id": "task1"}
        t1_ex_db = wf_db_access.TaskExecution.query(**query_filters)[0]
        t1_ac_ex_dbs = ex_db_access.ActionExecution.query(
            task_execution=str(t1_ex_db.id)
        )
        t1_lv_ac_dbs = lv_db_access.LiveAction.query(task_execution=str(t1_ex_db.id))

        # Assert delay value is rendered and assigned.
        self.assertEqual(t1_ex_db.delay, expected_delay_sec)

        for t1_lv_ac_db in t1_lv_ac_dbs:
            self.assertEqual(t1_lv_ac_db.delay, expected_delay_msec)

        for t1_ac_ex_db in t1_ac_ex_dbs:
            self.assertEqual(t1_ac_ex_db.delay, expected_delay_msec)

        status = [
            ac_ex.status == action_constants.LIVEACTION_STATUS_SUCCEEDED
            for ac_ex in t1_ac_ex_dbs
        ]

        self.assertTrue(all(status))

        for t1_ac_ex_db in t1_ac_ex_dbs:
            workflows.get_engine().process(t1_ac_ex_db)

        t1_ex_db = wf_db_access.TaskExecution.get_by_id(t1_ex_db.id)
        self.assertEqual(t1_ex_db.status, wf_statuses.SUCCEEDED)

        # Assert the main workflow is completed.
        wf_ex_db = wf_db_access.WorkflowExecution.get_by_id(wf_ex_db.id)
        self.assertEqual(wf_ex_db.status, wf_statuses.SUCCEEDED)
        lv_ac_db = lv_db_access.LiveAction.get_by_id(str(lv_ac_db.id))
        self.assertEqual(lv_ac_db.status, action_constants.LIVEACTION_STATUS_SUCCEEDED)

    def test_delay_for_with_items_concurrency(self):
        num_items = 3
        concurrency = 2
        expected_delay_sec = 1
        expected_delay_msec = expected_delay_sec * 1000

        wf_input = {"concurrency": concurrency, "delay": expected_delay_sec}
        wf_meta = base.get_wf_fixture_meta_data(
            TEST_PACK_PATH, "with-items-concurrency-delay.yaml"
        )
        lv_ac_db = lv_db_models.LiveActionDB(
            action=wf_meta["name"], parameters=wf_input
        )
        lv_ac_db, ac_ex_db = action_service.request(lv_ac_db)

        # Assert action execution is running.
        lv_ac_db = self._wait_on_status(
            lv_ac_db, action_constants.LIVEACTION_STATUS_RUNNING
        )
        wf_ex_db = wf_db_access.WorkflowExecution.query(
            action_execution=str(ac_ex_db.id)
        )[0]
        self.assertEqual(wf_ex_db.status, action_constants.LIVEACTION_STATUS_RUNNING)

        # Process the first set of action executions from with items concurrency.
        query_filters = {"workflow_execution": str(wf_ex_db.id), "task_id": "task1"}
        t1_ex_db = wf_db_access.TaskExecution.query(**query_filters)[0]
        t1_ac_ex_dbs = ex_db_access.ActionExecution.query(
            task_execution=str(t1_ex_db.id)
        )
        t1_lv_ac_dbs = lv_db_access.LiveAction.query(task_execution=str(t1_ex_db.id))

        # Assert the number of concurrent items is correct.
        self.assertEqual(len(t1_ac_ex_dbs), concurrency)

        # Assert delay value is rendered and assigned.
        self.assertEqual(t1_ex_db.delay, expected_delay_sec)

        for t1_lv_ac_db in t1_lv_ac_dbs:
            self.assertEqual(t1_lv_ac_db.delay, expected_delay_msec)

        for t1_ac_ex_db in t1_ac_ex_dbs:
            self.assertEqual(t1_ac_ex_db.delay, expected_delay_msec)

        status = [
            ac_ex.status == action_constants.LIVEACTION_STATUS_SUCCEEDED
            for ac_ex in t1_ac_ex_dbs
        ]

        self.assertTrue(all(status))

        for t1_ac_ex_db in t1_ac_ex_dbs:
            workflows.get_engine().process(t1_ac_ex_db)

        t1_ex_db = wf_db_access.TaskExecution.get_by_id(t1_ex_db.id)
        self.assertEqual(t1_ex_db.status, wf_statuses.RUNNING)

        wf_ex_db = wf_db_access.WorkflowExecution.get_by_id(wf_ex_db.id)
        self.assertEqual(wf_ex_db.status, wf_statuses.RUNNING)

        # Process the second set of action executions from with items concurrency.
        t1_ac_ex_dbs = ex_db_access.ActionExecution.query(
            task_execution=str(t1_ex_db.id)
        )
        t1_lv_ac_dbs = lv_db_access.LiveAction.query(task_execution=str(t1_ex_db.id))

        # Assert delay value is rendered and assigned only to the first set of action executions.
        t1_lv_ac_dbs_delays = [
            t1_lv_ac_db.delay
            for t1_lv_ac_db in t1_lv_ac_dbs
            if t1_lv_ac_db.delay is not None
        ]

        self.assertEqual(len(t1_lv_ac_dbs_delays), concurrency)

        t1_ac_ex_dbs_delays = [
            t1_ac_ex_db.delay
            for t1_ac_ex_db in t1_ac_ex_dbs
            if t1_ac_ex_db.delay is not None
        ]

        self.assertEqual(len(t1_ac_ex_dbs_delays), concurrency)

        # Assert all items are processed.
        self.assertEqual(len(t1_ac_ex_dbs), num_items)

        status = [
            ac_ex.status == action_constants.LIVEACTION_STATUS_SUCCEEDED
            for ac_ex in t1_ac_ex_dbs
        ]

        self.assertTrue(all(status))

        for t1_ac_ex_db in t1_ac_ex_dbs[concurrency:]:
            workflows.get_engine().process(t1_ac_ex_db)

        t1_ex_db = wf_db_access.TaskExecution.get_by_id(t1_ex_db.id)
        self.assertEqual(t1_ex_db.status, wf_statuses.SUCCEEDED)

        # Assert the main workflow is completed.
        wf_ex_db = wf_db_access.WorkflowExecution.get_by_id(wf_ex_db.id)
        self.assertEqual(wf_ex_db.status, wf_statuses.SUCCEEDED)
        lv_ac_db = lv_db_access.LiveAction.get_by_id(str(lv_ac_db.id))
        self.assertEqual(lv_ac_db.status, action_constants.LIVEACTION_STATUS_SUCCEEDED)

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
import os

import mock

import st2tests

# XXX: actionsensor import depends on config being setup.
import st2tests.config as tests_config

tests_config.parse_args()

from tests.unit import base

from st2common.bootstrap import actionsregistrar
from st2common.bootstrap import runnersregistrar
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
from st2common.constants import action as ac_const
from st2tests.fixtures.packs.core.fixture import PACK_PATH as CORE_PACK_PATH
from st2tests.fixtures.packs.orquesta_tests.fixture import PACK_PATH as TEST_PACK_PATH
from st2tests.mocks import liveaction as mock_lv_ac_xport
from st2tests.mocks import workflow as mock_wf_ex_xport
from st2tests.base import RunnerTestCase

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

PACKS = [TEST_PACK_PATH, CORE_PACK_PATH]

FAIL_SCHEMA = {
    "notvalid": {
        "type": "string",
    },
}


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
class OrquestaRunnerTest(RunnerTestCase, st2tests.ExecutionDbTestCase):
    @classmethod
    def setUpClass(cls):
        super(OrquestaRunnerTest, cls).setUpClass()

        # Register runners.
        runnersregistrar.register_runners()

        # Register test pack(s).
        actions_registrar = actionsregistrar.ActionsRegistrar(
            use_pack_cache=False, fail_on_failure=True
        )

        for pack in PACKS:
            actions_registrar.register_from_pack(pack)

    @classmethod
    def get_runner_class(cls, runner_name):
        return runners.get_runner(runner_name, runner_name).__class__

    def test_adherence_to_output_schema(self):
        wf_meta = base.get_wf_fixture_meta_data(
            TEST_PACK_PATH, "sequential_with_schema.yaml"
        )
        wf_input = {"who": "Thanos"}
        lv_ac_db = lv_db_models.LiveActionDB(
            action=wf_meta["name"], parameters=wf_input
        )
        lv_ac_db, ac_ex_db = ac_svc.request(lv_ac_db)
        lv_ac_db = lv_db_access.LiveAction.get_by_id(str(lv_ac_db.id))
        wf_ex_dbs = wf_db_access.WorkflowExecution.query(
            action_execution=str(ac_ex_db.id)
        )
        wf_ex_db = wf_ex_dbs[0]
        query_filters = {"workflow_execution": str(wf_ex_db.id), "task_id": "task1"}
        tk1_ex_db = wf_db_access.TaskExecution.query(**query_filters)[0]
        tk1_ac_ex_db = ex_db_access.ActionExecution.query(
            task_execution=str(tk1_ex_db.id)
        )[0]
        wf_svc.handle_action_execution_completion(tk1_ac_ex_db)
        tk1_ex_db = wf_db_access.TaskExecution.get_by_id(tk1_ex_db.id)
        wf_ex_db = wf_db_access.WorkflowExecution.get_by_id(wf_ex_db.id)
        query_filters = {"workflow_execution": str(wf_ex_db.id), "task_id": "task2"}
        tk2_ex_db = wf_db_access.TaskExecution.query(**query_filters)[0]
        tk2_ac_ex_db = ex_db_access.ActionExecution.query(
            task_execution=str(tk2_ex_db.id)
        )[0]
        wf_svc.handle_action_execution_completion(tk2_ac_ex_db)
        tk2_ex_db = wf_db_access.TaskExecution.get_by_id(tk2_ex_db.id)
        wf_ex_db = wf_db_access.WorkflowExecution.get_by_id(wf_ex_db.id)
        query_filters = {"workflow_execution": str(wf_ex_db.id), "task_id": "task3"}
        tk3_ex_db = wf_db_access.TaskExecution.query(**query_filters)[0]
        tk3_ac_ex_db = ex_db_access.ActionExecution.query(
            task_execution=str(tk3_ex_db.id)
        )[0]
        wf_svc.handle_action_execution_completion(tk3_ac_ex_db)
        wf_ex_db = wf_db_access.WorkflowExecution.get_by_id(wf_ex_db.id)
        lv_ac_db = lv_db_access.LiveAction.get_by_id(str(lv_ac_db.id))
        ac_ex_db = ex_db_access.ActionExecution.get_by_id(str(ac_ex_db.id))

        self.assertEqual(lv_ac_db.status, ac_const.LIVEACTION_STATUS_SUCCEEDED)
        self.assertEqual(ac_ex_db.status, ac_const.LIVEACTION_STATUS_SUCCEEDED)

    def test_fail_incorrect_output_schema(self):
        wf_meta = base.get_wf_fixture_meta_data(
            TEST_PACK_PATH, "sequential_with_broken_schema.yaml"
        )
        wf_input = {"who": "Thanos"}
        lv_ac_db = lv_db_models.LiveActionDB(
            action=wf_meta["name"], parameters=wf_input
        )
        lv_ac_db, ac_ex_db = ac_svc.request(lv_ac_db)
        lv_ac_db = lv_db_access.LiveAction.get_by_id(str(lv_ac_db.id))
        wf_ex_dbs = wf_db_access.WorkflowExecution.query(
            action_execution=str(ac_ex_db.id)
        )
        wf_ex_db = wf_ex_dbs[0]
        query_filters = {"workflow_execution": str(wf_ex_db.id), "task_id": "task1"}
        tk1_ex_db = wf_db_access.TaskExecution.query(**query_filters)[0]
        tk1_ac_ex_db = ex_db_access.ActionExecution.query(
            task_execution=str(tk1_ex_db.id)
        )[0]
        wf_svc.handle_action_execution_completion(tk1_ac_ex_db)
        tk1_ex_db = wf_db_access.TaskExecution.get_by_id(tk1_ex_db.id)
        wf_ex_db = wf_db_access.WorkflowExecution.get_by_id(wf_ex_db.id)
        query_filters = {"workflow_execution": str(wf_ex_db.id), "task_id": "task2"}
        tk2_ex_db = wf_db_access.TaskExecution.query(**query_filters)[0]
        tk2_ac_ex_db = ex_db_access.ActionExecution.query(
            task_execution=str(tk2_ex_db.id)
        )[0]
        wf_svc.handle_action_execution_completion(tk2_ac_ex_db)
        tk2_ex_db = wf_db_access.TaskExecution.get_by_id(tk2_ex_db.id)
        wf_ex_db = wf_db_access.WorkflowExecution.get_by_id(wf_ex_db.id)
        query_filters = {"workflow_execution": str(wf_ex_db.id), "task_id": "task3"}
        tk3_ex_db = wf_db_access.TaskExecution.query(**query_filters)[0]
        tk3_ac_ex_db = ex_db_access.ActionExecution.query(
            task_execution=str(tk3_ex_db.id)
        )[0]
        wf_svc.handle_action_execution_completion(tk3_ac_ex_db)
        wf_ex_db = wf_db_access.WorkflowExecution.get_by_id(wf_ex_db.id)
        lv_ac_db = lv_db_access.LiveAction.get_by_id(str(lv_ac_db.id))
        ac_ex_db = ex_db_access.ActionExecution.get_by_id(str(ac_ex_db.id))

        self.assertEqual(lv_ac_db.status, ac_const.LIVEACTION_STATUS_FAILED)
        self.assertEqual(ac_ex_db.status, ac_const.LIVEACTION_STATUS_FAILED)

        expected_result = {
            "error": "Additional properties are not allowed",
            "message": "Error validating output. See error output for more details.",
        }

        self.assertIn(expected_result["error"], ac_ex_db.result["error"])
        self.assertEqual(expected_result["message"], ac_ex_db.result["message"])

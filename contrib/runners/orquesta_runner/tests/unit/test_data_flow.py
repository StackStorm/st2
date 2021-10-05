# -*- coding: utf-8 -*-

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
import six

from orquesta import statuses as wf_statuses

import st2tests

# XXX: actionsensor import depends on config being setup.
import st2tests.config as tests_config

tests_config.parse_args()

from python_runner import python_runner
from tests.unit import base

from st2common.bootstrap import actionsregistrar
from st2common.bootstrap import runnersregistrar
from st2common.constants import action as ac_const
from st2common.constants import secrets as secrets_const
from st2common.models.api import execution as ex_api_models
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


TEST_PACK = "orquesta_tests"
TEST_PACK_PATH = (
    st2tests.fixturesloader.get_fixtures_packs_base_path() + "/" + TEST_PACK
)

PACKS = [
    TEST_PACK_PATH,
    st2tests.fixturesloader.get_fixtures_packs_base_path() + "/core",
]

TEST_1 = "xyz"
TEST_2 = "床前明月光 疑是地上霜 舉頭望明月 低頭思故鄉"
MOCK_PY_RESULT_1 = {
    "stderr": "",
    "stdout": "",
    "result": {"k2": TEST_1},
    "exit_code": 0,
}
MOCK_PY_RESULT_2 = {
    "stderr": "",
    "stdout": "",
    "result": {"k2": TEST_2},
    "exit_code": 0,
}
MOCK_PY_OUTPUT_1 = (ac_const.LIVEACTION_STATUS_SUCCEEDED, MOCK_PY_RESULT_1, None)
MOCK_PY_OUTPUT_2 = (ac_const.LIVEACTION_STATUS_SUCCEEDED, MOCK_PY_RESULT_2, None)


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

    def assert_data_flow(self, data):
        wf_meta = base.get_wf_fixture_meta_data(TEST_PACK_PATH, "data-flow.yaml")
        wf_input = {"a1": data}
        lv_ac_db = lv_db_models.LiveActionDB(
            action=wf_meta["name"], parameters=wf_input
        )
        lv_ac_db, ac_ex_db = ac_svc.request(lv_ac_db)

        # Assert action execution is running.
        lv_ac_db = lv_db_access.LiveAction.get_by_id(str(lv_ac_db.id))
        self.assertEqual(
            lv_ac_db.status, ac_const.LIVEACTION_STATUS_RUNNING, lv_ac_db.result
        )
        wf_ex_db = wf_db_access.WorkflowExecution.query(
            action_execution=str(ac_ex_db.id)
        )[0]
        self.assertEqual(wf_ex_db.status, ac_const.LIVEACTION_STATUS_RUNNING)

        # Assert task1 is already completed.
        query_filters = {"workflow_execution": str(wf_ex_db.id), "task_id": "task1"}
        tk1_ex_db = wf_db_access.TaskExecution.query(**query_filters)[0]
        tk1_ac_ex_db = ex_db_access.ActionExecution.query(
            task_execution=str(tk1_ex_db.id)
        )[0]
        tk1_lv_ac_db = lv_db_access.LiveAction.get_by_id(tk1_ac_ex_db.liveaction["id"])
        self.assertEqual(tk1_lv_ac_db.status, ac_const.LIVEACTION_STATUS_SUCCEEDED)

        # Manually handle action execution completion.
        wf_svc.handle_action_execution_completion(tk1_ac_ex_db)

        # Assert task1 succeeded and workflow is still running.
        tk1_ex_db = wf_db_access.TaskExecution.get_by_id(tk1_ex_db.id)
        self.assertEqual(tk1_ex_db.status, wf_statuses.SUCCEEDED)
        wf_ex_db = wf_db_access.WorkflowExecution.get_by_id(wf_ex_db.id)
        self.assertEqual(wf_ex_db.status, wf_statuses.RUNNING)

        # Assert task2 is already completed.
        query_filters = {"workflow_execution": str(wf_ex_db.id), "task_id": "task2"}
        tk2_ex_db = wf_db_access.TaskExecution.query(**query_filters)[0]
        tk2_ac_ex_db = ex_db_access.ActionExecution.query(
            task_execution=str(tk2_ex_db.id)
        )[0]
        tk2_lv_ac_db = lv_db_access.LiveAction.get_by_id(tk2_ac_ex_db.liveaction["id"])
        self.assertEqual(tk2_lv_ac_db.status, ac_const.LIVEACTION_STATUS_SUCCEEDED)

        # Manually handle action execution completion.
        wf_svc.handle_action_execution_completion(tk2_ac_ex_db)

        # Assert task2 succeeded and workflow is still running.
        tk2_ex_db = wf_db_access.TaskExecution.get_by_id(tk2_ex_db.id)
        self.assertEqual(tk2_ex_db.status, wf_statuses.SUCCEEDED)
        wf_ex_db = wf_db_access.WorkflowExecution.get_by_id(wf_ex_db.id)
        self.assertEqual(wf_ex_db.status, wf_statuses.RUNNING)

        # Assert task3 is already completed.
        query_filters = {"workflow_execution": str(wf_ex_db.id), "task_id": "task3"}
        tk3_ex_db = wf_db_access.TaskExecution.query(**query_filters)[0]
        tk3_ac_ex_db = ex_db_access.ActionExecution.query(
            task_execution=str(tk3_ex_db.id)
        )[0]
        tk3_lv_ac_db = lv_db_access.LiveAction.get_by_id(tk3_ac_ex_db.liveaction["id"])
        self.assertEqual(tk3_lv_ac_db.status, ac_const.LIVEACTION_STATUS_SUCCEEDED)

        # Manually handle action execution completion.
        wf_svc.handle_action_execution_completion(tk3_ac_ex_db)

        # Assert task3 succeeded and workflow is still running.
        tk3_ex_db = wf_db_access.TaskExecution.get_by_id(tk3_ex_db.id)
        self.assertEqual(tk3_ex_db.status, wf_statuses.SUCCEEDED)
        wf_ex_db = wf_db_access.WorkflowExecution.get_by_id(wf_ex_db.id)
        self.assertEqual(wf_ex_db.status, wf_statuses.RUNNING)

        # Assert task4 is already completed.
        query_filters = {"workflow_execution": str(wf_ex_db.id), "task_id": "task4"}
        tk4_ex_db = wf_db_access.TaskExecution.query(**query_filters)[0]
        tk4_ac_ex_db = ex_db_access.ActionExecution.query(
            task_execution=str(tk4_ex_db.id)
        )[0]
        tk4_lv_ac_db = lv_db_access.LiveAction.get_by_id(tk4_ac_ex_db.liveaction["id"])
        self.assertEqual(tk4_lv_ac_db.status, ac_const.LIVEACTION_STATUS_SUCCEEDED)

        # Manually handle action execution completion.
        wf_svc.handle_action_execution_completion(tk4_ac_ex_db)

        # Assert task4 succeeded and workflow is completed.
        tk4_ex_db = wf_db_access.TaskExecution.get_by_id(tk4_ex_db.id)
        self.assertEqual(tk4_ex_db.status, wf_statuses.SUCCEEDED)
        wf_ex_db = wf_db_access.WorkflowExecution.get_by_id(wf_ex_db.id)
        self.assertEqual(wf_ex_db.status, wf_statuses.SUCCEEDED)
        lv_ac_db = lv_db_access.LiveAction.get_by_id(str(lv_ac_db.id))
        self.assertEqual(lv_ac_db.status, ac_const.LIVEACTION_STATUS_SUCCEEDED)
        ac_ex_db = ex_db_access.ActionExecution.get_by_id(str(ac_ex_db.id))
        self.assertEqual(ac_ex_db.status, ac_const.LIVEACTION_STATUS_SUCCEEDED)

        # Check workflow output.
        expected_value = wf_input["a1"] if six.PY3 else wf_input["a1"].decode("utf-8")

        expected_output = {
            "a6": expected_value,
            "b6": expected_value,
            "a7": expected_value,
            "b7": expected_value,
        }

        self.assertDictEqual(wf_ex_db.output, expected_output)

        # Check liveaction and action execution result.
        expected_result = {"output": expected_output}

        self.assertDictEqual(lv_ac_db.result, expected_result)
        self.assertDictEqual(ac_ex_db.result, expected_result)

        # Assert expected output on conversion to API model
        ac_ex_api = ex_api_models.ActionExecutionAPI.from_model(
            ac_ex_db, mask_secrets=True
        )

        expected_masked_output = {
            "a6": expected_value,
            "b6": expected_value,
            "a7": expected_value,
            "b7": secrets_const.MASKED_ATTRIBUTE_VALUE,
        }

        expected_masked_result = {"output": expected_masked_output}

        self.assertDictEqual(ac_ex_api.result, expected_masked_result)

    @mock.patch.object(
        python_runner.PythonRunner,
        "run",
        mock.MagicMock(return_value=MOCK_PY_OUTPUT_1),
    )
    def test_string(self):
        self.assert_data_flow(TEST_1)

    @mock.patch.object(
        python_runner.PythonRunner,
        "run",
        mock.MagicMock(return_value=MOCK_PY_OUTPUT_2),
    )
    def test_unicode_string(self):
        self.assert_data_flow(TEST_2)

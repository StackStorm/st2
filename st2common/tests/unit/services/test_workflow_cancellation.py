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

import st2tests.config as tests_config

tests_config.parse_args()

from st2common.bootstrap import actionsregistrar
from st2common.bootstrap import runnersregistrar
from st2common.models.db import liveaction as lv_db_models
from st2common.services import action as ac_svc
from st2common.services import workflows as wf_svc
from st2common.transport import liveaction as lv_ac_xport
from st2common.transport import publishers
from st2tests.mocks import liveaction as mock_lv_ac_xport


TEST_FIXTURES = {
    "workflows": ["sequential.yaml", "join.yaml"],
    "actions": ["sequential.yaml", "join.yaml"],
}

TEST_PACK = "orquesta_tests"
TEST_PACK_PATH = (
    st2tests.fixturesloader.get_fixtures_packs_base_path() + "/" + TEST_PACK
)

PACKS = [
    TEST_PACK_PATH,
    st2tests.fixturesloader.get_fixtures_packs_base_path() + "/core",
]


@mock.patch.object(
    publishers.CUDPublisher, "publish_update", mock.MagicMock(return_value=None)
)
@mock.patch.object(
    publishers.CUDPublisher,
    "publish_create",
    mock.MagicMock(side_effect=mock_lv_ac_xport.MockLiveActionPublisher.publish_create),
)
@mock.patch.object(
    lv_ac_xport.LiveActionPublisher,
    "publish_state",
    mock.MagicMock(side_effect=mock_lv_ac_xport.MockLiveActionPublisher.publish_state),
)
class WorkflowExecutionCancellationTest(st2tests.WorkflowTestCase):
    @classmethod
    def setUpClass(cls):
        super(WorkflowExecutionCancellationTest, cls).setUpClass()

        # Register runners.
        runnersregistrar.register_runners()

        # Register test pack(s).
        actions_registrar = actionsregistrar.ActionsRegistrar(
            use_pack_cache=False, fail_on_failure=True
        )

        for pack in PACKS:
            actions_registrar.register_from_pack(pack)

    def test_cancellation(self):
        # Manually create the liveaction and action execution objects without publishing.
        wf_meta = self.get_wf_fixture_meta_data(
            TEST_PACK_PATH, TEST_FIXTURES["workflows"][0]
        )
        lv_ac_db = lv_db_models.LiveActionDB(action=wf_meta["name"])
        lv_ac_db, ac_ex_db = ac_svc.create_request(lv_ac_db)

        # Request and pre-process the workflow execution.
        wf_def = self.get_wf_def(TEST_PACK_PATH, wf_meta)
        st2_ctx = self.mock_st2_context(ac_ex_db)
        wf_ex_db = wf_svc.request(wf_def, ac_ex_db, st2_ctx)
        wf_ex_db = self.prep_wf_ex(wf_ex_db)

        # Manually request task executions.
        task_route = 0
        self.run_workflow_step(wf_ex_db, "task1", task_route)
        self.assert_task_running("task2", task_route)

        # Cancel the workflow when there is still active task(s).
        wf_ex_db = wf_svc.request_cancellation(ac_ex_db)
        conductor, wf_ex_db = wf_svc.refresh_conductor(str(wf_ex_db.id))
        self.assertEqual(conductor.get_workflow_status(), wf_statuses.CANCELING)
        self.assertEqual(wf_ex_db.status, wf_statuses.CANCELING)

        # Manually complete the task and ensure workflow is canceled.
        self.run_workflow_step(wf_ex_db, "task2", task_route)
        self.assert_task_not_started("task3", task_route)
        conductor, wf_ex_db = wf_svc.refresh_conductor(str(wf_ex_db.id))
        self.assertEqual(conductor.get_workflow_status(), wf_statuses.CANCELED)
        self.assertEqual(wf_ex_db.status, wf_statuses.CANCELED)

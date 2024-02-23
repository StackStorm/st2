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
import uuid

from orquesta import conducting
from orquesta import statuses as wf_statuses

import st2tests

import st2tests.config as tests_config

tests_config.parse_args()

from local_runner import local_shell_command_runner
from st2common.bootstrap import actionsregistrar
from st2common.bootstrap import runnersregistrar
from st2common.constants import action as action_constants
from st2common.exceptions import workflow as wf_exc
from st2common.models.db import liveaction as lv_db_models
from st2common.persistence import execution as ex_db_access
from st2common.persistence import liveaction as lv_db_access
from st2common.persistence import workflow as wf_db_access
from st2common.services import action as action_service
from st2common.services import workflows as workflow_service
from st2common.transport import liveaction as lv_ac_xport
from st2common.transport import publishers
from st2tests.fixtures.packs.core.fixture import PACK_PATH as CORE_PACK_PATH
from st2tests.fixtures.packs.orquesta_tests.fixture import PACK_PATH as TEST_PACK_PATH
from st2tests.mocks import liveaction as mock_lv_ac_xport


PACKS = [TEST_PACK_PATH, CORE_PACK_PATH]

RUNNER_RESULT_FAILED = (action_constants.LIVEACTION_STATUS_FAILED, {}, {})
RUNNER_RESULT_SUCCEEDED = (
    action_constants.LIVEACTION_STATUS_SUCCEEDED,
    {"stdout": "foobar", "succeeded": True, "failed": False, "stderr": ""},
    {},
)


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
class WorkflowExecutionRerunTest(st2tests.WorkflowTestCase):
    @classmethod
    def setUpClass(cls):
        super(WorkflowExecutionRerunTest, cls).setUpClass()

        # Register runners.
        runnersregistrar.register_runners()

        # Register test pack(s).
        actions_registrar = actionsregistrar.ActionsRegistrar(
            use_pack_cache=False, fail_on_failure=True
        )

        for pack in PACKS:
            actions_registrar.register_from_pack(pack)

    def prep_wf_ex_for_rerun(self):
        wf_meta = self.get_wf_fixture_meta_data(TEST_PACK_PATH, "sequential.yaml")

        # Manually create the liveaction and action execution objects without publishing.
        lv_ac_db1 = lv_db_models.LiveActionDB(action=wf_meta["name"])
        lv_ac_db1, ac_ex_db1 = action_service.create_request(lv_ac_db1)

        # Request the workflow execution.
        wf_def = self.get_wf_def(TEST_PACK_PATH, wf_meta)
        st2_ctx = self.mock_st2_context(ac_ex_db1)
        wf_ex_db = workflow_service.request(wf_def, ac_ex_db1, st2_ctx)
        wf_ex_db = self.prep_wf_ex(wf_ex_db)

        # Fail workflow execution.
        self.run_workflow_step(
            wf_ex_db,
            "task1",
            0,
            expected_ac_ex_db_status=action_constants.LIVEACTION_STATUS_FAILED,
            expected_tk_ex_db_status=wf_statuses.FAILED,
        )

        # Check workflow status.
        conductor, wf_ex_db = workflow_service.refresh_conductor(str(wf_ex_db.id))
        self.assertEqual(conductor.get_workflow_status(), wf_statuses.FAILED)
        self.assertEqual(wf_ex_db.status, wf_statuses.FAILED)
        lv_ac_db1 = lv_db_access.LiveAction.get_by_id(str(lv_ac_db1.id))
        self.assertEqual(lv_ac_db1.status, action_constants.LIVEACTION_STATUS_FAILED)
        ac_ex_db1 = ex_db_access.ActionExecution.get_by_id(str(ac_ex_db1.id))
        self.assertEqual(ac_ex_db1.status, action_constants.LIVEACTION_STATUS_FAILED)

        return wf_meta, lv_ac_db1, ac_ex_db1, wf_ex_db

    @mock.patch.object(
        local_shell_command_runner.LocalShellCommandRunner,
        "run",
        mock.MagicMock(side_effect=[RUNNER_RESULT_FAILED, RUNNER_RESULT_SUCCEEDED]),
    )
    def test_request_rerun(self):
        # Create and return a failed workflow execution.
        wf_meta, lv_ac_db1, ac_ex_db1, wf_ex_db = self.prep_wf_ex_for_rerun()

        # Manually create the liveaction and action execution objects for the rerun.
        lv_ac_db2 = lv_db_models.LiveActionDB(action=wf_meta["name"])
        lv_ac_db2, ac_ex_db2 = action_service.create_request(lv_ac_db2)

        # Request workflow execution rerun.
        st2_ctx = self.mock_st2_context(ac_ex_db2, ac_ex_db1.context)
        st2_ctx["workflow_execution_id"] = str(wf_ex_db.id)
        rerun_options = {"ref": str(ac_ex_db1.id), "tasks": ["task1"]}
        wf_ex_db = workflow_service.request_rerun(ac_ex_db2, st2_ctx, rerun_options)
        wf_ex_db = self.prep_wf_ex(wf_ex_db)

        # Check workflow status.
        conductor, wf_ex_db = workflow_service.refresh_conductor(str(wf_ex_db.id))
        self.assertEqual(conductor.get_workflow_status(), wf_statuses.RUNNING)
        self.assertEqual(wf_ex_db.status, wf_statuses.RUNNING)

        # Complete task1.
        self.run_workflow_step(wf_ex_db, "task1", 0)

        # Check workflow status and make sure it is still running.
        conductor, wf_ex_db = workflow_service.refresh_conductor(str(wf_ex_db.id))
        self.assertEqual(conductor.get_workflow_status(), wf_statuses.RUNNING)
        self.assertEqual(wf_ex_db.status, wf_statuses.RUNNING)
        lv_ac_db2 = lv_db_access.LiveAction.get_by_id(str(lv_ac_db2.id))
        self.assertEqual(lv_ac_db2.status, action_constants.LIVEACTION_STATUS_RUNNING)
        ac_ex_db2 = ex_db_access.ActionExecution.get_by_id(str(ac_ex_db2.id))
        self.assertEqual(ac_ex_db2.status, action_constants.LIVEACTION_STATUS_RUNNING)

    def test_request_rerun_while_original_is_still_running(self):
        wf_meta = self.get_wf_fixture_meta_data(TEST_PACK_PATH, "sequential.yaml")

        # Manually create the liveaction and action execution objects without publishing.
        lv_ac_db1 = lv_db_models.LiveActionDB(action=wf_meta["name"])
        lv_ac_db1, ac_ex_db1 = action_service.create_request(lv_ac_db1)

        # Request the workflow execution.
        wf_def = self.get_wf_def(TEST_PACK_PATH, wf_meta)
        st2_ctx = self.mock_st2_context(ac_ex_db1)
        wf_ex_db = workflow_service.request(wf_def, ac_ex_db1, st2_ctx)
        wf_ex_db = self.prep_wf_ex(wf_ex_db)

        # Check workflow status.
        conductor, wf_ex_db = workflow_service.refresh_conductor(str(wf_ex_db.id))
        self.assertEqual(conductor.get_workflow_status(), wf_statuses.RUNNING)
        self.assertEqual(wf_ex_db.status, wf_statuses.RUNNING)

        # Manually create the liveaction and action execution objects for the rerun.
        lv_ac_db2 = lv_db_models.LiveActionDB(action=wf_meta["name"])
        lv_ac_db2, ac_ex_db2 = action_service.create_request(lv_ac_db2)

        # Request workflow execution rerun.
        st2_ctx = self.mock_st2_context(ac_ex_db2, ac_ex_db1.context)
        st2_ctx["workflow_execution_id"] = str(wf_ex_db.id)
        rerun_options = {"ref": str(ac_ex_db1.id), "tasks": ["task1"]}
        expected_error = (
            '^Unable to rerun workflow execution ".*" '
            "because it is not in a completed state.$"
        )

        self.assertRaisesRegexp(
            wf_exc.WorkflowExecutionRerunException,
            expected_error,
            workflow_service.request_rerun,
            ac_ex_db2,
            st2_ctx,
            rerun_options,
        )

    @mock.patch.object(
        local_shell_command_runner.LocalShellCommandRunner,
        "run",
        mock.MagicMock(side_effect=[RUNNER_RESULT_FAILED, RUNNER_RESULT_SUCCEEDED]),
    )
    def test_request_rerun_again_while_prev_rerun_is_still_running(self):
        # Create and return a failed workflow execution.
        wf_meta, lv_ac_db1, ac_ex_db1, wf_ex_db = self.prep_wf_ex_for_rerun()

        # Manually create the liveaction and action execution objects for the rerun.
        lv_ac_db2 = lv_db_models.LiveActionDB(action=wf_meta["name"])
        lv_ac_db2, ac_ex_db2 = action_service.create_request(lv_ac_db2)

        # Request workflow execution rerun.
        st2_ctx = self.mock_st2_context(ac_ex_db2, ac_ex_db1.context)
        st2_ctx["workflow_execution_id"] = str(wf_ex_db.id)
        rerun_options = {"ref": str(ac_ex_db1.id), "tasks": ["task1"]}
        wf_ex_db = workflow_service.request_rerun(ac_ex_db2, st2_ctx, rerun_options)
        wf_ex_db = self.prep_wf_ex(wf_ex_db)

        # Check workflow status.
        conductor, wf_ex_db = workflow_service.refresh_conductor(str(wf_ex_db.id))
        self.assertEqual(conductor.get_workflow_status(), wf_statuses.RUNNING)
        self.assertEqual(wf_ex_db.status, wf_statuses.RUNNING)

        # Complete task1.
        self.run_workflow_step(wf_ex_db, "task1", 0)

        # Check workflow status and make sure it is still running.
        conductor, wf_ex_db = workflow_service.refresh_conductor(str(wf_ex_db.id))
        self.assertEqual(conductor.get_workflow_status(), wf_statuses.RUNNING)
        self.assertEqual(wf_ex_db.status, wf_statuses.RUNNING)
        lv_ac_db2 = lv_db_access.LiveAction.get_by_id(str(lv_ac_db2.id))
        self.assertEqual(lv_ac_db2.status, action_constants.LIVEACTION_STATUS_RUNNING)
        ac_ex_db2 = ex_db_access.ActionExecution.get_by_id(str(ac_ex_db2.id))
        self.assertEqual(ac_ex_db2.status, action_constants.LIVEACTION_STATUS_RUNNING)

        # Manually create the liveaction and action execution objects for the rerun.
        lv_ac_db3 = lv_db_models.LiveActionDB(action=wf_meta["name"])
        lv_ac_db3, ac_ex_db3 = action_service.create_request(lv_ac_db3)

        # Request workflow execution rerun again.
        st2_ctx = self.mock_st2_context(ac_ex_db3, ac_ex_db1.context)
        st2_ctx["workflow_execution_id"] = str(wf_ex_db.id)
        rerun_options = {"ref": str(ac_ex_db1.id), "tasks": ["task1"]}
        expected_error = (
            '^Unable to rerun workflow execution ".*" '
            "because it is not in a completed state.$"
        )

        self.assertRaisesRegexp(
            wf_exc.WorkflowExecutionRerunException,
            expected_error,
            workflow_service.request_rerun,
            ac_ex_db3,
            st2_ctx,
            rerun_options,
        )

    @mock.patch.object(
        local_shell_command_runner.LocalShellCommandRunner,
        "run",
        mock.MagicMock(return_value=RUNNER_RESULT_FAILED),
    )
    def test_request_rerun_with_missing_workflow_execution_id(self):
        # Create and return a failed workflow execution.
        wf_meta, lv_ac_db1, ac_ex_db1, wf_ex_db = self.prep_wf_ex_for_rerun()

        # Manually create the liveaction and action execution objects for the rerun.
        lv_ac_db2 = lv_db_models.LiveActionDB(action=wf_meta["name"])
        lv_ac_db2, ac_ex_db2 = action_service.create_request(lv_ac_db2)

        # Request workflow execution rerun without workflow_execution_id.
        st2_ctx = self.mock_st2_context(ac_ex_db2, ac_ex_db1.context)
        rerun_options = {"ref": str(ac_ex_db1.id), "tasks": ["task1"]}
        expected_error = (
            "Unable to rerun workflow execution because "
            "workflow_execution_id is not provided."
        )

        self.assertRaisesRegexp(
            wf_exc.WorkflowExecutionRerunException,
            expected_error,
            workflow_service.request_rerun,
            ac_ex_db2,
            st2_ctx,
            rerun_options,
        )

    @mock.patch.object(
        local_shell_command_runner.LocalShellCommandRunner,
        "run",
        mock.MagicMock(return_value=RUNNER_RESULT_FAILED),
    )
    def test_request_rerun_with_nonexistent_workflow_execution(self):
        # Create and return a failed workflow execution.
        wf_meta, lv_ac_db1, ac_ex_db1, wf_ex_db = self.prep_wf_ex_for_rerun()

        # Manually create the liveaction and action execution objects for the rerun.
        lv_ac_db2 = lv_db_models.LiveActionDB(action=wf_meta["name"])
        lv_ac_db2, ac_ex_db2 = action_service.create_request(lv_ac_db2)

        # Request workflow execution rerun with bogus workflow_execution_id.
        st2_ctx = self.mock_st2_context(ac_ex_db2, ac_ex_db1.context)
        st2_ctx["workflow_execution_id"] = uuid.uuid4().hex[0:24]
        rerun_options = {"ref": str(ac_ex_db1.id), "tasks": ["task1"]}
        expected_error = (
            '^Unable to rerun workflow execution ".*" ' "because it does not exist.$"
        )

        self.assertRaisesRegexp(
            wf_exc.WorkflowExecutionRerunException,
            expected_error,
            workflow_service.request_rerun,
            ac_ex_db2,
            st2_ctx,
            rerun_options,
        )

    @mock.patch.object(
        local_shell_command_runner.LocalShellCommandRunner,
        "run",
        mock.MagicMock(return_value=RUNNER_RESULT_FAILED),
    )
    def test_request_rerun_with_workflow_execution_not_abended(self):
        # Create and return a failed workflow execution.
        wf_meta, lv_ac_db1, ac_ex_db1, wf_ex_db = self.prep_wf_ex_for_rerun()

        # Manually set workflow execution status to paused.
        wf_ex_db.status = wf_statuses.PAUSED
        wf_ex_db = wf_db_access.WorkflowExecution.add_or_update(wf_ex_db)

        # Manually create the liveaction and action execution objects for the rerun.
        lv_ac_db2 = lv_db_models.LiveActionDB(action=wf_meta["name"])
        lv_ac_db2, ac_ex_db2 = action_service.create_request(lv_ac_db2)

        # Request workflow execution rerun with bogus workflow_execution_id.
        st2_ctx = self.mock_st2_context(ac_ex_db2, ac_ex_db1.context)
        st2_ctx["workflow_execution_id"] = str(wf_ex_db.id)
        rerun_options = {"ref": str(ac_ex_db1.id), "tasks": ["task1"]}
        expected_error = (
            '^Unable to rerun workflow execution ".*" '
            "because it is not in a completed state.$"
        )

        self.assertRaisesRegexp(
            wf_exc.WorkflowExecutionRerunException,
            expected_error,
            workflow_service.request_rerun,
            ac_ex_db2,
            st2_ctx,
            rerun_options,
        )

    @mock.patch.object(
        local_shell_command_runner.LocalShellCommandRunner,
        "run",
        mock.MagicMock(return_value=RUNNER_RESULT_FAILED),
    )
    def test_request_rerun_with_conductor_status_not_abended(self):
        # Create and return a failed workflow execution.
        wf_meta, lv_ac_db1, ac_ex_db1, wf_ex_db = self.prep_wf_ex_for_rerun()

        # Manually set workflow conductor state to paused.
        wf_ex_db.state["status"] = wf_statuses.PAUSED
        wf_ex_db = wf_db_access.WorkflowExecution.add_or_update(wf_ex_db)

        # Manually create the liveaction and action execution objects for the rerun.
        lv_ac_db2 = lv_db_models.LiveActionDB(action=wf_meta["name"])
        lv_ac_db2, ac_ex_db2 = action_service.create_request(lv_ac_db2)

        # Request workflow execution rerun with bogus workflow_execution_id.
        st2_ctx = self.mock_st2_context(ac_ex_db2, ac_ex_db1.context)
        st2_ctx["workflow_execution_id"] = str(wf_ex_db.id)
        rerun_options = {"ref": str(ac_ex_db1.id), "tasks": ["task1"]}
        expected_error = (
            "Unable to rerun workflow because it is not in a completed state."
        )

        self.assertRaisesRegexp(
            wf_exc.WorkflowExecutionRerunException,
            expected_error,
            workflow_service.request_rerun,
            ac_ex_db2,
            st2_ctx,
            rerun_options,
        )

    @mock.patch.object(
        local_shell_command_runner.LocalShellCommandRunner,
        "run",
        mock.MagicMock(return_value=RUNNER_RESULT_FAILED),
    )
    def test_request_rerun_with_bad_task_name(self):
        # Create and return a failed workflow execution.
        wf_meta, lv_ac_db1, ac_ex_db1, wf_ex_db = self.prep_wf_ex_for_rerun()

        # Manually create the liveaction and action execution objects for the rerun.
        lv_ac_db2 = lv_db_models.LiveActionDB(action=wf_meta["name"])
        lv_ac_db2, ac_ex_db2 = action_service.create_request(lv_ac_db2)

        # Request workflow execution.
        st2_ctx = self.mock_st2_context(ac_ex_db2, ac_ex_db1.context)
        st2_ctx["workflow_execution_id"] = str(wf_ex_db.id)
        rerun_options = {"ref": str(ac_ex_db1.id), "tasks": ["task5354"]}
        expected_error = (
            "^Unable to rerun workflow because one or more tasks is not found: .*$"
        )

        self.assertRaisesRegexp(
            wf_exc.WorkflowExecutionRerunException,
            expected_error,
            workflow_service.request_rerun,
            ac_ex_db2,
            st2_ctx,
            rerun_options,
        )

    @mock.patch.object(
        local_shell_command_runner.LocalShellCommandRunner,
        "run",
        mock.MagicMock(return_value=RUNNER_RESULT_FAILED),
    )
    def test_request_rerun_with_conductor_status_not_resuming(self):
        # Create and return a failed workflow execution.
        wf_meta, lv_ac_db1, ac_ex_db1, wf_ex_db = self.prep_wf_ex_for_rerun()

        # Manually create the liveaction and action execution objects for the rerun.
        lv_ac_db2 = lv_db_models.LiveActionDB(action=wf_meta["name"])
        lv_ac_db2, ac_ex_db2 = action_service.create_request(lv_ac_db2)

        # Request workflow execution rerun with bogus workflow_execution_id.
        st2_ctx = self.mock_st2_context(ac_ex_db2, ac_ex_db1.context)
        st2_ctx["workflow_execution_id"] = str(wf_ex_db.id)
        rerun_options = {"ref": str(ac_ex_db1.id), "tasks": ["task1"]}
        expected_error = (
            '^Unable to rerun workflow execution ".*" ' "due to an unknown cause."
        )

        with mock.patch.object(
            conducting.WorkflowConductor,
            "get_workflow_status",
            mock.MagicMock(return_value=wf_statuses.FAILED),
        ):
            self.assertRaisesRegexp(
                wf_exc.WorkflowExecutionRerunException,
                expected_error,
                workflow_service.request_rerun,
                ac_ex_db2,
                st2_ctx,
                rerun_options,
            )

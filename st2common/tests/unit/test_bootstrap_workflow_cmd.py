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

from st2common.util.monkey_patch import monkey_patch

monkey_patch()

import bson
import mock

from st2common.cmd import bootstrap_workflow
from st2common.constants import action as action_constants
from st2common.constants.exit_codes import FAILURE_EXIT_CODE
from st2common.constants.exit_codes import SUCCESS_EXIT_CODE
from st2common.models.db.execution import ActionExecutionDB
from st2common.models.db.liveaction import LiveActionDB
from st2common.persistence.execution import ActionExecution
from st2common.persistence.liveaction import LiveAction
from st2common.services import workflows as wf_svc
from st2tests.base import CleanDbTestCase


class TestBootstrapWorkflowCLI(CleanDbTestCase):
    def _make_paused_execution(self, paused_by):
        lv_ac_db = LiveActionDB(
            action="core.local",
            status=action_constants.LIVEACTION_STATUS_PAUSED,
            context={"paused_by": paused_by} if paused_by is not None else {},
        )
        lv_ac_db = LiveAction.add_or_update(lv_ac_db, publish=False)
        ac_ex_db = ActionExecutionDB(
            liveaction_id=str(lv_ac_db.id),
            action={"ref": "core.local"},
            runner={"name": "local-shell-cmd"},
            status=action_constants.LIVEACTION_STATUS_PAUSED,
            context={},
        )
        ac_ex_db = ActionExecution.add_or_update(ac_ex_db, publish=False)
        return lv_ac_db, ac_ex_db

    def test_missing_execution_id_returns_not_found(self):
        # No such execution exists.
        bogus = str(bson.ObjectId())
        with mock.patch.object(wf_svc, "bootstrap_resume_execution") as mock_resume:
            # Expect a database miss to raise, main catches → FAILURE.
            # _bootstrap_one raises via get_by_id; main wraps it.
            with self.assertRaises(Exception):
                bootstrap_workflow._bootstrap_one(bogus)
            mock_resume.assert_not_called()

    def test_rejects_execution_not_paused(self):
        lv_ac_db = LiveActionDB(
            action="core.local",
            status=action_constants.LIVEACTION_STATUS_SUCCEEDED,
            context={"paused_by": wf_svc.WORKFLOW_ENGINE_START_STOP_SEQ},
        )
        lv_ac_db = LiveAction.add_or_update(lv_ac_db, publish=False)
        ac_ex_db = ActionExecutionDB(
            liveaction_id=str(lv_ac_db.id),
            action={"ref": "core.local"},
            runner={"name": "local-shell-cmd"},
            status=action_constants.LIVEACTION_STATUS_SUCCEEDED,
            context={},
        )
        ac_ex_db = ActionExecution.add_or_update(ac_ex_db, publish=False)

        with mock.patch.object(wf_svc, "bootstrap_resume_execution") as mock_resume:
            rc = bootstrap_workflow._bootstrap_one(str(ac_ex_db.id))
            self.assertEqual(rc, FAILURE_EXIT_CODE)
            mock_resume.assert_not_called()

    def test_rejects_paused_by_other_actor(self):
        _lv_ac, ac_ex_db = self._make_paused_execution(paused_by="some_user@stackstorm")

        with mock.patch.object(wf_svc, "bootstrap_resume_execution") as mock_resume:
            rc = bootstrap_workflow._bootstrap_one(str(ac_ex_db.id))
            self.assertEqual(rc, FAILURE_EXIT_CODE)
            mock_resume.assert_not_called()

    def test_happy_path_calls_service(self):
        lv_ac_db, ac_ex_db = self._make_paused_execution(
            paused_by=wf_svc.WORKFLOW_ENGINE_START_STOP_SEQ
        )

        with mock.patch.object(wf_svc, "bootstrap_resume_execution") as mock_resume:
            rc = bootstrap_workflow._bootstrap_one(str(ac_ex_db.id))
            self.assertEqual(rc, SUCCESS_EXIT_CODE)
            mock_resume.assert_called_once()
            # Called with the LiveActionDB matching our record.
            args, _ = mock_resume.call_args
            self.assertEqual(str(args[0].id), str(lv_ac_db.id))

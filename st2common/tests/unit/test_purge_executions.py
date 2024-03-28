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

# pytest: make sure monkey_patching happens before importing mongoengine
from st2common.util.monkey_patch import monkey_patch

monkey_patch()

import copy
from datetime import timedelta

import mock
import bson

from st2common import log as logging
from st2common.garbage_collection.executions import purge_executions
from st2common.constants import action as action_constants
from st2common.persistence.execution import ActionExecution
from st2common.persistence.execution import ActionExecutionOutput
from st2common.models.db.execution import ActionExecutionOutputDB
from st2common.persistence.liveaction import LiveAction
from st2common.util import date as date_utils
from st2tests.base import CleanDbTestCase
from st2tests.fixtures.generic.fixture import PACK_NAME as GENERIC_PACK
from st2tests.fixturesloader import FixturesLoader
from six.moves import range

LOG = logging.getLogger(__name__)

TEST_FIXTURES = {"executions": ["execution1.yaml"], "liveactions": ["liveaction4.yaml"]}


class TestPurgeExecutions(CleanDbTestCase):
    @classmethod
    def setUpClass(cls):
        CleanDbTestCase.setUpClass()
        super(TestPurgeExecutions, cls).setUpClass()

    def setUp(self):
        super(TestPurgeExecutions, self).setUp()
        fixtures_loader = FixturesLoader()
        self.models = fixtures_loader.load_models(
            fixtures_pack=GENERIC_PACK, fixtures_dict=TEST_FIXTURES
        )

    def test_no_timestamp_doesnt_delete_things(self):
        now = date_utils.get_datetime_utc_now()
        exec_model = copy.deepcopy(self.models["executions"]["execution1.yaml"])
        exec_model["start_timestamp"] = now - timedelta(days=15)
        exec_model["end_timestamp"] = now - timedelta(days=14)
        exec_model["status"] = action_constants.LIVEACTION_STATUS_SUCCEEDED
        exec_model["id"] = bson.ObjectId()
        ActionExecution.add_or_update(exec_model)

        # Insert corresponding stdout and stderr db mock models
        self._insert_mock_stdout_and_stderr_objects_for_execution(
            exec_model["id"], count=3
        )

        execs = ActionExecution.get_all()
        self.assertEqual(len(execs), 1)
        stdout_dbs = ActionExecutionOutput.query(output_type="stdout")
        self.assertEqual(len(stdout_dbs), 3)
        stderr_dbs = ActionExecutionOutput.query(output_type="stderr")
        self.assertEqual(len(stderr_dbs), 3)

        expected_msg = "Specify a valid timestamp"
        self.assertRaisesRegex(
            ValueError, expected_msg, purge_executions, logger=LOG, timestamp=None
        )
        execs = ActionExecution.get_all()
        self.assertEqual(len(execs), 1)
        stdout_dbs = ActionExecutionOutput.query(output_type="stdout")
        self.assertEqual(len(stdout_dbs), 3)
        stderr_dbs = ActionExecutionOutput.query(output_type="stderr")
        self.assertEqual(len(stderr_dbs), 3)

    def test_purge_executions_with_action_ref(self):
        now = date_utils.get_datetime_utc_now()
        exec_model = copy.deepcopy(self.models["executions"]["execution1.yaml"])
        exec_model["start_timestamp"] = now - timedelta(days=15)
        exec_model["end_timestamp"] = now - timedelta(days=14)
        exec_model["status"] = action_constants.LIVEACTION_STATUS_SUCCEEDED
        exec_model["id"] = bson.ObjectId()
        ActionExecution.add_or_update(exec_model)

        # Insert corresponding stdout and stderr db mock models
        self._insert_mock_stdout_and_stderr_objects_for_execution(
            exec_model["id"], count=3
        )

        execs = ActionExecution.get_all()
        self.assertEqual(len(execs), 1)
        stdout_dbs = ActionExecutionOutput.query(output_type="stdout")
        self.assertEqual(len(stdout_dbs), 3)
        stderr_dbs = ActionExecutionOutput.query(output_type="stderr")
        self.assertEqual(len(stderr_dbs), 3)

        # Invalid action reference, nothing should be deleted
        purge_executions(
            logger=LOG, action_ref="core.localzzz", timestamp=now - timedelta(days=10)
        )

        execs = ActionExecution.get_all()
        self.assertEqual(len(execs), 1)
        stdout_dbs = ActionExecutionOutput.query(output_type="stdout")
        self.assertEqual(len(stdout_dbs), 3)
        stderr_dbs = ActionExecutionOutput.query(output_type="stderr")
        self.assertEqual(len(stderr_dbs), 3)

        purge_executions(
            logger=LOG, action_ref="core.local", timestamp=now - timedelta(days=10)
        )

        execs = ActionExecution.get_all()
        self.assertEqual(len(execs), 0)
        stdout_dbs = ActionExecutionOutput.query(output_type="stdout")
        self.assertEqual(len(stdout_dbs), 0)
        stderr_dbs = ActionExecutionOutput.query(output_type="stderr")
        self.assertEqual(len(stderr_dbs), 0)

    def test_purge_executions_with_timestamp(self):
        now = date_utils.get_datetime_utc_now()

        # Write one execution after cut-off threshold
        exec_model = copy.deepcopy(self.models["executions"]["execution1.yaml"])
        exec_model["start_timestamp"] = now - timedelta(days=15)
        exec_model["end_timestamp"] = now - timedelta(days=14)
        exec_model["status"] = action_constants.LIVEACTION_STATUS_SUCCEEDED
        exec_model["id"] = bson.ObjectId()
        ActionExecution.add_or_update(exec_model)

        # Insert corresponding stdout and stderr db mock models
        self._insert_mock_stdout_and_stderr_objects_for_execution(
            exec_model["id"], count=3
        )

        # Write one execution before cut-off threshold
        exec_model = copy.deepcopy(self.models["executions"]["execution1.yaml"])
        exec_model["start_timestamp"] = now - timedelta(days=22)
        exec_model["end_timestamp"] = now - timedelta(days=21)
        exec_model["status"] = action_constants.LIVEACTION_STATUS_SUCCEEDED
        exec_model["id"] = bson.ObjectId()
        ActionExecution.add_or_update(exec_model)

        # Insert corresponding stdout and stderr db mock models
        self._insert_mock_stdout_and_stderr_objects_for_execution(
            exec_model["id"], count=3
        )

        execs = ActionExecution.get_all()
        self.assertEqual(len(execs), 2)
        stdout_dbs = ActionExecutionOutput.query(output_type="stdout")
        self.assertEqual(len(stdout_dbs), 6)
        stderr_dbs = ActionExecutionOutput.query(output_type="stderr")
        self.assertEqual(len(stderr_dbs), 6)

        purge_executions(logger=LOG, timestamp=now - timedelta(days=20))
        execs = ActionExecution.get_all()
        self.assertEqual(len(execs), 1)
        stdout_dbs = ActionExecutionOutput.query(output_type="stdout")
        self.assertEqual(len(stdout_dbs), 3)
        stderr_dbs = ActionExecutionOutput.query(output_type="stderr")
        self.assertEqual(len(stderr_dbs), 3)

    def test_liveaction_gets_deleted(self):
        now = date_utils.get_datetime_utc_now()
        start_ts = now - timedelta(days=15)
        end_ts = now - timedelta(days=14)

        liveaction_model = copy.deepcopy(self.models["liveactions"]["liveaction4.yaml"])
        liveaction_model["start_timestamp"] = start_ts
        liveaction_model["end_timestamp"] = end_ts
        liveaction_model["status"] = action_constants.LIVEACTION_STATUS_SUCCEEDED
        liveaction = LiveAction.add_or_update(liveaction_model)

        # Write one execution before cut-off threshold
        exec_model = copy.deepcopy(self.models["executions"]["execution1.yaml"])
        exec_model["start_timestamp"] = start_ts
        exec_model["end_timestamp"] = end_ts
        exec_model["status"] = action_constants.LIVEACTION_STATUS_SUCCEEDED
        exec_model["id"] = bson.ObjectId()
        exec_model["liveaction"]["id"] = str(liveaction.id)
        ActionExecution.add_or_update(exec_model)

        liveactions = LiveAction.get_all()
        executions = ActionExecution.get_all()
        self.assertEqual(len(liveactions), 1)
        self.assertEqual(len(executions), 1)

        purge_executions(logger=LOG, timestamp=now - timedelta(days=10))

        liveactions = LiveAction.get_all()
        executions = ActionExecution.get_all()
        self.assertEqual(len(executions), 0)
        self.assertEqual(len(liveactions), 0)

    def test_purge_incomplete(self):
        now = date_utils.get_datetime_utc_now()
        start_ts = now - timedelta(days=15)

        # Write executions before cut-off threshold
        exec_model = copy.deepcopy(self.models["executions"]["execution1.yaml"])
        exec_model["start_timestamp"] = start_ts
        exec_model["status"] = action_constants.LIVEACTION_STATUS_SCHEDULED
        exec_model["id"] = bson.ObjectId()
        ActionExecution.add_or_update(exec_model)

        # Insert corresponding stdout and stderr db mock models
        self._insert_mock_stdout_and_stderr_objects_for_execution(
            exec_model["id"], count=1
        )

        exec_model = copy.deepcopy(self.models["executions"]["execution1.yaml"])
        exec_model["start_timestamp"] = start_ts
        exec_model["status"] = action_constants.LIVEACTION_STATUS_RUNNING
        exec_model["id"] = bson.ObjectId()
        ActionExecution.add_or_update(exec_model)

        # Insert corresponding stdout and stderr db mock models
        self._insert_mock_stdout_and_stderr_objects_for_execution(
            exec_model["id"], count=1
        )

        exec_model = copy.deepcopy(self.models["executions"]["execution1.yaml"])
        exec_model["start_timestamp"] = start_ts
        exec_model["status"] = action_constants.LIVEACTION_STATUS_DELAYED
        exec_model["id"] = bson.ObjectId()
        ActionExecution.add_or_update(exec_model)

        # Insert corresponding stdout and stderr db mock models
        self._insert_mock_stdout_and_stderr_objects_for_execution(
            exec_model["id"], count=1
        )

        exec_model = copy.deepcopy(self.models["executions"]["execution1.yaml"])
        exec_model["start_timestamp"] = start_ts
        exec_model["status"] = action_constants.LIVEACTION_STATUS_CANCELING
        exec_model["id"] = bson.ObjectId()
        ActionExecution.add_or_update(exec_model)

        # Insert corresponding stdout and stderr db mock models
        self._insert_mock_stdout_and_stderr_objects_for_execution(
            exec_model["id"], count=1
        )

        exec_model = copy.deepcopy(self.models["executions"]["execution1.yaml"])
        exec_model["start_timestamp"] = start_ts
        exec_model["status"] = action_constants.LIVEACTION_STATUS_REQUESTED
        exec_model["id"] = bson.ObjectId()
        ActionExecution.add_or_update(exec_model)

        # Insert corresponding stdout and stderr db mock models
        self._insert_mock_stdout_and_stderr_objects_for_execution(
            exec_model["id"], count=1
        )

        self.assertEqual(len(ActionExecution.get_all()), 5)
        stdout_dbs = ActionExecutionOutput.query(output_type="stdout")
        self.assertEqual(len(stdout_dbs), 5)
        stderr_dbs = ActionExecutionOutput.query(output_type="stderr")
        self.assertEqual(len(stderr_dbs), 5)

        # Incompleted executions shouldnt be purged
        purge_executions(
            logger=LOG, timestamp=now - timedelta(days=10), purge_incomplete=False
        )
        self.assertEqual(len(ActionExecution.get_all()), 5)
        stdout_dbs = ActionExecutionOutput.query(output_type="stdout")
        self.assertEqual(len(stdout_dbs), 5)
        stderr_dbs = ActionExecutionOutput.query(output_type="stderr")
        self.assertEqual(len(stderr_dbs), 5)

        purge_executions(
            logger=LOG, timestamp=now - timedelta(days=10), purge_incomplete=True
        )
        self.assertEqual(len(ActionExecution.get_all()), 0)
        stdout_dbs = ActionExecutionOutput.query(output_type="stdout")
        self.assertEqual(len(stdout_dbs), 0)
        stderr_dbs = ActionExecutionOutput.query(output_type="stderr")
        self.assertEqual(len(stderr_dbs), 0)

    @mock.patch("st2common.garbage_collection.executions.LiveAction")
    @mock.patch("st2common.garbage_collection.executions.ActionExecution")
    def test_purge_executions_whole_model_is_not_loaded_in_memory(
        self, mock_ActionExecution, mock_LiveAction
    ):
        # Verify that whole execution objects are not loaded in memory and we just retrieve the
        # id field
        self.assertEqual(mock_ActionExecution.query.call_count, 0)
        self.assertEqual(mock_LiveAction.query.call_count, 0)
        now = date_utils.get_datetime_utc_now()
        purge_executions(
            logger=LOG, timestamp=now - timedelta(days=10), purge_incomplete=True
        )

        self.assertEqual(mock_ActionExecution.query.call_count, 2)
        self.assertEqual(mock_LiveAction.query.call_count, 1)

        self.assertEqual(
            mock_ActionExecution.query.call_args_list[0][1]["only_fields"], ["id"]
        )
        self.assertTrue(
            mock_ActionExecution.query.call_args_list[0][1]["no_dereference"]
        )
        self.assertEqual(
            mock_ActionExecution.query.call_args_list[1][1]["only_fields"], ["id"]
        )
        self.assertTrue(
            mock_ActionExecution.query.call_args_list[1][1]["no_dereference"]
        )
        self.assertEqual(
            mock_LiveAction.query.call_args_list[0][1]["only_fields"], ["id"]
        )
        self.assertTrue(mock_LiveAction.query.call_args_list[0][1]["no_dereference"])

    def _insert_mock_stdout_and_stderr_objects_for_execution(
        self, execution_id, count=5
    ):
        execution_id = str(execution_id)

        stdout_dbs, stderr_dbs = [], []
        for i in range(0, count):
            stdout_db = ActionExecutionOutputDB(
                execution_id=execution_id,
                action_ref="dummy.pack",
                runner_ref="dummy",
                output_type="stdout",
                data="stdout %s" % (i),
            )
            ActionExecutionOutput.add_or_update(stdout_db)

            stderr_db = ActionExecutionOutputDB(
                execution_id=execution_id,
                action_ref="dummy.pack",
                runner_ref="dummy",
                output_type="stderr",
                data="stderr%s" % (i),
            )
            ActionExecutionOutput.add_or_update(stderr_db)

        return stdout_dbs, stderr_dbs

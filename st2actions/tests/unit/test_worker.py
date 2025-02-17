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

from bson.errors import InvalidStringData
import eventlet
import mock
import os
from oslo_config import cfg
from tooz.drivers.redis import RedisDriver
import tempfile

# This import must be early for import-time side-effects.
from st2tests.base import DbTestCase

import st2actions.worker as actions_worker
import st2tests.config as tests_config
from st2common.constants import action as action_constants
from st2common.models.db.liveaction import LiveActionDB
from st2common.models.system.common import ResourceReference
from st2common.persistence.execution import ActionExecution
from st2common.persistence.liveaction import LiveAction
from st2common.services import executions
from st2common.services import coordination
from st2common.util import date as date_utils
from st2common.bootstrap import runnersregistrar as runners_registrar
from local_runner.local_shell_command_runner import LocalShellCommandRunner

from st2tests.fixtures.generic.fixture import PACK_NAME as FIXTURES_PACK
from st2tests.fixturesloader import FixturesLoader
from six.moves import range

TEST_FIXTURES = {"actions": ["local.yaml"]}

NON_UTF8_RESULT = {
    "stderr": "",
    "stdout": "\x82\n",
    "succeeded": True,
    "failed": False,
    "return_code": 0,
}


class WorkerTestCase(DbTestCase):
    fixtures_loader = FixturesLoader()

    @classmethod
    def setUpClass(cls):
        super(WorkerTestCase, cls).setUpClass()

        runners_registrar.register_runners()

        models = WorkerTestCase.fixtures_loader.save_fixtures_to_db(
            fixtures_pack=FIXTURES_PACK, fixtures_dict=TEST_FIXTURES
        )
        WorkerTestCase.local_action_db = models["actions"]["local.yaml"]

    @staticmethod
    def reset_config(
        graceful_shutdown=True,  # default is True (st2common.config)
        exit_still_active_check=None,  # default is 300 (st2common.config)
        still_active_check_interval=None,  # default is 2 (st2common.config)
        service_registry=None,  # default is False (st2common.config)
    ):
        tests_config.reset()
        tests_config.parse_args()
        cfg.CONF.set_override(
            name="graceful_shutdown", override=graceful_shutdown, group="actionrunner"
        )
        if exit_still_active_check is not None:
            cfg.CONF.set_override(
                name="exit_still_active_check",
                override=exit_still_active_check,
                group="actionrunner",
            )
        if still_active_check_interval is not None:
            cfg.CONF.set_override(
                name="still_active_check_interval",
                override=still_active_check_interval,
                group="actionrunner",
            )
        if service_registry is not None:
            cfg.CONF.set_override(
                name="service_registry", override=service_registry, group="coordination"
            )

    def _get_liveaction_model(self, action_db, params):
        status = action_constants.LIVEACTION_STATUS_REQUESTED
        start_timestamp = date_utils.get_datetime_utc_now()
        action_ref = ResourceReference(name=action_db.name, pack=action_db.pack).ref
        parameters = params
        context = {"user": cfg.CONF.system_user.user}
        liveaction_db = LiveActionDB(
            status=status,
            start_timestamp=start_timestamp,
            action=action_ref,
            parameters=parameters,
            context=context,
        )
        return liveaction_db

    @mock.patch.object(
        LocalShellCommandRunner,
        "run",
        mock.MagicMock(
            return_value=(
                action_constants.LIVEACTION_STATUS_SUCCEEDED,
                NON_UTF8_RESULT,
                None,
            )
        ),
    )
    def test_non_utf8_action_result_string(self):
        action_worker = actions_worker.get_worker()
        params = {"cmd": "python -c 'print \"\\x82\"'"}
        liveaction_db = self._get_liveaction_model(
            WorkerTestCase.local_action_db, params
        )
        liveaction_db = LiveAction.add_or_update(liveaction_db)
        execution_db = executions.create_execution_object(liveaction_db)

        try:
            action_worker._run_action(liveaction_db)
        except InvalidStringData:
            liveaction_db = LiveAction.get_by_id(liveaction_db.id)
            self.assertEqual(
                liveaction_db.status, action_constants.LIVEACTION_STATUS_FAILED
            )
            self.assertIn("error", liveaction_db.result)
            self.assertIn("traceback", liveaction_db.result)
            execution_db = ActionExecution.get_by_id(execution_db.id)
            self.assertEqual(
                liveaction_db.status, action_constants.LIVEACTION_STATUS_FAILED
            )

    def test_worker_shutdown(self):
        self.reset_config(graceful_shutdown=False)

        action_worker = actions_worker.get_worker()
        temp_file = None

        # Create a temporary file that is deleted when the file is closed and then set up an
        # action to wait for this file to be deleted. This allows this test to run the action
        # over a separate thread, run the shutdown sequence on the main thread, and then let
        # the local runner to exit gracefully and allow _run_action to finish execution.
        with tempfile.NamedTemporaryFile() as fp:
            temp_file = fp.name
            self.assertIsNotNone(temp_file)
            self.assertTrue(os.path.isfile(temp_file))

            # Launch the action execution in a separate thread.
            params = {"cmd": "while [ -e '%s' ]; do sleep 0.1; done" % temp_file}
            liveaction_db = self._get_liveaction_model(
                WorkerTestCase.local_action_db, params
            )
            liveaction_db = LiveAction.add_or_update(liveaction_db)
            executions.create_execution_object(liveaction_db)
            runner_thread = eventlet.spawn(action_worker._run_action, liveaction_db)

            # Wait for the worker up to 10s to add the liveaction to _running_liveactions.
            for i in range(0, int(10 / 0.1)):
                eventlet.sleep(0.1)
                if len(action_worker._running_liveactions) > 0:
                    break

            self.assertEqual(len(action_worker._running_liveactions), 1)

            # Shutdown the worker to trigger the abandon process.
            action_worker.shutdown()
            liveaction_db = LiveAction.get_by_id(liveaction_db.id)

            # Verify that _running_liveactions is empty and the liveaction is abandoned.
            self.assertEqual(len(action_worker._running_liveactions), 0)
            self.assertEqual(
                liveaction_db.status,
                action_constants.LIVEACTION_STATUS_ABANDONED,
                str(liveaction_db),
            )

        # Make sure the temporary file has been deleted.
        self.assertFalse(os.path.isfile(temp_file))

        # Wait for the local runner to complete. This will activate the finally block in
        # _run_action but will not result in KeyError because the discard method is used to
        # to remove the liveaction from _running_liveactions.
        runner_thread.wait()

    @mock.patch.object(
        RedisDriver,
        "get_members",
        mock.MagicMock(
            return_value=coordination.NoOpAsyncResult(("member-1", "member-2"))
        ),
    )
    def test_worker_graceful_shutdown_with_multiple_runners(self):
        self.reset_config(
            exit_still_active_check=10,
            still_active_check_interval=1,
            service_registry=True,
        )

        action_worker = actions_worker.get_worker()
        temp_file = None

        # Create a temporary file that is deleted when the file is closed and then set up an
        # action to wait for this file to be deleted. This allows this test to run the action
        # over a separate thread, run the shutdown sequence on the main thread, and then let
        # the local runner to exit gracefully and allow _run_action to finish execution.
        with tempfile.NamedTemporaryFile() as fp:
            temp_file = fp.name
            self.assertIsNotNone(temp_file)
            self.assertTrue(os.path.isfile(temp_file))

            # Launch the action execution in a separate thread.
            params = {"cmd": "while [ -e '%s' ]; do sleep 0.1; done" % temp_file}
            liveaction_db = self._get_liveaction_model(
                WorkerTestCase.local_action_db, params
            )
            liveaction_db = LiveAction.add_or_update(liveaction_db)
            executions.create_execution_object(liveaction_db)
            runner_thread = eventlet.spawn(action_worker._run_action, liveaction_db)

            # Wait for the worker up to 10s to add the liveaction to _running_liveactions.
            for i in range(0, int(10 / 0.1)):
                eventlet.sleep(0.1)
                if len(action_worker._running_liveactions) > 0:
                    break

            self.assertEqual(len(action_worker._running_liveactions), 1)

            # Shutdown the worker to trigger the abandon process.
            shutdown_thread = eventlet.spawn(action_worker.shutdown)

        # Make sure the temporary file has been deleted.
        self.assertFalse(os.path.isfile(temp_file))

        # Wait for the worker up to 10s to remove the liveaction from _running_liveactions.
        for i in range(0, int(10 / 0.1)):
            eventlet.sleep(0.1)
            if len(action_worker._running_liveactions) < 1:
                break
        liveaction_db = LiveAction.get_by_id(liveaction_db.id)

        # Verify that _running_liveactions is empty and the liveaction is succeeded.
        self.assertEqual(len(action_worker._running_liveactions), 0)
        self.assertEqual(
            liveaction_db.status,
            action_constants.LIVEACTION_STATUS_SUCCEEDED,
            str(liveaction_db),
        )

        # Wait for the local runner to complete. This will activate the finally block in
        # _run_action but will not result in KeyError because the discard method is used to
        # to remove the liveaction from _running_liveactions.
        runner_thread.wait()
        shutdown_thread.kill()

    def test_worker_graceful_shutdown_with_single_runner(self):
        self.reset_config(
            exit_still_active_check=10,
            still_active_check_interval=1,
            service_registry=True,
        )

        action_worker = actions_worker.get_worker()
        temp_file = None

        # Create a temporary file that is deleted when the file is closed and then set up an
        # action to wait for this file to be deleted. This allows this test to run the action
        # over a separate thread, run the shutdown sequence on the main thread, and then let
        # the local runner to exit gracefully and allow _run_action to finish execution.
        with tempfile.NamedTemporaryFile() as fp:
            temp_file = fp.name
            self.assertIsNotNone(temp_file)
            self.assertTrue(os.path.isfile(temp_file))

            # Launch the action execution in a separate thread.
            params = {"cmd": "while [ -e '%s' ]; do sleep 0.1; done" % temp_file}
            liveaction_db = self._get_liveaction_model(
                WorkerTestCase.local_action_db, params
            )
            liveaction_db = LiveAction.add_or_update(liveaction_db)
            executions.create_execution_object(liveaction_db)
            runner_thread = eventlet.spawn(action_worker._run_action, liveaction_db)

            # Wait for the worker up to 10s to add the liveaction to _running_liveactions.
            for i in range(0, int(10 / 0.1)):
                eventlet.sleep(0.1)
                if len(action_worker._running_liveactions) > 0:
                    break

            self.assertEqual(len(action_worker._running_liveactions), 1)

            # Shutdown the worker to trigger the abandon process.
            shutdown_thread = eventlet.spawn(action_worker.shutdown)
            # Wait for action runner shutdown sequence to complete
            eventlet.sleep(5)

        # Make sure the temporary file has been deleted.
        self.assertFalse(os.path.isfile(temp_file))

        # Wait for the worker up to 10s to remove the liveaction from _running_liveactions.
        for i in range(0, int(10 / 0.1)):
            eventlet.sleep(0.1)
            if len(action_worker._running_liveactions) < 1:
                break
        liveaction_db = LiveAction.get_by_id(liveaction_db.id)

        # Verify that _running_liveactions is empty and the liveaction is abandoned.
        self.assertEqual(len(action_worker._running_liveactions), 0)
        self.assertEqual(
            liveaction_db.status,
            action_constants.LIVEACTION_STATUS_ABANDONED,
            str(liveaction_db),
        )

        # Wait for the local runner to complete. This will activate the finally block in
        # _run_action but will not result in KeyError because the discard method is used to
        # to remove the liveaction from _running_liveactions.
        runner_thread.wait()
        shutdown_thread.kill()

    @mock.patch.object(
        RedisDriver,
        "get_members",
        mock.MagicMock(return_value=coordination.NoOpAsyncResult(("member-1",))),
    )
    def test_worker_graceful_shutdown_exit_timeout(self):
        self.reset_config(exit_still_active_check=5)

        action_worker = actions_worker.get_worker()
        temp_file = None

        # Create a temporary file that is deleted when the file is closed and then set up an
        # action to wait for this file to be deleted. This allows this test to run the action
        # over a separate thread, run the shutdown sequence on the main thread, and then let
        # the local runner to exit gracefully and allow _run_action to finish execution.
        with tempfile.NamedTemporaryFile() as fp:
            temp_file = fp.name
            self.assertIsNotNone(temp_file)
            self.assertTrue(os.path.isfile(temp_file))

            # Launch the action execution in a separate thread.
            params = {"cmd": "while [ -e '%s' ]; do sleep 0.1; done" % temp_file}
            liveaction_db = self._get_liveaction_model(
                WorkerTestCase.local_action_db, params
            )
            liveaction_db = LiveAction.add_or_update(liveaction_db)
            executions.create_execution_object(liveaction_db)
            runner_thread = eventlet.spawn(action_worker._run_action, liveaction_db)

            # Wait for the worker up to 10s to add the liveaction to _running_liveactions.
            for i in range(0, int(10 / 0.1)):
                eventlet.sleep(0.1)
                if len(action_worker._running_liveactions) > 0:
                    break

            self.assertEqual(len(action_worker._running_liveactions), 1)

            # Shutdown the worker to trigger the abandon process.
            shutdown_thread = eventlet.spawn(action_worker.shutdown)
            # Continue the excution for 5+ seconds to ensure timeout occurs.
            eventlet.sleep(6)

        # Make sure the temporary file has been deleted.
        self.assertFalse(os.path.isfile(temp_file))

        # Wait for the worker up to 10s to remove the liveaction from _running_liveactions.
        for i in range(0, int(10 / 0.1)):
            eventlet.sleep(0.1)
            if len(action_worker._running_liveactions) < 1:
                break
        liveaction_db = LiveAction.get_by_id(liveaction_db.id)

        # Verify that _running_liveactions is empty and the liveaction is abandoned.
        self.assertEqual(len(action_worker._running_liveactions), 0)
        self.assertEqual(
            liveaction_db.status,
            action_constants.LIVEACTION_STATUS_ABANDONED,
            str(liveaction_db),
        )

        # Wait for the local runner to complete. This will activate the finally block in
        # _run_action but will not result in KeyError because the discard method is used to
        # to remove the liveaction from _running_liveactions.
        runner_thread.wait()
        shutdown_thread.kill()

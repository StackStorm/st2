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

from oslo_config import cfg

# This import must be early for import-time side-effects.
from st2tests.base import DbTestCase

from st2common.constants import action as action_constants
from st2common.runners.base import get_runner
from st2common.exceptions.actionrunner import (
    ActionRunnerCreateError,
    ActionRunnerDispatchError,
)
from st2common.models.system.common import ResourceReference
from st2common.models.db.liveaction import LiveActionDB
from st2common.models.db.runner import RunnerTypeDB
from st2common.persistence.liveaction import LiveAction
from st2common.persistence.executionstate import ActionExecutionState
from st2common.runners.base import PollingAsyncActionRunner
from st2common.services import executions
from st2common.util import date as date_utils
from st2common.transport.publishers import PoolPublisher

from st2tests.fixtures.generic.fixture import PACK_NAME as FIXTURES_PACK
from st2tests.fixturesloader import FixturesLoader


# XXX: There is dependency on config being setup before importing
# RunnerContainer. Do not move this until you fix config
# dependencies.
from st2actions.container.base import get_runner_container

TEST_FIXTURES = {
    "runners": [
        "run-local.yaml",
        "testrunner1.yaml",
        "testfailingrunner1.yaml",
        "testasyncrunner1.yaml",
        "testasyncrunner2.yaml",
    ],
    "actions": [
        "local.yaml",
        "action1.yaml",
        "async_action1.yaml",
        "async_action2.yaml",
        "action-invalid-runner.yaml",
    ],
}

NON_UTF8_RESULT = {
    "stderr": "",
    "stdout": "\x82\n",
    "succeeded": True,
    "failed": False,
    "return_code": 0,
}

from st2tests.mocks.runners import runner
from st2tests.mocks.runners import polling_async_runner


@mock.patch(
    "st2common.runners.base.get_runner", mock.Mock(return_value=runner.get_runner())
)
@mock.patch(
    "st2actions.container.base.get_runner", mock.Mock(return_value=runner.get_runner())
)
@mock.patch.object(PoolPublisher, "publish", mock.MagicMock())
class RunnerContainerTest(DbTestCase):
    action_db = None
    async_action_db = None
    failingaction_db = None
    runnertype_db = None
    fixtures_loader = FixturesLoader()

    @classmethod
    def setUpClass(cls):
        super(RunnerContainerTest, cls).setUpClass()

        cfg.CONF.set_override(
            name="validate_output_schema", override=False, group="system"
        )

        models = RunnerContainerTest.fixtures_loader.save_fixtures_to_db(
            fixtures_pack=FIXTURES_PACK, fixtures_dict=TEST_FIXTURES
        )
        RunnerContainerTest.runnertype_db = models["runners"]["testrunner1.yaml"]
        RunnerContainerTest.action_db = models["actions"]["action1.yaml"]
        RunnerContainerTest.local_action_db = models["actions"]["local.yaml"]
        RunnerContainerTest.async_action_db = models["actions"]["async_action1.yaml"]
        RunnerContainerTest.polling_async_action_db = models["actions"][
            "async_action2.yaml"
        ]
        RunnerContainerTest.failingaction_db = models["actions"][
            "action-invalid-runner.yaml"
        ]

    @classmethod
    def tearDownClass(cls):
        RunnerContainerTest.fixtures_loader.delete_fixtures_from_db(
            fixtures_pack=FIXTURES_PACK, fixtures_dict=TEST_FIXTURES
        )
        super(RunnerContainerTest, cls).tearDownClass()

    def test_get_runner_module(self):
        runner = get_runner(name="local-shell-script")
        self.assertIsNotNone(runner, "TestRunner must be valid.")

    def test_pre_run_runner_is_disabled(self):
        runnertype_db = RunnerContainerTest.runnertype_db
        runner = get_runner(name="local-shell-cmd")

        runner.runner_type = runnertype_db
        runner.runner_type.enabled = False

        expected_msg = 'Runner "test-runner-1" has been disabled by the administrator'
        self.assertRaisesRegex(ValueError, expected_msg, runner.pre_run)

    def test_created_temporary_auth_token_is_correctly_scoped_to_user_who_ran_the_action(
        self,
    ):
        params = {
            "actionstr": "bar",
            "mock_status": action_constants.LIVEACTION_STATUS_SUCCEEDED,
        }

        global global_runner
        global_runner = None

        def mock_get_runner(*args, **kwargs):
            global global_runner
            runner = original_get_runner(*args, **kwargs)
            global_runner = runner
            return runner

        # user joe_1

        runner_container = get_runner_container()
        original_get_runner = runner_container._get_runner

        liveaction_db = self._get_failingaction_exec_db_model(params)
        liveaction_db = LiveAction.add_or_update(liveaction_db)
        liveaction_db.context = {"user": "user_joe_1"}
        executions.create_execution_object(liveaction_db)

        runner_container._get_runner = mock_get_runner

        self.assertEqual(getattr(global_runner, "auth_token", None), None)
        runner_container.dispatch(liveaction_db)
        self.assertEqual(global_runner.auth_token.user, "user_joe_1")
        self.assertEqual(
            global_runner.auth_token.metadata["service"], "actions_container"
        )

        runner_container._get_runner = original_get_runner

        # user mark_1
        global_runner = None
        runner_container = get_runner_container()
        original_get_runner = runner_container._get_runner

        liveaction_db = self._get_failingaction_exec_db_model(params)
        liveaction_db = LiveAction.add_or_update(liveaction_db)
        liveaction_db.context = {"user": "user_mark_2"}
        executions.create_execution_object(liveaction_db)
        original_get_runner = runner_container._get_runner

        runner_container._get_runner = mock_get_runner

        self.assertEqual(getattr(global_runner, "auth_token", None), None)
        runner_container.dispatch(liveaction_db)
        self.assertEqual(global_runner.auth_token.user, "user_mark_2")
        self.assertEqual(
            global_runner.auth_token.metadata["service"], "actions_container"
        )

    def test_post_run_is_always_called_after_run(self):
        # 1. post_run should be called on success, failure, etc.
        runner_container = get_runner_container()
        params = {
            "actionstr": "bar",
            "mock_status": action_constants.LIVEACTION_STATUS_SUCCEEDED,
        }
        liveaction_db = self._get_failingaction_exec_db_model(params)
        liveaction_db = LiveAction.add_or_update(liveaction_db)
        executions.create_execution_object(liveaction_db)

        global global_runner
        global_runner = None
        original_get_runner = runner_container._get_runner

        def mock_get_runner(*args, **kwargs):
            global global_runner
            runner = original_get_runner(*args, **kwargs)
            global_runner = runner
            return runner

        runner_container._get_runner = mock_get_runner

        # Note: We can't assert here that post_run hasn't been called yet because runner instance
        # is only instantiated later inside dispatch method
        runner_container.dispatch(liveaction_db)
        self.assertTrue(global_runner.post_run_called)

        # 2. Verify post_run is called if run() throws
        runner_container = get_runner_container()
        params = {"actionstr": "bar", "raise": True}
        liveaction_db = self._get_failingaction_exec_db_model(params)
        liveaction_db = LiveAction.add_or_update(liveaction_db)
        executions.create_execution_object(liveaction_db)

        global_runner = None
        original_get_runner = runner_container._get_runner

        def mock_get_runner(*args, **kwargs):
            global global_runner
            runner = original_get_runner(*args, **kwargs)
            global_runner = runner
            return runner

        runner_container._get_runner = mock_get_runner

        # Note: We can't assert here that post_run hasn't been called yet because runner instance
        # is only instantiated later inside dispatch method
        runner_container.dispatch(liveaction_db)
        self.assertTrue(global_runner.post_run_called)

        # 2. Verify post_run is also called if _delete_auth_token throws
        runner_container = get_runner_container()
        runner_container._delete_auth_token = mock.Mock(side_effect=ValueError("throw"))
        params = {
            "actionstr": "bar",
            "mock_status": action_constants.LIVEACTION_STATUS_SUCCEEDED,
        }
        liveaction_db = self._get_failingaction_exec_db_model(params)
        liveaction_db = LiveAction.add_or_update(liveaction_db)
        executions.create_execution_object(liveaction_db)

        global_runner = None
        original_get_runner = runner_container._get_runner

        def mock_get_runner(*args, **kwargs):
            global global_runner
            runner = original_get_runner(*args, **kwargs)
            global_runner = runner
            return runner

        runner_container._get_runner = mock_get_runner

        # Note: We can't assert here that post_run hasn't been called yet because runner instance
        # is only instantiated later inside dispatch method
        runner_container.dispatch(liveaction_db)
        self.assertTrue(global_runner.post_run_called)

    def test_get_runner_module_fail(self):
        runnertype_db = RunnerTypeDB(name="dummy", runner_module="absent.module")
        runner = None
        try:
            runner = get_runner(
                runnertype_db.runner_module, runnertype_db.runner_module
            )
        except ActionRunnerCreateError:
            pass
        self.assertFalse(runner, "TestRunner must be valid.")

    def test_dispatch(self):
        runner_container = get_runner_container()
        params = {"actionstr": "bar"}
        liveaction_db = self._get_liveaction_model(
            RunnerContainerTest.action_db, params
        )
        liveaction_db = LiveAction.add_or_update(liveaction_db)
        executions.create_execution_object(liveaction_db)
        # Assert that execution ran successfully.
        runner_container.dispatch(liveaction_db)
        liveaction_db = LiveAction.get_by_id(liveaction_db.id)
        result = liveaction_db.result
        self.assertTrue(result.get("action_params").get("actionint") == 10)
        self.assertTrue(result.get("action_params").get("actionstr") == "bar")

        # Assert that context is written correctly.
        context = {
            "user": cfg.CONF.system_user.user,
            "third_party_system": {"ref_id": "1234"},
        }

        self.assertDictEqual(liveaction_db.context, context)

    def test_dispatch_unsupported_status(self):
        runner_container = get_runner_container()
        params = {"actionstr": "bar"}
        liveaction_db = self._get_liveaction_model(
            RunnerContainerTest.action_db, params
        )
        liveaction_db = LiveAction.add_or_update(liveaction_db)
        executions.create_execution_object(liveaction_db)

        # Manually set the liveaction_db to some unsupported status.
        liveaction_db.status = action_constants.LIVEACTION_STATUS_CANCELED

        # Assert exception is raised on dispatch.
        self.assertRaises(
            ActionRunnerDispatchError, runner_container.dispatch, liveaction_db
        )

    def test_dispatch_runner_failure(self):
        runner_container = get_runner_container()
        params = {"actionstr": "bar"}
        liveaction_db = self._get_failingaction_exec_db_model(params)
        liveaction_db = LiveAction.add_or_update(liveaction_db)
        executions.create_execution_object(liveaction_db)
        runner_container.dispatch(liveaction_db)
        # pickup updated liveaction_db
        liveaction_db = LiveAction.get_by_id(liveaction_db.id)
        self.assertIn("error", liveaction_db.result)
        self.assertIn("traceback", liveaction_db.result)

    def test_dispatch_override_default_action_params(self):
        runner_container = get_runner_container()
        params = {"actionstr": "foo", "actionint": 20}
        liveaction_db = self._get_liveaction_model(
            RunnerContainerTest.action_db, params
        )
        liveaction_db = LiveAction.add_or_update(liveaction_db)
        executions.create_execution_object(liveaction_db)
        # Assert that execution ran successfully.
        runner_container.dispatch(liveaction_db)
        liveaction_db = LiveAction.get_by_id(liveaction_db.id)
        result = liveaction_db.result
        self.assertTrue(result.get("action_params").get("actionint") == 20)
        self.assertTrue(result.get("action_params").get("actionstr") == "foo")

    def test_state_db_created_for_polling_async_actions(self):
        runner_container = get_runner_container()

        params = {"actionstr": "foo", "actionint": 20, "async_test": True}

        liveaction_db = self._get_liveaction_model(
            RunnerContainerTest.polling_async_action_db, params
        )

        liveaction_db = LiveAction.add_or_update(liveaction_db)
        executions.create_execution_object(liveaction_db)

        # Assert that execution ran without exceptions.
        with mock.patch(
            "st2actions.container.base.get_runner",
            mock.Mock(return_value=polling_async_runner.get_runner()),
        ):
            runner_container.dispatch(liveaction_db)
        states = ActionExecutionState.get_all()
        found = [state for state in states if state.execution_id == liveaction_db.id]

        self.assertTrue(len(found) > 0, "There should be a state db object.")
        self.assertTrue(len(found) == 1, "There should only be one state db object.")
        self.assertIsNotNone(found[0].query_context)
        self.assertIsNotNone(found[0].query_module)

    @mock.patch.object(
        PollingAsyncActionRunner,
        "is_polling_enabled",
        mock.MagicMock(return_value=False),
    )
    def test_state_db_not_created_for_disabled_polling_async_actions(self):
        runner_container = get_runner_container()

        params = {"actionstr": "foo", "actionint": 20, "async_test": True}

        liveaction_db = self._get_liveaction_model(
            RunnerContainerTest.polling_async_action_db, params
        )

        liveaction_db = LiveAction.add_or_update(liveaction_db)
        executions.create_execution_object(liveaction_db)

        # Assert that execution ran without exceptions.
        runner_container.dispatch(liveaction_db)
        states = ActionExecutionState.get_all()
        found = [state for state in states if state.execution_id == liveaction_db.id]

        self.assertTrue(len(found) == 0, "There should not be a state db object.")

    def test_state_db_not_created_for_async_actions(self):
        runner_container = get_runner_container()

        params = {"actionstr": "foo", "actionint": 20, "async_test": True}

        liveaction_db = self._get_liveaction_model(
            RunnerContainerTest.async_action_db, params
        )

        liveaction_db = LiveAction.add_or_update(liveaction_db)
        executions.create_execution_object(liveaction_db)

        # Assert that execution ran without exceptions.
        runner_container.dispatch(liveaction_db)
        states = ActionExecutionState.get_all()
        found = [state for state in states if state.execution_id == liveaction_db.id]

        self.assertTrue(len(found) == 0, "There should not be a state db object.")

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

    def _get_failingaction_exec_db_model(self, params):
        status = action_constants.LIVEACTION_STATUS_REQUESTED
        start_timestamp = date_utils.get_datetime_utc_now()
        action_ref = ResourceReference(
            name=RunnerContainerTest.failingaction_db.name,
            pack=RunnerContainerTest.failingaction_db.pack,
        ).ref
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

    def _get_output_schema_exec_db_model(self, params):
        status = action_constants.LIVEACTION_STATUS_REQUESTED
        start_timestamp = date_utils.get_datetime_utc_now()
        action_ref = ResourceReference(
            name=RunnerContainerTest.schema_output_action_db.name,
            pack=RunnerContainerTest.schema_output_action_db.pack,
        ).ref
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

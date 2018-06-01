# Licensed to the StackStorm, Inc ('StackStorm') under one or more
# contributor license agreements.  See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.
# The ASF licenses this file to You under the Apache License, Version 2.0
# (the "License"); you may not use this file except in compliance with
# the License.  You may obtain a copy of the License at
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

from bson.errors import InvalidStringData
from oslo_config import cfg

from st2common.constants import action as action_constants
from st2common.runners.base import get_runner
from st2common.exceptions.actionrunner import ActionRunnerCreateError, ActionRunnerDispatchError
from st2common.models.system.common import ResourceReference
from st2common.models.db.liveaction import LiveActionDB
from st2common.models.db.runner import RunnerTypeDB
from st2common.persistence.liveaction import LiveAction
from st2common.persistence.executionstate import ActionExecutionState
from st2common.runners.base import PollingAsyncActionRunner
from st2common.services import executions
from st2common.util import date as date_utils
from st2common.transport.publishers import PoolPublisher

from local_runner import local_shell_command_runner
from local_runner.local_shell_command_runner import LocalShellCommandRunner

from st2tests.base import DbTestCase
import st2tests.config as tests_config
tests_config.parse_args()
from st2tests.fixturesloader import FixturesLoader


# XXX: There is dependency on config being setup before importing
# RunnerContainer. Do not move this until you fix config
# dependencies.
from st2actions.container.base import get_runner_container

TEST_FIXTURES = {
    'runners': [
        'run-local.yaml',
        'testrunner1.yaml',
        'testfailingrunner1.yaml',
        'testasyncrunner1.yaml',
        'testasyncrunner2.yaml'
    ],
    'actions': [
        'local.yaml',
        'action1.yaml',
        'async_action1.yaml',
        'async_action2.yaml',
        'action-invalid-runner.yaml'
    ]
}

FIXTURES_PACK = 'generic'

NON_UTF8_RESULT = {
    'stderr': '',
    'stdout': '\x82\n',
    'succeeded': True,
    'failed': False,
    'return_code': 0
}


@mock.patch.object(PoolPublisher, 'publish', mock.MagicMock())
class RunnerContainerTest(DbTestCase):
    action_db = None
    async_action_db = None
    failingaction_db = None
    runnertype_db = None
    fixtures_loader = FixturesLoader()

    @classmethod
    def setUpClass(cls):
        super(RunnerContainerTest, cls).setUpClass()
        models = RunnerContainerTest.fixtures_loader.save_fixtures_to_db(
            fixtures_pack=FIXTURES_PACK, fixtures_dict=TEST_FIXTURES)
        RunnerContainerTest.runnertype_db = models['runners']['testrunner1.yaml']
        RunnerContainerTest.action_db = models['actions']['action1.yaml']
        RunnerContainerTest.local_action_db = models['actions']['local.yaml']
        RunnerContainerTest.async_action_db = models['actions']['async_action1.yaml']
        RunnerContainerTest.polling_async_action_db = models['actions']['async_action2.yaml']
        RunnerContainerTest.failingaction_db = models['actions']['action-invalid-runner.yaml']

    @classmethod
    def tearDownClass(cls):
        RunnerContainerTest.fixtures_loader.delete_fixtures_from_db(
            fixtures_pack=FIXTURES_PACK, fixtures_dict=TEST_FIXTURES)
        super(RunnerContainerTest, cls).tearDownClass()

    def test_get_runner_module(self):
        runnertype_db = RunnerContainerTest.runnertype_db
        runner = get_runner(runnertype_db.runner_module, runnertype_db.runner_module)
        self.assertTrue(runner is not None, 'TestRunner must be valid.')

    def test_pre_run_runner_is_disabled(self):
        runnertype_db = RunnerContainerTest.runnertype_db
        runner = get_runner(runnertype_db.runner_module, runnertype_db.runner_module)

        runner.runner_type = runnertype_db
        runner.runner_type.enabled = False

        expected_msg = 'Runner "test-runner-1" has been disabled by the administrator'
        self.assertRaisesRegexp(ValueError, expected_msg, runner.pre_run)

    def test_created_temporary_auth_token_is_correctly_scoped_to_user_who_ran_the_action(self):
        params = {
            'actionstr': 'bar',
            'mock_status': action_constants.LIVEACTION_STATUS_SUCCEEDED
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
        liveaction_db.context = {'user': 'user_joe_1'}
        executions.create_execution_object(liveaction_db)

        runner_container._get_runner = mock_get_runner

        self.assertEqual(getattr(global_runner, 'auth_token', None), None)
        runner_container.dispatch(liveaction_db)
        self.assertEqual(global_runner.auth_token.user, 'user_joe_1')
        self.assertEqual(global_runner.auth_token.metadata['service'], 'actions_container')

        runner_container._get_runner = original_get_runner

        # user mark_1
        global_runner = None
        runner_container = get_runner_container()
        original_get_runner = runner_container._get_runner

        liveaction_db = self._get_failingaction_exec_db_model(params)
        liveaction_db = LiveAction.add_or_update(liveaction_db)
        liveaction_db.context = {'user': 'user_mark_2'}
        executions.create_execution_object(liveaction_db)
        original_get_runner = runner_container._get_runner

        runner_container._get_runner = mock_get_runner

        self.assertEqual(getattr(global_runner, 'auth_token', None), None)
        runner_container.dispatch(liveaction_db)
        self.assertEqual(global_runner.auth_token.user, 'user_mark_2')
        self.assertEqual(global_runner.auth_token.metadata['service'], 'actions_container')

    def test_post_run_is_always_called_after_run(self):
        # 1. post_run should be called on success, failure, etc.
        runner_container = get_runner_container()
        params = {
            'actionstr': 'bar',
            'mock_status': action_constants.LIVEACTION_STATUS_SUCCEEDED
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
        params = {
            'actionstr': 'bar',
            'raise': True
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

        # 2. Verify post_run is also called if _delete_auth_token throws
        runner_container = get_runner_container()
        runner_container._delete_auth_token = mock.Mock(side_effect=ValueError('throw'))
        params = {
            'actionstr': 'bar',
            'mock_status': action_constants.LIVEACTION_STATUS_SUCCEEDED
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
        runnertype_db = RunnerTypeDB(name='dummy', runner_module='absent.module')
        runner = None
        try:
            runner = get_runner(runnertype_db.runner_module, runnertype_db.runner_module)
        except ActionRunnerCreateError:
            pass
        self.assertFalse(runner, 'TestRunner must be valid.')

    def test_dispatch(self):
        runner_container = get_runner_container()
        params = {
            'actionstr': 'bar'
        }
        liveaction_db = self._get_liveaction_model(RunnerContainerTest.action_db, params)
        liveaction_db = LiveAction.add_or_update(liveaction_db)
        executions.create_execution_object(liveaction_db)
        # Assert that execution ran successfully.
        runner_container.dispatch(liveaction_db)
        liveaction_db = LiveAction.get_by_id(liveaction_db.id)
        result = liveaction_db.result
        self.assertTrue(result.get('action_params').get('actionint') == 10)
        self.assertTrue(result.get('action_params').get('actionstr') == 'bar')

        # Assert that context is written correctly.
        context = {
            'user': 'stanley',
            'third_party_system': {
                'ref_id': '1234'
            }
        }

        self.assertDictEqual(liveaction_db.context, context)

    def test_dispatch_unsupported_status(self):
        runner_container = get_runner_container()
        params = {'actionstr': 'bar'}
        liveaction_db = self._get_liveaction_model(RunnerContainerTest.action_db, params)
        liveaction_db = LiveAction.add_or_update(liveaction_db)
        executions.create_execution_object(liveaction_db)

        # Manually set the liveaction_db to some unsupported status.
        liveaction_db.status = action_constants.LIVEACTION_STATUS_CANCELED

        # Assert exception is raised on dispatch.
        self.assertRaises(
            ActionRunnerDispatchError,
            runner_container.dispatch,
            liveaction_db
        )

    @mock.patch.object(LocalShellCommandRunner, 'run', mock.MagicMock(
        return_value=(action_constants.LIVEACTION_STATUS_SUCCEEDED, NON_UTF8_RESULT, None)))
    @mock.patch('st2common.runners.base.register_runner',
                mock.MagicMock(return_value=local_shell_command_runner))
    def test_dispatch_non_utf8_result(self):
        runner_container = get_runner_container()
        params = {
            'cmd': "python -c 'print \"\\x82\"'"
        }
        liveaction_db = self._get_liveaction_model(RunnerContainerTest.local_action_db, params)
        liveaction_db = LiveAction.add_or_update(liveaction_db)
        executions.create_execution_object(liveaction_db)

        try:
            runner_container.dispatch(liveaction_db)
            self.fail('Mongo won\'t handle non UTF-8 strings. Should have failed.')
        except InvalidStringData:
            pass

    def test_dispatch_runner_failure(self):
        runner_container = get_runner_container()
        params = {
            'actionstr': 'bar'
        }
        liveaction_db = self._get_failingaction_exec_db_model(params)
        liveaction_db = LiveAction.add_or_update(liveaction_db)
        executions.create_execution_object(liveaction_db)
        runner_container.dispatch(liveaction_db)
        # pickup updated liveaction_db
        liveaction_db = LiveAction.get_by_id(liveaction_db.id)
        self.assertTrue('error' in liveaction_db.result)
        self.assertTrue('traceback' in liveaction_db.result)

    def test_dispatch_override_default_action_params(self):
        runner_container = get_runner_container()
        params = {
            'actionstr': 'foo',
            'actionint': 20
        }
        liveaction_db = self._get_liveaction_model(RunnerContainerTest.action_db, params)
        liveaction_db = LiveAction.add_or_update(liveaction_db)
        executions.create_execution_object(liveaction_db)
        # Assert that execution ran successfully.
        runner_container.dispatch(liveaction_db)
        liveaction_db = LiveAction.get_by_id(liveaction_db.id)
        result = liveaction_db.result
        self.assertTrue(result.get('action_params').get('actionint') == 20)
        self.assertTrue(result.get('action_params').get('actionstr') == 'foo')

    def test_state_db_created_for_polling_async_actions(self):
        runner_container = get_runner_container()

        params = {
            'actionstr': 'foo',
            'actionint': 20,
            'async_test': True
        }

        liveaction_db = self._get_liveaction_model(
            RunnerContainerTest.polling_async_action_db,
            params
        )

        liveaction_db = LiveAction.add_or_update(liveaction_db)
        executions.create_execution_object(liveaction_db)

        # Assert that execution ran without exceptions.
        runner_container.dispatch(liveaction_db)
        states = ActionExecutionState.get_all()
        found = [state for state in states if state.execution_id == liveaction_db.id]

        self.assertTrue(len(found) > 0, 'There should be a state db object.')
        self.assertTrue(len(found) == 1, 'There should only be one state db object.')
        self.assertTrue(found[0].query_context is not None)
        self.assertTrue(found[0].query_module is not None)

    @mock.patch.object(
        PollingAsyncActionRunner,
        'is_polling_enabled',
        mock.MagicMock(return_value=False))
    def test_state_db_not_created_for_disabled_polling_async_actions(self):
        runner_container = get_runner_container()

        params = {
            'actionstr': 'foo',
            'actionint': 20,
            'async_test': True
        }

        liveaction_db = self._get_liveaction_model(
            RunnerContainerTest.polling_async_action_db,
            params
        )

        liveaction_db = LiveAction.add_or_update(liveaction_db)
        executions.create_execution_object(liveaction_db)

        # Assert that execution ran without exceptions.
        runner_container.dispatch(liveaction_db)
        states = ActionExecutionState.get_all()
        found = [state for state in states if state.execution_id == liveaction_db.id]

        self.assertTrue(len(found) == 0, 'There should not be a state db object.')

    def test_state_db_not_created_for_async_actions(self):
        runner_container = get_runner_container()

        params = {
            'actionstr': 'foo',
            'actionint': 20,
            'async_test': True
        }

        liveaction_db = self._get_liveaction_model(
            RunnerContainerTest.async_action_db,
            params
        )

        liveaction_db = LiveAction.add_or_update(liveaction_db)
        executions.create_execution_object(liveaction_db)

        # Assert that execution ran without exceptions.
        runner_container.dispatch(liveaction_db)
        states = ActionExecutionState.get_all()
        found = [state for state in states if state.execution_id == liveaction_db.id]

        self.assertTrue(len(found) == 0, 'There should not be a state db object.')

    def _get_liveaction_model(self, action_db, params):
        status = action_constants.LIVEACTION_STATUS_REQUESTED
        start_timestamp = date_utils.get_datetime_utc_now()
        action_ref = ResourceReference(name=action_db.name, pack=action_db.pack).ref
        parameters = params
        context = {'user': cfg.CONF.system_user.user}
        liveaction_db = LiveActionDB(status=status, start_timestamp=start_timestamp,
                                     action=action_ref, parameters=parameters,
                                     context=context)
        return liveaction_db

    def _get_failingaction_exec_db_model(self, params):
        status = action_constants.LIVEACTION_STATUS_REQUESTED
        start_timestamp = date_utils.get_datetime_utc_now()
        action_ref = ResourceReference(
            name=RunnerContainerTest.failingaction_db.name,
            pack=RunnerContainerTest.failingaction_db.pack).ref
        parameters = params
        context = {'user': cfg.CONF.system_user.user}
        liveaction_db = LiveActionDB(status=status, start_timestamp=start_timestamp,
                                     action=action_ref, parameters=parameters,
                                     context=context)
        return liveaction_db

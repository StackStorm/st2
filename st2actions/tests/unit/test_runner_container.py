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

import datetime
import mock

from oslo.config import cfg
from st2actions.runners import get_runner
from st2common.exceptions.actionrunner import ActionRunnerCreateError
from st2common.models.system.common import ResourceReference
from st2common.models.db.action import (ActionExecutionDB, RunnerTypeDB)
from st2common.persistence.action import (ActionExecution, ActionExecutionState)
from st2common.transport.publishers import PoolPublisher
from st2tests.base import DbTestCase
import st2tests.config as tests_config
tests_config.parse_args()
from st2tests.fixturesloader import FixturesLoader


# XXX: There is dependency on config being setup before importing
# RunnerContainer. Do not move this until you fix config
# dependencies.
from st2actions.container.base import get_runner_container

TEST_FIXTURES = {
    'runners': ['testrunner1.json', 'testfailingrunner1.json', 'testasyncrunner1.json'],
    'actions': ['action1.json', 'async_action1.json', 'action-invalid-runner.json']
}

FIXTURES_PACK = 'generic'


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
        RunnerContainerTest.runnertype_db = models['runners']['testrunner1.json']
        RunnerContainerTest.action_db = models['actions']['action1.json']
        RunnerContainerTest.async_action_db = models['actions']['async_action1.json']
        RunnerContainerTest.failingaction_db = models['actions']['action-invalid-runner.json']

    def test_get_runner_module(self):
        runnertype_db = RunnerContainerTest.runnertype_db
        runner = get_runner(runnertype_db.runner_module)
        self.assertTrue(runner is not None, 'TestRunner must be valid.')

    def test_get_runner_module_fail(self):
        runnertype_db = RunnerTypeDB()
        runnertype_db.runner_module = 'absent.module'
        runner = None
        try:
            runner = get_runner(runnertype_db.runner_module)
        except ActionRunnerCreateError:
            pass
        self.assertFalse(runner, 'TestRunner must be valid.')

    def test_dispatch(self):
        runner_container = get_runner_container()
        params = {
            'actionstr': 'bar'
        }
        actionexec_db = self._get_action_exec_db_model(RunnerContainerTest.action_db, params)
        actionexec_db = ActionExecution.add_or_update(actionexec_db)
        # Assert that execution ran successfully.
        runner_container.dispatch(actionexec_db)
        actionexec_db = ActionExecution.get_by_id(actionexec_db.id)
        result = actionexec_db.result
        self.assertTrue(result.get('action_params').get('actionint') == 10)
        self.assertTrue(result.get('action_params').get('actionstr') == 'bar')

    def test_dispatch_runner_failure(self):
        runner_container = get_runner_container()
        params = {
            'actionstr': 'bar'
        }
        actionexec_db = self._get_failingaction_exec_db_model(params)
        actionexec_db = ActionExecution.add_or_update(actionexec_db)
        runner_container.dispatch(actionexec_db)
        # pickup updated actionexec_db
        actionexec_db = ActionExecution.get_by_id(actionexec_db.id)
        self.assertTrue('message' in actionexec_db.result)
        self.assertTrue('traceback' in actionexec_db.result)

    def test_dispatch_override_default_action_params(self):
        runner_container = get_runner_container()
        params = {
            'actionstr': 'foo',
            'actionint': 20
        }
        actionexec_db = self._get_action_exec_db_model(RunnerContainerTest.action_db, params)
        actionexec_db = ActionExecution.add_or_update(actionexec_db)

        # Assert that execution ran successfully.
        runner_container.dispatch(actionexec_db)
        actionexec_db = ActionExecution.get_by_id(actionexec_db.id)
        result = actionexec_db.result
        self.assertTrue(result.get('action_params').get('actionint') == 20)
        self.assertTrue(result.get('action_params').get('actionstr') == 'foo')

    def test_state_db_creation_async_actions(self):
        runner_container = get_runner_container()
        params = {
            'actionstr': 'foo',
            'actionint': 20,
            'async_test': True
        }
        actionexec_db = self._get_action_exec_db_model(RunnerContainerTest.async_action_db, params)
        actionexec_db = ActionExecution.add_or_update(actionexec_db)

        # Assert that execution ran without exceptions.
        runner_container.dispatch(actionexec_db)
        states = ActionExecutionState.get_all()

        found = None
        for state in states:
            if state.execution_id == actionexec_db.id:
                found = state
        self.assertTrue(found is not None, 'There should be a state db object.')
        self.assertTrue(found.query_context is not None)
        self.assertTrue(found.query_module is not None)

    def _get_action_exec_db_model(self, action_db, params):
        actionexec_db = ActionExecutionDB()
        actionexec_db.status = 'initializing'
        actionexec_db.start_timestamp = datetime.datetime.utcnow()
        actionexec_db.action = ResourceReference(
            name=action_db.name,
            pack=action_db.pack).ref
        actionexec_db.parameters = params
        actionexec_db.context = {'user': cfg.CONF.system_user.user}
        return actionexec_db

    def _get_failingaction_exec_db_model(self, params):
        actionexec_db = ActionExecutionDB()
        actionexec_db.status = 'initializing'
        actionexec_db.start_timestamp = datetime.datetime.now()
        actionexec_db.action = ResourceReference(
            name=RunnerContainerTest.failingaction_db.name,
            pack=RunnerContainerTest.failingaction_db.pack).ref
        actionexec_db.parameters = params
        actionexec_db.context = {'user': cfg.CONF.system_user.user}
        return actionexec_db

    @classmethod
    def tearDownClass(cls):
        RunnerContainerTest.fixtures_loader.delete_fixtures_from_db(
            fixtures_pack=FIXTURES_PACK, fixtures_dict=TEST_FIXTURES)
        super(RunnerContainerTest, cls).tearDownClass()

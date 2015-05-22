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
from st2common.constants import action as action_constants
from st2actions.runners import get_runner
from st2common.exceptions.actionrunner import ActionRunnerCreateError
from st2common.models.system.common import ResourceReference
from st2common.models.db.action import (LiveActionDB, RunnerTypeDB)
from st2common.persistence.liveaction import LiveAction
from st2common.persistence.executionstate import ActionExecutionState
from st2common.services import executions
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
    'runners': ['testrunner1.yaml', 'testfailingrunner1.yaml', 'testasyncrunner1.yaml'],
    'actions': ['action1.yaml', 'async_action1.yaml', 'action-invalid-runner.yaml']
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
        RunnerContainerTest.runnertype_db = models['runners']['testrunner1.yaml']
        RunnerContainerTest.action_db = models['actions']['action1.yaml']
        RunnerContainerTest.async_action_db = models['actions']['async_action1.yaml']
        RunnerContainerTest.failingaction_db = models['actions']['action-invalid-runner.yaml']

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
        liveaction_db = self._get_action_exec_db_model(RunnerContainerTest.action_db, params)
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
        self.assertTrue('message' in liveaction_db.result)
        self.assertTrue('traceback' in liveaction_db.result)

    def test_dispatch_override_default_action_params(self):
        runner_container = get_runner_container()
        params = {
            'actionstr': 'foo',
            'actionint': 20
        }
        liveaction_db = self._get_action_exec_db_model(RunnerContainerTest.action_db, params)
        liveaction_db = LiveAction.add_or_update(liveaction_db)
        executions.create_execution_object(liveaction_db)
        # Assert that execution ran successfully.
        runner_container.dispatch(liveaction_db)
        liveaction_db = LiveAction.get_by_id(liveaction_db.id)
        result = liveaction_db.result
        self.assertTrue(result.get('action_params').get('actionint') == 20)
        self.assertTrue(result.get('action_params').get('actionstr') == 'foo')

    def test_state_db_creation_async_actions(self):
        runner_container = get_runner_container()
        params = {
            'actionstr': 'foo',
            'actionint': 20,
            'async_test': True
        }
        liveaction_db = self._get_action_exec_db_model(RunnerContainerTest.async_action_db, params)
        liveaction_db = LiveAction.add_or_update(liveaction_db)
        executions.create_execution_object(liveaction_db)
        # Assert that execution ran without exceptions.
        runner_container.dispatch(liveaction_db)
        states = ActionExecutionState.get_all()

        found = None
        for state in states:
            if state.execution_id == liveaction_db.id:
                found = state
        self.assertTrue(found is not None, 'There should be a state db object.')
        self.assertTrue(found.query_context is not None)
        self.assertTrue(found.query_module is not None)

    def _get_action_exec_db_model(self, action_db, params):
        liveaction_db = LiveActionDB()
        liveaction_db.status = action_constants.LIVEACTION_STATUS_REQUESTED
        liveaction_db.start_timestamp = datetime.datetime.utcnow()
        liveaction_db.action = ResourceReference(
            name=action_db.name,
            pack=action_db.pack).ref
        liveaction_db.parameters = params
        liveaction_db.context = {'user': cfg.CONF.system_user.user}
        return liveaction_db

    def _get_failingaction_exec_db_model(self, params):
        liveaction_db = LiveActionDB()
        liveaction_db.status = action_constants.LIVEACTION_STATUS_REQUESTED
        liveaction_db.start_timestamp = datetime.datetime.now()
        liveaction_db.action = ResourceReference(
            name=RunnerContainerTest.failingaction_db.name,
            pack=RunnerContainerTest.failingaction_db.pack).ref
        liveaction_db.parameters = params
        liveaction_db.context = {'user': cfg.CONF.system_user.user}
        return liveaction_db

    @classmethod
    def tearDownClass(cls):
        RunnerContainerTest.fixtures_loader.delete_fixtures_from_db(
            fixtures_pack=FIXTURES_PACK, fixtures_dict=TEST_FIXTURES)
        super(RunnerContainerTest, cls).tearDownClass()

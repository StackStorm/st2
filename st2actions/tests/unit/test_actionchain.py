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

import mock
import six

from unittest2 import TestCase

from st2actions.runners import actionchainrunner as acr
from st2actions.container.service import RunnerContainerService
from st2common.exceptions import actionrunner as runnerexceptions
from st2common.constants.action import ACTIONEXEC_STATUS_RUNNING
from st2common.constants.action import ACTIONEXEC_STATUS_SUCCEEDED
from st2common.constants.action import ACTIONEXEC_STATUS_FAILED
from st2common.models.db.datastore import KeyValuePairDB
from st2common.persistence.datastore import KeyValuePair
from st2common.services import action as action_service
from st2common.util import action_db as action_db_util
from st2tests import DbTestCase
import st2tests.config as tests_config
from st2tests.fixturesloader import FixturesLoader


class DummyActionExecution(object):
    def __init__(self, status=ACTIONEXEC_STATUS_SUCCEEDED, result=''):
        self.id = None
        self.status = status
        self.result = result


FIXTURES_PACK = 'generic'

TEST_FIXTURES = {
    'actionchains': ['chain1.json']
}

TEST_MODELS = {
    'actions': ['a1.json', 'a2.json'],
    'runners': ['testrunner1.json']
}

FIXTURES = FixturesLoader().load_fixtures(fixtures_pack=FIXTURES_PACK,
                                          fixtures_dict=TEST_FIXTURES)
CHAIN_1 = FIXTURES['actionchains']['chain1.json']

MODELS = FixturesLoader().load_models(fixtures_pack=FIXTURES_PACK,
                                      fixtures_dict=TEST_MODELS)
ACTION_1 = MODELS['actions']['a1.json']
ACTION_2 = MODELS['actions']['a2.json']
RUNNER = MODELS['runners']['testrunner1.json']

CHAIN_1_PATH = FixturesLoader().get_fixture_file_path_abs(
    FIXTURES_PACK, 'actionchains', 'chain1.json')
CHAIN_STR_TEMP_PATH = FixturesLoader().get_fixture_file_path_abs(
    FIXTURES_PACK, 'actionchains', 'chain_str_template.json')
CHAIN_LIST_TEMP_PATH = FixturesLoader().get_fixture_file_path_abs(
    FIXTURES_PACK, 'actionchains', 'chain_list_template.json')
CHAIN_DICT_TEMP_PATH = FixturesLoader().get_fixture_file_path_abs(
    FIXTURES_PACK, 'actionchains', 'chain_dict_template.json')
CHAIN_DEP_INPUT = FixturesLoader().get_fixture_file_path_abs(
    FIXTURES_PACK, 'actionchains', 'chain_dependent_input.json')
CHAIN_DEP_RESULTS_INPUT = FixturesLoader().get_fixture_file_path_abs(
    FIXTURES_PACK, 'actionchains', 'chain_dep_result_input.json')
MALFORMED_CHAIN_PATH = FixturesLoader().get_fixture_file_path_abs(
    FIXTURES_PACK, 'actionchains', 'malformedchain.json')
CHAIN_TYPED_PARAMS = FixturesLoader().get_fixture_file_path_abs(
    FIXTURES_PACK, 'actionchains', 'chain_typed_params.json')
CHAIN_SYSTEM_PARAMS = FixturesLoader().get_fixture_file_path_abs(
    FIXTURES_PACK, 'actionchains', 'chain_typed_system_params.json')

CHAIN_EMPTY = {}


class TestActionChain(TestCase):

    @classmethod
    def setUpClass(cls):
        tests_config.parse_args()

    def test_chain_creation_basic(self):
        action_chain = acr.ActionChain(CHAIN_1)

        expected_node_count = 0
        expected_link_count = 0
        for node in CHAIN_1['chain']:
            expected_node_count += 1
            if 'on-success' in node:
                expected_link_count += 1
            if 'on-failure' in node:
                expected_link_count += 1

        self.assertEqual(len(action_chain.nodes), expected_node_count)

        link_count = 0
        for _, links in six.iteritems(action_chain.links):
            link_count += len(links)
        self.assertEqual(link_count, expected_link_count)

        self.assertEqual(action_chain.default, CHAIN_1['default'])

    def test_chain_iteration(self):
        action_chain = acr.ActionChain(CHAIN_1)

        for node in CHAIN_1['chain']:
            if 'on-success' in node:
                next_node = action_chain.get_next_node(node['name'], 'on-success')
                self.assertEqual(next_node.name, node['on-success'])
            if 'on-failure' in node:
                next_node = action_chain.get_next_node(node['name'], 'on-failure')
                self.assertEqual(next_node.name, node['on-failure'])

        default = action_chain.get_next_node()
        self.assertEqual(type(default), acr.ActionChain.Node)
        self.assertEqual(default.name, CHAIN_1['default'])

    def test_empty_chain(self):
        action_chain = acr.ActionChain(CHAIN_EMPTY)
        self.assertEqual(len(action_chain.nodes), 0)
        self.assertEqual(len(action_chain.links), 0)
        self.assertEqual(action_chain.default, '')


@mock.patch.object(action_db_util, 'get_runnertype_by_name',
                   mock.MagicMock(return_value=RUNNER))
class TestActionChainRunner(DbTestCase):

    def test_runner_creation(self):
        runner = acr.get_runner()
        self.assertTrue(runner)
        self.assertTrue(runner.runner_id)

    def test_malformed_chain(self):
        try:
            chain_runner = acr.get_runner()
            chain_runner.entry_point = MALFORMED_CHAIN_PATH
            chain_runner.action = ACTION_1
            chain_runner.container_service = RunnerContainerService()
            chain_runner.pre_run()
            self.assertTrue(False, 'Expected pre_run to fail.')
        except runnerexceptions.ActionRunnerPreRunError:
            self.assertTrue(True)

    @mock.patch.object(action_db_util, 'get_action_by_ref',
                       mock.MagicMock(return_value=ACTION_1))
    @mock.patch.object(action_service, 'schedule', return_value=DummyActionExecution())
    def test_chain_runner_success_path(self, schedule):
        chain_runner = acr.get_runner()
        chain_runner.entry_point = CHAIN_1_PATH
        chain_runner.action = ACTION_1
        chain_runner.container_service = RunnerContainerService()
        chain_runner.pre_run()
        chain_runner.run({})
        self.assertNotEqual(chain_runner.action_chain, None)
        # based on the chain the callcount is known to be 3. Not great but works.
        self.assertEqual(schedule.call_count, 3)

    @mock.patch('eventlet.sleep', mock.MagicMock())
    @mock.patch.object(action_db_util, 'get_actionexec_by_id', mock.MagicMock(
        return_value=DummyActionExecution()))
    @mock.patch.object(action_db_util, 'get_action_by_ref',
                       mock.MagicMock(return_value=ACTION_1))
    @mock.patch.object(action_service, 'schedule',
                       return_value=DummyActionExecution(status=ACTIONEXEC_STATUS_RUNNING))
    def test_chain_runner_success_path_with_wait(self, schedule):
        chain_runner = acr.get_runner()
        chain_runner.entry_point = CHAIN_1_PATH
        chain_runner.action = ACTION_1
        chain_runner.container_service = RunnerContainerService()
        chain_runner.pre_run()
        chain_runner.run({})
        self.assertNotEqual(chain_runner.action_chain, None)
        # based on the chain the callcount is known to be 3. Not great but works.
        self.assertEqual(schedule.call_count, 3)

    @mock.patch.object(action_db_util, 'get_action_by_ref',
                       mock.MagicMock(return_value=ACTION_1))
    @mock.patch.object(action_service, 'schedule',
                       return_value=DummyActionExecution(status=ACTIONEXEC_STATUS_FAILED))
    def test_chain_runner_failure_path(self, schedule):
        chain_runner = acr.get_runner()
        chain_runner.entry_point = CHAIN_1_PATH
        chain_runner.action = ACTION_1
        chain_runner.container_service = RunnerContainerService()
        chain_runner.pre_run()
        status, _ = chain_runner.run({})
        self.assertEqual(status, ACTIONEXEC_STATUS_FAILED)
        self.assertNotEqual(chain_runner.action_chain, None)
        # based on the chain the callcount is known to be 2. Not great but works.
        self.assertEqual(schedule.call_count, 2)

    @mock.patch.object(action_db_util, 'get_action_by_ref',
                       mock.MagicMock(return_value=ACTION_1))
    @mock.patch.object(action_service, 'schedule', side_effect=RuntimeError('Test Failure.'))
    def test_chain_runner_action_exception(self, schedule):
        chain_runner = acr.get_runner()
        chain_runner.entry_point = CHAIN_1_PATH
        chain_runner.action = ACTION_1
        chain_runner.container_service = RunnerContainerService()
        chain_runner.pre_run()
        status, results = chain_runner.run({})
        self.assertEqual(status, ACTIONEXEC_STATUS_FAILED)
        self.assertNotEqual(chain_runner.action_chain, None)
        # based on the chain the callcount is known to be 2. Not great but works.
        self.assertEqual(schedule.call_count, 2)
        self.assertEqual(len([result['error'] for _, result in six.iteritems(results)]),
                         2, 'Expected errors')

    @mock.patch.object(action_db_util, 'get_action_by_ref',
                       mock.MagicMock(return_value=ACTION_1))
    @mock.patch.object(action_service, 'schedule', return_value=DummyActionExecution())
    def test_chain_runner_str_param_temp(self, schedule):
        chain_runner = acr.get_runner()
        chain_runner.entry_point = CHAIN_STR_TEMP_PATH
        chain_runner.action = ACTION_1
        chain_runner.container_service = RunnerContainerService()
        chain_runner.pre_run()
        chain_runner.run({'s1': 1, 's2': 2, 's3': 3, 's4': 4})
        self.assertNotEqual(chain_runner.action_chain, None)
        mock_args, _ = schedule.call_args
        self.assertEqual(mock_args[0].parameters, {"p1": "1"})

    @mock.patch.object(action_db_util, 'get_action_by_ref',
                       mock.MagicMock(return_value=ACTION_1))
    @mock.patch.object(action_service, 'schedule', return_value=DummyActionExecution())
    def test_chain_runner_list_param_temp(self, schedule):
        chain_runner = acr.get_runner()
        chain_runner.entry_point = CHAIN_LIST_TEMP_PATH
        chain_runner.action = ACTION_1
        chain_runner.container_service = RunnerContainerService()
        chain_runner.pre_run()
        chain_runner.run({'s1': 1, 's2': 2, 's3': 3, 's4': 4})
        self.assertNotEqual(chain_runner.action_chain, None)
        mock_args, _ = schedule.call_args
        self.assertEqual(mock_args[0].parameters, {"p1": "[2, 3, 4]"})

    @mock.patch.object(action_db_util, 'get_action_by_ref',
                       mock.MagicMock(return_value=ACTION_1))
    @mock.patch.object(action_service, 'schedule', return_value=DummyActionExecution())
    def test_chain_runner_dict_param_temp(self, schedule):
        chain_runner = acr.get_runner()
        chain_runner.entry_point = CHAIN_DICT_TEMP_PATH
        chain_runner.action = ACTION_1
        chain_runner.container_service = RunnerContainerService()
        chain_runner.pre_run()
        chain_runner.run({'s1': 1, 's2': 2, 's3': 3, 's4': 4})
        self.assertNotEqual(chain_runner.action_chain, None)
        expected_value = {"p1": {"p1.3": "[3, 4]", "p1.2": "2", "p1.1": "1"}}
        mock_args, _ = schedule.call_args
        self.assertEqual(mock_args[0].parameters, expected_value)

    @mock.patch.object(action_db_util, 'get_action_by_ref',
                       mock.MagicMock(return_value=ACTION_1))
    @mock.patch.object(action_service, 'schedule',
                       return_value=DummyActionExecution(result={'o1': '1'}))
    def test_chain_runner_dependent_param_temp(self, schedule):
        chain_runner = acr.get_runner()
        chain_runner.entry_point = CHAIN_DEP_INPUT
        chain_runner.action = ACTION_1
        chain_runner.container_service = RunnerContainerService()
        chain_runner.pre_run()
        chain_runner.run({'s1': 1, 's2': 2, 's3': 3, 's4': 4})
        self.assertNotEqual(chain_runner.action_chain, None)
        expected_values = [{u'p1': u'1'},
                           {u'p1': u'1'},
                           {u'p2': u'1', u'p3': u'1', u'p1': u'1'}]
        # Each of the call_args must be one of
        for call_args in schedule.call_args_list:
            self.assertTrue(call_args[0][0].parameters in expected_values)
            expected_values.remove(call_args[0][0].parameters)
        self.assertEqual(len(expected_values), 0, 'Not all expected values received.')

    @mock.patch.object(action_db_util, 'get_action_by_ref',
                       mock.MagicMock(return_value=ACTION_1))
    @mock.patch.object(action_service, 'schedule',
                       return_value=DummyActionExecution(result={'o1': '1'}))
    def test_chain_runner_dependent_results_param(self, schedule):
        chain_runner = acr.get_runner()
        chain_runner.entry_point = CHAIN_DEP_RESULTS_INPUT
        chain_runner.action = ACTION_1
        chain_runner.container_service = RunnerContainerService()
        chain_runner.pre_run()
        chain_runner.run({'s1': 1})
        self.assertNotEqual(chain_runner.action_chain, None)
        expected_values = [{u'p1': u'1'},
                           {u'p1': u'1'},
                           {u'out': u"{u'c2': {'o1': '1'}, u'c1': {'o1': '1'}}"}]
        # Each of the call_args must be one of
        self.assertEqual(schedule.call_count, 3)
        for call_args in schedule.call_args_list:
            self.assertTrue(call_args[0][0].parameters in expected_values)
            expected_values.remove(call_args[0][0].parameters)
        self.assertEqual(len(expected_values), 0, 'Not all expected values received.')

    @mock.patch.object(action_db_util, 'get_action_by_ref',
                       mock.MagicMock(return_value=ACTION_1))
    @mock.patch.object(action_service, 'schedule', return_value=DummyActionExecution())
    def test_chain_runner_missing_param_temp(self, schedule):
        chain_runner = acr.get_runner()
        chain_runner.entry_point = CHAIN_STR_TEMP_PATH
        chain_runner.action = ACTION_1
        chain_runner.container_service = RunnerContainerService()
        chain_runner.pre_run()
        chain_runner.run({})
        self.assertEqual(schedule.call_count, 0, 'No call expected.')

    @mock.patch.object(action_db_util, 'get_action_by_ref',
                       mock.MagicMock(return_value=ACTION_2))
    @mock.patch.object(action_service, 'schedule', return_value=DummyActionExecution())
    def test_chain_runner_typed_params(self, schedule):
        chain_runner = acr.get_runner()
        chain_runner.entry_point = CHAIN_TYPED_PARAMS
        chain_runner.action = ACTION_2
        chain_runner.container_service = RunnerContainerService()
        chain_runner.pre_run()
        chain_runner.run({'s1': 1, 's2': 'two', 's3': 3.14})
        self.assertNotEqual(chain_runner.action_chain, None)
        expected_value = {'booltype': True,
                          'inttype': 1,
                          'numbertype': 3.14,
                          'strtype': 'two',
                          'arrtype': ['1', 'two'],
                          'objtype': {'s2': 'two',
                                      'k1': '1'}}
        mock_args, _ = schedule.call_args
        self.assertEqual(mock_args[0].parameters, expected_value)

    @mock.patch.object(action_db_util, 'get_action_by_ref',
                       mock.MagicMock(return_value=ACTION_2))
    @mock.patch.object(action_service, 'schedule', return_value=DummyActionExecution())
    def test_chain_runner_typed_system_params(self, schedule):
        KeyValuePair.add_or_update(KeyValuePairDB(name='a', value='1'))
        KeyValuePair.add_or_update(KeyValuePairDB(name='a.b.c', value='two'))
        chain_runner = acr.get_runner()
        chain_runner.entry_point = CHAIN_SYSTEM_PARAMS
        chain_runner.action = ACTION_2
        chain_runner.container_service = RunnerContainerService()
        chain_runner.pre_run()
        chain_runner.run({})
        self.assertNotEqual(chain_runner.action_chain, None)
        expected_value = {'inttype': 1,
                          'strtype': 'two'}
        mock_args, _ = schedule.call_args
        self.assertEqual(mock_args[0].parameters, expected_value)

    @classmethod
    def tearDownClass(cls):
        FixturesLoader().delete_models_from_db(MODELS)

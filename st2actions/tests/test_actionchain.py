import json
import mock
import os
import six

from unittest2 import TestCase

from st2actions.runners import actionchainrunner as acr
from st2actions.container.service import RunnerContainerService
from st2common.exceptions import actionrunner as runnerexceptions
from st2common.models.api import action
from st2common.services import action as action_service
from st2common.util import action_db as action_db_util
import st2tests.config as tests_config


class DummyActionExecution(object):
    def __init__(self, status=action.ACTIONEXEC_STATUS_SUCCEEDED, result=''):
        self.id = None
        self.status = status
        self.result = result


class DummyAction(object):
    def __init__(self):
        self.content_pack = None
        self.entry_point = None
        self.parameters = None
        self.runner_type = {'name': None}

    @staticmethod
    def from_dict(**kw):
        inst = DummyAction()
        for k, v in kw.items():
            setattr(inst, k, v)
        return inst


class DummyRunner(object):
    def __init__(self):
        self.runner_parameters = {}


CHAIN_1_PATH = os.path.join(os.path.dirname(os.path.realpath(__file__)),
                            'fixtures/actionchains/chain1.json')
with open(CHAIN_1_PATH, 'r') as fd:
    CHAIN_1 = json.load(fd)
CHAIN_STR_TEMP_PATH = os.path.join(os.path.dirname(os.path.realpath(__file__)),
                                   'fixtures/actionchains/chain_str_template.json')
CHAIN_LIST_TEMP_PATH = os.path.join(os.path.dirname(os.path.realpath(__file__)),
                                    'fixtures/actionchains/chain_list_template.json')
CHAIN_DICT_TEMP_PATH = os.path.join(os.path.dirname(os.path.realpath(__file__)),
                                    'fixtures/actionchains/chain_dict_template.json')
CHAIN_DEP_INPUT = os.path.join(os.path.dirname(os.path.realpath(__file__)),
                               'fixtures/actionchains/chain_dependent_input.json')
CHAIN_DEP_RESULTS_INPUT = os.path.join(os.path.dirname(os.path.realpath(__file__)),
                                       'fixtures/actionchains/chain_dep_result_input.json')
MALFORMED_CHAIN_PATH = os.path.join(os.path.dirname(os.path.realpath(__file__)),
                                    'fixtures/actionchains/malformedchain.json')
CHAIN_TYPED_PARAMS = os.path.join(os.path.dirname(os.path.realpath(__file__)),
                                  'fixtures/actionchains/chain_typed_params.json')
CHAIN_EMPTY = {}
ACTION_1_PATH = os.path.join(os.path.dirname(os.path.realpath(__file__)),
                             'fixtures/actionchains/a1.json')
with open(ACTION_1_PATH, 'r') as fd:
    ACTION_1 = DummyAction.from_dict(**json.load(fd))
ACTION_2_PATH = os.path.join(os.path.dirname(os.path.realpath(__file__)),
                             'fixtures/actionchains/a2.json')
with open(ACTION_2_PATH, 'r') as fd:
    ACTION_2 = DummyAction.from_dict(**json.load(fd))


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
                   mock.MagicMock(return_value=DummyRunner()))
class TestActionChainRunner(TestCase):

    def test_runner_creation(self):
        runner = acr.get_runner()
        self.assertTrue(runner)
        self.assertTrue(runner.id)

    def test_malformed_chain(self):
        try:
            chain_runner = acr.get_runner()
            chain_runner.entry_point = MALFORMED_CHAIN_PATH
            chain_runner.action = DummyAction()
            chain_runner.container_service = RunnerContainerService()
            chain_runner.pre_run()
            self.assertTrue(False, 'Expected pre_run to fail.')
        except runnerexceptions.ActionRunnerPreRunError:
            self.assertTrue(True)

    @mock.patch.object(action_db_util, '_get_action_by_pack_and_name',
                       mock.MagicMock(return_value=ACTION_1))
    @mock.patch.object(action_service, 'schedule', return_value=DummyActionExecution())
    def test_chain_runner_success_path(self, schedule):
        chain_runner = acr.get_runner()
        chain_runner.entry_point = CHAIN_1_PATH
        chain_runner.action = DummyAction()
        chain_runner.container_service = RunnerContainerService()
        chain_runner.pre_run()
        chain_runner.run({})
        self.assertNotEqual(chain_runner.action_chain, None)
        # based on the chain the callcount is known to be 3. Not great but works.
        self.assertEqual(schedule.call_count, 3)

    @mock.patch('eventlet.sleep', mock.MagicMock())
    @mock.patch.object(action_db_util, 'get_actionexec_by_id', mock.MagicMock(
        return_value=DummyActionExecution()))
    @mock.patch.object(action_db_util, '_get_action_by_pack_and_name',
                       mock.MagicMock(return_value=ACTION_1))
    @mock.patch.object(action_service, 'schedule',
                       return_value=DummyActionExecution(status=action.ACTIONEXEC_STATUS_RUNNING))
    def test_chain_runner_success_path_with_wait(self, schedule):
        chain_runner = acr.get_runner()
        chain_runner.entry_point = CHAIN_1_PATH
        chain_runner.action = DummyAction()
        chain_runner.container_service = RunnerContainerService()
        chain_runner.pre_run()
        chain_runner.run({})
        self.assertNotEqual(chain_runner.action_chain, None)
        # based on the chain the callcount is known to be 3. Not great but works.
        self.assertEqual(schedule.call_count, 3)

    @mock.patch.object(action_db_util, '_get_action_by_pack_and_name',
                       mock.MagicMock(return_value=ACTION_1))
    @mock.patch.object(action_service, 'schedule',
                       return_value=DummyActionExecution(status=action.ACTIONEXEC_STATUS_FAILED))
    def test_chain_runner_failure_path(self, schedule):
        chain_runner = acr.get_runner()
        chain_runner.entry_point = CHAIN_1_PATH
        chain_runner.action = DummyAction()
        chain_runner.container_service = RunnerContainerService()
        chain_runner.pre_run()
        success = chain_runner.run({})
        self.assertFalse(success)
        self.assertEqual(chain_runner.container_service.get_status(),
                         action.ACTIONEXEC_STATUS_FAILED)
        self.assertNotEqual(chain_runner.action_chain, None)
        # based on the chain the callcount is known to be 2. Not great but works.
        self.assertEqual(schedule.call_count, 2)

    @mock.patch.object(action_db_util, '_get_action_by_pack_and_name',
                       mock.MagicMock(return_value=ACTION_1))
    @mock.patch.object(action_service, 'schedule', side_effect=RuntimeError('Test Failure.'))
    def test_chain_runner_action_exception(self, schedule):
        chain_runner = acr.get_runner()
        chain_runner.entry_point = CHAIN_1_PATH
        chain_runner.action = DummyAction()
        chain_runner.container_service = RunnerContainerService()
        chain_runner.pre_run()
        chain_runner.run({})
        self.assertNotEqual(chain_runner.action_chain, None)
        # based on the chain the callcount is known to be 2. Not great but works.
        self.assertEqual(schedule.call_count, 2)

    @mock.patch.object(action_db_util, '_get_action_by_pack_and_name',
                       mock.MagicMock(return_value=ACTION_1))
    @mock.patch.object(action_service, 'schedule', return_value=DummyActionExecution())
    def test_chain_runner_str_param_temp(self, schedule):
        chain_runner = acr.get_runner()
        chain_runner.entry_point = CHAIN_STR_TEMP_PATH
        chain_runner.action = DummyAction()
        chain_runner.container_service = RunnerContainerService()
        chain_runner.pre_run()
        chain_runner.run({'s1': 1, 's2': 2, 's3': 3, 's4': 4})
        self.assertNotEqual(chain_runner.action_chain, None)
        mock_args, _ = schedule.call_args
        self.assertEqual(mock_args[0].parameters, {"p1": "1"})

    @mock.patch.object(action_db_util, '_get_action_by_pack_and_name',
                       mock.MagicMock(return_value=ACTION_1))
    @mock.patch.object(action_service, 'schedule', return_value=DummyActionExecution())
    def test_chain_runner_list_param_temp(self, schedule):
        chain_runner = acr.get_runner()
        chain_runner.entry_point = CHAIN_LIST_TEMP_PATH
        chain_runner.action = DummyAction()
        chain_runner.container_service = RunnerContainerService()
        chain_runner.pre_run()
        chain_runner.run({'s1': 1, 's2': 2, 's3': 3, 's4': 4})
        self.assertNotEqual(chain_runner.action_chain, None)
        mock_args, _ = schedule.call_args
        self.assertEqual(mock_args[0].parameters, {"p1": "[2, 3, 4]"})

    @mock.patch.object(action_db_util, '_get_action_by_pack_and_name',
                       mock.MagicMock(return_value=ACTION_1))
    @mock.patch.object(action_service, 'schedule', return_value=DummyActionExecution())
    def test_chain_runner_dict_param_temp(self, schedule):
        chain_runner = acr.get_runner()
        chain_runner.entry_point = CHAIN_DICT_TEMP_PATH
        chain_runner.action = DummyAction()
        chain_runner.container_service = RunnerContainerService()
        chain_runner.pre_run()
        chain_runner.run({'s1': 1, 's2': 2, 's3': 3, 's4': 4})
        self.assertNotEqual(chain_runner.action_chain, None)
        expected_value = {"p1": {"p1.3": "[3, 4]", "p1.2": "2", "p1.1": "1"}}
        mock_args, _ = schedule.call_args
        self.assertEqual(mock_args[0].parameters, expected_value)

    @mock.patch.object(action_db_util, '_get_action_by_pack_and_name',
                       mock.MagicMock(return_value=ACTION_1))
    @mock.patch.object(action_service, 'schedule',
                       return_value=DummyActionExecution(result={'o1': '1'}))
    def test_chain_runner_dependent_param_temp(self, schedule):
        chain_runner = acr.get_runner()
        chain_runner.entry_point = CHAIN_DEP_INPUT
        chain_runner.action = DummyAction()
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

    @mock.patch.object(action_db_util, '_get_action_by_pack_and_name',
                       mock.MagicMock(return_value=ACTION_1))
    @mock.patch.object(action_service, 'schedule',
                       return_value=DummyActionExecution(result={'o1': '1'}))
    def test_chain_runner_dependent_results_param(self, schedule):
        chain_runner = acr.get_runner()
        chain_runner.entry_point = CHAIN_DEP_RESULTS_INPUT
        chain_runner.action = DummyAction()
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

    @mock.patch.object(action_db_util, '_get_action_by_pack_and_name',
                       mock.MagicMock(return_value=ACTION_1))
    @mock.patch.object(action_service, 'schedule', return_value=DummyActionExecution())
    def test_chain_runner_missing_param_temp(self, schedule):
        chain_runner = acr.get_runner()
        chain_runner.entry_point = CHAIN_STR_TEMP_PATH
        chain_runner.action = DummyAction()
        chain_runner.container_service = RunnerContainerService()
        chain_runner.pre_run()
        chain_runner.run({})
        self.assertEqual(schedule.call_count, 0, 'No call expected.')

    @mock.patch.object(action_db_util, '_get_action_by_pack_and_name',
                       mock.MagicMock(return_value=ACTION_2))
    @mock.patch.object(action_service, 'schedule', return_value=DummyActionExecution())
    def test_chain_runner_typed_params(self, schedule):
        chain_runner = acr.get_runner()
        chain_runner.entry_point = CHAIN_TYPED_PARAMS
        chain_runner.action = DummyAction()
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

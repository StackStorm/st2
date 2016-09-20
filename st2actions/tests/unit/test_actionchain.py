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

from st2actions.runners import actionchainrunner as acr
from st2actions.container.service import RunnerContainerService
from st2common.exceptions import actionrunner as runnerexceptions
from st2common.constants.action import LIVEACTION_STATUS_RUNNING
from st2common.constants.action import LIVEACTION_STATUS_SUCCEEDED
from st2common.constants.action import LIVEACTION_STATUS_CANCELED
from st2common.constants.action import LIVEACTION_STATUS_TIMED_OUT
from st2common.constants.action import LIVEACTION_STATUS_FAILED
from st2common.models.api.notification import NotificationsHelper
from st2common.models.db.liveaction import LiveActionDB
from st2common.models.db.keyvalue import KeyValuePairDB
from st2common.models.system.common import ResourceReference
from st2common.persistence.keyvalue import KeyValuePair
from st2common.persistence.runner import RunnerType
from st2common.services import action as action_service
from st2common.util import action_db as action_db_util
from st2common.exceptions.action import ParameterRenderingFailedException
from st2tests import DbTestCase
from st2tests.fixturesloader import FixturesLoader


class DummyActionExecution(object):
    def __init__(self, status=LIVEACTION_STATUS_SUCCEEDED, result=''):
        self.id = None
        self.status = status
        self.result = result


FIXTURES_PACK = 'generic'

TEST_MODELS = {
    'actions': ['a1.yaml', 'a2.yaml', 'action_4_action_context_param.yaml'],
    'runners': ['testrunner1.yaml']
}

MODELS = FixturesLoader().load_models(fixtures_pack=FIXTURES_PACK,
                                      fixtures_dict=TEST_MODELS)
ACTION_1 = MODELS['actions']['a1.yaml']
ACTION_2 = MODELS['actions']['a2.yaml']
ACTION_3 = MODELS['actions']['action_4_action_context_param.yaml']
RUNNER = MODELS['runners']['testrunner1.yaml']

CHAIN_1_PATH = FixturesLoader().get_fixture_file_path_abs(
    FIXTURES_PACK, 'actionchains', 'chain1.yaml')
CHAIN_2_PATH = FixturesLoader().get_fixture_file_path_abs(
    FIXTURES_PACK, 'actionchains', 'chain2.yaml')
CHAIN_ACTION_CALL_NO_PARAMS_PATH = FixturesLoader().get_fixture_file_path_abs(
    FIXTURES_PACK, 'actionchains', 'chain_action_call_no_params.yaml')
CHAIN_NO_DEFAULT = FixturesLoader().get_fixture_file_path_abs(
    FIXTURES_PACK, 'actionchains', 'no_default_chain.yaml')
CHAIN_NO_DEFAULT_2 = FixturesLoader().get_fixture_file_path_abs(
    FIXTURES_PACK, 'actionchains', 'no_default_chain_2.yaml')
CHAIN_BAD_DEFAULT = FixturesLoader().get_fixture_file_path_abs(
    FIXTURES_PACK, 'actionchains', 'bad_default_chain.yaml')
CHAIN_BROKEN_ON_SUCCESS_PATH_STATIC_TASK_NAME = FixturesLoader().get_fixture_file_path_abs(
    FIXTURES_PACK, 'actionchains', 'chain_broken_on_success_path_static_task_name.yaml')
CHAIN_BROKEN_ON_FAILURE_PATH_STATIC_TASK_NAME = FixturesLoader().get_fixture_file_path_abs(
    FIXTURES_PACK, 'actionchains', 'chain_broken_on_failure_path_static_task_name.yaml')
CHAIN_FIRST_TASK_RENDER_FAIL_PATH = FixturesLoader().get_fixture_file_path_abs(
    FIXTURES_PACK, 'actionchains', 'chain_first_task_parameter_render_fail.yaml')
CHAIN_SECOND_TASK_RENDER_FAIL_PATH = FixturesLoader().get_fixture_file_path_abs(
    FIXTURES_PACK, 'actionchains', 'chain_second_task_parameter_render_fail.yaml')
CHAIN_LIST_TEMP_PATH = FixturesLoader().get_fixture_file_path_abs(
    FIXTURES_PACK, 'actionchains', 'chain_list_template.yaml')
CHAIN_DICT_TEMP_PATH = FixturesLoader().get_fixture_file_path_abs(
    FIXTURES_PACK, 'actionchains', 'chain_dict_template.yaml')
CHAIN_DEP_INPUT = FixturesLoader().get_fixture_file_path_abs(
    FIXTURES_PACK, 'actionchains', 'chain_dependent_input.yaml')
CHAIN_DEP_RESULTS_INPUT = FixturesLoader().get_fixture_file_path_abs(
    FIXTURES_PACK, 'actionchains', 'chain_dep_result_input.yaml')
MALFORMED_CHAIN_PATH = FixturesLoader().get_fixture_file_path_abs(
    FIXTURES_PACK, 'actionchains', 'malformedchain.yaml')
CHAIN_TYPED_PARAMS = FixturesLoader().get_fixture_file_path_abs(
    FIXTURES_PACK, 'actionchains', 'chain_typed_params.yaml')
CHAIN_SYSTEM_PARAMS = FixturesLoader().get_fixture_file_path_abs(
    FIXTURES_PACK, 'actionchains', 'chain_typed_system_params.yaml')
CHAIN_WITH_ACTIONPARAM_VARS = FixturesLoader().get_fixture_file_path_abs(
    FIXTURES_PACK, 'actionchains', 'chain_with_actionparam_vars.yaml')
CHAIN_WITH_SYSTEM_VARS = FixturesLoader().get_fixture_file_path_abs(
    FIXTURES_PACK, 'actionchains', 'chain_with_system_vars.yaml')
CHAIN_WITH_PUBLISH = FixturesLoader().get_fixture_file_path_abs(
    FIXTURES_PACK, 'actionchains', 'chain_with_publish.yaml')
CHAIN_WITH_PUBLISH_PARAM_RENDERING_FAILURE = FixturesLoader().get_fixture_file_path_abs(
    FIXTURES_PACK, 'actionchains', 'chain_publish_params_rendering_failure.yaml')
CHAIN_WITH_INVALID_ACTION = FixturesLoader().get_fixture_file_path_abs(
    FIXTURES_PACK, 'actionchains', 'chain_with_invalid_action.yaml')
CHAIN_ACTION_PARAMS_AND_PARAMETERS_ATTRIBUTE = FixturesLoader().get_fixture_file_path_abs(
    FIXTURES_PACK, 'actionchains', 'chain_action_params_and_parameters.yaml')
CHAIN_ACTION_PARAMS_ATTRIBUTE = FixturesLoader().get_fixture_file_path_abs(
    FIXTURES_PACK, 'actionchains', 'chain_action_params_attribute.yaml')
CHAIN_ACTION_PARAMETERS_ATTRIBUTE = FixturesLoader().get_fixture_file_path_abs(
    FIXTURES_PACK, 'actionchains', 'chain_action_parameters_attribute.yaml')
CHAIN_ACTION_INVALID_PARAMETER_TYPE = FixturesLoader().get_fixture_file_path_abs(
    FIXTURES_PACK, 'actionchains', 'chain_invalid_parameter_type_passed_to_action.yaml')

CHAIN_NOTIFY_API = {'notify': {'on-complete': {'message': 'foo happened.'}}}
CHAIN_NOTIFY_DB = NotificationsHelper.to_model(CHAIN_NOTIFY_API)


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
    @mock.patch.object(action_service, 'request', return_value=(DummyActionExecution(), None))
    def test_chain_runner_success_path(self, request):
        chain_runner = acr.get_runner()
        chain_runner.entry_point = CHAIN_1_PATH
        chain_runner.action = ACTION_1
        action_ref = ResourceReference.to_string_reference(name=ACTION_1.name,
                                                           pack=ACTION_1.pack)
        chain_runner.liveaction = LiveActionDB(action=action_ref)
        chain_runner.liveaction.notify = CHAIN_NOTIFY_DB
        chain_runner.container_service = RunnerContainerService()
        chain_runner.pre_run()
        chain_runner.run({})
        self.assertNotEqual(chain_runner.chain_holder.actionchain, None)
        # based on the chain the callcount is known to be 3. Not great but works.
        self.assertEqual(request.call_count, 3)

    @mock.patch.object(action_db_util, 'get_action_by_ref',
                       mock.MagicMock(return_value=ACTION_1))
    @mock.patch.object(action_service, 'request', return_value=(DummyActionExecution(), None))
    def test_chain_runner_chain_second_task_times_out(self, request):
        # Second task in the chain times out so the action chain status should be timeout
        chain_runner = acr.get_runner()
        chain_runner.entry_point = CHAIN_2_PATH
        chain_runner.action = ACTION_1

        original_run_action = chain_runner._run_action

        def mock_run_action(*args, **kwargs):
            original_live_action = args[0]
            liveaction = original_run_action(*args, **kwargs)
            if original_live_action.action == 'wolfpack.a2':
                # Mock a timeout for second task
                liveaction.status = LIVEACTION_STATUS_TIMED_OUT
            return liveaction

        chain_runner._run_action = mock_run_action

        action_ref = ResourceReference.to_string_reference(name=ACTION_1.name,
                                                           pack=ACTION_1.pack)
        chain_runner.liveaction = LiveActionDB(action=action_ref)
        chain_runner.container_service = RunnerContainerService()
        chain_runner.pre_run()
        status, _, _ = chain_runner.run({})

        self.assertEqual(status, LIVEACTION_STATUS_TIMED_OUT)
        self.assertNotEqual(chain_runner.chain_holder.actionchain, None)
        # based on the chain the callcount is known to be 3. Not great but works.
        self.assertEqual(request.call_count, 3)

    @mock.patch.object(action_db_util, 'get_action_by_ref',
                       mock.MagicMock(return_value=ACTION_1))
    @mock.patch.object(action_service, 'request', return_value=(DummyActionExecution(), None))
    def test_chain_runner_task_is_canceled_while_running(self, request):
        # Second task in the action is CANCELED, make sure runner doesn't get stuck in an infinite
        # loop
        chain_runner = acr.get_runner()
        chain_runner.entry_point = CHAIN_2_PATH
        chain_runner.action = ACTION_1

        original_run_action = chain_runner._run_action

        def mock_run_action(*args, **kwargs):
            original_live_action = args[0]
            if original_live_action.action == 'wolfpack.a2':
                status = LIVEACTION_STATUS_CANCELED
            else:
                status = LIVEACTION_STATUS_SUCCEEDED
            request.return_value = (DummyActionExecution(status=status), None)
            liveaction = original_run_action(*args, **kwargs)
            return liveaction

        chain_runner._run_action = mock_run_action

        action_ref = ResourceReference.to_string_reference(name=ACTION_1.name,
                                                           pack=ACTION_1.pack)
        chain_runner.liveaction = LiveActionDB(action=action_ref)
        chain_runner.container_service = RunnerContainerService()
        chain_runner.pre_run()
        status, _, _ = chain_runner.run({})

        self.assertEqual(status, LIVEACTION_STATUS_CANCELED)
        self.assertNotEqual(chain_runner.chain_holder.actionchain, None)
        # Chain count should be 2 since the last task doesn't get called since the second one was
        # canceled
        self.assertEqual(request.call_count, 2)

    @mock.patch.object(action_db_util, 'get_action_by_ref',
                       mock.MagicMock(return_value=ACTION_1))
    @mock.patch.object(action_service, 'request', return_value=(DummyActionExecution(), None))
    def test_chain_runner_success_task_action_call_with_no_params(self, request):
        # Make sure that the runner doesn't explode if task definition contains
        # no "params" section
        chain_runner = acr.get_runner()
        chain_runner.entry_point = CHAIN_ACTION_CALL_NO_PARAMS_PATH
        chain_runner.action = ACTION_1
        action_ref = ResourceReference.to_string_reference(name=ACTION_1.name,
                                                           pack=ACTION_1.pack)
        chain_runner.liveaction = LiveActionDB(action=action_ref)
        chain_runner.liveaction.notify = CHAIN_NOTIFY_DB
        chain_runner.container_service = RunnerContainerService()
        chain_runner.pre_run()
        chain_runner.run({})
        self.assertNotEqual(chain_runner.chain_holder.actionchain, None)
        # based on the chain the callcount is known to be 3. Not great but works.
        self.assertEqual(request.call_count, 3)

    @mock.patch.object(action_db_util, 'get_action_by_ref',
                       mock.MagicMock(return_value=ACTION_1))
    @mock.patch.object(action_service, 'request', return_value=(DummyActionExecution(), None))
    def test_chain_runner_no_default(self, request):
        chain_runner = acr.get_runner()
        chain_runner.entry_point = CHAIN_NO_DEFAULT
        chain_runner.action = ACTION_1
        chain_runner.container_service = RunnerContainerService()
        chain_runner.pre_run()
        chain_runner.run({})
        self.assertNotEqual(chain_runner.chain_holder.actionchain, None)
        # In case of this chain default_node is the first_node.
        default_node = chain_runner.chain_holder.actionchain.default
        first_node = chain_runner.chain_holder.actionchain.chain[0]
        self.assertEqual(default_node, first_node.name)
        # based on the chain the callcount is known to be 3. Not great but works.
        self.assertEqual(request.call_count, 3)

    @mock.patch.object(action_db_util, 'get_action_by_ref',
                       mock.MagicMock(return_value=ACTION_1))
    @mock.patch.object(action_service, 'request', return_value=(DummyActionExecution(), None))
    def test_chain_runner_no_default_multiple_options(self, request):
        # subtle difference is that when there are multiple possible default nodes
        # the order per chain definition may not be preseved. This is really a
        # poorly formatted chain but we still the best attempt to work.
        chain_runner = acr.get_runner()
        chain_runner.entry_point = CHAIN_NO_DEFAULT_2
        chain_runner.action = ACTION_1
        chain_runner.container_service = RunnerContainerService()
        chain_runner.pre_run()
        chain_runner.run({})
        self.assertNotEqual(chain_runner.chain_holder.actionchain, None)
        # In case of this chain default_node is the first_node.
        default_node = chain_runner.chain_holder.actionchain.default
        first_node = chain_runner.chain_holder.actionchain.chain[0]
        self.assertEqual(default_node, first_node.name)
        # based on the chain the callcount is known to be 2.
        self.assertEqual(request.call_count, 2)

    @mock.patch.object(action_db_util, 'get_action_by_ref',
                       mock.MagicMock(return_value=ACTION_1))
    @mock.patch.object(action_service, 'request', return_value=(DummyActionExecution(), None))
    def test_chain_runner_bad_default(self, request):
        chain_runner = acr.get_runner()
        chain_runner.entry_point = CHAIN_BAD_DEFAULT
        chain_runner.action = ACTION_1
        chain_runner.container_service = RunnerContainerService()
        expected_msg = 'Unable to find node with name "bad_default" referenced in "default".'
        self.assertRaisesRegexp(runnerexceptions.ActionRunnerPreRunError,
                                expected_msg, chain_runner.pre_run)

    @mock.patch('eventlet.sleep', mock.MagicMock())
    @mock.patch.object(action_db_util, 'get_liveaction_by_id', mock.MagicMock(
        return_value=DummyActionExecution()))
    @mock.patch.object(action_db_util, 'get_action_by_ref',
                       mock.MagicMock(return_value=ACTION_1))
    @mock.patch.object(action_service, 'request',
                       return_value=(DummyActionExecution(status=LIVEACTION_STATUS_RUNNING), None))
    def test_chain_runner_success_path_with_wait(self, request):
        chain_runner = acr.get_runner()
        chain_runner.entry_point = CHAIN_1_PATH
        chain_runner.action = ACTION_1
        chain_runner.container_service = RunnerContainerService()
        chain_runner.pre_run()
        chain_runner.run({})
        self.assertNotEqual(chain_runner.chain_holder.actionchain, None)
        # based on the chain the callcount is known to be 3. Not great but works.
        self.assertEqual(request.call_count, 3)

    @mock.patch.object(action_db_util, 'get_action_by_ref',
                       mock.MagicMock(return_value=ACTION_1))
    @mock.patch.object(action_service, 'request',
                       return_value=(DummyActionExecution(status=LIVEACTION_STATUS_FAILED), None))
    def test_chain_runner_failure_path(self, request):
        chain_runner = acr.get_runner()
        chain_runner.entry_point = CHAIN_1_PATH
        chain_runner.action = ACTION_1
        chain_runner.container_service = RunnerContainerService()
        chain_runner.pre_run()
        status, _, _ = chain_runner.run({})
        self.assertEqual(status, LIVEACTION_STATUS_FAILED)
        self.assertNotEqual(chain_runner.chain_holder.actionchain, None)
        # based on the chain the callcount is known to be 2. Not great but works.
        self.assertEqual(request.call_count, 2)

    @mock.patch.object(action_db_util, 'get_action_by_ref',
                       mock.MagicMock(return_value=ACTION_1))
    @mock.patch.object(action_service, 'request',
                       return_value=(DummyActionExecution(), None))
    def test_chain_runner_broken_on_success_path_static_task_name(self, request):
        chain_runner = acr.get_runner()
        chain_runner.entry_point = CHAIN_BROKEN_ON_SUCCESS_PATH_STATIC_TASK_NAME
        chain_runner.action = ACTION_1
        chain_runner.container_service = RunnerContainerService()

        expected_msg = ('Unable to find node with name "c5" referenced in "on-success" '
                        'in task "c2"')
        self.assertRaisesRegexp(runnerexceptions.ActionRunnerPreRunError,
                                expected_msg, chain_runner.pre_run)

    @mock.patch.object(action_db_util, 'get_action_by_ref',
                       mock.MagicMock(return_value=ACTION_1))
    @mock.patch.object(action_service, 'request',
                       return_value=(DummyActionExecution(), None))
    def test_chain_runner_broken_on_failure_path_static_task_name(self, request):
        chain_runner = acr.get_runner()
        chain_runner.entry_point = CHAIN_BROKEN_ON_FAILURE_PATH_STATIC_TASK_NAME
        chain_runner.action = ACTION_1
        chain_runner.container_service = RunnerContainerService()

        expected_msg = ('Unable to find node with name "c6" referenced in "on-failure" '
                        'in task "c2"')
        self.assertRaisesRegexp(runnerexceptions.ActionRunnerPreRunError,
                                expected_msg, chain_runner.pre_run)

    @mock.patch.object(action_db_util, 'get_action_by_ref',
                       mock.MagicMock(return_value=ACTION_1))
    @mock.patch.object(action_service, 'request', side_effect=RuntimeError('Test Failure.'))
    def test_chain_runner_action_exception(self, request):
        chain_runner = acr.get_runner()
        chain_runner.entry_point = CHAIN_1_PATH
        chain_runner.action = ACTION_1
        chain_runner.container_service = RunnerContainerService()
        chain_runner.pre_run()
        status, results, _ = chain_runner.run({})
        self.assertEqual(status, LIVEACTION_STATUS_FAILED)
        self.assertNotEqual(chain_runner.chain_holder.actionchain, None)

        # based on the chain the callcount is known to be 2. Not great but works.
        self.assertEqual(request.call_count, 2)

        error_count = 0
        for task_result in results['tasks']:
            if task_result['result'].get('error', None):
                error_count += 1

        self.assertEqual(error_count, 2)

    @mock.patch.object(action_db_util, 'get_action_by_ref',
                       mock.MagicMock(return_value=ACTION_1))
    @mock.patch.object(action_service, 'request', return_value=(DummyActionExecution(), None))
    def test_chain_runner_str_param_temp(self, request):
        chain_runner = acr.get_runner()
        chain_runner.entry_point = CHAIN_FIRST_TASK_RENDER_FAIL_PATH
        chain_runner.action = ACTION_1
        chain_runner.container_service = RunnerContainerService()
        chain_runner.pre_run()
        chain_runner.run({'s1': 1, 's2': 2, 's3': 3, 's4': 4})
        self.assertNotEqual(chain_runner.chain_holder.actionchain, None)
        mock_args, _ = request.call_args
        self.assertEqual(mock_args[0].parameters, {"p1": "1"})

    @mock.patch.object(action_db_util, 'get_action_by_ref',
                       mock.MagicMock(return_value=ACTION_1))
    @mock.patch.object(action_service, 'request', return_value=(DummyActionExecution(), None))
    def test_chain_runner_list_param_temp(self, request):
        chain_runner = acr.get_runner()
        chain_runner.entry_point = CHAIN_LIST_TEMP_PATH
        chain_runner.action = ACTION_1
        chain_runner.container_service = RunnerContainerService()
        chain_runner.pre_run()
        chain_runner.run({'s1': 1, 's2': 2, 's3': 3, 's4': 4})
        self.assertNotEqual(chain_runner.chain_holder.actionchain, None)
        mock_args, _ = request.call_args
        self.assertEqual(mock_args[0].parameters, {"p1": "[2, 3, 4]"})

    @mock.patch.object(action_db_util, 'get_action_by_ref',
                       mock.MagicMock(return_value=ACTION_1))
    @mock.patch.object(action_service, 'request', return_value=(DummyActionExecution(), None))
    def test_chain_runner_dict_param_temp(self, request):
        chain_runner = acr.get_runner()
        chain_runner.entry_point = CHAIN_DICT_TEMP_PATH
        chain_runner.action = ACTION_1
        chain_runner.container_service = RunnerContainerService()
        chain_runner.pre_run()
        chain_runner.run({'s1': 1, 's2': 2, 's3': 3, 's4': 4})
        self.assertNotEqual(chain_runner.chain_holder.actionchain, None)
        expected_value = {"p1": {"p1.3": "[3, 4]", "p1.2": "2", "p1.1": "1"}}
        mock_args, _ = request.call_args
        self.assertEqual(mock_args[0].parameters, expected_value)

    @mock.patch.object(action_db_util, 'get_action_by_ref',
                       mock.MagicMock(return_value=ACTION_1))
    @mock.patch.object(action_service, 'request',
                       return_value=(DummyActionExecution(result={'o1': '1'}), None))
    def test_chain_runner_dependent_param_temp(self, request):
        chain_runner = acr.get_runner()
        chain_runner.entry_point = CHAIN_DEP_INPUT
        chain_runner.action = ACTION_1
        chain_runner.container_service = RunnerContainerService()
        chain_runner.pre_run()
        chain_runner.run({'s1': 1, 's2': 2, 's3': 3, 's4': 4})
        self.assertNotEqual(chain_runner.chain_holder.actionchain, None)
        expected_values = [{u'p1': u'1'},
                           {u'p1': u'1'},
                           {u'p2': u'1', u'p3': u'1', u'p1': u'1'}]
        # Each of the call_args must be one of
        for call_args in request.call_args_list:
            self.assertTrue(call_args[0][0].parameters in expected_values)
            expected_values.remove(call_args[0][0].parameters)
        self.assertEqual(len(expected_values), 0, 'Not all expected values received.')

    @mock.patch.object(action_db_util, 'get_action_by_ref',
                       mock.MagicMock(return_value=ACTION_1))
    @mock.patch.object(action_service, 'request',
                       return_value=(DummyActionExecution(result={'o1': '1'}), None))
    def test_chain_runner_dependent_results_param(self, request):
        chain_runner = acr.get_runner()
        chain_runner.entry_point = CHAIN_DEP_RESULTS_INPUT
        chain_runner.action = ACTION_1
        chain_runner.container_service = RunnerContainerService()
        chain_runner.pre_run()
        chain_runner.run({'s1': 1})
        self.assertNotEqual(chain_runner.chain_holder.actionchain, None)
        expected_values = [{u'p1': u'1'},
                           {u'p1': u'1'},
                           {u'out': u"{'c2': {'o1': '1'}, 'c1': {'o1': '1'}}"}]
        # Each of the call_args must be one of
        self.assertEqual(request.call_count, 3)
        for call_args in request.call_args_list:
            self.assertTrue(call_args[0][0].parameters in expected_values)
            expected_values.remove(call_args[0][0].parameters)
        self.assertEqual(len(expected_values), 0, 'Not all expected values received.')

    @mock.patch.object(action_db_util, 'get_action_by_ref',
                       mock.MagicMock(return_value=ACTION_1))
    @mock.patch.object(RunnerType, 'get_by_name',
                       mock.MagicMock(return_value=RUNNER))
    @mock.patch.object(action_service, 'request', return_value=(DummyActionExecution(), None))
    def test_chain_runner_missing_param_temp(self, request):
        chain_runner = acr.get_runner()
        chain_runner.entry_point = CHAIN_FIRST_TASK_RENDER_FAIL_PATH
        chain_runner.action = ACTION_1
        chain_runner.container_service = RunnerContainerService()
        chain_runner.pre_run()
        chain_runner.run({})
        self.assertEqual(request.call_count, 0, 'No call expected.')

    @mock.patch.object(action_db_util, 'get_action_by_ref',
                       mock.MagicMock(return_value=ACTION_1))
    @mock.patch.object(action_service, 'request', return_value=(DummyActionExecution(), None))
    def test_chain_runner_failure_during_param_rendering_single_task(self, request):
        # Parameter rendering should result in a top level error which aborts
        # the whole chain
        chain_runner = acr.get_runner()
        chain_runner.entry_point = CHAIN_FIRST_TASK_RENDER_FAIL_PATH
        chain_runner.action = ACTION_1
        chain_runner.container_service = RunnerContainerService()
        chain_runner.pre_run()
        status, result, _ = chain_runner.run({})

        # No tasks ran because rendering of parameters for the first task failed
        self.assertEqual(status, LIVEACTION_STATUS_FAILED)
        self.assertEqual(result['tasks'], [])
        self.assertTrue('error' in result)
        self.assertTrue('traceback' in result)
        self.assertTrue('Failed to run task "c1". Parameter rendering failed' in result['error'])
        self.assertTrue('Traceback' in result['traceback'])

    @mock.patch.object(action_db_util, 'get_action_by_ref',
                       mock.MagicMock(return_value=ACTION_1))
    @mock.patch.object(action_service, 'request', return_value=(DummyActionExecution(), None))
    def test_chain_runner_failure_during_param_rendering_multiple_tasks(self, request):
        # Parameter rendering should result in a top level error which aborts
        # the whole chain
        chain_runner = acr.get_runner()
        chain_runner.entry_point = CHAIN_SECOND_TASK_RENDER_FAIL_PATH
        chain_runner.action = ACTION_1
        chain_runner.container_service = RunnerContainerService()
        chain_runner.pre_run()
        status, result, _ = chain_runner.run({})

        # Verify that only first task has ran
        self.assertEqual(status, LIVEACTION_STATUS_FAILED)
        self.assertEqual(len(result['tasks']), 1)
        self.assertEqual(result['tasks'][0]['name'], 'c1')

        expected_error = ('Failed rendering value for action parameter "p1" in '
                          'task "c2" (template string={{s1}}):')

        self.assertTrue('error' in result)
        self.assertTrue('traceback' in result)
        self.assertTrue('Failed to run task "c2". Parameter rendering failed' in result['error'])
        self.assertTrue(expected_error in result['error'])
        self.assertTrue('Traceback' in result['traceback'])

    @mock.patch.object(action_db_util, 'get_action_by_ref',
                       mock.MagicMock(return_value=ACTION_2))
    @mock.patch.object(action_service, 'request', return_value=(DummyActionExecution(), None))
    def test_chain_runner_typed_params(self, request):
        chain_runner = acr.get_runner()
        chain_runner.entry_point = CHAIN_TYPED_PARAMS
        chain_runner.action = ACTION_2
        chain_runner.container_service = RunnerContainerService()
        chain_runner.pre_run()
        chain_runner.run({'s1': 1, 's2': 'two', 's3': 3.14})
        self.assertNotEqual(chain_runner.chain_holder.actionchain, None)
        expected_value = {'booltype': True,
                          'inttype': 1,
                          'numbertype': 3.14,
                          'strtype': 'two',
                          'arrtype': ['1', 'two'],
                          'objtype': {'s2': 'two',
                                      'k1': '1'}}
        mock_args, _ = request.call_args
        self.assertEqual(mock_args[0].parameters, expected_value)

    @mock.patch.object(action_db_util, 'get_action_by_ref',
                       mock.MagicMock(return_value=ACTION_2))
    @mock.patch.object(action_service, 'request', return_value=(DummyActionExecution(), None))
    def test_chain_runner_typed_system_params(self, request):
        kvps = []
        try:
            kvps.append(KeyValuePair.add_or_update(KeyValuePairDB(name='a', value='1')))
            kvps.append(KeyValuePair.add_or_update(KeyValuePairDB(name='a.b.c', value='two')))
            chain_runner = acr.get_runner()
            chain_runner.entry_point = CHAIN_SYSTEM_PARAMS
            chain_runner.action = ACTION_2
            chain_runner.container_service = RunnerContainerService()
            chain_runner.pre_run()
            chain_runner.run({})
            self.assertNotEqual(chain_runner.chain_holder.actionchain, None)
            expected_value = {'inttype': 1,
                              'strtype': 'two'}
            mock_args, _ = request.call_args
            self.assertEqual(mock_args[0].parameters, expected_value)
        finally:
            for kvp in kvps:
                KeyValuePair.delete(kvp)

    @mock.patch.object(action_db_util, 'get_action_by_ref',
                       mock.MagicMock(return_value=ACTION_2))
    @mock.patch.object(action_service, 'request', return_value=(DummyActionExecution(), None))
    def test_chain_runner_vars_system_params(self, request):
        kvps = []
        try:
            kvps.append(KeyValuePair.add_or_update(KeyValuePairDB(name='a', value='two')))
            chain_runner = acr.get_runner()
            chain_runner.entry_point = CHAIN_WITH_SYSTEM_VARS
            chain_runner.action = ACTION_2
            chain_runner.container_service = RunnerContainerService()
            chain_runner.pre_run()
            chain_runner.run({})
            self.assertNotEqual(chain_runner.chain_holder.actionchain, None)
            expected_value = {'inttype': 1,
                              'strtype': 'two',
                              'booltype': True}
            mock_args, _ = request.call_args
            self.assertEqual(mock_args[0].parameters, expected_value)
        finally:
            for kvp in kvps:
                KeyValuePair.delete(kvp)

    @mock.patch.object(action_db_util, 'get_action_by_ref',
                       mock.MagicMock(return_value=ACTION_2))
    @mock.patch.object(action_service, 'request', return_value=(DummyActionExecution(), None))
    def test_chain_runner_vars_action_params(self, request):
        chain_runner = acr.get_runner()
        chain_runner.entry_point = CHAIN_WITH_ACTIONPARAM_VARS
        chain_runner.action = ACTION_2
        chain_runner.container_service = RunnerContainerService()
        chain_runner.pre_run()
        chain_runner.run({'input_a': 'two'})
        self.assertNotEqual(chain_runner.chain_holder.actionchain, None)
        expected_value = {'inttype': 1,
                          'strtype': 'two',
                          'booltype': True}
        mock_args, _ = request.call_args
        self.assertEqual(mock_args[0].parameters, expected_value)

    @mock.patch.object(action_db_util, 'get_action_by_ref',
                       mock.MagicMock(return_value=ACTION_2))
    @mock.patch.object(action_service, 'request',
                       return_value=(DummyActionExecution(result={'raw_out': 'published'}), None))
    def test_chain_runner_publish(self, request):
        chain_runner = acr.get_runner()
        chain_runner.entry_point = CHAIN_WITH_PUBLISH
        chain_runner.action = ACTION_2
        chain_runner.container_service = RunnerContainerService()
        chain_runner.runner_parameters = {'display_published': True}
        chain_runner.pre_run()

        action_parameters = {'action_param_1': 'test value 1'}
        _, result, _ = chain_runner.run(action_parameters=action_parameters)

        # We also assert that the action parameters are available in the
        # "publish" scope
        self.assertNotEqual(chain_runner.chain_holder.actionchain, None)
        expected_value = {'inttype': 1,
                          'strtype': 'published',
                          'booltype': True,
                          'published_action_param': action_parameters['action_param_1']}
        mock_args, _ = request.call_args
        self.assertEqual(mock_args[0].parameters, expected_value)
        # Assert that the variables are correctly published
        self.assertEqual(result['published'],
                         {'published_action_param': u'test value 1', 'o1': u'published'})

    @mock.patch.object(action_db_util, 'get_action_by_ref',
                       mock.MagicMock(return_value=ACTION_1))
    @mock.patch.object(action_service, 'request', return_value=(DummyActionExecution(), None))
    def test_chain_runner_publish_param_rendering_failure(self, request):
        # Parameter rendering should result in a top level error which aborts
        # the whole chain
        chain_runner = acr.get_runner()
        chain_runner.entry_point = CHAIN_WITH_PUBLISH_PARAM_RENDERING_FAILURE
        chain_runner.action = ACTION_1
        chain_runner.container_service = RunnerContainerService()
        chain_runner.pre_run()

        try:
            chain_runner.run({})
        except ParameterRenderingFailedException as e:
            # TODO: Should we treat this as task error? Right now it bubbles all
            # the way up and it's not really consistent with action param
            # rendering failure
            expected_error = ('Failed rendering value for publish parameter "p1" in '
                              'task "c2" (template string={{ not_defined }}):')
            self.assertTrue(expected_error in str(e))
            pass
        else:
            self.fail('Exception was not thrown')

    @mock.patch.object(action_db_util, 'get_action_by_ref',
                       mock.MagicMock(return_value=ACTION_2))
    @mock.patch.object(action_service, 'request', return_value=(DummyActionExecution(), None))
    def test_chain_task_passes_invalid_parameter_type_to_action(self, mock_request):
        chain_runner = acr.get_runner()
        chain_runner.entry_point = CHAIN_ACTION_INVALID_PARAMETER_TYPE
        chain_runner.action = ACTION_2
        chain_runner.container_service = RunnerContainerService()
        chain_runner.pre_run()

        action_parameters = {}
        expected_msg = ('Failed to cast value "stringnotanarray" \(type: str\) for parameter '
                        '"arrtype" of type "array"')
        self.assertRaisesRegexp(ValueError, expected_msg, chain_runner.run,
                                action_parameters=action_parameters)

    @mock.patch.object(action_db_util, 'get_action_by_ref',
                       mock.MagicMock(return_value=None))
    @mock.patch.object(action_service, 'request',
                       return_value=(DummyActionExecution(result={'raw_out': 'published'}), None))
    def test_action_chain_runner_referenced_action_doesnt_exist(self, mock_request):
        # Action referenced by a task doesn't exist, should result in a top level error
        chain_runner = acr.get_runner()
        chain_runner.entry_point = CHAIN_WITH_INVALID_ACTION
        chain_runner.action = ACTION_2
        chain_runner.container_service = RunnerContainerService()
        chain_runner.pre_run()

        action_parameters = {}
        status, output, _ = chain_runner.run(action_parameters=action_parameters)

        expected_error = ('Failed to run task "c1". Action with reference "wolfpack.a2" '
                          'doesn\'t exist.')
        self.assertEqual(status, LIVEACTION_STATUS_FAILED)
        self.assertTrue(expected_error in output['error'])
        self.assertTrue('Traceback' in output['traceback'], output['traceback'])

    def test_exception_is_thrown_if_both_params_and_parameters_attributes_are_provided(self):
        chain_runner = acr.get_runner()
        chain_runner.entry_point = CHAIN_ACTION_PARAMS_AND_PARAMETERS_ATTRIBUTE
        chain_runner.action = ACTION_2
        chain_runner.container_service = RunnerContainerService()

        expected_msg = ('Either "params" or "parameters" attribute needs to be provided, but '
                       'not both')
        self.assertRaisesRegexp(runnerexceptions.ActionRunnerPreRunError, expected_msg,
                                chain_runner.pre_run)

    @mock.patch.object(action_db_util, 'get_action_by_ref',
                       mock.MagicMock(return_value=ACTION_1))
    @mock.patch.object(action_service, 'request', return_value=(DummyActionExecution(), None))
    def test_params_and_parameters_attributes_both_work(self, _):
        # "params" attribute used
        chain_runner = acr.get_runner()
        chain_runner.entry_point = CHAIN_ACTION_PARAMS_ATTRIBUTE
        chain_runner.action = ACTION_2
        chain_runner.container_service = RunnerContainerService()
        chain_runner.pre_run()

        original_build_liveaction_object = chain_runner._build_liveaction_object

        def mock_build_liveaction_object(action_node, resolved_params, parent_context):
            # Verify parameters are correctly passed to the action
            self.assertEqual(resolved_params, {'pparams': 'v1'})
            original_build_liveaction_object(action_node=action_node,
                                             resolved_params=resolved_params,
                                             parent_context=parent_context)

        chain_runner._build_liveaction_object = mock_build_liveaction_object

        action_parameters = {}
        status, output, _ = chain_runner.run(action_parameters=action_parameters)
        self.assertEqual(status, LIVEACTION_STATUS_SUCCEEDED)

        # "parameters" attribute used
        chain_runner = acr.get_runner()
        chain_runner.entry_point = CHAIN_ACTION_PARAMETERS_ATTRIBUTE
        chain_runner.action = ACTION_2
        chain_runner.container_service = RunnerContainerService()
        chain_runner.pre_run()

        def mock_build_liveaction_object(action_node, resolved_params, parent_context):
            # Verify parameters are correctly passed to the action
            self.assertEqual(resolved_params, {'pparameters': 'v1'})
            original_build_liveaction_object(action_node=action_node,
                                             resolved_params=resolved_params,
                                             parent_context=parent_context)

        chain_runner._build_liveaction_object = mock_build_liveaction_object

        action_parameters = {}
        status, output, _ = chain_runner.run(action_parameters=action_parameters)
        self.assertEqual(status, LIVEACTION_STATUS_SUCCEEDED)

    @classmethod
    def tearDownClass(cls):
        FixturesLoader().delete_models_from_db(MODELS)

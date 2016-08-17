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

import os

import mock

from st2actions.runners import pythonrunner
from st2actions.runners.python_action_wrapper import PythonActionWrapper
from st2actions.runners.pythonrunner import Action
from st2actions.container import service
from st2actions.runners.utils import get_action_class_instance
from st2common.services import config as config_service
from st2common.constants.action import ACTION_OUTPUT_RESULT_DELIMITER
from st2common.constants.action import LIVEACTION_STATUS_SUCCEEDED, LIVEACTION_STATUS_FAILED
from st2common.constants.action import LIVEACTION_STATUS_TIMED_OUT
from st2common.constants.pack import SYSTEM_PACK_NAME
from base import RunnerTestCase
from st2tests.base import CleanDbTestCase
import st2tests.base as tests_base


PASCAL_ROW_ACTION_PATH = os.path.join(tests_base.get_resources_path(), 'packs',
                                      'pythonactions/actions/pascal_row.py')
TEST_ACTION_PATH = os.path.join(tests_base.get_resources_path(), 'packs',
                                'pythonactions/actions/test.py')

# Note: runner inherits parent args which doesn't work with tests since test pass additional
# unrecognized args
mock_sys = mock.Mock()
mock_sys.argv = []


@mock.patch('st2actions.runners.pythonrunner.sys', mock_sys)
class PythonRunnerTestCase(RunnerTestCase, CleanDbTestCase):
    register_packs = True
    register_pack_configs = True

    def test_runner_creation(self):
        runner = pythonrunner.get_runner()
        self.assertTrue(runner is not None, 'Creation failed. No instance.')
        self.assertEqual(type(runner), pythonrunner.PythonRunner, 'Creation failed. No instance.')

    def test_simple_action_with_result_no_status(self):
        runner = pythonrunner.get_runner()
        runner.action = self._get_mock_action_obj()
        runner.runner_parameters = {}
        runner.entry_point = PASCAL_ROW_ACTION_PATH
        runner.container_service = service.RunnerContainerService()
        runner.pre_run()
        (status, output, _) = runner.run({'row_index': 5})
        self.assertEqual(status, LIVEACTION_STATUS_SUCCEEDED)
        self.assertTrue(output is not None)
        self.assertEqual(output['result'], [1, 5, 10, 10, 5, 1])

    def test_simple_action_with_result_as_None_no_status(self):
        runner = pythonrunner.get_runner()
        runner.action = self._get_mock_action_obj()
        runner.runner_parameters = {}
        runner.entry_point = PASCAL_ROW_ACTION_PATH
        runner.container_service = service.RunnerContainerService()
        runner.pre_run()
        (status, output, _) = runner.run({'row_index': 'b'})
        self.assertEqual(status, LIVEACTION_STATUS_SUCCEEDED)
        self.assertTrue(output is not None)
        self.assertEqual(output['exit_code'], 0)
        self.assertEqual(output['result'], None)

    def test_simple_action_timeout(self):
        timeout = 0
        runner = pythonrunner.get_runner()
        runner.action = self._get_mock_action_obj()
        runner.runner_parameters = {pythonrunner.RUNNER_TIMEOUT: timeout}
        runner.entry_point = PASCAL_ROW_ACTION_PATH
        runner.container_service = service.RunnerContainerService()
        runner.pre_run()
        (status, output, _) = runner.run({'row_index': 4})
        self.assertEqual(status, LIVEACTION_STATUS_TIMED_OUT)
        self.assertTrue(output is not None)
        self.assertEqual(output['result'], 'None')
        self.assertEqual(output['error'], 'Action failed to complete in 0 seconds')
        self.assertEqual(output['exit_code'], -9)

    def test_simple_action_with_status_succeeded(self):
        runner = pythonrunner.get_runner()
        runner.action = self._get_mock_action_obj()
        runner.runner_parameters = {}
        runner.entry_point = PASCAL_ROW_ACTION_PATH
        runner.container_service = service.RunnerContainerService()
        runner.pre_run()
        (status, output, _) = runner.run({'row_index': 4})
        self.assertEqual(status, LIVEACTION_STATUS_SUCCEEDED)
        self.assertTrue(output is not None)
        self.assertEqual(output['result'], [1, 4, 6, 4, 1])

    def test_simple_action_with_status_failed(self):
        runner = pythonrunner.get_runner()
        runner.action = self._get_mock_action_obj()
        runner.runner_parameters = {}
        runner.entry_point = PASCAL_ROW_ACTION_PATH
        runner.container_service = service.RunnerContainerService()
        runner.pre_run()
        (status, output, _) = runner.run({'row_index': 'a'})
        self.assertEqual(status, LIVEACTION_STATUS_FAILED)
        self.assertTrue(output is not None)
        self.assertEqual(output['result'], "This is suppose to fail don't worry!!")

    def test_simple_action_with_status_failed_result_none(self):
        runner = pythonrunner.get_runner()
        runner.action = self._get_mock_action_obj()
        runner.runner_parameters = {}
        runner.entry_point = PASCAL_ROW_ACTION_PATH
        runner.container_service = service.RunnerContainerService()
        runner.pre_run()
        (status, output, _) = runner.run({'row_index': 'c'})
        self.assertEqual(status, LIVEACTION_STATUS_FAILED)
        self.assertTrue(output is not None)
        self.assertEqual(output['result'], None)

    def test_exception_in_simple_action_with_invalid_status(self):
        runner = pythonrunner.get_runner()
        runner.action = self._get_mock_action_obj()
        runner.runner_parameters = {}
        runner.entry_point = PASCAL_ROW_ACTION_PATH
        runner.container_service = service.RunnerContainerService()
        runner.pre_run()
        self.assertRaises(ValueError,
                          runner.run, action_parameters={'row_index': 'd'})

    def test_simple_action_no_status_backward_compatibility(self):
        runner = pythonrunner.get_runner()
        runner.action = self._get_mock_action_obj()
        runner.runner_parameters = {}
        runner.entry_point = PASCAL_ROW_ACTION_PATH
        runner.container_service = service.RunnerContainerService()
        runner.pre_run()
        (status, output, _) = runner.run({'row_index': 'e'})
        self.assertEqual(status, LIVEACTION_STATUS_SUCCEEDED)
        self.assertTrue(output is not None)
        self.assertEqual(output['result'], [1, 2])

    def test_simple_action_config_value_provided_overriden_in_datastore(self):
        wrapper = PythonActionWrapper(pack='dummy_pack_5', file_path=PASCAL_ROW_ACTION_PATH,
                                      user='joe')

        # No values provided in the datastore
        instance = wrapper._get_action_instance()
        self.assertEqual(instance.config['api_key'], 'some_api_key')  # static value
        self.assertEqual(instance.config['regions'], ['us-west-1'])  # static value
        self.assertEqual(instance.config['api_secret'], None)
        self.assertEqual(instance.config['private_key_path'], None)

        # api_secret overriden in the datastore (user scoped value)
        config_service.set_datastore_value_for_config_key(pack_name='dummy_pack_5',
                                                          key_name='api_secret',
                                                          user='joe',
                                                          value='foosecret',
                                                          secret=True)

        # private_key_path overriden in the datastore (global / non-user scoped value)
        config_service.set_datastore_value_for_config_key(pack_name='dummy_pack_5',
                                                          key_name='private_key_path',
                                                          value='foopath')

        instance = wrapper._get_action_instance()
        self.assertEqual(instance.config['api_key'], 'some_api_key')  # static value
        self.assertEqual(instance.config['regions'], ['us-west-1'])  # static value
        self.assertEqual(instance.config['api_secret'], 'foosecret')
        self.assertEqual(instance.config['private_key_path'], 'foopath')

    def test_simple_action_fail(self):
        runner = pythonrunner.get_runner()
        runner.action = self._get_mock_action_obj()
        runner.runner_parameters = {}
        runner.entry_point = PASCAL_ROW_ACTION_PATH
        runner.container_service = service.RunnerContainerService()
        runner.pre_run()
        (status, result, _) = runner.run({'row_index': '4'})
        self.assertTrue(result is not None)
        self.assertEqual(status, LIVEACTION_STATUS_FAILED)

    def test_simple_action_no_file(self):
        runner = pythonrunner.get_runner()
        runner.action = self._get_mock_action_obj()
        runner.runner_parameters = {}
        runner.entry_point = 'foo.py'
        runner.container_service = service.RunnerContainerService()
        runner.pre_run()
        (status, result, _) = runner.run({})
        self.assertTrue(result is not None)
        self.assertEqual(status, LIVEACTION_STATUS_FAILED)

    def test_simple_action_no_entry_point(self):
        runner = pythonrunner.get_runner()
        runner.action = self._get_mock_action_obj()
        runner.runner_parameters = {}
        runner.entry_point = ''
        runner.container_service = service.RunnerContainerService()

        expected_msg = 'Action .*? is missing entry_point attribute'
        self.assertRaisesRegexp(Exception, expected_msg, runner.run, {})

    @mock.patch('st2common.util.green.shell.subprocess.Popen')
    def test_action_with_user_supplied_env_vars(self, mock_popen):
        env_vars = {'key1': 'val1', 'key2': 'val2', 'PYTHONPATH': 'foobar'}

        mock_process = mock.Mock()
        mock_process.communicate.return_value = ('', '')
        mock_popen.return_value = mock_process

        runner = pythonrunner.get_runner()
        runner.action = self._get_mock_action_obj()
        runner.runner_parameters = {'env': env_vars}
        runner.entry_point = PASCAL_ROW_ACTION_PATH
        runner.container_service = service.RunnerContainerService()
        runner.pre_run()
        (_, _, _) = runner.run({'row_index': 4})

        _, call_kwargs = mock_popen.call_args
        actual_env = call_kwargs['env']

        for key, value in env_vars.items():
            # Verify that a blacklsited PYTHONPATH has been filtered out
            if key == 'PYTHONPATH':
                self.assertTrue(actual_env[key] != value)
            else:
                self.assertEqual(actual_env[key], value)

    @mock.patch('st2common.util.green.shell.subprocess.Popen')
    def test_stdout_interception_and_parsing(self, mock_popen):
        values = {'delimiter': ACTION_OUTPUT_RESULT_DELIMITER}

        # No output to stdout and no result (implicit None)
        mock_stdout = '%(delimiter)sNone%(delimiter)s' % values
        mock_stderr = 'foo stderr'
        mock_process = mock.Mock()
        mock_process.communicate.return_value = (mock_stdout, mock_stderr)
        mock_process.returncode = 0
        mock_popen.return_value = mock_process

        runner = pythonrunner.get_runner()
        runner.action = self._get_mock_action_obj()
        runner.runner_parameters = {}
        runner.entry_point = PASCAL_ROW_ACTION_PATH
        runner.container_service = service.RunnerContainerService()
        runner.pre_run()
        (_, output, _) = runner.run({'row_index': 4})

        self.assertEqual(output['stdout'], '')
        self.assertEqual(output['stderr'], mock_stderr)
        self.assertEqual(output['result'], 'None')
        self.assertEqual(output['exit_code'], 0)

        # Output to stdout, no result (implicit None),return_code 1 and status
        # failed
        mock_stdout = 'pre result%(delimiter)sNone%(delimiter)spost result' % values
        mock_stderr = 'foo stderr'
        mock_process = mock.Mock()
        mock_process.communicate.return_value = (mock_stdout, mock_stderr)
        mock_process.returncode = 1
        mock_popen.return_value = mock_process

        runner = pythonrunner.get_runner()
        runner.action = self._get_mock_action_obj()
        runner.runner_parameters = {}
        runner.entry_point = PASCAL_ROW_ACTION_PATH
        runner.container_service = service.RunnerContainerService()
        runner.pre_run()
        (status, output, _) = runner.run({'row_index': 4})
        self.assertEqual(output['stdout'], 'pre resultpost result')
        self.assertEqual(output['stderr'], mock_stderr)
        self.assertEqual(output['result'], 'None')
        self.assertEqual(output['exit_code'], 1)
        self.assertEqual(status, 'failed')

        # Output to stdout, no result (implicit None), return_code 1 and status
        # succedded
        mock_stdout = 'pre result%(delimiter)sNone%(delimiter)spost result' % values
        mock_stderr = 'foo stderr'
        mock_process = mock.Mock()
        mock_process.communicate.return_value = (mock_stdout, mock_stderr)
        mock_process.returncode = 0
        mock_popen.return_value = mock_process
        runner = pythonrunner.get_runner()
        runner.action = self._get_mock_action_obj()
        runner.runner_parameters = {}
        runner.entry_point = PASCAL_ROW_ACTION_PATH
        runner.container_service = service.RunnerContainerService()
        runner.pre_run()
        (status, output, _) = runner.run({'row_index': 4})
        self.assertEqual(output['stdout'], 'pre resultpost result')
        self.assertEqual(output['stderr'], mock_stderr)
        self.assertEqual(output['result'], 'None')
        self.assertEqual(output['exit_code'], 0)
        self.assertEqual(status, 'succeeded')

    @mock.patch('st2common.util.green.shell.subprocess.Popen')
    def test_common_st2_env_vars_are_available_to_the_action(self, mock_popen):
        mock_process = mock.Mock()
        mock_process.communicate.return_value = ('', '')
        mock_popen.return_value = mock_process

        runner = pythonrunner.get_runner()
        runner.auth_token = mock.Mock()
        runner.auth_token.token = 'ponies'
        runner.action = self._get_mock_action_obj()
        runner.runner_parameters = {}
        runner.entry_point = PASCAL_ROW_ACTION_PATH
        runner.container_service = service.RunnerContainerService()
        runner.pre_run()
        (_, _, _) = runner.run({'row_index': 4})

        _, call_kwargs = mock_popen.call_args
        actual_env = call_kwargs['env']
        self.assertCommonSt2EnvVarsAvailableInEnv(env=actual_env)

    def test_action_class_instantiation_action_service_argument(self):
        class Action1(Action):
            # Constructor not overriden so no issue here
            pass

            def run(self):
                pass

        class Action2(Action):
            # Constructor overriden, but takes action_service argument
            def __init__(self, config, action_service=None):
                super(Action2, self).__init__(config=config,
                                              action_service=action_service)

            def run(self):
                pass

        class Action3(Action):
            # Constructor overriden, but doesn't take to action service
            def __init__(self, config):
                super(Action3, self).__init__(config=config)

            def run(self):
                pass

        config = {'a': 1, 'b': 2}
        action_service = 'ActionService!'

        action1 = get_action_class_instance(action_cls=Action1, config=config,
                                            action_service=action_service)
        self.assertEqual(action1.config, config)
        self.assertEqual(action1.action_service, action_service)

        action2 = get_action_class_instance(action_cls=Action2, config=config,
                                            action_service=action_service)
        self.assertEqual(action2.config, config)
        self.assertEqual(action2.action_service, action_service)

        action3 = get_action_class_instance(action_cls=Action3, config=config,
                                            action_service=action_service)
        self.assertEqual(action3.config, config)
        self.assertEqual(action3.action_service, action_service)

    def test_action_with_same_module_name_as_module_in_stdlib(self):
        runner = pythonrunner.get_runner()
        runner.action = self._get_mock_action_obj()
        runner.runner_parameters = {}
        runner.entry_point = TEST_ACTION_PATH
        runner.container_service = service.RunnerContainerService()
        runner.pre_run()
        (status, output, _) = runner.run({})
        self.assertEqual(status, LIVEACTION_STATUS_SUCCEEDED)
        self.assertTrue(output is not None)
        self.assertEqual(output['result'], 'test action')

    def _get_mock_action_obj(self):
        """
        Return mock action object.

        Pack gets set to the system pack so the action doesn't require a separate virtualenv.
        """
        action = mock.Mock()
        action.pack = SYSTEM_PACK_NAME
        action.entry_point = 'foo.py'
        return action

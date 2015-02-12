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
from unittest2 import TestCase

import mock

from st2actions.runners import pythonrunner
from st2actions.container import service
from st2common.constants.action import ACTIONEXEC_STATUS_SUCCEEDED, ACTIONEXEC_STATUS_FAILED
from st2common.constants.pack import SYSTEM_PACK_NAME
import st2tests.base as tests_base
import st2tests.config as tests_config


PACAL_ROW_ACTION_PATH = os.path.join(tests_base.get_resources_path(), 'packs',
                                     'pythonactions/actions/pascal_row.py')


class PythonRunnerTestCase(TestCase):

    @classmethod
    def setUpClass(cls):
        tests_config.parse_args()

    def test_runner_creation(self):
        runner = pythonrunner.get_runner()
        self.assertTrue(runner is not None, 'Creation failed. No instance.')
        self.assertEqual(type(runner), pythonrunner.PythonRunner, 'Creation failed. No instance.')

    def test_simple_action(self):
        runner = pythonrunner.get_runner()
        runner.action = self._get_mock_action_obj()
        runner.runner_parameters = {}
        runner.entry_point = PACAL_ROW_ACTION_PATH
        runner.container_service = service.RunnerContainerService()
        runner.pre_run()
        (status, result, context) = runner.run({'row_index': 4})
        self.assertEqual(status, ACTIONEXEC_STATUS_SUCCEEDED)
        self.assertTrue(result is not None)
        self.assertEqual(result['result'], [1, 4, 6, 4, 1])

    def test_simple_action_fail(self):
        runner = pythonrunner.get_runner()
        runner.action = self._get_mock_action_obj()
        runner.runner_parameters = {}
        runner.entry_point = PACAL_ROW_ACTION_PATH
        runner.container_service = service.RunnerContainerService()
        runner.pre_run()
        (status, result, context) = runner.run({'row_index': '4'})
        self.assertTrue(result is not None)
        self.assertEqual(status, ACTIONEXEC_STATUS_FAILED)

    def test_simple_action_no_file(self):
        runner = pythonrunner.get_runner()
        runner.action = self._get_mock_action_obj()
        runner.runner_parameters = {}
        runner.entry_point = 'foo.py'
        runner.container_service = service.RunnerContainerService()
        runner.pre_run()
        (status, result, context) = runner.run({})
        self.assertTrue(result is not None)
        self.assertEqual(status, ACTIONEXEC_STATUS_FAILED)

    def test_simple_action_no_entry_point(self):
        runner = pythonrunner.get_runner()
        runner.action = self._get_mock_action_obj()
        runner.runner_parameters = {}
        runner.entry_point = ''
        runner.container_service = service.RunnerContainerService()

        expected_msg = 'Action .*? is missing entry_point attribute'
        self.assertRaisesRegexp(Exception, expected_msg, runner.run, {})

    @mock.patch('st2actions.runners.pythonrunner.subprocess.Popen')
    def test_action_with_user_supplied_env_vars(self, mock_popen):
        env_vars = {'key1': 'val1', 'key2': 'val2', 'PYTHONPATH': 'foobar'}

        mock_process = mock.Mock()
        mock_process.communicate.return_value = ('', '')
        mock_popen.return_value = mock_process

        runner = pythonrunner.get_runner()
        runner.action = self._get_mock_action_obj()
        runner.runner_parameters = {'env': env_vars}
        runner.entry_point = PACAL_ROW_ACTION_PATH
        runner.container_service = service.RunnerContainerService()
        runner.pre_run()
        (status, result, context) = runner.run({'row_index': 4})

        call_args, call_kwargs = mock_popen.call_args
        actual_env = call_kwargs['env']

        for key, value in env_vars.items():
            # Verify that a blacklsited PYTHONPATH has been filtered out
            if key == 'PYTHONPATH':
                self.assertTrue(actual_env[key] != value)
            else:
                self.assertEqual(actual_env[key], value)

    def _get_mock_action_obj(self):
        """
        Return mock action object.

        Pack gets set to the system pack so the action doesn't require a separate virtualenv.
        """
        action = mock.Mock()
        action.pack = SYSTEM_PACK_NAME
        action.entry_point = 'foo.py'
        return action

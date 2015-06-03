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

# XXX: FabricRunner import depends on config being setup.
import st2tests.config as tests_config
tests_config.parse_args()

import mock
from unittest2 import TestCase

from st2actions.runners.fabric_runner import BaseFabricRunner
from st2common.constants.action import LIVEACTION_STATUS_SUCCEEDED, LIVEACTION_STATUS_FAILED
from st2common.models.system.action import RemoteScriptAction
from st2common.models.system.action import FabricRemoteScriptAction


class FabricRunner(BaseFabricRunner):
    def run(self):
        pass


class FabricRunnerTestCase(TestCase):
    def test_get_env_vars(self):
        env_vars = {'key1': 'val1', 'key2': 'val2'}

        runner = FabricRunner('id')
        runner.runner_parameters = {'hosts': 'localhost', 'env': env_vars}
        # This is awful, context is just set at some point, no idea when and
        # where MOVE IT TO CONSTRUCTOR!11
        runner.context = {}
        runner.pre_run()

        actual_env_vars = runner._get_env_vars()
        self.assertEqual(actual_env_vars, env_vars)


class TestFabricRunnerResultStatus(TestCase):

    def test_pf_ok_all_success(self):
        result = {
            '1': {'succeeded': True},
            '2': {'succeeded': True},
            '3': {'succeeded': True},
        }
        self.assertEquals(LIVEACTION_STATUS_SUCCEEDED,
                          FabricRunner._get_result_status(result, True))

    def test_pf_ok_some_success(self):
        result = {
            '1': {'succeeded': False},
            '2': {'succeeded': True},
            '3': {'succeeded': False},
        }
        self.assertEquals(LIVEACTION_STATUS_SUCCEEDED,
                          FabricRunner._get_result_status(result, True))

        result = {
            '1': {'succeeded': True},
            '2': {'succeeded': False},
            '3': {'succeeded': False},
        }
        self.assertEquals(LIVEACTION_STATUS_SUCCEEDED,
                          FabricRunner._get_result_status(result, True))

        result = {
            '1': {'succeeded': False},
            '2': {'succeeded': False},
            '3': {'succeeded': True},
        }
        self.assertEquals(LIVEACTION_STATUS_SUCCEEDED,
                          FabricRunner._get_result_status(result, True))

    def test_pf_ok_all_fail(self):
        result = {
            '1': {'succeeded': False},
            '2': {'succeeded': False},
            '3': {'succeeded': False},
        }
        self.assertEquals(LIVEACTION_STATUS_FAILED,
                          FabricRunner._get_result_status(result, True))

    def test_pf_not_ok_all_success(self):
        result = {
            '1': {'succeeded': True},
            '2': {'succeeded': True},
            '3': {'succeeded': True},
        }
        self.assertEquals(LIVEACTION_STATUS_SUCCEEDED,
                          FabricRunner._get_result_status(result, False))

    def test_pf_not_ok_some_success(self):
        result = {
            '1': {'succeeded': False},
            '2': {'succeeded': True},
            '3': {'succeeded': False},
        }
        self.assertEquals(LIVEACTION_STATUS_FAILED,
                          FabricRunner._get_result_status(result, False))

        result = {
            '1': {'succeeded': True},
            '2': {'succeeded': False},
            '3': {'succeeded': False},
        }
        self.assertEquals(LIVEACTION_STATUS_FAILED,
                          FabricRunner._get_result_status(result, False))

        result = {
            '1': {'succeeded': False},
            '2': {'succeeded': False},
            '3': {'succeeded': True},
        }
        self.assertEquals(LIVEACTION_STATUS_FAILED,
                          FabricRunner._get_result_status(result, False))

    def test_pf_not_ok_all_fail(self):
        result = {
            '1': {'succeeded': False},
            '2': {'succeeded': False},
            '3': {'succeeded': False},
        }
        self.assertEquals(LIVEACTION_STATUS_FAILED,
                          FabricRunner._get_result_status(result, False))


class RemoteScriptActionTestCase(TestCase):
    def test_parameter_formatting(self):
        # Only named args
        named_args = {'--foo1': 'bar1', '--foo2': 'bar2', '--foo3': True,
                      '--foo4': False}

        action = RemoteScriptAction(name='foo', action_exec_id='dummy',
                                    script_local_path_abs='test.py',
                                    script_local_libs_path_abs='/',
                                    remote_dir='/tmp',
                                    named_args=named_args, positional_args=None)
        self.assertEqual(action.command, '/tmp/test.py --foo1=bar1 --foo2=bar2 --foo3')


class FabricRemoteScriptActionTestCase(TestCase):

    @mock.patch('st2common.models.system.action.run')
    @mock.patch('st2common.models.system.action.put')
    @mock.patch('st2common.models.system.action.shell_env')
    @mock.patch('st2common.models.system.action.settings')
    def test_settings_are_used(self, mock_settings, mock_shell_env, mock_put, mock_run):
        # Test that the remote script action uses fabric environment and authentication settings
        named_args = {}
        action = FabricRemoteScriptAction(name='foo', action_exec_id='dummy',
                                          script_local_path_abs='test.py',
                                          script_local_libs_path_abs='/',
                                          remote_dir='/tmp',
                                          named_args=named_args, positional_args=None)

        task = action.get_fabric_task()

        self.assertEqual(mock_settings.call_count, 0)
        self.assertEqual(mock_shell_env.call_count, 0)
        task.run()
        self.assertEqual(mock_settings.call_count, 1)
        self.assertEqual(mock_shell_env.call_count, 1)

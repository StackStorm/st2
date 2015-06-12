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

from unittest2 import TestCase

import st2actions.runners.cloudslang.cloudslang_runner as csr
from st2common.constants.action import LIVEACTION_STATUS_SUCCEEDED
from st2common.constants.action import LIVEACTION_STATUS_FAILED

import st2tests.config as tests_config
tests_config.parse_args()


class CloudSlangRunnerTestCase(TestCase):

    def test_runner_creation(self):
        runner = csr.get_runner()
        self.assertTrue(runner)
        self.assertTrue(runner.runner_id)

    def test_pre_run_sets_attributes(self):
        entry_point = 'path'
        inputs = {'a': 1}
        timeout = 10

        runner = csr.get_runner()
        runner.entry_point = entry_point
        runner.runner_parameters = {
            csr.RUNNER_INPUTS: inputs,
            csr.RUNNER_TIMEOUT: timeout,
        }
        tests_config._register_mistral_opts()
        runner.pre_run()
        self.assertEqual(runner.entry_point, entry_point)
        self.assertEqual(runner._inputs, inputs)
        self.assertEqual(runner._timeout, timeout)

    @mock.patch('st2actions.runners.cloudslang.cloudslang_runner.quote_unix')
    @mock.patch('st2actions.runners.cloudslang.cloudslang_runner.run_command')
    def test_run_calls_a_new_process_success(self, mock_run_command, mock_quote_unix):
        entry_point = 'path'
        timeout = 1

        runner = csr.get_runner()
        runner.entry_point = entry_point
        runner.runner_parameters = {
            csr.RUNNER_INPUTS: None,
            csr.RUNNER_TIMEOUT: timeout,
        }
        runner.pre_run()
        mock_run_command.return_value = (0, "", "", False)
        mock_quote_unix.return_value = ""
        result = runner.run({})
        mock_quote_unix.assert_called_with(tests_config.CONF.cloudslang.home_dir)
        self.assertTrue(mock_run_command.called)
        self.assertEqual(LIVEACTION_STATUS_SUCCEEDED, result[0])

    @mock.patch('st2actions.runners.cloudslang.cloudslang_runner.quote_unix')
    @mock.patch('st2actions.runners.cloudslang.cloudslang_runner.run_command')
    def test_run_calls_a_new_process_failure(self, mock_run_command, mock_quote_unix):
        timeout = 1
        runner = csr.get_runner()
        runner.runner_parameters = {
            csr.RUNNER_INPUTS: None,
            csr.RUNNER_TIMEOUT: timeout,
        }
        runner.pre_run()
        mock_run_command.return_value = (1, "", "", False)
        mock_quote_unix.return_value = ""
        result = runner.run({})
        mock_quote_unix.assert_called_with(tests_config.CONF.cloudslang.home_dir)
        self.assertTrue(mock_run_command.called)
        self.assertEqual(LIVEACTION_STATUS_FAILED, result[0])

    @mock.patch('st2actions.runners.cloudslang.cloudslang_runner.run_command')
    def test_run_calls_a_new_process_timeout(self, mock_run_command):
        entry_point = 'path'
        timeout = 1
        runner = csr.get_runner()
        runner.entry_point = entry_point
        runner.runner_parameters = {
            csr.RUNNER_INPUTS: None,
            csr.RUNNER_TIMEOUT: timeout,
        }
        runner.pre_run()
        mock_run_command.return_value = (0, "", "", True)
        result = runner.run({})
        self.assertTrue(mock_run_command.called)
        self.assertEqual(LIVEACTION_STATUS_FAILED, result[0])

    @mock.patch('st2actions.runners.cloudslang.cloudslang_runner.run_command')
    @mock.patch('st2actions.runners.cloudslang.cloudslang_runner.yaml.safe_dump')
    def test_inputs_are_save_to_file_properly(self, mock_yaml_dump, mock_run_command):
        entry_point = 'path'
        inputs = {'a': 1}
        timeout = 1
        runner = csr.get_runner()
        runner.entry_point = entry_point
        runner.runner_parameters = {
            csr.RUNNER_INPUTS: inputs,
            csr.RUNNER_TIMEOUT: timeout,
        }
        runner.pre_run()
        mock_run_command.return_value = (0, "", "", True)
        mock_yaml_dump.return_value = ""
        result = runner.run({})
        self.assertTrue(mock_run_command.called)
        mock_yaml_dump.assert_called_with(inputs, default_flow_style=False)
        self.assertEqual(LIVEACTION_STATUS_FAILED, result[0])

    @mock.patch('st2actions.runners.cloudslang.cloudslang_runner.run_command')
    @mock.patch('st2actions.runners.cloudslang.cloudslang_runner.os.remove')
    def test_temp_file_deletes_when_exception_occurs(self, mock_os_remove, mock_run_command):
        entry_point = 'path'
        inputs = {'a': 1}
        timeout = 1
        runner = csr.get_runner()
        runner.entry_point = entry_point
        runner.runner_parameters = {
            csr.RUNNER_INPUTS: inputs,
            csr.RUNNER_TIMEOUT: timeout,
        }
        runner.pre_run()
        mock_run_command.return_value = (0, "", "", True)
        mock_run_command.side_effect = IOError('Boom!')
        with self.assertRaisesRegex(IOError, "Boom!"):
            runner.run({})
        self.assertTrue(mock_os_remove.called)

        # lets really remove it now
        os.remove(mock_os_remove.call_args[0][0])

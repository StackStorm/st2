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
import os
from unittest2 import TestCase

import mock
from six.moves import zip

from st2common.constants.action import LIVEACTION_STATUS_SUCCEEDED
from st2common.constants.action import LIVEACTION_STATUS_FAILED
from st2common.constants.action import LIVEACTION_STATUS_TIMED_OUT

from windows_runner.windows_command_runner import BaseWindowsRunner
from windows_runner.windows_script_runner import WindowsScriptRunner

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FIXTURES_DIR = os.path.abspath(os.path.join(BASE_DIR, '../fixtures/windows'))


class WindowsRunnerTestCase(TestCase):
    def test_get_winexe_command_args(self):
        arguments = [
            {
                'host': 'localhost',
                'username': 'Administrator1',
                'password': 'bar1',
                'command': 'powershell.exe "C:\\\\myscript.ps1"'
            },
            {
                'host': '127.0.0.1',
                'username': 'Administrator2',
                'password': 'bar2',
                'command': 'dir'
            },
            {
                'host': 'localhost',
                'username': 'Administrator3',
                'password': 'bar3',
                'command': 'dir',
                'domain': 'MyDomain'
            }
        ]
        expected_values = [
            [
                'winexe',
                '--interactive', '0',
                '-U', 'Administrator1%bar1',
                '//localhost',
                'powershell.exe "C:\\\\myscript.ps1"'
            ],
            [
                'winexe',
                '--interactive', '0',
                '-U', 'Administrator2%bar2',
                '//127.0.0.1',
                'dir'
            ],
            [
                'winexe',
                '--interactive', '0',
                '-U', 'MyDomain\Administrator3%bar3',
                '//localhost',
                'dir'
            ]
        ]

        runner = self._get_base_runner()
        for arguments, expected_value in zip(arguments, expected_values):
            actual_value = runner._get_winexe_command_args(**arguments)
            self.assertEqual(actual_value, expected_value)

    def test_get_smbclient_command_args(self):
        arguments = [
            {
                'host': 'localhost',
                'username': 'Administrator1',
                'password': 'bar1',
                'command': 'put /home/1.txt 1.txt',
                'share': 'C$'
            },
            {
                'host': 'localhost',
                'username': 'Administrator2',
                'password': 'bar2',
                'command': 'put /home/2.txt 2.txt',
                'share': 'D$'
            },
            {
                'host': 'localhost',
                'username': 'Administrator3',
                'password': 'bar3',
                'command': 'dir',
                'share': 'E$',
                'domain': 'MyDomain'
            }
        ]
        expected_values = [
            [
                'smbclient',
                '-U', 'Administrator1%bar1',
                '//localhost/C$',
                '-c', 'put /home/1.txt 1.txt'
            ],
            [
                'smbclient',
                '-U', 'Administrator2%bar2',
                '//localhost/D$',
                '-c', 'put /home/2.txt 2.txt'
            ],
            [
                'smbclient',
                '-U', 'MyDomain\Administrator3%bar3',
                '//localhost/E$',
                '-c', 'dir'
            ],
        ]

        runner = self._get_base_runner()
        for arguments, expected_value in zip(arguments, expected_values):
            actual_value = runner._get_smbclient_command_args(**arguments)
            self.assertEqual(actual_value, expected_value)

    def test_get_script_args(self):
        arguments = [
            {
                'positional_args': 'a b c',
                'named_args': {
                    'arg1': 'value1',
                    'arg2': 'value2'
                }
            },
            {
                'positional_args': 'a b c',
                'named_args': {
                    'arg1': 'value1',
                    'arg2': True,
                    'arg3': False,
                    'arg4': ['foo', 'bar', 'baz']
                }
            }
        ]
        expected_values = [
            'a b c -arg1 value1 -arg2 value2',
            'a b c -arg1 value1 -arg2 -arg3:$false -arg4 foo,bar,baz'
        ]

        runner = self._get_mock_script_runner()
        for arguments, expected_value in zip(arguments, expected_values):
            actual_value = runner._get_script_arguments(**arguments)
            self.assertEqual(actual_value, expected_value)

    def test_parse_share_information(self):
        runner = self._get_mock_script_runner()

        fixture_path = os.path.join(FIXTURES_DIR, 'net_share_C_stdout.txt')
        with open(fixture_path, 'r') as fp:
            stdout = fp.read()

        result = runner._parse_share_information(stdout=stdout)

        expected_keys = ['share_name', 'path', 'remark', 'maximum_users', 'users', 'caching',
                         'permission']
        for key in expected_keys:
            self.assertTrue(key in result)

        self.assertEqual(result['share_name'], 'C$')
        self.assertEqual(result['path'], 'C:\\')
        self.assertEqual(result['users'], None)

    @mock.patch('windows_runner.windows_script_runner.run_command')
    def test_get_share_absolute_path(self, mock_run_command):
        runner = self._get_mock_script_runner()

        fixture_path = os.path.join(FIXTURES_DIR, 'net_share_C_stdout.txt')
        with open(fixture_path, 'r') as fp:
            stdout = fp.read()

        # Failure, non-zero status code
        mock_run_command.return_value = (2, '', '', False)
        self.assertRaises(Exception, runner._get_share_absolute_path, share='C$')

        # Failure, missing / corrupted data
        mock_run_command.return_value = (0, '', '', False)
        self.assertRaises(Exception, runner._get_share_absolute_path, share='C$')

        # Success, everything OK
        mock_run_command.return_value = (0, stdout, '', False)
        share_path = runner._get_share_absolute_path(share='C$')
        self.assertEqual(share_path, 'C:\\')

    def test_run_output_object_and_status(self):
        runner = self._get_mock_script_runner()

        runner._upload_file = mock.Mock(return_value=('/tmp/a', '/tmp/b'))
        runner._delete_directory = mock.Mock()
        runner._get_share_absolute_path = mock.Mock(return_value='/tmp')
        runner._parse_winexe_error = mock.Mock(return_value='')
        runner._verify_winexe_exists = mock.Mock()

        # success
        exit_code, stdout, stderr, timed_out = 0, 'stdout foo', 'stderr bar', False
        runner._run_script = mock.Mock(return_value=(exit_code, stdout, stderr, timed_out))

        runner.runner_parameters = {}
        (status, output, _) = runner.run({})

        expected_output = {
            'stdout': 'stdout foo',
            'stderr': 'stderr bar',
            'return_code': 0,
            'succeeded': True,
            'failed': False
        }

        self.assertEqual(status, LIVEACTION_STATUS_SUCCEEDED)
        self.assertDictEqual(output, expected_output)

        # failure
        exit_code, stdout, stderr, timed_out = 1, 'stdout fail', 'stderr fail', False
        runner._run_script = mock.Mock(return_value=(exit_code, stdout, stderr, timed_out))

        runner.runner_parameters = {}
        (status, output, _) = runner.run({})

        expected_output = {
            'stdout': 'stdout fail',
            'stderr': 'stderr fail',
            'return_code': 1,
            'succeeded': False,
            'failed': True
        }

        self.assertEqual(status, LIVEACTION_STATUS_FAILED)
        self.assertDictEqual(output, expected_output)

        # failure with winexe error
        exit_code, stdout, stderr, timed_out = 1, 'stdout fail 2', 'stderr fail 2', False
        runner._run_script = mock.Mock(return_value=(exit_code, stdout, stderr, timed_out))
        runner._parse_winexe_error = mock.Mock(return_value='winexe error 2')

        runner.runner_parameters = {}
        (status, output, _) = runner.run({})

        expected_output = {
            'stdout': 'stdout fail 2',
            'stderr': 'stderr fail 2',
            'return_code': 1,
            'succeeded': False,
            'failed': True,
            'error': 'winexe error 2'
        }

        # timeout with non zero exit code
        exit_code, stdout, stderr, timed_out = 200, 'stdout timeout', 'stderr timeout', True
        runner._run_script = mock.Mock(return_value=(exit_code, stdout, stderr, timed_out))
        runner._parse_winexe_error = mock.Mock(return_value=None)
        runner._timeout = 5

        runner.runner_parameters = {}
        (status, output, _) = runner.run({})

        expected_output = {
            'stdout': 'stdout timeout',
            'stderr': 'stderr timeout',
            'return_code': 200,
            'succeeded': False,
            'failed': True,
            'error': 'Action failed to complete in 5 seconds'
        }

        self.assertEqual(status, LIVEACTION_STATUS_TIMED_OUT)
        self.assertDictEqual(output, expected_output)

        # timeout with zero exit code
        exit_code, stdout, stderr, timed_out = 0, 'stdout timeout', 'stderr timeout', True
        runner._run_script = mock.Mock(return_value=(exit_code, stdout, stderr, timed_out))
        runner._timeout = 5
        runner._parse_winexe_error = mock.Mock(return_value='winexe error')

        runner.runner_parameters = {}
        (status, output, _) = runner.run({})

        expected_output = {
            'stdout': 'stdout timeout',
            'stderr': 'stderr timeout',
            'return_code': 0,
            'succeeded': False,
            'failed': True,
            'error': 'Action failed to complete in 5 seconds: winexe error'
        }

        self.assertEqual(status, LIVEACTION_STATUS_TIMED_OUT)
        self.assertDictEqual(output, expected_output)

    def test_shell_command_parameter_escaping(self):
        pass

    def _get_base_runner(self):
        class Runner(BaseWindowsRunner):
            def pre_run(self):
                pass

            def run(self):
                pass

        runner = Runner('id')
        return runner

    def _get_mock_script_runner(self, action_parameters=None):
        runner = WindowsScriptRunner('id')
        runner._host = None
        runner._username = None
        runner._password = None
        runner._timeout = None
        runner._share = None

        action_db = mock.Mock()
        action_db.pack = 'dummy_pack_1'
        action_db.entry_point = 'foo.py'
        action_db.parameters = action_parameters or {}

        runner.action = action_db

        return runner

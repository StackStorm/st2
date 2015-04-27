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

from st2actions.runners.windows_runner import BaseWindowsRunner
from st2actions.runners.windows_script_runner import WindowsScriptRunner

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
                '-U', 'Administrator1',
                '--password', 'bar1',
                '//localhost',
                'powershell.exe "C:\\\\myscript.ps1"'
            ],
            [
                'winexe',
                '--interactive', '0',
                '-U', 'Administrator2',
                '--password', 'bar2',
                '//127.0.0.1',
                'dir'
            ],
            [
                'winexe',
                '--interactive', '0',
                '-U', 'MyDomain\Administrator3',
                '--password', 'bar3',
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

    def test_parse_share_information(self):
        runner = self._get_script_runner()

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

    @mock.patch('st2actions.runners.windows_script_runner.run_command')
    def test_get_share_absolute_path(self, mock_run_command):
        runner = self._get_script_runner()

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

    def _get_script_runner(self):
        runner = WindowsScriptRunner('id')
        runner._host = None
        runner._username = None
        runner._password = None
        runner._timeout = None

        return runner

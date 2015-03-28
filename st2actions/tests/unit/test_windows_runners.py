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

from unittest2 import TestCase

from st2actions.runners.windows_runner import BaseWindowsRunner


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

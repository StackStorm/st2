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

import pwd
import os
import copy
import unittest2

from st2common.models.system.action import ShellCommandAction
from st2common.models.system.action import ShellScriptAction


CURRENT_DIR = os.path.dirname(os.path.realpath(__file__))
FIXTURES_DIR = os.path.abspath(os.path.join(CURRENT_DIR, '../fixtures'))
LOGGED_USER_USERNAME = pwd.getpwuid(os.getuid())[0]


class ShellCommandActionTestCase(unittest2.TestCase):
    def setUp(self):
        self._base_kwargs = {
            'name': 'test action',
            'action_exec_id': '1',
            'command': 'ls -la',
            'env_vars': {},
            'timeout': None
        }

    def test_user_argument(self):
        # User is the same as logged user, no sudo should be used
        kwargs = copy.deepcopy(self._base_kwargs)
        kwargs['sudo'] = False
        kwargs['user'] = LOGGED_USER_USERNAME
        action = ShellCommandAction(**kwargs)
        command = action.get_full_command_string()
        self.assertEqual(command, 'ls -la')

        # User is different, sudo should be used
        kwargs = copy.deepcopy(self._base_kwargs)
        kwargs['sudo'] = False
        kwargs['user'] = 'mauser'
        action = ShellCommandAction(**kwargs)
        command = action.get_full_command_string()
        self.assertEqual(command, 'sudo -E -u mauser -- bash -c \'ls -la\'')

        # sudo is used, it doesn't matter what user is specified since the
        # command should run as root
        kwargs = copy.deepcopy(self._base_kwargs)
        kwargs['sudo'] = True
        kwargs['user'] = 'mauser'
        action = ShellCommandAction(**kwargs)
        command = action.get_full_command_string()
        self.assertEqual(command, 'sudo -E -- bash -c \'ls -la\'')


class ShellScriptActionTestCase(unittest2.TestCase):
    def setUp(self):
        self._base_kwargs = {
            'name': 'test action',
            'action_exec_id': '1',
            'script_local_path_abs': '/tmp/foo.sh',
            'named_args': {},
            'positional_args': [],
            'env_vars': {},
            'timeout': None
        }

    def _get_fixture(self, name):
        path = os.path.join(FIXTURES_DIR, 'localrunner', name)

        with open(path, 'r') as fp:
            content = fp.read().strip()

        return content

    def test_user_argument(self):
        # User is the same as logged user, no sudo should be used
        kwargs = copy.deepcopy(self._base_kwargs)
        kwargs['sudo'] = False
        kwargs['user'] = LOGGED_USER_USERNAME
        action = ShellScriptAction(**kwargs)
        command = action.get_full_command_string()
        self.assertEqual(command, '/tmp/foo.sh')

        # User is different, sudo should be used
        kwargs = copy.deepcopy(self._base_kwargs)
        kwargs['sudo'] = False
        kwargs['user'] = 'mauser'
        action = ShellScriptAction(**kwargs)
        command = action.get_full_command_string()
        self.assertEqual(command, 'sudo -E -u mauser -- bash -c /tmp/foo.sh')

        # sudo is used, it doesn't matter what user is specified since the
        # command should run as root
        kwargs = copy.deepcopy(self._base_kwargs)
        kwargs['sudo'] = True
        kwargs['user'] = 'mauser'
        action = ShellScriptAction(**kwargs)
        command = action.get_full_command_string()
        self.assertEqual(command, 'sudo -E -- bash -c /tmp/foo.sh')

    def test_command_construction_with_parameters(self):
        # same user, named args, no positional args
        kwargs = copy.deepcopy(self._base_kwargs)
        kwargs['sudo'] = False
        kwargs['user'] = LOGGED_USER_USERNAME
        kwargs['named_args'] = {'key1': 'value1', 'key2': 'value2'}
        kwargs['positional_args'] = []
        action = ShellScriptAction(**kwargs)
        command = action.get_full_command_string()
        self.assertEqual(command, '/tmp/foo.sh key2=value2 key1=value1')

        # different user, named args, no positional args
        kwargs = copy.deepcopy(self._base_kwargs)
        kwargs['sudo'] = False
        kwargs['user'] = 'mauser'
        kwargs['named_args'] = {'key1': 'value1', 'key2': 'value2'}
        kwargs['positional_args'] = []
        action = ShellScriptAction(**kwargs)
        command = action.get_full_command_string()
        expected = 'sudo -E -u mauser -- bash -c \'/tmp/foo.sh key2=value2 key1=value1\''
        self.assertEqual(command, expected)

        # same user, positional args, no named args
        kwargs = copy.deepcopy(self._base_kwargs)
        kwargs['sudo'] = False
        kwargs['user'] = LOGGED_USER_USERNAME
        kwargs['named_args'] = {}
        kwargs['positional_args'] = ['ein', 'zwei', 'drei']
        action = ShellScriptAction(**kwargs)
        command = action.get_full_command_string()
        self.assertEqual(command, '/tmp/foo.sh ein zwei drei')

        # different user, named args, positional args
        kwargs = copy.deepcopy(self._base_kwargs)
        kwargs['sudo'] = False
        kwargs['user'] = 'mauser'
        kwargs['named_args'] = {}
        kwargs['positional_args'] = ['ein', 'zwei', 'drei']
        action = ShellScriptAction(**kwargs)
        command = action.get_full_command_string()
        expected = 'sudo -E -u mauser -- bash -c \'/tmp/foo.sh ein zwei drei\''
        self.assertEqual(command, expected)

        # same user, positional and named args
        kwargs = copy.deepcopy(self._base_kwargs)
        kwargs['sudo'] = False
        kwargs['user'] = LOGGED_USER_USERNAME
        kwargs['named_args'] = {'key1': 'value1', 'key2': 'value2'}
        kwargs['positional_args'] = ['ein', 'zwei', 'drei']
        action = ShellScriptAction(**kwargs)
        command = action.get_full_command_string()
        self.assertEqual(command, '/tmp/foo.sh key2=value2 key1=value1 ein zwei drei')

        # different user, positional and named args
        kwargs = copy.deepcopy(self._base_kwargs)
        kwargs['sudo'] = False
        kwargs['user'] = 'mauser'
        kwargs['named_args'] = {'key1': 'value1', 'key2': 'value2'}
        kwargs['positional_args'] = ['ein', 'zwei', 'drei']
        action = ShellScriptAction(**kwargs)
        command = action.get_full_command_string()
        expected = ('sudo -E -u mauser -- bash -c \'/tmp/foo.sh key2=value2 '
                    'key1=value1 ein zwei drei\'')
        self.assertEqual(command, expected)

    def test_named_parameter_escaping(self):
        # no sudo
        kwargs = copy.deepcopy(self._base_kwargs)
        kwargs['sudo'] = False
        kwargs['user'] = LOGGED_USER_USERNAME
        kwargs['named_args'] = {
            'key1': 'value foo bar',
            'key2': 'value "bar" foo',
            'key3': 'date ; whoami',
            'key4': '"date ; whoami"',
        }
        action = ShellScriptAction(**kwargs)
        command = action.get_full_command_string()
        expected = self._get_fixture('escaping_test_command_1.txt')
        self.assertEqual(command, expected)

        # sudo
        kwargs = copy.deepcopy(self._base_kwargs)
        kwargs['sudo'] = True
        kwargs['user'] = LOGGED_USER_USERNAME
        kwargs['named_args'] = {
            'key1': 'value foo bar',
            'key2': 'value "bar" foo',
            'key3': 'date ; whoami',
            'key4': '"date ; whoami"',
        }
        action = ShellScriptAction(**kwargs)
        command = action.get_full_command_string()
        expected = self._get_fixture('escaping_test_command_2.txt')
        self.assertEqual(command, expected)

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
import json
import mock
import logging

from tests import base

from st2client import shell
from st2client.utils import httpclient


LOG = logging.getLogger(__name__)


class TestShell(base.BaseCLITestCase):

    def __init__(self, *args, **kwargs):
        super(TestShell, self).__init__(*args, **kwargs)
        self.shell = shell.Shell()

    def setUp(self):
        super(TestShell, self).setUp()

        # Setup environment.
        for var in ['ST2_BASE_URL', 'ST2_AUTH_URL', 'ST2_API_URL']:
            if var in os.environ:
                del os.environ[var]

    def test_endpoints_default(self):
        base_url = 'http://localhost'
        auth_url = 'https://localhost:9100'
        api_url = 'http://localhost:9101/v1'
        args = ['trigger', 'list']
        parsed_args = self.shell.parser.parse_args(args)
        client = self.shell.get_client(parsed_args)
        self.assertEqual(client.endpoints['base'], base_url)
        self.assertEqual(client.endpoints['auth'], auth_url)
        self.assertEqual(client.endpoints['api'], api_url)

    def test_endpoints_base_url_from_cli(self):
        base_url = 'http://www.st2.com'
        auth_url = 'https://www.st2.com:9100'
        api_url = 'http://www.st2.com:9101/v1'
        args = ['--url', base_url, 'trigger', 'list']
        parsed_args = self.shell.parser.parse_args(args)
        client = self.shell.get_client(parsed_args)
        self.assertEqual(client.endpoints['base'], base_url)
        self.assertEqual(client.endpoints['auth'], auth_url)
        self.assertEqual(client.endpoints['api'], api_url)

    def test_endpoints_base_url_from_env(self):
        base_url = 'http://www.st2.com'
        auth_url = 'https://www.st2.com:9100'
        api_url = 'http://www.st2.com:9101/v1'
        os.environ['ST2_BASE_URL'] = base_url
        args = ['trigger', 'list']
        parsed_args = self.shell.parser.parse_args(args)
        client = self.shell.get_client(parsed_args)
        self.assertEqual(client.endpoints['base'], base_url)
        self.assertEqual(client.endpoints['auth'], auth_url)
        self.assertEqual(client.endpoints['api'], api_url)

    def test_endpoints_override_from_cli(self):
        base_url = 'http://www.st2.com'
        auth_url = 'http://www.st2.com:8888'
        api_url = 'http://www.stackstorm1.com:9101/v1'
        args = ['--url', base_url,
                '--auth-url', auth_url,
                '--api-url', api_url,
                'trigger', 'list']
        parsed_args = self.shell.parser.parse_args(args)
        client = self.shell.get_client(parsed_args)
        self.assertEqual(client.endpoints['base'], base_url)
        self.assertEqual(client.endpoints['auth'], auth_url)
        self.assertEqual(client.endpoints['api'], api_url)

    def test_endpoints_override_from_env(self):
        base_url = 'http://www.st2.com'
        auth_url = 'http://www.st2.com:8888'
        api_url = 'http://www.stackstorm1.com:9101/v1'
        os.environ['ST2_BASE_URL'] = base_url
        os.environ['ST2_AUTH_URL'] = auth_url
        os.environ['ST2_API_URL'] = api_url
        args = ['trigger', 'list']
        parsed_args = self.shell.parser.parse_args(args)
        client = self.shell.get_client(parsed_args)
        self.assertEqual(client.endpoints['base'], base_url)
        self.assertEqual(client.endpoints['auth'], auth_url)
        self.assertEqual(client.endpoints['api'], api_url)

    @mock.patch.object(
        httpclient.HTTPClient, 'get',
        mock.MagicMock(return_value=base.FakeResponse(json.dumps(base.RESOURCES), 200, 'OK')))
    def test_exit_code_on_success(self):
        argv = ['trigger', 'list']
        self.assertEqual(self.shell.run(argv), 0)

    @mock.patch.object(
        httpclient.HTTPClient, 'get',
        mock.MagicMock(return_value=base.FakeResponse(None, 500, 'INTERNAL SERVER ERROR')))
    def test_exit_code_on_error(self):
        argv = ['trigger', 'list']
        self.assertEqual(self.shell.run(argv), 1)

    def _validate_parser(self, args_list, is_subcommand=True):
        for args in args_list:
            ns = self.shell.parser.parse_args(args)
            func = (self.shell.commands[args[0]].run_and_print
                    if not is_subcommand
                    else self.shell.commands[args[0]].commands[args[1]].run_and_print)
            self.assertEqual(ns.func, func)

    def test_trigger(self):
        args_list = [
            ['trigger', 'list'],
            ['trigger', 'get', 'abc'],
            ['trigger', 'create', '/tmp/trigger.json'],
            ['trigger', 'update', '123', '/tmp/trigger.json'],
            ['trigger', 'delete', 'abc']
        ]
        self._validate_parser(args_list)

    def test_rule(self):
        args_list = [
            ['rule', 'list'],
            ['rule', 'get', 'abc'],
            ['rule', 'create', '/tmp/rule.json'],
            ['rule', 'update', '123', '/tmp/rule.json'],
            ['rule', 'delete', 'abc']
        ]
        self._validate_parser(args_list)

    def test_runner(self):
        args_list = [
            ['runner', 'list'],
            ['runner', 'get', 'abc']
        ]
        self._validate_parser(args_list)

    def test_action(self):
        args_list = [
            ['action', 'list'],
            ['action', 'get', 'abc'],
            ['action', 'create', '/tmp/action.json'],
            ['action', 'update', '123', '/tmp/action.json'],
            ['action', 'delete', 'abc'],
            ['action', 'execute', '-h'],
            ['action', 'execute', 'remote', '-h'],
            ['action', 'execute', 'remote', 'hosts=192.168.1.1', 'user=st2', 'cmd="ls -l"'],
            ['action', 'execute', 'remote-fib', 'hosts=192.168.1.1', '3', '8']
        ]
        self._validate_parser(args_list)

    def test_run(self):
        args_list = [
            ['run', '-h'],
            ['run', 'abc', '-h'],
            ['run', 'remote', 'hosts=192.168.1.1', 'user=st2', 'cmd="ls -l"'],
            ['run', 'remote-fib', 'hosts=192.168.1.1', '3', '8']
        ]
        self._validate_parser(args_list, is_subcommand=False)

    def test_action_execution(self):
        args_list = [
            ['execution', 'list'],
            ['execution', 'get', '123'],
        ]
        self._validate_parser(args_list)

    def test_key(self):
        args_list = [
            ['key', 'list'],
            ['key', 'get', 'abc'],
            ['key', 'create', 'abc', '123'],
            ['key', 'update', 'abc', '456'],
            ['key', 'delete', 'abc'],
            ['key', 'load', '/tmp/keys.json']
        ]
        self._validate_parser(args_list)

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
import time
import datetime
import json
import logging
import tempfile

import mock
import unittest2

from st2client.shell import Shell
from st2client.client import Client
from st2client.utils import httpclient
from st2common.models.db.auth import TokenDB
from tests import base

LOG = logging.getLogger(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE_PATH_FULL = os.path.join(BASE_DIR, '../fixtures/st2rc.full.ini')
CONFIG_FILE_PATH_PARTIAL = os.path.join(BASE_DIR, '../fixtures/st2rc.partial.ini')

MOCK_CONFIG = """
[credentials]
username = foo
password = bar
"""


class TestShell(base.BaseCLITestCase):
    capture_output = True

    def __init__(self, *args, **kwargs):
        super(TestShell, self).__init__(*args, **kwargs)
        self.shell = Shell()

    def test_endpoints_default(self):
        base_url = 'http://127.0.0.1'
        auth_url = 'http://127.0.0.1:9100'
        api_url = 'http://127.0.0.1:9101/v1'
        args = ['trigger', 'list']
        parsed_args = self.shell.parser.parse_args(args)
        client = self.shell.get_client(parsed_args)
        self.assertEqual(client.endpoints['base'], base_url)
        self.assertEqual(client.endpoints['auth'], auth_url)
        self.assertEqual(client.endpoints['api'], api_url)

    def test_endpoints_base_url_from_cli(self):
        base_url = 'http://www.st2.com'
        auth_url = 'http://www.st2.com:9100'
        api_url = 'http://www.st2.com:9101/v1'
        args = ['--url', base_url, 'trigger', 'list']
        parsed_args = self.shell.parser.parse_args(args)
        client = self.shell.get_client(parsed_args)
        self.assertEqual(client.endpoints['base'], base_url)
        self.assertEqual(client.endpoints['auth'], auth_url)
        self.assertEqual(client.endpoints['api'], api_url)

    def test_endpoints_base_url_from_env(self):
        base_url = 'http://www.st2.com'
        auth_url = 'http://www.st2.com:9100'
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

    def test_action_execution(self):
        args_list = [
            ['execution', 'list'],
            ['execution', 'get', '123'],
            ['execution', 'get', '123', '-d'],
            ['execution', 'get', '123', '-k', 'localhost.stdout'],
            ['execution', 're-run', '123'],
            ['execution', 're-run', '123', '--tasks', 'x', 'y', 'z'],
            ['execution', 're-run', '123', '--tasks', 'x', 'y', 'z', '--no-reset', 'x'],
            ['execution', 're-run', '123', 'a=1', 'b=x', 'c=True']
        ]
        self._validate_parser(args_list)

        # Test mutually exclusive argument groups
        self.assertRaises(SystemExit, self._validate_parser,
                          [['execution', 'get', '123', '-d', '-k', 'localhost.stdout']])

    def test_key(self):
        args_list = [
            ['key', 'list'],
            ['key', 'get', 'abc'],
            ['key', 'set', 'abc', '123'],
            ['key', 'delete', 'abc'],
            ['key', 'load', '/tmp/keys.json']
        ]
        self._validate_parser(args_list)

    def test_policy(self):
        args_list = [
            ['policy', 'list'],
            ['policy', 'list', '-p', 'core'],
            ['policy', 'list', '--pack', 'core'],
            ['policy', 'list', '-r', 'core.local'],
            ['policy', 'list', '--resource-ref', 'core.local'],
            ['policy', 'list', '-pt', 'action.type1'],
            ['policy', 'list', '--policy-type', 'action.type1'],
            ['policy', 'list', '-r', 'core.local', '-pt', 'action.type1'],
            ['policy', 'list', '--resource-ref', 'core.local', '--policy-type', 'action.type1'],
            ['policy', 'get', 'abc'],
            ['policy', 'create', '/tmp/policy.json'],
            ['policy', 'update', '123', '/tmp/policy.json'],
            ['policy', 'delete', 'abc']
        ]
        self._validate_parser(args_list)

    def test_policy_type(self):
        args_list = [
            ['policy-type', 'list'],
            ['policy-type', 'list', '-r', 'action'],
            ['policy-type', 'list', '--resource-type', 'action'],
            ['policy-type', 'get', 'abc']
        ]
        self._validate_parser(args_list)

    @mock.patch('st2client.shell.ST2_CONFIG_PATH', '/home/does/not/exist')
    def test_print_config_default_config_no_config(self):
        os.environ['ST2_CONFIG_FILE'] = '/home/does/not/exist'
        argv = ['--print-config']
        self.assertEqual(self.shell.run(argv), 3)

        self.stdout.seek(0)
        stdout = self.stdout.read()

        self.assertTrue('username = None' in stdout)
        self.assertTrue('cache_token = True' in stdout)

    def test_print_config_custom_config_as_env_variable(self):
        os.environ['ST2_CONFIG_FILE'] = CONFIG_FILE_PATH_FULL
        argv = ['--print-config']
        self.assertEqual(self.shell.run(argv), 3)

        self.stdout.seek(0)
        stdout = self.stdout.read()

        self.assertTrue('username = test1' in stdout)
        self.assertTrue('cache_token = False' in stdout)

    def test_print_config_custom_config_as_command_line_argument(self):
        argv = ['--print-config', '--config-file=%s' % (CONFIG_FILE_PATH_FULL)]
        self.assertEqual(self.shell.run(argv), 3)

        self.stdout.seek(0)
        stdout = self.stdout.read()

        self.assertTrue('username = test1' in stdout)
        self.assertTrue('cache_token = False' in stdout)

    def test_run(self):
        args_list = [
            ['run', '-h'],
            ['run', 'abc', '-h'],
            ['run', 'remote', 'hosts=192.168.1.1', 'user=st2', 'cmd="ls -l"'],
            ['run', 'remote-fib', 'hosts=192.168.1.1', '3', '8']
        ]
        self._validate_parser(args_list, is_subcommand=False)

    def test_runner(self):
        args_list = [
            ['runner', 'list'],
            ['runner', 'get', 'abc']
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

    def test_trigger(self):
        args_list = [
            ['trigger', 'list'],
            ['trigger', 'get', 'abc'],
            ['trigger', 'create', '/tmp/trigger.json'],
            ['trigger', 'update', '123', '/tmp/trigger.json'],
            ['trigger', 'delete', 'abc']
        ]
        self._validate_parser(args_list)


class CLITokenCachingTestCase(unittest2.TestCase):
    def setUp(self):
        super(CLITokenCachingTestCase, self).setUp()
        self._mock_config_directory_path = tempfile.mkdtemp()
        self._mock_config_path = os.path.join(self._mock_config_directory_path, 'config')
        self._p1 = mock.patch('st2client.shell.ST2_CONFIG_DIRECTORY',
                             self._mock_config_directory_path)
        self._p2 = mock.patch('st2client.shell.ST2_CONFIG_PATH',
                             self._mock_config_path)
        self._p1.start()
        self._p2.start()

    def tearDown(self):
        super(CLITokenCachingTestCase, self).tearDown()
        self._p1.stop()
        self._p2.stop()

    def _write_mock_config(self):
        with open(self._mock_config_path, 'w') as fp:
            fp.write(MOCK_CONFIG)

    def test_get_cached_auth_token_no_token_cache_file(self):
        client = Client()
        shell = Shell()
        username = 'testu'
        password = 'testp'

        result = shell._get_cached_auth_token(client=client, username=username,
                                              password=password)
        self.assertEqual(result, None)

    def test_get_cached_auth_token_corrupted_token_cache_file(self):
        client = Client()
        shell = Shell()
        username = 'testu'
        password = 'testp'

        cached_token_path = shell._get_cached_token_path_for_user(username=username)
        with open(cached_token_path, 'w') as fp:
            fp.write('CORRRRRUPTED!')

        expected_msg = 'File (.+) with cached token is corrupted or invalid'
        self.assertRaisesRegexp(ValueError, expected_msg, shell._get_cached_auth_token,
                                client=client, username=username, password=password)

    def test_get_cached_auth_token_expired_token_in_cache_file(self):
        client = Client()
        shell = Shell()
        username = 'testu'
        password = 'testp'

        cached_token_path = shell._get_cached_token_path_for_user(username=username)
        data = {
            'token': 'expired',
            'expire_timestamp': (int(time.time()) - 10)
        }
        with open(cached_token_path, 'w') as fp:
            fp.write(json.dumps(data))

        result = shell._get_cached_auth_token(client=client, username=username,
                                              password=password)
        self.assertEqual(result, None)

    def test_get_cached_auth_token_valid_token_in_cache_file(self):
        client = Client()
        shell = Shell()
        username = 'testu'
        password = 'testp'

        cached_token_path = shell._get_cached_token_path_for_user(username=username)
        data = {
            'token': 'yayvalid',
            'expire_timestamp': (int(time.time()) + 20)
        }
        with open(cached_token_path, 'w') as fp:
            fp.write(json.dumps(data))

        result = shell._get_cached_auth_token(client=client, username=username,
                                              password=password)
        self.assertEqual(result, 'yayvalid')

    def test_cache_auth_token_success(self):
        client = Client()
        shell = Shell()
        username = 'testu'
        password = 'testp'
        expiry = datetime.datetime.utcnow() + datetime.timedelta(seconds=30)

        result = shell._get_cached_auth_token(client=client, username=username,
                                              password=password)
        self.assertEqual(result, None)

        token_db = TokenDB(user=username, token='fyeah', expiry=expiry)
        shell._cache_auth_token(token_obj=token_db)

        result = shell._get_cached_auth_token(client=client, username=username,
                                              password=password)
        self.assertEqual(result, 'fyeah')

    def test_automatic_auth_skipped_on_auth_command(self):
        self._write_mock_config()

        shell = Shell()
        shell._get_auth_token = mock.Mock()

        argv = ['auth', 'testu', '-p', 'testp']
        args = shell.parser.parse_args(args=argv)
        shell.get_client(args=args)
        self.assertEqual(shell._get_auth_token.call_count, 0)

    def test_automatic_auth_skipped_if_token_provided_as_env_variable(self):
        self._write_mock_config()

        shell = Shell()
        shell._get_auth_token = mock.Mock()

        os.environ['ST2_AUTH_TOKEN'] = 'fooo'
        argv = ['action', 'list']
        args = shell.parser.parse_args(args=argv)
        shell.get_client(args=args)
        self.assertEqual(shell._get_auth_token.call_count, 0)

    def test_automatic_auth_skipped_if_token_provided_as_cli_argument(self):
        self._write_mock_config()

        shell = Shell()
        shell._get_auth_token = mock.Mock()

        argv = ['action', 'list', '--token=bar']
        args = shell.parser.parse_args(args=argv)
        shell.get_client(args=args)
        self.assertEqual(shell._get_auth_token.call_count, 0)

        argv = ['action', 'list', '-t', 'bar']
        args = shell.parser.parse_args(args=argv)
        shell.get_client(args=args)
        self.assertEqual(shell._get_auth_token.call_count, 0)

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
import time
import datetime
import json
import logging
import shutil
import tempfile

import requests
import six
import mock
import unittest2

import st2client
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

MOCK_PACKAGE_METADATA = """
[server]
version = 2.8dev
git_sha = abcdefg
circle_build_url = https://circleci.com/gh/StackStorm/st2/7213
"""


class ShellTestCase(base.BaseCLITestCase):
    capture_output = True

    def __init__(self, *args, **kwargs):
        super(ShellTestCase, self).__init__(*args, **kwargs)
        self.shell = Shell()

    def setUp(self):
        super(ShellTestCase, self).setUp()

        if six.PY3:
            # In python --version outputs to stdout and in 2.x to stderr
            self.version_output = self.stdout
        else:
            self.version_output = self.stderr

    def test_commands_usage_and_help_strings(self):
        # No command, should print out user friendly usage / help string
        self.assertEqual(self.shell.run([]), 2)

        self.stderr.seek(0)
        stderr = self.stderr.read()
        self.assertTrue('Usage: ' in stderr)
        self.assertTrue('For example:' in stderr)
        self.assertTrue('CLI for StackStorm' in stderr)
        self.assertTrue('positional arguments:' in stderr)

        self.stdout.truncate()
        self.stderr.truncate()

        # --help should result in the same output
        try:
            self.assertEqual(self.shell.run(['--help']), 0)
        except SystemExit as e:
            self.assertEqual(e.code, 0)

        self.stdout.seek(0)
        stdout = self.stdout.read()
        self.assertTrue('Usage: ' in stdout)
        self.assertTrue('For example:' in stdout)
        self.assertTrue('CLI for StackStorm' in stdout)
        self.assertTrue('positional arguments:' in stdout)

        self.stdout.truncate()
        self.stderr.truncate()

        # Sub command with no args
        try:
            self.assertEqual(self.shell.run(['action']), 2)
        except SystemExit as e:
            self.assertEqual(e.code, 2)

        self.stderr.seek(0)
        stderr = self.stderr.read()

        self.assertTrue('usage' in stderr)

        if six.PY2:
            self.assertTrue('{list,get,create,update' in stderr)
            self.assertTrue('error: too few arguments' in stderr)

    def test_endpoints_default(self):
        base_url = 'http://127.0.0.1'
        auth_url = 'http://127.0.0.1:9100'
        api_url = 'http://127.0.0.1:9101/v1'
        stream_url = 'http://127.0.0.1:9102/v1'
        args = ['trigger', 'list']
        parsed_args = self.shell.parser.parse_args(args)
        client = self.shell.get_client(parsed_args)
        self.assertEqual(client.endpoints['base'], base_url)
        self.assertEqual(client.endpoints['auth'], auth_url)
        self.assertEqual(client.endpoints['api'], api_url)
        self.assertEqual(client.endpoints['stream'], stream_url)

    def test_endpoints_base_url_from_cli(self):
        base_url = 'http://www.st2.com'
        auth_url = 'http://www.st2.com:9100'
        api_url = 'http://www.st2.com:9101/v1'
        stream_url = 'http://www.st2.com:9102/v1'
        args = ['--url', base_url, 'trigger', 'list']
        parsed_args = self.shell.parser.parse_args(args)
        client = self.shell.get_client(parsed_args)
        self.assertEqual(client.endpoints['base'], base_url)
        self.assertEqual(client.endpoints['auth'], auth_url)
        self.assertEqual(client.endpoints['api'], api_url)
        self.assertEqual(client.endpoints['stream'], stream_url)

    def test_endpoints_base_url_from_env(self):
        base_url = 'http://www.st2.com'
        auth_url = 'http://www.st2.com:9100'
        api_url = 'http://www.st2.com:9101/v1'
        stream_url = 'http://www.st2.com:9102/v1'
        os.environ['ST2_BASE_URL'] = base_url
        args = ['trigger', 'list']
        parsed_args = self.shell.parser.parse_args(args)
        client = self.shell.get_client(parsed_args)
        self.assertEqual(client.endpoints['base'], base_url)
        self.assertEqual(client.endpoints['auth'], auth_url)
        self.assertEqual(client.endpoints['api'], api_url)
        self.assertEqual(client.endpoints['stream'], stream_url)

    def test_endpoints_override_from_cli(self):
        base_url = 'http://www.st2.com'
        auth_url = 'http://www.st2.com:8888'
        api_url = 'http://www.stackstorm1.com:9101/v1'
        stream_url = 'http://www.stackstorm1.com:9102/v1'
        args = ['--url', base_url,
                '--auth-url', auth_url,
                '--api-url', api_url,
                '--stream-url', stream_url,
                'trigger', 'list']
        parsed_args = self.shell.parser.parse_args(args)
        client = self.shell.get_client(parsed_args)
        self.assertEqual(client.endpoints['base'], base_url)
        self.assertEqual(client.endpoints['auth'], auth_url)
        self.assertEqual(client.endpoints['api'], api_url)
        self.assertEqual(client.endpoints['stream'], stream_url)

    def test_endpoints_override_from_env(self):
        base_url = 'http://www.st2.com'
        auth_url = 'http://www.st2.com:8888'
        api_url = 'http://www.stackstorm1.com:9101/v1'
        stream_url = 'http://www.stackstorm1.com:9102/v1'
        os.environ['ST2_BASE_URL'] = base_url
        os.environ['ST2_AUTH_URL'] = auth_url
        os.environ['ST2_API_URL'] = api_url
        os.environ['ST2_STREAM_URL'] = stream_url
        args = ['trigger', 'list']
        parsed_args = self.shell.parser.parse_args(args)
        client = self.shell.get_client(parsed_args)
        self.assertEqual(client.endpoints['base'], base_url)
        self.assertEqual(client.endpoints['auth'], auth_url)
        self.assertEqual(client.endpoints['api'], api_url)
        self.assertEqual(client.endpoints['stream'], stream_url)

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
            ['execution', 'list', '-a', 'all'],
            ['execution', 'list', '--attr=all'],
            ['execution', 'get', '123'],
            ['execution', 'get', '123', '-d'],
            ['execution', 'get', '123', '-k', 'localhost.stdout'],
            ['execution', 're-run', '123'],
            ['execution', 're-run', '123', '--tasks', 'x', 'y', 'z'],
            ['execution', 're-run', '123', '--tasks', 'x', 'y', 'z', '--no-reset', 'x'],
            ['execution', 're-run', '123', 'a=1', 'b=x', 'c=True'],
            ['execution', 'cancel', '123'],
            ['execution', 'cancel', '123', '456'],
            ['execution', 'pause', '123'],
            ['execution', 'pause', '123', '456'],
            ['execution', 'resume', '123'],
            ['execution', 'resume', '123', '456']
        ]
        self._validate_parser(args_list)

        # Test mutually exclusive argument groups
        self.assertRaises(SystemExit, self._validate_parser,
                          [['execution', 'get', '123', '-d', '-k', 'localhost.stdout']])

    def test_key(self):
        args_list = [
            ['key', 'list'],
            ['key', 'list', '-n', '2'],
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

    def test_pack(self):
        args_list = [
            ['pack', 'list'],
            ['pack', 'get', 'abc'],
            ['pack', 'search', 'abc'],
            ['pack', 'show', 'abc'],
            ['pack', 'remove', 'abc'],
            ['pack', 'remove', 'abc', '--detail'],
            ['pack', 'install', 'abc'],
            ['pack', 'install', 'abc', '--force'],
            ['pack', 'install', 'abc', '--detail'],
            ['pack', 'config', 'abc']
        ]
        self._validate_parser(args_list)

    @mock.patch('st2client.base.ST2_CONFIG_PATH', '/home/does/not/exist')
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
            ['rule', 'list', '-n', '1'],
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

    def test_workflow(self):
        args_list = [
            ['workflow', 'inspect', '--file', '/path/to/workflow/definition'],
            ['workflow', 'inspect', '--action', 'mock.foobar']
        ]

        self._validate_parser(args_list)

    @mock.patch('sys.exit', mock.Mock())
    @mock.patch('st2client.shell.__version__', 'v2.8.0')
    def test_get_version_no_package_metadata_file_stable_version(self):
        # stable version, package metadata file doesn't exist on disk - no git revision should be
        # included
        shell = Shell()
        shell.parser.parse_args(args=['--version'])

        self.version_output.seek(0)
        stderr = self.version_output.read()
        self.assertTrue('v2.8.0, on Python' in stderr)

    @mock.patch('sys.exit', mock.Mock())
    @mock.patch('st2client.shell.__version__', 'v2.8.0')
    def test_get_version_package_metadata_file_exists_stable_version(self):
        # stable version, package metadata file exists on disk - no git revision should be included
        package_metadata_path = self._write_mock_package_metadata_file()
        st2client.shell.PACKAGE_METADATA_FILE_PATH = package_metadata_path

        shell = Shell()
        shell.run(argv=['--version'])

        self.version_output.seek(0)
        stderr = self.version_output.read()
        self.assertTrue('v2.8.0, on Python' in stderr)

    @mock.patch('sys.exit', mock.Mock())
    @mock.patch('st2client.shell.__version__', 'v2.9dev')
    @mock.patch('st2client.shell.PACKAGE_METADATA_FILE_PATH', '/tmp/doesnt/exist.1')
    def test_get_version_no_package_metadata_file_dev_version(self):
        # dev version, package metadata file doesn't exist on disk - no git revision should be
        # included since package metadata file doesn't exist on disk
        shell = Shell()
        shell.parser.parse_args(args=['--version'])

        self.version_output.seek(0)
        stderr = self.version_output.read()
        self.assertTrue('v2.9dev, on Python' in stderr)

    @mock.patch('sys.exit', mock.Mock())
    @mock.patch('st2client.shell.__version__', 'v2.9dev')
    def test_get_version_package_metadata_file_exists_dev_version(self):
        # dev version, package metadata file exists on disk - git revision should be included
        # since package metadata file exists on disk and contains server.git_sha attribute
        package_metadata_path = self._write_mock_package_metadata_file()
        st2client.shell.PACKAGE_METADATA_FILE_PATH = package_metadata_path

        shell = Shell()
        shell.parser.parse_args(args=['--version'])

        self.version_output.seek(0)
        stderr = self.version_output.read()
        self.assertTrue('v2.9dev (abcdefg), on Python' in stderr)

    @mock.patch('locale.getdefaultlocale', mock.Mock(return_value=['en_US']))
    @mock.patch('locale.getpreferredencoding', mock.Mock(return_value='iso'))
    @mock.patch.object(
        httpclient.HTTPClient, 'get',
        mock.MagicMock(return_value=base.FakeResponse(json.dumps(base.RESOURCES), 200, 'OK')))
    @mock.patch('st2client.shell.LOGGER')
    def test_non_unicode_encoding_locale_warning_is_printed(self, mock_logger):
        shell = Shell()
        shell.run(argv=['trigger', 'list'])

        call_args = mock_logger.warn.call_args[0][0]
        self.assertTrue('Locale en_US with encoding iso which is not UTF-8 is used.' in call_args)

    @mock.patch('locale.getdefaultlocale', mock.Mock(side_effect=ValueError('bar')))
    @mock.patch('locale.getpreferredencoding', mock.Mock(side_effect=ValueError('bar')))
    @mock.patch.object(
        httpclient.HTTPClient, 'get',
        mock.MagicMock(return_value=base.FakeResponse(json.dumps(base.RESOURCES), 200, 'OK')))
    @mock.patch('st2client.shell.LOGGER')
    def test_failed_to_get_locale_encoding_warning_is_printed(self, mock_logger):
        shell = Shell()
        shell.run(argv=['trigger', 'list'])

        call_args = mock_logger.warn.call_args[0][0]
        self.assertTrue('Locale unknown with encoding unknown which is not UTF-8 is used.' in
                        call_args)

    def _write_mock_package_metadata_file(self):
        _, package_metadata_path = tempfile.mkstemp()

        with open(package_metadata_path, 'w') as fp:
            fp.write(MOCK_PACKAGE_METADATA)

        return package_metadata_path

    @unittest2.skipIf(True, 'skipping until checks are re-enabled')
    @mock.patch.object(
        requests, 'get',
        mock.MagicMock(return_value=base.FakeResponse("{}", 200, 'OK')))
    def test_dont_warn_multiple_times(self):
        mock_temp_dir_path = tempfile.mkdtemp()
        mock_config_dir_path = os.path.join(mock_temp_dir_path, 'testconfig')
        mock_config_path = os.path.join(mock_config_dir_path, 'config')

        # Make the temporary config directory
        os.makedirs(mock_config_dir_path)

        old_perms = os.stat(mock_config_dir_path).st_mode
        new_perms = old_perms | 0o7
        os.chmod(mock_config_dir_path, new_perms)

        # Make the temporary config file
        shutil.copyfile(CONFIG_FILE_PATH_FULL, mock_config_path)
        os.chmod(mock_config_path, 0o777)  # nosec

        shell = Shell()
        shell.LOG = mock.Mock()

        # Test without token.
        shell.run(['--config-file', mock_config_path, 'action', 'list'])

        self.assertEqual(shell.LOG.warn.call_count, 2)
        self.assertEqual(
            shell.LOG.warn.call_args_list[0][0][0][:63],
            'The StackStorm configuration directory permissions are insecure')
        self.assertEqual(
            shell.LOG.warn.call_args_list[1][0][0][:58],
            'The StackStorm configuration file permissions are insecure')

        self.assertEqual(shell.LOG.info.call_count, 2)
        self.assertEqual(
            shell.LOG.info.call_args_list[0][0][0], "The SGID bit is not "
            "set on the StackStorm configuration directory.")

        self.assertEqual(
            shell.LOG.info.call_args_list[1][0][0], 'Skipping parsing CLI config')


class CLITokenCachingTestCase(unittest2.TestCase):
    def setUp(self):
        super(CLITokenCachingTestCase, self).setUp()
        self._mock_temp_dir_path = tempfile.mkdtemp()
        self._mock_config_directory_path = os.path.join(self._mock_temp_dir_path, 'testconfig')
        self._mock_config_path = os.path.join(self._mock_config_directory_path, 'config')

        os.makedirs(self._mock_config_directory_path)

        self._p1 = mock.patch('st2client.base.ST2_CONFIG_DIRECTORY',
                              self._mock_config_directory_path)
        self._p2 = mock.patch('st2client.base.ST2_CONFIG_PATH',
                              self._mock_config_path)
        self._p1.start()
        self._p2.start()

    def tearDown(self):
        super(CLITokenCachingTestCase, self).tearDown()
        self._p1.stop()
        self._p2.stop()

        for var in [
            'ST2_BASE_URL',
            'ST2_API_URL',
            'ST2_STREAM_URL',
            'ST2_DATASTORE_URL',
            'ST2_AUTH_TOKEN'
        ]:
            if var in os.environ:
                del os.environ[var]

    def _write_mock_config(self):
        with open(self._mock_config_path, 'w') as fp:
            fp.write(MOCK_CONFIG)

    def test_get_cached_auth_token_invalid_permissions(self):
        shell = Shell()
        client = Client()
        username = 'testu'
        password = 'testp'

        cached_token_path = shell._get_cached_token_path_for_user(username=username)
        data = {
            'token': 'yayvalid',
            'expire_timestamp': (int(time.time()) + 20)
        }
        with open(cached_token_path, 'w') as fp:
            fp.write(json.dumps(data))

        # 1. Current user doesn't have read access to the config directory
        os.chmod(self._mock_config_directory_path, 0o000)

        shell.LOG = mock.Mock()
        result = shell._get_cached_auth_token(client=client, username=username,
                                              password=password)

        self.assertEqual(result, None)
        self.assertEqual(shell.LOG.warn.call_count, 1)
        log_message = shell.LOG.warn.call_args[0][0]

        expected_msg = ('Unable to retrieve cached token from .*? read access to the parent '
                        'directory')
        self.assertRegexpMatches(log_message, expected_msg)

        # 2. Read access on the directory, but not on the cached token file
        os.chmod(self._mock_config_directory_path, 0o777)  # nosec
        os.chmod(cached_token_path, 0o000)

        shell.LOG = mock.Mock()
        result = shell._get_cached_auth_token(client=client, username=username,
                                              password=password)
        self.assertEqual(result, None)

        self.assertEqual(shell.LOG.warn.call_count, 1)
        log_message = shell.LOG.warn.call_args[0][0]

        expected_msg = ('Unable to retrieve cached token from .*? read access to this file')
        self.assertRegexpMatches(log_message, expected_msg)

        # 3. Other users also have read access to the file
        os.chmod(self._mock_config_directory_path, 0o777)  # nosec
        os.chmod(cached_token_path, 0o444)

        shell.LOG = mock.Mock()
        result = shell._get_cached_auth_token(client=client, username=username,
                                              password=password)
        self.assertEqual(result, 'yayvalid')

        self.assertEqual(shell.LOG.warn.call_count, 1)
        log_message = shell.LOG.warn.call_args[0][0]

        expected_msg = ('Permissions .*? for cached token file .*? are too permissive.*')
        self.assertRegexpMatches(log_message, expected_msg)

    def test_cache_auth_token_invalid_permissions(self):
        shell = Shell()
        username = 'testu'

        cached_token_path = shell._get_cached_token_path_for_user(username=username)
        expiry = datetime.datetime.utcnow() + datetime.timedelta(seconds=30)

        token_db = TokenDB(user=username, token='fyeah', expiry=expiry)

        cached_token_path = shell._get_cached_token_path_for_user(username=username)
        data = {
            'token': 'yayvalid',
            'expire_timestamp': (int(time.time()) + 20)
        }
        with open(cached_token_path, 'w') as fp:
            fp.write(json.dumps(data))

        # 1. Current user has no write access to the parent directory
        os.chmod(self._mock_config_directory_path, 0o000)

        shell.LOG = mock.Mock()
        shell._cache_auth_token(token_obj=token_db)

        self.assertEqual(shell.LOG.warn.call_count, 1)
        log_message = shell.LOG.warn.call_args[0][0]

        expected_msg = ('Unable to write token to .*? doesn\'t have write access to the parent '
                        'directory')
        self.assertRegexpMatches(log_message, expected_msg)

        # 2. Current user has no write access to the cached token file
        os.chmod(self._mock_config_directory_path, 0o777)  # nosec
        os.chmod(cached_token_path, 0o000)

        shell.LOG = mock.Mock()
        shell._cache_auth_token(token_obj=token_db)

        self.assertEqual(shell.LOG.warn.call_count, 1)
        log_message = shell.LOG.warn.call_args[0][0]

        expected_msg = ('Unable to write token to .*? doesn\'t have write access to this file')
        self.assertRegexpMatches(log_message, expected_msg)

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

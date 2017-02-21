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
import uuid
import json
import mock
import tempfile
import requests
import argparse
import logging

from tests import base
from st2client import shell
from st2client.models.core import add_auth_token_to_kwargs_from_env
from st2client.commands.resource import add_auth_token_to_kwargs_from_cli
from st2client.utils.httpclient import add_auth_token_to_headers, add_json_content_type_to_headers


LOG = logging.getLogger(__name__)

RULE = {
    'id': uuid.uuid4().hex,
    'description': 'i am THE rule.',
    'name': 'drule',
    'pack': 'cli',
}


class TestLoginBase(base.BaseCLITestCase):
    """
    A base class for testing related to 'st2 login' commands

    This exists primarily to ensure that each specific test case is kept atomic,
    since the tests create actual files on the filesystem - as well as to cut down
    on duplicate code in each test class
    """

    capture_output = True

    DOTST2_PATH = os.path.expanduser('~/.st2/')
    CONFIG_FILE = tempfile.mkstemp(suffix='st2.conf')
    CONFIG_CONTENTS = """
    [credentials]
    username = olduser
    password = Password1!
    """

    def __init__(self, *args, **kwargs):
        super(TestLoginBase, self).__init__(*args, **kwargs)

        # We're overriding the default behavior for CLI test cases here
        self.DEFAULT_SKIP_CONFIG = '0'

        self.parser = argparse.ArgumentParser()
        self.parser.add_argument('-t', '--token', dest='token')
        self.parser.add_argument('--api-key', dest='api_key')
        self.shell = shell.Shell()

    def setUp(self):
        super(TestLoginBase, self).setUp()

        # Remove any existing config file
        if os.path.isfile(self.CONFIG_FILE):
            os.remove(self.CONFIG_FILE)

        with open(self.CONFIG_FILE, 'w') as cfg:
            for line in self.CONFIG_CONTENTS.split('\n'):
                cfg.write('%s\n' % line.strip())

    def tearDown(self):
        super(TestLoginBase, self).tearDown()

        # Clean up config file
        os.remove(self.CONFIG_FILE)

        # Clean up tokens
        for file in [f for f in os.listdir(self.DOTST2_PATH) if 'token-' in f]:
            os.remove(self.DOTST2_PATH + file)


class TestLoginPasswordAndConfig(TestLoginBase):

    CONFIG_FILE = '/tmp/logintest.cfg'

    TOKEN = {
        'user': 'st2admin',
        'token': '44583f15945b4095afbf57058535ca64',
        'expiry': '2017-02-12T00:53:09.632783Z',
        'id': '589e607532ed3535707f10eb',
        'metadata': {}
    }

    @mock.patch.object(
        requests, 'post',
        mock.MagicMock(return_value=base.FakeResponse(json.dumps(TOKEN), 200, 'OK')))
    def runTest(self):
        '''Test 'st2 login' functionality by specifying a password and a configuration file
        '''

        expected_username = self.TOKEN['user']
        args = ['--config', self.CONFIG_FILE, 'login', expected_username, '--password',
                'Password1!']

        self.shell.run(args)

        with open(self.CONFIG_FILE, 'r') as config_file:
            for line in config_file.readlines():
                # Make sure certain values are not present
                self.assertFalse('password' in line)
                self.assertFalse('olduser' in line)

                # Make sure configured username is what we expect
                if 'username' in line:
                    self.assertEquals(line.split(' ')[2][:-1], expected_username)

            # validate token was created
            self.assertTrue(os.path.isfile('%stoken-%s' % (self.DOTST2_PATH, expected_username)))


class TestLoginIntPwdAndConfig(TestLoginBase):

    CONFIG_FILE = '/tmp/logintest.cfg'

    TOKEN = {
        'user': 'st2admin',
        'token': '44583f15945b4095afbf57058535ca64',
        'expiry': '2017-02-12T00:53:09.632783Z',
        'id': '589e607532ed3535707f10eb',
        'metadata': {}
    }

    @mock.patch.object(
        requests, 'post',
        mock.MagicMock(return_value=base.FakeResponse(json.dumps(TOKEN), 200, 'OK')))
    @mock.patch.object(
        requests, 'get',
        mock.MagicMock(return_value=base.FakeResponse(json.dumps({}), 200, 'OK')))
    @mock.patch('st2client.commands.auth.getpass')
    def runTest(self, mock_gp):
        '''Test 'st2 login' functionality with interactive password entry
        '''

        expected_username = self.TOKEN['user']
        args = ['--config', self.CONFIG_FILE, 'login', expected_username]

        mock_gp.getpass.return_value = 'Password1!'

        self.shell.run(args)

        expected_kwargs = {
            'headers': {'content-type': 'application/json'},
            'auth': ('st2admin', 'Password1!')
        }
        requests.post.assert_called_with('http://127.0.0.1:9100/tokens', '{}', **expected_kwargs)

        with open(self.CONFIG_FILE, 'r') as config_file:
            for line in config_file.readlines():
                # Make sure certain values are not present
                self.assertFalse('password' in line)
                self.assertFalse('olduser' in line)

                # Make sure configured username is what we expect
                if 'username' in line:
                    self.assertEquals(line.split(' ')[2][:-1], expected_username)

            # validate token was created
            self.assertTrue(os.path.isfile('%stoken-%s' % (self.DOTST2_PATH, expected_username)))

        # Validate token is sent on subsequent requests to st2 API
        args = ['--config', self.CONFIG_FILE, 'pack', 'list']
        self.shell.run(args)

        expected_kwargs = {
            'headers': {
                'X-Auth-Token': self.TOKEN['token']
            },
            'params': {}
        }
        requests.get.assert_called_with('http://127.0.0.1:9101/v1/packs', **expected_kwargs)


class TestLoginWritePwdOkay(TestLoginBase):

    CONFIG_FILE = '/tmp/logintest.cfg'

    TOKEN = {
        'user': 'st2admin',
        'token': '44583f15945b4095afbf57058535ca64',
        'expiry': '2017-02-12T00:53:09.632783Z',
        'id': '589e607532ed3535707f10eb',
        'metadata': {}
    }

    @mock.patch.object(
        requests, 'post',
        mock.MagicMock(return_value=base.FakeResponse(json.dumps(TOKEN), 200, 'OK')))
    @mock.patch('st2client.commands.auth.getpass')
    def runTest(self, mock_gp):
        '''Test 'st2 login' functionality with --write-password flag set
        '''

        expected_username = self.TOKEN['user']
        args = ['--config', self.CONFIG_FILE, 'login', expected_username, '--password',
                'Password1!', '--write-password']

        self.shell.run(args)

        with open(self.CONFIG_FILE, 'r') as config_file:

            for line in config_file.readlines():

                # Make sure certain values are not present
                self.assertFalse('olduser' in line)

                # Make sure configured username is what we expect
                if 'username' in line:
                    self.assertEquals(line.split(' ')[2][:-1], expected_username)

            # validate token was created
            self.assertTrue(os.path.isfile('%stoken-%s' % (self.DOTST2_PATH, expected_username)))


class TestLoginUncaughtException(TestLoginBase):

    CONFIG_FILE = '/tmp/logintest.cfg'

    TOKEN = {
        'user': 'st2admin',
        'token': '44583f15945b4095afbf57058535ca64',
        'expiry': '2017-02-12T00:53:09.632783Z',
        'id': '589e607532ed3535707f10eb',
        'metadata': {}
    }

    @mock.patch.object(
        requests, 'post',
        mock.MagicMock(return_value=base.FakeResponse(json.dumps(TOKEN), 200, 'OK')))
    @mock.patch('st2client.commands.auth.getpass')
    def runTest(self, mock_gp):
        '''Test 'st2 login' ability to detect unhandled exceptions
        '''

        expected_username = self.TOKEN['user']
        args = ['--config', self.CONFIG_FILE, 'login', expected_username]

        mock_gp.getpass = mock.MagicMock(side_effect=Exception)

        self.shell.run(args)
        retcode = self.shell.run(args)

        self.assertTrue('Failed to log in as %s' % expected_username in self.stdout.getvalue())
        self.assertTrue('Logged in as' not in self.stdout.getvalue())
        self.assertEqual(retcode, 0)


class TestWhoami(TestLoginBase):

    CONFIG_FILE = '/tmp/logintest.cfg'

    USERNAME = 'st2foouser'

    CONFIG_CONTENTS = """
    [credentials]
    username = %s
    password = Password1!
    """ % USERNAME

    @mock.patch.object(
        requests, 'post',
        mock.MagicMock(return_value=base.FakeResponse(json.dumps({}), 200, 'OK')))
    def runTest(self):
        '''Test 'st2 whoami' functionality
        '''

        retcode = self.shell.run(['--config', self.CONFIG_FILE, 'whoami'])

        self.assertEqual(retcode, 0)
        self.assertTrue(self.USERNAME in self.stdout.getvalue())


class TestWhoamiMissingUser(TestLoginBase):

    CONFIG_FILE = '/tmp/logintest.cfg'

    CONFIG_CONTENTS = ("""
    [credentials]
    foo = bar
    """)

    @mock.patch.object(
        requests, 'post',
        mock.MagicMock(return_value=base.FakeResponse(json.dumps({}), 200, 'OK')))
    def runTest(self):
        '''Test 'st2 whoami' functionality with a missing username
        '''

        retcode = self.shell.run(['--config', self.CONFIG_FILE, 'whoami'])

        self.assertEqual('Unable to retrieve currently logged-in user',
                         self.stdout.getvalue().strip())
        self.assertEqual(retcode, 0)


class TestWhoamiMissingCreds(TestLoginBase):

    CONFIG_FILE = '/tmp/logintest.cfg'

    CONFIG_CONTENTS = ("""
    [nonsense]
    foo = bar
    """)

    @mock.patch.object(
        requests, 'post',
        mock.MagicMock(return_value=base.FakeResponse(json.dumps({}), 200, 'OK')))
    def runTest(self):
        '''Test 'st2 whoami' functionality with a missing credentials section
        '''

        retcode = self.shell.run(['--config', self.CONFIG_FILE, 'whoami'])
        self.assertEqual('Unable to retrieve currently logged-in user',
                         self.stdout.getvalue().strip())
        self.assertEqual(retcode, 0)


class TestWhoamiUncaughtException(TestLoginBase):

    CONFIG_FILE = '/tmp/logintest.cfg'

    USERNAME = 'st2foouser'

    CONFIG_CONTENTS = ("""
    [credentials]
    username = %s
    password = Password1!
    """ % USERNAME)

    @mock.patch.object(
        requests, 'post',
        mock.MagicMock(return_value=base.FakeResponse(json.dumps({}), 200, 'OK')))
    @mock.patch('st2client.commands.auth.BaseCLIApp')
    def runTest(self, mock_cli):
        '''Test 'st2 whoami' ability to detect unhandled exceptions
        '''

        # Only mocking "BaseCLIApp" here in order to generate an exception for this specific test
        mock_cli.return_value._get_config_file_path = mock.MagicMock(side_effect=Exception)

        retcode = self.shell.run(['--config', self.CONFIG_FILE, 'whoami'])

        self.assertEqual('Unable to retrieve currently logged-in user',
                         self.stdout.getvalue().strip())
        self.assertEqual(retcode, 0)


class TestAuthToken(base.BaseCLITestCase):

    def __init__(self, *args, **kwargs):
        super(TestAuthToken, self).__init__(*args, **kwargs)
        self.parser = argparse.ArgumentParser()
        self.parser.add_argument('-t', '--token', dest='token')
        self.parser.add_argument('--api-key', dest='api_key')
        self.shell = shell.Shell()

    def setUp(self):
        super(TestAuthToken, self).setUp()

        # Setup environment.
        os.environ['ST2_BASE_URL'] = 'http://127.0.0.1'

    def tearDown(self):
        super(TestAuthToken, self).tearDown()

        # Clean up environment.
        if 'ST2_AUTH_TOKEN' in os.environ:
            del os.environ['ST2_AUTH_TOKEN']
        if 'ST2_API_KEY' in os.environ:
            del os.environ['ST2_API_KEY']
        if 'ST2_BASE_URL' in os.environ:
            del os.environ['ST2_BASE_URL']

    @add_auth_token_to_kwargs_from_cli
    @add_auth_token_to_kwargs_from_env
    def _mock_run(self, args, **kwargs):
        return kwargs

    def test_decorate_auth_token_by_cli(self):
        token = uuid.uuid4().hex
        args = self.parser.parse_args(args=['-t', token])
        self.assertDictEqual(self._mock_run(args), {'token': token})
        args = self.parser.parse_args(args=['--token', token])
        self.assertDictEqual(self._mock_run(args), {'token': token})

    def test_decorate_api_key_by_cli(self):
        token = uuid.uuid4().hex
        args = self.parser.parse_args(args=['--api-key', token])
        self.assertDictEqual(self._mock_run(args), {'api_key': token})

    def test_decorate_auth_token_by_env(self):
        token = uuid.uuid4().hex
        os.environ['ST2_AUTH_TOKEN'] = token
        args = self.parser.parse_args(args=[])
        self.assertDictEqual(self._mock_run(args), {'token': token})

    def test_decorate_api_key_by_env(self):
        token = uuid.uuid4().hex
        os.environ['ST2_API_KEY'] = token
        args = self.parser.parse_args(args=[])
        self.assertDictEqual(self._mock_run(args), {'api_key': token})

    def test_decorate_without_auth_token(self):
        args = self.parser.parse_args(args=[])
        self.assertDictEqual(self._mock_run(args), {})

    @add_auth_token_to_headers
    @add_json_content_type_to_headers
    def _mock_http(self, url, **kwargs):
        return kwargs

    def test_decorate_auth_token_to_http_headers(self):
        token = uuid.uuid4().hex
        kwargs = self._mock_http('/', token=token)
        expected = {'content-type': 'application/json', 'X-Auth-Token': token}
        self.assertIn('headers', kwargs)
        self.assertDictEqual(kwargs['headers'], expected)

    def test_decorate_api_key_to_http_headers(self):
        token = uuid.uuid4().hex
        kwargs = self._mock_http('/', api_key=token)
        expected = {'content-type': 'application/json', 'St2-Api-Key': token}
        self.assertIn('headers', kwargs)
        self.assertDictEqual(kwargs['headers'], expected)

    def test_decorate_without_auth_token_to_http_headers(self):
        kwargs = self._mock_http('/', auth=('stanley', 'stanley'))
        expected = {'content-type': 'application/json'}
        self.assertIn('auth', kwargs)
        self.assertEqual(kwargs['auth'], ('stanley', 'stanley'))
        self.assertIn('headers', kwargs)
        self.assertDictEqual(kwargs['headers'], expected)

    @mock.patch.object(
        requests, 'get',
        mock.MagicMock(return_value=base.FakeResponse(json.dumps({}), 200, 'OK')))
    def test_decorate_resource_list(self):
        url = 'http://127.0.0.1:9101/v1/rules/?limit=50'

        # Test without token.
        self.shell.run(['rule', 'list'])
        kwargs = {}
        requests.get.assert_called_with(url, **kwargs)

        # Test with token from  cli.
        token = uuid.uuid4().hex
        self.shell.run(['rule', 'list', '-t', token])
        kwargs = {'headers': {'X-Auth-Token': token}}
        requests.get.assert_called_with(url, **kwargs)

        # Test with token from env.
        token = uuid.uuid4().hex
        os.environ['ST2_AUTH_TOKEN'] = token
        self.shell.run(['rule', 'list'])
        kwargs = {'headers': {'X-Auth-Token': token}}
        requests.get.assert_called_with(url, **kwargs)

    @mock.patch.object(
        requests, 'get',
        mock.MagicMock(return_value=base.FakeResponse(json.dumps(RULE), 200, 'OK')))
    def test_decorate_resource_get(self):
        rule_ref = '%s.%s' % (RULE['pack'], RULE['name'])
        url = 'http://127.0.0.1:9101/v1/rules/%s' % rule_ref

        # Test without token.
        self.shell.run(['rule', 'get', rule_ref])
        kwargs = {}
        requests.get.assert_called_with(url, **kwargs)

        # Test with token from cli.
        token = uuid.uuid4().hex
        self.shell.run(['rule', 'get', rule_ref, '-t', token])
        kwargs = {'headers': {'X-Auth-Token': token}}
        requests.get.assert_called_with(url, **kwargs)

        # Test with token from env.
        token = uuid.uuid4().hex
        os.environ['ST2_AUTH_TOKEN'] = token
        self.shell.run(['rule', 'get', rule_ref])
        kwargs = {'headers': {'X-Auth-Token': token}}
        requests.get.assert_called_with(url, **kwargs)

    @mock.patch.object(
        requests, 'post',
        mock.MagicMock(return_value=base.FakeResponse(json.dumps(RULE), 200, 'OK')))
    def test_decorate_resource_post(self):
        url = 'http://127.0.0.1:9101/v1/rules'
        data = {'name': RULE['name'], 'description': RULE['description']}

        fd, path = tempfile.mkstemp(suffix='.json')
        try:
            with open(path, 'a') as f:
                f.write(json.dumps(data, indent=4))

            # Test without token.
            self.shell.run(['rule', 'create', path])
            kwargs = {'headers': {'content-type': 'application/json'}}
            requests.post.assert_called_with(url, json.dumps(data), **kwargs)

            # Test with token from cli.
            token = uuid.uuid4().hex
            self.shell.run(['rule', 'create', path, '-t', token])
            kwargs = {'headers': {'content-type': 'application/json', 'X-Auth-Token': token}}
            requests.post.assert_called_with(url, json.dumps(data), **kwargs)

            # Test with token from env.
            token = uuid.uuid4().hex
            os.environ['ST2_AUTH_TOKEN'] = token
            self.shell.run(['rule', 'create', path])
            kwargs = {'headers': {'content-type': 'application/json', 'X-Auth-Token': token}}
            requests.post.assert_called_with(url, json.dumps(data), **kwargs)
        finally:
            os.close(fd)
            os.unlink(path)

    @mock.patch.object(
        requests, 'get',
        mock.MagicMock(return_value=base.FakeResponse(json.dumps(RULE), 200, 'OK')))
    @mock.patch.object(
        requests, 'put',
        mock.MagicMock(return_value=base.FakeResponse(json.dumps(RULE), 200, 'OK')))
    def test_decorate_resource_put(self):
        rule_ref = '%s.%s' % (RULE['pack'], RULE['name'])

        get_url = 'http://127.0.0.1:9101/v1/rules/%s' % rule_ref
        put_url = 'http://127.0.0.1:9101/v1/rules/%s' % RULE['id']
        data = {'name': RULE['name'], 'description': RULE['description'], 'pack': RULE['pack']}

        fd, path = tempfile.mkstemp(suffix='.json')
        try:
            with open(path, 'a') as f:
                f.write(json.dumps(data, indent=4))

            # Test without token.
            self.shell.run(['rule', 'update', rule_ref, path])
            kwargs = {}
            requests.get.assert_called_with(get_url, **kwargs)
            kwargs = {'headers': {'content-type': 'application/json'}}
            requests.put.assert_called_with(put_url, json.dumps(RULE), **kwargs)

            # Test with token from cli.
            token = uuid.uuid4().hex
            self.shell.run(['rule', 'update', rule_ref, path, '-t', token])
            kwargs = {'headers': {'X-Auth-Token': token}}
            requests.get.assert_called_with(get_url, **kwargs)
            kwargs = {'headers': {'content-type': 'application/json', 'X-Auth-Token': token}}
            requests.put.assert_called_with(put_url, json.dumps(RULE), **kwargs)

            # Test with token from env.
            token = uuid.uuid4().hex
            os.environ['ST2_AUTH_TOKEN'] = token
            self.shell.run(['rule', 'update', rule_ref, path])
            kwargs = {'headers': {'X-Auth-Token': token}}
            requests.get.assert_called_with(get_url, **kwargs)
            kwargs = {'headers': {'content-type': 'application/json', 'X-Auth-Token': token}}
            requests.put.assert_called_with(put_url, json.dumps(RULE), **kwargs)
        finally:
            os.close(fd)
            os.unlink(path)

    @mock.patch.object(
        requests, 'get',
        mock.MagicMock(return_value=base.FakeResponse(json.dumps(RULE), 200, 'OK')))
    @mock.patch.object(
        requests, 'delete',
        mock.MagicMock(return_value=base.FakeResponse('', 204, 'OK')))
    def test_decorate_resource_delete(self):
        rule_ref = '%s.%s' % (RULE['pack'], RULE['name'])
        get_url = 'http://127.0.0.1:9101/v1/rules/%s' % rule_ref
        del_url = 'http://127.0.0.1:9101/v1/rules/%s' % RULE['id']

        # Test without token.
        self.shell.run(['rule', 'delete', rule_ref])
        kwargs = {}
        requests.get.assert_called_with(get_url, **kwargs)
        requests.delete.assert_called_with(del_url, **kwargs)

        # Test with token from cli.
        token = uuid.uuid4().hex
        self.shell.run(['rule', 'delete', rule_ref, '-t', token])
        kwargs = {'headers': {'X-Auth-Token': token}}
        requests.get.assert_called_with(get_url, **kwargs)
        requests.delete.assert_called_with(del_url, **kwargs)

        # Test with token from env.
        token = uuid.uuid4().hex
        os.environ['ST2_AUTH_TOKEN'] = token
        self.shell.run(['rule', 'delete', rule_ref])
        kwargs = {'headers': {'X-Auth-Token': token}}
        requests.get.assert_called_with(get_url, **kwargs)
        requests.delete.assert_called_with(del_url, **kwargs)

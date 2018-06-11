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

import time
import mock
from base64 import b64encode
from winrm import Response
from winrm.exceptions import WinRMOperationTimeoutError

from st2common.runners.base import ActionRunner
from st2tests.base import RunnerTestCase
from winrm_runner.winrm_base import WinRmBaseRunner, WinRmRunnerTimoutError
from winrm_runner.winrm_base import WINRM_TIMEOUT_EXIT_CODE
from winrm_runner import winrm_ps_command_runner

class WinRmBaseTestCase(RunnerTestCase):

    def setUp(self):
        super(WinRmBaseTestCase, self).setUpClass()
        self._runner = winrm_ps_command_runner.get_runner()

    def _init_runner(self):
        runner_parameters = {'host': 'host@domain.tld',
                             'username': 'user@domain.tld',
                             'password': 'xyz987'}
        self._runner.runner_parameters = runner_parameters
        self._runner.pre_run()

    def test_win_rm_runner_timout_error(self):
        error = WinRmRunnerTimoutError('test_response')
        self.assertIsInstance(error, Exception)
        self.assertEquals(error.response, 'test_response')
        with self.assertRaises(WinRmRunnerTimoutError):
            raise WinRmRunnerTimoutError('test raising')

    def test_init(self):
        runner = winrm_ps_command_runner.WinRmPsCommandRunner('abcdef')
        self.assertIsInstance(runner, WinRmBaseRunner)
        self.assertIsInstance(runner, ActionRunner)
        self.assertEquals(runner.runner_id, "abcdef")

    @mock.patch('winrm_runner.winrm_base.ActionRunner.pre_run')
    def test_pre_run(self, mock_pre_run):
        runner_parameters = {'host': 'host@domain.tld',
                             'username': 'user@domain.tld',
                             'password': 'abc123',
                             'timeout': 99,
                             'port': 1234,
                             'scheme': 'http',
                             'transport': 'ntlm',
                             'verify_ssl_cert': False,
                             'cwd': 'C:\\Test',
                             'env': {'TEST_VAR': 'TEST_VALUE'},
                             'kwarg_op': '/'}
        self._runner.runner_parameters = runner_parameters
        self._runner.pre_run()
        mock_pre_run.assert_called_with()
        self.assertEquals(self._runner._host, 'host@domain.tld')
        self.assertEquals(self._runner._username, 'user@domain.tld')
        self.assertEquals(self._runner._password, 'abc123')
        self.assertEquals(self._runner._timeout, 99)
        self.assertEquals(self._runner._read_timeout, 100)
        self.assertEquals(self._runner._port, 1234)
        self.assertEquals(self._runner._scheme, 'http')
        self.assertEquals(self._runner._transport, 'ntlm')
        self.assertEquals(self._runner._winrm_url, 'http://host@domain.tld:1234/wsman')
        self.assertEquals(self._runner._verify_ssl, False)
        self.assertEquals(self._runner._server_cert_validation, 'ignore')
        self.assertEquals(self._runner._cwd, 'C:\\Test')
        self.assertEquals(self._runner._env, {'TEST_VAR': 'TEST_VALUE'})
        self.assertEquals(self._runner._kwarg_op, '/')

    @mock.patch('winrm_runner.winrm_base.ActionRunner.pre_run')
    def test_pre_run_defaults(self, mock_pre_run):
        runner_parameters = {'host': 'host@domain.tld',
                             'username': 'user@domain.tld',
                             'password': 'abc123'}
        self._runner.runner_parameters = runner_parameters
        self._runner.pre_run()
        mock_pre_run.assert_called_with()
        self.assertEquals(self._runner._host, 'host@domain.tld')
        self.assertEquals(self._runner._username, 'user@domain.tld')
        self.assertEquals(self._runner._password, 'abc123')
        self.assertEquals(self._runner._timeout, 60)
        self.assertEquals(self._runner._read_timeout, 61)
        self.assertEquals(self._runner._port, 5986)
        self.assertEquals(self._runner._scheme, 'https')
        self.assertEquals(self._runner._transport, 'ntlm')
        self.assertEquals(self._runner._winrm_url, 'https://host@domain.tld:5986/wsman')
        self.assertEquals(self._runner._verify_ssl, True)
        self.assertEquals(self._runner._server_cert_validation, 'validate')
        self.assertEquals(self._runner._cwd, None)
        self.assertEquals(self._runner._env, {})
        self.assertEquals(self._runner._kwarg_op, '-')

    @mock.patch('winrm_runner.winrm_base.ActionRunner.pre_run')
    def test_pre_run_5985_force_http(self, mock_pre_run):
        runner_parameters = {'host': 'host@domain.tld',
                             'username': 'user@domain.tld',
                             'password': 'abc123',
                             'port': 5985,
                             'scheme': 'https'}
        self._runner.runner_parameters = runner_parameters
        self._runner.pre_run()
        mock_pre_run.assert_called_with()
        self.assertEquals(self._runner._host, 'host@domain.tld')
        self.assertEquals(self._runner._username, 'user@domain.tld')
        self.assertEquals(self._runner._password, 'abc123')
        self.assertEquals(self._runner._timeout, 60)
        self.assertEquals(self._runner._read_timeout, 61)
        # ensure port is still 5985
        self.assertEquals(self._runner._port, 5985)
        # ensure scheme is set back to http
        self.assertEquals(self._runner._scheme, 'http')
        self.assertEquals(self._runner._transport, 'ntlm')
        self.assertEquals(self._runner._winrm_url, 'http://host@domain.tld:5985/wsman')
        self.assertEquals(self._runner._verify_ssl, True)
        self.assertEquals(self._runner._server_cert_validation, 'validate')
        self.assertEquals(self._runner._cwd, None)
        self.assertEquals(self._runner._env, {})
        self.assertEquals(self._runner._kwarg_op, '-')

    @mock.patch('winrm_runner.winrm_base.ActionRunner.pre_run')
    def test_pre_run_none_env(self, mock_pre_run):
        runner_parameters = {'host': 'host@domain.tld',
                             'username': 'user@domain.tld',
                             'password': 'abc123',
                             'env': None}
        self._runner.runner_parameters = runner_parameters
        self._runner.pre_run()
        mock_pre_run.assert_called_with()
        # ensure that env is set to {} even though we passed in None
        self.assertEquals(self._runner._env, {})

    @mock.patch('winrm_runner.winrm_base.ActionRunner.pre_run')
    def test_pre_run_ssl_verify_true(self, mock_pre_run):
        runner_parameters = {'host': 'host@domain.tld',
                             'username': 'user@domain.tld',
                             'password': 'abc123',
                             'verify_ssl_cert': True}
        self._runner.runner_parameters = runner_parameters
        self._runner.pre_run()
        mock_pre_run.assert_called_with()
        self.assertEquals(self._runner._verify_ssl, True)
        self.assertEquals(self._runner._server_cert_validation, 'validate')

    @mock.patch('winrm_runner.winrm_base.ActionRunner.pre_run')
    def test_pre_run_ssl_verify_false(self, mock_pre_run):
        runner_parameters = {'host': 'host@domain.tld',
                             'username': 'user@domain.tld',
                             'password': 'abc123',
                             'verify_ssl_cert': False}
        self._runner.runner_parameters = runner_parameters
        self._runner.pre_run()
        mock_pre_run.assert_called_with()
        self.assertEquals(self._runner._verify_ssl, False)
        self.assertEquals(self._runner._server_cert_validation, 'ignore')

    @mock.patch('winrm_runner.winrm_base.Session')
    def test_create_session(self, mock_session):
        self._runner._winrm_url = 'https://host@domain.tld:5986/wsman'
        self._runner._username = 'user@domain.tld'
        self._runner._password = 'abc123'
        self._runner._transport = 'ntlm'
        self._runner._server_cert_validation = 'validate'
        self._runner._timeout = 60
        self._runner._read_timeout = 61
        mock_session.return_value = "session"

        result = self._runner._create_session()
        self.assertEquals(result, "session")
        mock_session.assert_called_with('https://host@domain.tld:5986/wsman',
                                        auth=('user@domain.tld', 'abc123'),
                                        transport='ntlm',
                                        server_cert_validation='validate',
                                        operation_timeout_sec=60,
                                        read_timeout_sec=61)

    def test_get_command_output(self):
        self._runner._timeout = 0
        mock_protocol = mock.MagicMock()
        mock_protocol._raw_get_command_output.side_effect = [
            ('output1', 'error1', 123, False),
            ('output2', 'error2', 456, False),
            ('output3', 'error3', 789, True)
        ]

        result = self._runner._winrm_get_command_output(mock_protocol, 567, 890)

        self.assertEquals(result, ('output1output2output3', 'error1error2error3', 789))
        mock_protocol._raw_get_command_output.assert_has_calls = [
            mock.call(567, 890),
            mock.call(567, 890),
            mock.call(567, 890)
        ]

    def test_get_command_output_timeout(self):
        self._runner._timeout = 1

        mock_protocol = mock.MagicMock()
        def sleep_for_timeout(*args, **kwargs):
            time.sleep(2)
            return ('output1', 'error1', 123, False)
        mock_protocol._raw_get_command_output.side_effect = sleep_for_timeout

        with self.assertRaises(WinRmRunnerTimoutError) as cm:
            self._runner._winrm_get_command_output(mock_protocol, 567, 890)

        timeout_exception = cm.exception
        self.assertEqual(timeout_exception.response.std_out, 'output1')
        self.assertEqual(timeout_exception.response.std_err, 'error1')
        self.assertEqual(timeout_exception.response.status_code, WINRM_TIMEOUT_EXIT_CODE)
        mock_protocol._raw_get_command_output.assert_called_with(567, 890)

    def test_get_command_output_operation_timeout(self):
        self._runner._timeout = 1

        mock_protocol = mock.MagicMock()
        def sleep_for_timeout_then_raise(*args, **kwargs):
            time.sleep(2)
            raise WinRMOperationTimeoutError()
        mock_protocol._raw_get_command_output.side_effect = sleep_for_timeout_then_raise

        with self.assertRaises(WinRmRunnerTimoutError) as cm:
            self._runner._winrm_get_command_output(mock_protocol, 567, 890)

        timeout_exception = cm.exception
        self.assertEqual(timeout_exception.response.std_out, '')
        self.assertEqual(timeout_exception.response.std_err, '')
        self.assertEqual(timeout_exception.response.status_code, WINRM_TIMEOUT_EXIT_CODE)
        mock_protocol._raw_get_command_output.assert_called_with(567, 890)

    def test_winrm_run_cmd(self):
        mock_protocol = mock.MagicMock()
        mock_protocol.open_shell.return_value = 123
        mock_protocol.run_command.return_value = 456
        mock_protocol._raw_get_command_output.return_value = ('output', 'error', 9, True)
        mock_session = mock.MagicMock(protocol=mock_protocol)

        self._init_runner()
        result = self._runner._winrm_run_cmd(mock_session, "fake-command",
                                             args=['arg1', 'arg2'],
                                             env={'PATH': 'C:\\st2\\bin'},
                                             cwd='C:\\st2')
        expected_response = Response(('output', 'error', 9))
        expected_response.timeout = False

        self.assertEquals(result.__dict__, expected_response.__dict__)
        mock_protocol.open_shell.assert_called_with(env_vars={'PATH': 'C:\\st2\\bin'},
                                                    working_directory='C:\\st2')
        mock_protocol.run_command.assert_called_with(123, 'fake-command', ['arg1', 'arg2'])
        mock_protocol._raw_get_command_output.assert_called_with(123, 456)
        mock_protocol.cleanup_command.assert_called_with(123, 456)
        mock_protocol.close_shell.assert_called_with(123)

    @mock.patch('winrm_runner.winrm_base.WinRmBaseRunner._winrm_get_command_output')
    def test_winrm_run_cmd_timeout(self, mock_get_command_output):
        mock_protocol = mock.MagicMock()
        mock_protocol.open_shell.return_value = 123
        mock_protocol.run_command.return_value = 456
        mock_session = mock.MagicMock(protocol=mock_protocol)
        mock_get_command_output.side_effect = WinRmRunnerTimoutError(Response(('', '', 5)))

        self._init_runner()
        result = self._runner._winrm_run_cmd(mock_session, "fake-command",
                                             args=['arg1', 'arg2'],
                                             env={'PATH': 'C:\\st2\\bin'},
                                             cwd='C:\\st2')
        expected_response = Response(('', '', 5))
        expected_response.timeout = True

        self.assertEquals(result.__dict__, expected_response.__dict__)
        mock_protocol.open_shell.assert_called_with(env_vars={'PATH': 'C:\\st2\\bin'},
                                                    working_directory='C:\\st2')
        mock_protocol.run_command.assert_called_with(123, 'fake-command', ['arg1', 'arg2'])
        mock_protocol.cleanup_command.assert_called_with(123, 456)
        mock_protocol.close_shell.assert_called_with(123)

    @mock.patch('winrm_runner.winrm_base.WinRmBaseRunner._winrm_run_cmd')
    def test_winrm_run_ps(self, mock_run_cmd):
        mock_run_cmd.return_value = Response(('output', '', 3))
        script = "Get-ADUser stanley"

        result = self._runner._winrm_run_ps("session", script,
                                            env={'PATH': 'C:\\st2\\bin'},
                                            cwd='C:\\st2')

        self.assertEquals(result.__dict__,
                          Response(('output', '', 3)).__dict__)
        expected_ps = ('powershell -encodedcommand ' +
                       b64encode("Get-ADUser stanley".encode('utf_16_le')).decode('ascii'))
        mock_run_cmd.assert_called_with("session",
                                        expected_ps,
                                        env={'PATH': 'C:\\st2\\bin'},
                                        cwd='C:\\st2')

    @mock.patch('winrm_runner.winrm_base.WinRmBaseRunner._winrm_run_cmd')
    def test_winrm_run_ps_clean_stderr(self, mock_run_cmd):
        mock_run_cmd.return_value = Response(('output', 'error', 3))
        mock_session = mock.MagicMock()
        mock_session._clean_error_msg.return_value = 'e'
        script = "Get-ADUser stanley"

        result = self._runner._winrm_run_ps(mock_session, script,
                                            env={'PATH': 'C:\\st2\\bin'},
                                            cwd='C:\\st2')

        self.assertEquals(result.__dict__,
                          Response(('output', 'e', 3)).__dict__)
        expected_ps = ('powershell -encodedcommand ' +
                       b64encode("Get-ADUser stanley".encode('utf_16_le')).decode('ascii'))
        mock_run_cmd.assert_called_with(mock_session,
                                        expected_ps,
                                        env={'PATH': 'C:\\st2\\bin'},
                                        cwd='C:\\st2')
        mock_session._clean_error_msg.assert_called_with('error')

# Licensed to the Apache Software Foundation (ASF) under one or more
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
from StringIO import StringIO
import unittest2

from oslo_config import cfg
from mock import (call, patch, Mock, MagicMock)
import paramiko

from st2actions.runners.ssh.paramiko_ssh import ParamikoSSHClient
from st2tests.fixturesloader import get_resources_base_path
import st2tests.config as tests_config
tests_config.parse_args()


class ParamikoSSHClientTests(unittest2.TestCase):

    @patch('paramiko.SSHClient', Mock)
    def setUp(self):
        """
        Creates the object patching the actual connection.
        """
        cfg.CONF.set_override(name='ssh_key_file', override=None, group='system_user')

        conn_params = {'hostname': 'dummy.host.org',
                       'port': 8822,
                       'username': 'ubuntu',
                       'key_files': '~/.ssh/ubuntu_ssh',
                       'timeout': '600'}
        self.ssh_cli = ParamikoSSHClient(**conn_params)

    @patch('paramiko.SSHClient', Mock)
    @patch.object(ParamikoSSHClient, '_is_key_file_needs_passphrase',
                  MagicMock(return_value=False))
    def test_create_with_password(self):
        conn_params = {'hostname': 'dummy.host.org',
                       'username': 'ubuntu',
                       'password': 'ubuntu'}
        mock = ParamikoSSHClient(**conn_params)
        mock.connect()

        expected_conn = {'username': 'ubuntu',
                         'password': 'ubuntu',
                         'allow_agent': False,
                         'hostname': 'dummy.host.org',
                         'look_for_keys': False,
                         'timeout': 60,
                         'port': 22}
        mock.client.connect.assert_called_once_with(**expected_conn)

    @patch('paramiko.SSHClient', Mock)
    @patch.object(ParamikoSSHClient, '_is_key_file_needs_passphrase',
                  MagicMock(return_value=False))
    def test_deprecated_key_argument(self):
        conn_params = {'hostname': 'dummy.host.org',
                       'username': 'ubuntu',
                       'key_files': 'id_rsa'}
        mock = ParamikoSSHClient(**conn_params)
        mock.connect()

        expected_conn = {'username': 'ubuntu',
                         'allow_agent': False,
                         'hostname': 'dummy.host.org',
                         'look_for_keys': False,
                         'key_filename': 'id_rsa',
                         'timeout': 60,
                         'port': 22}
        mock.client.connect.assert_called_once_with(**expected_conn)

    def test_key_files_and_key_material_arguments_are_mutual_exclusive(self):
        conn_params = {'hostname': 'dummy.host.org',
                       'username': 'ubuntu',
                       'key_files': 'id_rsa',
                       'key_material': 'key'}

        expected_msg = ('key_files and key_material arguments are mutually '
                        'exclusive')
        self.assertRaisesRegexp(ValueError, expected_msg,
                                ParamikoSSHClient, **conn_params)

    @patch('paramiko.SSHClient', Mock)
    @patch.object(ParamikoSSHClient, '_is_key_file_needs_passphrase',
                  MagicMock(return_value=False))
    def test_key_material_argument(self):
        path = os.path.join(get_resources_base_path(),
                            'ssh', 'dummy_rsa')

        with open(path, 'r') as fp:
            private_key = fp.read()

        conn_params = {'hostname': 'dummy.host.org',
                       'username': 'ubuntu',
                       'key_material': private_key}
        mock = ParamikoSSHClient(**conn_params)
        mock.connect()

        pkey = paramiko.RSAKey.from_private_key(StringIO(private_key))
        expected_conn = {'username': 'ubuntu',
                         'allow_agent': False,
                         'hostname': 'dummy.host.org',
                         'look_for_keys': False,
                         'pkey': pkey,
                         'timeout': 60,
                         'port': 22}
        mock.client.connect.assert_called_once_with(**expected_conn)

    @patch('paramiko.SSHClient', Mock)
    @patch.object(ParamikoSSHClient, '_is_key_file_needs_passphrase',
                  MagicMock(return_value=False))
    def test_key_material_argument_invalid_key(self):
        conn_params = {'hostname': 'dummy.host.org',
                       'username': 'ubuntu',
                       'key_material': 'id_rsa'}

        mock = ParamikoSSHClient(**conn_params)

        expected_msg = 'Invalid or unsupported key type'
        self.assertRaisesRegexp(paramiko.ssh_exception.SSHException,
                                expected_msg, mock.connect)

    @patch('paramiko.SSHClient', Mock)
    @patch.object(ParamikoSSHClient, '_is_key_file_needs_passphrase',
                  MagicMock(return_value=True))
    def test_passphrase_no_key_provided(self):
        conn_params = {'hostname': 'dummy.host.org',
                       'username': 'ubuntu',
                       'passphrase': 'testphrase'}

        expected_msg = 'passphrase should accompany private key material'
        self.assertRaisesRegexp(ValueError, expected_msg, ParamikoSSHClient,
                                **conn_params)

    @patch('paramiko.SSHClient', Mock)
    def test_passphrase_not_provided_for_encrypted_key_file(self):
        path = os.path.join(get_resources_base_path(),
                            'ssh', 'dummy_rsa_passphrase')
        conn_params = {'hostname': 'dummy.host.org',
                       'username': 'ubuntu',
                       'key_files': path}
        mock = ParamikoSSHClient(**conn_params)
        self.assertRaises(paramiko.ssh_exception.PasswordRequiredException, mock.connect)

    @patch('paramiko.SSHClient', Mock)
    @patch.object(ParamikoSSHClient, '_is_key_file_needs_passphrase',
                  MagicMock(return_value=True))
    def test_key_with_passphrase_success(self):
        path = os.path.join(get_resources_base_path(),
                            'ssh', 'dummy_rsa_passphrase')

        with open(path, 'r') as fp:
            private_key = fp.read()

        # Key material provided
        conn_params = {'hostname': 'dummy.host.org',
                       'username': 'ubuntu',
                       'key_material': private_key,
                       'passphrase': 'testphrase'}
        mock = ParamikoSSHClient(**conn_params)
        mock.connect()

        pkey = paramiko.RSAKey.from_private_key(StringIO(private_key), 'testphrase')
        expected_conn = {'username': 'ubuntu',
                         'allow_agent': False,
                         'hostname': 'dummy.host.org',
                         'look_for_keys': False,
                         'pkey': pkey,
                         'timeout': 60,
                         'port': 22}
        mock.client.connect.assert_called_once_with(**expected_conn)

        # Path to private key file provided
        conn_params = {'hostname': 'dummy.host.org',
                       'username': 'ubuntu',
                       'key_files': path,
                       'passphrase': 'testphrase'}
        mock = ParamikoSSHClient(**conn_params)
        mock.connect()

        expected_conn = {'username': 'ubuntu',
                         'allow_agent': False,
                         'hostname': 'dummy.host.org',
                         'look_for_keys': False,
                         'key_filename': path,
                         'password': 'testphrase',
                         'timeout': 60,
                         'port': 22}
        mock.client.connect.assert_called_once_with(**expected_conn)

    @patch('paramiko.SSHClient', Mock)
    @patch.object(ParamikoSSHClient, '_is_key_file_needs_passphrase',
                  MagicMock(return_value=True))
    def test_passphrase_and_no_key(self):
        conn_params = {'hostname': 'dummy.host.org',
                       'username': 'ubuntu',
                       'passphrase': 'testphrase'}

        expected_msg = 'passphrase should accompany private key material'
        self.assertRaisesRegexp(ValueError, expected_msg,
                                ParamikoSSHClient, **conn_params)

    @patch('paramiko.SSHClient', Mock)
    @patch.object(ParamikoSSHClient, '_is_key_file_needs_passphrase',
                  MagicMock(return_value=True))
    def test_incorrect_passphrase(self):
        path = os.path.join(get_resources_base_path(),
                            'ssh', 'dummy_rsa_passphrase')

        with open(path, 'r') as fp:
            private_key = fp.read()

        conn_params = {'hostname': 'dummy.host.org',
                       'username': 'ubuntu',
                       'key_material': private_key,
                       'passphrase': 'incorrect'}
        mock = ParamikoSSHClient(**conn_params)

        expected_msg = 'Invalid passphrase or invalid/unsupported key type'
        self.assertRaisesRegexp(paramiko.ssh_exception.SSHException,
                                expected_msg, mock.connect)

    @patch('paramiko.SSHClient', Mock)
    @patch.object(ParamikoSSHClient, '_is_key_file_needs_passphrase',
                  MagicMock(return_value=False))
    def test_key_material_contains_path_not_contents(self):
        conn_params = {'hostname': 'dummy.host.org',
                       'username': 'ubuntu'}
        key_materials = [
            '~/.ssh/id_rsa',
            '/tmp/id_rsa',
            'C:\\id_rsa'
        ]

        expected_msg = ('"private_key" parameter needs to contain private key data / content and '
                        'not a path')

        for key_material in key_materials:
            conn_params = conn_params.copy()
            conn_params['key_material'] = key_material
            mock = ParamikoSSHClient(**conn_params)

            self.assertRaisesRegexp(paramiko.ssh_exception.SSHException,
                                    expected_msg, mock.connect)

    @patch('paramiko.SSHClient', Mock)
    @patch.object(ParamikoSSHClient, '_is_key_file_needs_passphrase',
                  MagicMock(return_value=False))
    def test_create_with_key(self):
        conn_params = {'hostname': 'dummy.host.org',
                       'username': 'ubuntu',
                       'key_files': 'id_rsa'}
        mock = ParamikoSSHClient(**conn_params)
        mock.connect()

        expected_conn = {'username': 'ubuntu',
                         'allow_agent': False,
                         'hostname': 'dummy.host.org',
                         'look_for_keys': False,
                         'key_filename': 'id_rsa',
                         'timeout': 60,
                         'port': 22}
        mock.client.connect.assert_called_once_with(**expected_conn)

    @patch('paramiko.SSHClient', Mock)
    @patch.object(ParamikoSSHClient, '_is_key_file_needs_passphrase',
                  MagicMock(return_value=False))
    def test_create_with_key_via_bastion(self):
        conn_params = {'hostname': 'dummy.host.org',
                       'bastion_host': 'bastion.host.org',
                       'username': 'ubuntu',
                       'key_files': 'id_rsa'}
        mock = ParamikoSSHClient(**conn_params)
        mock.connect()

        expected_bastion_conn = {'username': 'ubuntu',
                                 'allow_agent': False,
                                 'hostname': 'bastion.host.org',
                                 'look_for_keys': False,
                                 'key_filename': 'id_rsa',
                                 'timeout': 60,
                                 'port': 22}
        mock.bastion_client.connect.assert_called_once_with(**expected_bastion_conn)

        expected_conn = {'username': 'ubuntu',
                         'allow_agent': False,
                         'hostname': 'dummy.host.org',
                         'look_for_keys': False,
                         'key_filename': 'id_rsa',
                         'timeout': 60,
                         'port': 22,
                         'sock': mock.bastion_socket}
        mock.client.connect.assert_called_once_with(**expected_conn)

    @patch('paramiko.SSHClient', Mock)
    @patch.object(ParamikoSSHClient, '_is_key_file_needs_passphrase',
                  MagicMock(return_value=False))
    def test_create_with_password_and_key(self):
        conn_params = {'hostname': 'dummy.host.org',
                       'username': 'ubuntu',
                       'password': 'ubuntu',
                       'key_files': 'id_rsa'}
        mock = ParamikoSSHClient(**conn_params)
        mock.connect()

        expected_conn = {'username': 'ubuntu',
                         'password': 'ubuntu',
                         'allow_agent': False,
                         'hostname': 'dummy.host.org',
                         'look_for_keys': False,
                         'key_filename': 'id_rsa',
                         'timeout': 60,
                         'port': 22}
        mock.client.connect.assert_called_once_with(**expected_conn)

    @patch('paramiko.SSHClient', Mock)
    @patch.object(ParamikoSSHClient, '_is_key_file_needs_passphrase',
                  MagicMock(return_value=False))
    def test_create_without_credentials(self):
        """
        Initialize object with no credentials.

        Just to have better coverage, initialize the object
        without 'password' neither 'key'.
        """
        conn_params = {'hostname': 'dummy.host.org',
                       'username': 'ubuntu'}
        mock = ParamikoSSHClient(**conn_params)
        mock.connect()

        expected_conn = {'username': 'ubuntu',
                         'hostname': 'dummy.host.org',
                         'allow_agent': True,
                         'look_for_keys': True,
                         'timeout': 60,
                         'port': 22}
        mock.client.connect.assert_called_once_with(**expected_conn)

    @patch('paramiko.SSHClient', Mock)
    @patch.object(ParamikoSSHClient, '_is_key_file_needs_passphrase',
                  MagicMock(return_value=False))
    def test_create_without_credentials_use_default_key(self):
        # No credentials are provided by default stanley ssh key exists so it should use that
        cfg.CONF.set_override(name='ssh_key_file', override='stanley_rsa', group='system_user')

        conn_params = {'hostname': 'dummy.host.org',
                       'username': 'ubuntu'}
        mock = ParamikoSSHClient(**conn_params)
        mock.connect()

        expected_conn = {'username': 'ubuntu',
                         'hostname': 'dummy.host.org',
                         'key_filename': 'stanley_rsa',
                         'allow_agent': False,
                         'look_for_keys': False,
                         'timeout': 60,
                         'port': 22}
        mock.client.connect.assert_called_once_with(**expected_conn)

    @patch('paramiko.SSHClient', Mock)
    @patch.object(ParamikoSSHClient, '_consume_stdout',
                  MagicMock(return_value=StringIO('')))
    @patch.object(ParamikoSSHClient, '_consume_stderr',
                  MagicMock(return_value=StringIO('')))
    @patch.object(os.path, 'exists', MagicMock(return_value=True))
    @patch.object(os, 'stat', MagicMock(return_value=None))
    @patch.object(ParamikoSSHClient, '_is_key_file_needs_passphrase',
                  MagicMock(return_value=False))
    def test_basic_usage_absolute_path(self):
        """
        Basic execution.
        """
        mock = self.ssh_cli
        # script to execute
        sd = "/root/random_script.sh"

        # Connect behavior
        mock.connect()
        mock_cli = mock.client  # The actual mocked object: SSHClient
        expected_conn = {'username': 'ubuntu',
                         'key_filename': '~/.ssh/ubuntu_ssh',
                         'allow_agent': False,
                         'hostname': 'dummy.host.org',
                         'look_for_keys': False,
                         'timeout': '600',
                         'port': 8822}
        mock_cli.connect.assert_called_once_with(**expected_conn)

        mock.put(sd, sd, mirror_local_mode=False)
        mock_cli.open_sftp().put.assert_called_once_with(sd, sd)

        mock.run(sd)

        # Make assertions over 'run' method
        mock_cli.get_transport().open_session().exec_command \
                .assert_called_once_with(sd)

        mock.close()

    @patch('paramiko.SSHClient', Mock)
    @patch.object(ParamikoSSHClient, '_is_key_file_needs_passphrase',
                  MagicMock(return_value=False))
    def test_delete_script(self):
        """
        Provide a basic test with 'delete' action.
        """
        mock = self.ssh_cli
        # script to execute
        sd = '/root/random_script.sh'

        mock.connect()

        mock.delete_file(sd)
        # Make assertions over the 'delete' method
        mock.client.open_sftp().unlink.assert_called_with(sd)

        mock.close()

    @patch('paramiko.SSHClient', Mock)
    @patch.object(ParamikoSSHClient, '_is_key_file_needs_passphrase',
                  MagicMock(return_value=False))
    @patch.object(ParamikoSSHClient, 'exists', return_value=False)
    def test_put_dir(self, *args):
        mock = self.ssh_cli
        mock.connect()

        local_dir = os.path.join(get_resources_base_path(), 'packs')
        mock.put_dir(local_path=local_dir, remote_path='/tmp')

        mock_cli = mock.client  # The actual mocked object: SSHClient

        # Assert that expected dirs are created on remote box.
        calls = [call('/tmp/packs/pythonactions'), call('/tmp/packs/pythonactions/actions')]
        mock_cli.open_sftp().mkdir.assert_has_calls(calls, any_order=True)

        # Assert that expected files are copied to remote box.
        local_file = os.path.join(get_resources_base_path(),
                                  'packs/pythonactions/actions/pascal_row.py')
        remote_file = os.path.join('/tmp', 'packs/pythonactions/actions/pascal_row.py')

        calls = [call(local_file, remote_file)]
        mock_cli.open_sftp().put.assert_has_calls(calls, any_order=True)

    @patch('paramiko.SSHClient', Mock)
    @patch.object(ParamikoSSHClient, '_is_key_file_needs_passphrase',
                  MagicMock(return_value=False))
    def test_consume_stdout(self):
        # Test utf-8 decoding of ``stdout`` still works fine when reading CHUNK_SIZE splits a
        # multi-byte utf-8 character in the middle. We should wait to collect all bytes
        # and finally decode.
        conn_params = {'hostname': 'dummy.host.org',
                       'username': 'ubuntu'}
        mock = ParamikoSSHClient(**conn_params)
        mock.CHUNK_SIZE = 1
        chan = Mock()
        chan.recv_ready.side_effect = [True, True, True, True, False]

        chan.recv.side_effect = ['\xF0', '\x90', '\x8D', '\x88']
        try:
            '\xF0'.decode('utf-8')
            self.fail('Test fixture is not right.')
        except UnicodeDecodeError:
            pass
        stdout = mock._consume_stdout(chan)
        self.assertEqual(u'\U00010348', stdout.getvalue())

    @patch('paramiko.SSHClient', Mock)
    @patch.object(ParamikoSSHClient, '_is_key_file_needs_passphrase',
                  MagicMock(return_value=False))
    def test_consume_stderr(self):
        # Test utf-8 decoding of ``stderr`` still works fine when reading CHUNK_SIZE splits a
        # multi-byte utf-8 character in the middle. We should wait to collect all bytes
        # and finally decode.
        conn_params = {'hostname': 'dummy.host.org',
                       'username': 'ubuntu'}
        mock = ParamikoSSHClient(**conn_params)
        mock.CHUNK_SIZE = 1
        chan = Mock()
        chan.recv_stderr_ready.side_effect = [True, True, True, True, False]

        chan.recv_stderr.side_effect = ['\xF0', '\x90', '\x8D', '\x88']
        try:
            '\xF0'.decode('utf-8')
            self.fail('Test fixture is not right.')
        except UnicodeDecodeError:
            pass
        stderr = mock._consume_stderr(chan)
        self.assertEqual(u'\U00010348', stderr.getvalue())

    @patch('paramiko.SSHClient', Mock)
    @patch.object(ParamikoSSHClient, '_consume_stdout',
                  MagicMock(return_value=StringIO('')))
    @patch.object(ParamikoSSHClient, '_consume_stderr',
                  MagicMock(return_value=StringIO('')))
    @patch.object(os.path, 'exists', MagicMock(return_value=True))
    @patch.object(os, 'stat', MagicMock(return_value=None))
    @patch.object(ParamikoSSHClient, '_is_key_file_needs_passphrase',
                  MagicMock(return_value=False))
    def test_sftp_connection_is_only_established_if_required(self):
        # Verify that SFTP connection is lazily established only if and when needed.
        conn_params = {'hostname': 'dummy.host.org',
                       'username': 'ubuntu'}

        # Verify sftp connection and client hasn't been established yet
        client = ParamikoSSHClient(**conn_params)
        client.connect()

        self.assertTrue(client.sftp_client is None)

        # run method doesn't require sftp access so it shouldn't establish connection
        client = ParamikoSSHClient(**conn_params)
        client.connect()
        client.run(cmd='whoami')

        self.assertTrue(client.sftp_client is None)

        # Methods bellow require SFTP access so they should cause SFTP connection to be established
        # put
        client = ParamikoSSHClient(**conn_params)
        client.connect()
        path = '/root/random_script.sh'
        client.put(path, path, mirror_local_mode=False)

        self.assertTrue(client.sftp_client is not None)

        # exists
        client = ParamikoSSHClient(**conn_params)
        client.connect()
        client.exists('/root/somepath.txt')

        self.assertTrue(client.sftp_client is not None)

        # mkdir
        client = ParamikoSSHClient(**conn_params)
        client.connect()
        client.mkdir('/root/somedirfoo')

        self.assertTrue(client.sftp_client is not None)

        # Verify close doesn't throw if SFTP connection is not established
        client = ParamikoSSHClient(**conn_params)
        client.connect()

        self.assertTrue(client.sftp_client is None)
        client.close()

        # Verify SFTP connection is closed if it's opened
        client = ParamikoSSHClient(**conn_params)
        client.connect()
        client.mkdir('/root/somedirfoo')

        self.assertTrue(client.sftp_client is not None)
        client.close()

        self.assertEqual(client.sftp_client.close.call_count, 1)

# Copyright 2020 The StackStorm Authors.
# Copyright 2019 Extreme Networks, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
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

import mock
import paramiko
import unittest
from oslo_config import cfg
from mock import call, patch, Mock, MagicMock
from six.moves import StringIO

from st2common.constants.runners import DEFAULT_SSH_PORT
from st2common.runners.paramiko_ssh import ParamikoSSHClient
from st2tests.fixturesloader import get_resources_base_path
import st2tests.config as tests_config

__all__ = ["ParamikoSSHClientTestCase"]


class ParamikoSSHClientTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        tests_config.parse_args()

    @patch("paramiko.SSHClient", Mock)
    def setUp(self):
        """
        Creates the object patching the actual connection.
        """
        cfg.CONF.set_override(name="ssh_key_file", override=None, group="system_user")
        cfg.CONF.set_override(name="use_ssh_config", override=False, group="ssh_runner")
        cfg.CONF.set_override(
            name="ssh_connect_timeout", override=30, group="ssh_runner"
        )

        conn_params = {
            "hostname": "dummy.host.org",
            "port": 8822,
            "username": "ubuntu",
            "key_files": "~/.ssh/ubuntu_ssh",
            "timeout": 30,
        }
        self.ssh_cli = ParamikoSSHClient(**conn_params)

    @patch("paramiko.SSHClient", Mock)
    @patch.object(
        ParamikoSSHClient,
        "_is_key_file_needs_passphrase",
        MagicMock(return_value=False),
    )
    @patch("paramiko.ProxyCommand")
    def test_set_proxycommand(self, mock_ProxyCommand):
        """
        Loads proxy commands from ssh config file
        """
        ssh_config_file_path = os.path.join(
            get_resources_base_path(), "ssh", "dummy_ssh_config"
        )
        cfg.CONF.set_override(
            name="ssh_config_file_path",
            override=ssh_config_file_path,
            group="ssh_runner",
        )
        cfg.CONF.set_override(name="use_ssh_config", override=True, group="ssh_runner")

        conn_params = {
            "hostname": "dummy.host.org",
            "username": "ubuntu",
            "password": "foo",
        }
        mock = ParamikoSSHClient(**conn_params)
        mock.connect()
        mock_ProxyCommand.assert_called_once_with(
            "ssh -q -W dummy.host.org:22 dummy_bastion"
        )

    @patch("paramiko.SSHClient", Mock)
    @patch.object(
        ParamikoSSHClient,
        "_is_key_file_needs_passphrase",
        MagicMock(return_value=False),
    )
    @patch("paramiko.ProxyCommand")
    def test_fail_set_proxycommand(self, mock_ProxyCommand):
        """
        Loads proxy commands from ssh config file
        """
        ssh_config_file_path = os.path.join(
            get_resources_base_path(), "ssh", "dummy_ssh_config_fail"
        )
        cfg.CONF.set_override(
            name="ssh_config_file_path",
            override=ssh_config_file_path,
            group="ssh_runner",
        )
        cfg.CONF.set_override(name="use_ssh_config", override=True, group="ssh_runner")

        conn_params = {"hostname": "dummy.host.org"}
        mock = ParamikoSSHClient(**conn_params)
        self.assertRaises(Exception, mock.connect)
        mock_ProxyCommand.assert_not_called()

    @patch("paramiko.SSHClient", Mock)
    @patch.object(
        ParamikoSSHClient,
        "_is_key_file_needs_passphrase",
        MagicMock(return_value=False),
    )
    def test_create_with_password(self):
        conn_params = {
            "hostname": "dummy.host.org",
            "username": "ubuntu",
            "password": "ubuntu",
        }
        mock = ParamikoSSHClient(**conn_params)
        mock.connect()

        expected_conn = {
            "username": "ubuntu",
            "password": "ubuntu",
            "allow_agent": False,
            "hostname": "dummy.host.org",
            "look_for_keys": False,
            "timeout": 30,
            "port": 22,
        }
        mock.client.connect.assert_called_once_with(**expected_conn)

    @patch("paramiko.SSHClient", Mock)
    @patch.object(
        ParamikoSSHClient,
        "_is_key_file_needs_passphrase",
        MagicMock(return_value=False),
    )
    def test_deprecated_key_argument(self):
        conn_params = {
            "hostname": "dummy.host.org",
            "username": "ubuntu",
            "key_files": "id_rsa",
        }
        mock = ParamikoSSHClient(**conn_params)
        mock.connect()

        expected_conn = {
            "username": "ubuntu",
            "allow_agent": False,
            "hostname": "dummy.host.org",
            "look_for_keys": False,
            "key_filename": "id_rsa",
            "timeout": 30,
            "port": 22,
        }
        mock.client.connect.assert_called_once_with(**expected_conn)

    def test_key_files_and_key_material_arguments_are_mutual_exclusive(self):
        conn_params = {
            "hostname": "dummy.host.org",
            "username": "ubuntu",
            "key_files": "id_rsa",
            "key_material": "key",
        }

        expected_msg = (
            "key_files and key_material arguments are mutually exclusive. "
            "Supply only one."
        )

        client = ParamikoSSHClient(**conn_params)

        self.assertRaisesRegex(ValueError, expected_msg, client.connect)

    @patch("paramiko.SSHClient", Mock)
    @patch.object(
        ParamikoSSHClient,
        "_is_key_file_needs_passphrase",
        MagicMock(return_value=False),
    )
    def test_key_material_argument(self):
        path = os.path.join(get_resources_base_path(), "ssh", "dummy_rsa")

        with open(path, "r") as fp:
            private_key = fp.read()

        conn_params = {
            "hostname": "dummy.host.org",
            "username": "ubuntu",
            "key_material": private_key,
        }
        mock = ParamikoSSHClient(**conn_params)
        mock.connect()

        pkey = paramiko.RSAKey.from_private_key(StringIO(private_key))
        expected_conn = {
            "username": "ubuntu",
            "allow_agent": False,
            "hostname": "dummy.host.org",
            "look_for_keys": False,
            "pkey": pkey,
            "timeout": 30,
            "port": 22,
        }
        mock.client.connect.assert_called_once_with(**expected_conn)

    @patch("paramiko.SSHClient", Mock)
    @patch.object(
        ParamikoSSHClient,
        "_is_key_file_needs_passphrase",
        MagicMock(return_value=False),
    )
    def test_key_material_argument_invalid_key(self):
        conn_params = {
            "hostname": "dummy.host.org",
            "username": "ubuntu",
            "key_material": "id_rsa",
        }

        mock = ParamikoSSHClient(**conn_params)

        expected_msg = "Invalid or unsupported key type"
        self.assertRaisesRegex(
            paramiko.ssh_exception.SSHException, expected_msg, mock.connect
        )

    @patch("paramiko.SSHClient", Mock)
    @patch.object(
        ParamikoSSHClient, "_is_key_file_needs_passphrase", MagicMock(return_value=True)
    )
    def test_passphrase_no_key_provided(self):
        conn_params = {
            "hostname": "dummy.host.org",
            "username": "ubuntu",
            "passphrase": "testphrase",
        }

        expected_msg = "passphrase should accompany private key material"
        client = ParamikoSSHClient(**conn_params)
        self.assertRaisesRegex(ValueError, expected_msg, client.connect)

    @patch("paramiko.SSHClient", Mock)
    def test_passphrase_not_provided_for_encrypted_key_file(self):
        path = os.path.join(get_resources_base_path(), "ssh", "dummy_rsa_passphrase")
        conn_params = {
            "hostname": "dummy.host.org",
            "username": "ubuntu",
            "key_files": path,
        }
        mock = ParamikoSSHClient(**conn_params)
        self.assertRaises(
            paramiko.ssh_exception.PasswordRequiredException, mock.connect
        )

    @patch("paramiko.SSHClient", Mock)
    @patch.object(
        ParamikoSSHClient, "_is_key_file_needs_passphrase", MagicMock(return_value=True)
    )
    def test_key_with_passphrase_success(self):
        path = os.path.join(get_resources_base_path(), "ssh", "dummy_rsa_passphrase")

        with open(path, "r") as fp:
            private_key = fp.read()

        # Key material provided
        conn_params = {
            "hostname": "dummy.host.org",
            "username": "ubuntu",
            "key_material": private_key,
            "passphrase": "testphrase",
        }
        mock = ParamikoSSHClient(**conn_params)
        mock.connect()

        pkey = paramiko.RSAKey.from_private_key(StringIO(private_key), "testphrase")
        expected_conn = {
            "username": "ubuntu",
            "allow_agent": False,
            "hostname": "dummy.host.org",
            "look_for_keys": False,
            "pkey": pkey,
            "timeout": 30,
            "port": 22,
        }
        mock.client.connect.assert_called_once_with(**expected_conn)

        # Path to private key file provided
        conn_params = {
            "hostname": "dummy.host.org",
            "username": "ubuntu",
            "key_files": path,
            "passphrase": "testphrase",
        }
        mock = ParamikoSSHClient(**conn_params)
        mock.connect()

        expected_conn = {
            "username": "ubuntu",
            "allow_agent": False,
            "hostname": "dummy.host.org",
            "look_for_keys": False,
            "key_filename": path,
            "password": "testphrase",
            "timeout": 30,
            "port": 22,
        }
        mock.client.connect.assert_called_once_with(**expected_conn)

    @patch("paramiko.SSHClient", Mock)
    @patch.object(
        ParamikoSSHClient, "_is_key_file_needs_passphrase", MagicMock(return_value=True)
    )
    def test_passphrase_and_no_key(self):
        conn_params = {
            "hostname": "dummy.host.org",
            "username": "ubuntu",
            "passphrase": "testphrase",
        }

        expected_msg = "passphrase should accompany private key material"
        client = ParamikoSSHClient(**conn_params)

        self.assertRaisesRegex(ValueError, expected_msg, client.connect)

    @patch("paramiko.SSHClient", Mock)
    @patch.object(
        ParamikoSSHClient, "_is_key_file_needs_passphrase", MagicMock(return_value=True)
    )
    def test_incorrect_passphrase(self):
        path = os.path.join(get_resources_base_path(), "ssh", "dummy_rsa_passphrase")

        with open(path, "r") as fp:
            private_key = fp.read()

        conn_params = {
            "hostname": "dummy.host.org",
            "username": "ubuntu",
            "key_material": private_key,
            "passphrase": "incorrect",
        }
        mock = ParamikoSSHClient(**conn_params)

        expected_msg = "Invalid passphrase or invalid/unsupported key type"
        self.assertRaisesRegex(
            paramiko.ssh_exception.SSHException, expected_msg, mock.connect
        )

    @patch("paramiko.SSHClient", Mock)
    @patch.object(
        ParamikoSSHClient,
        "_is_key_file_needs_passphrase",
        MagicMock(return_value=False),
    )
    def test_key_material_contains_path_not_contents(self):
        conn_params = {"hostname": "dummy.host.org", "username": "ubuntu"}
        key_materials = ["~/.ssh/id_rsa", "/tmp/id_rsa", "C:\\id_rsa"]

        expected_msg = (
            '"private_key" parameter needs to contain private key data / content and '
            "not a path"
        )

        for key_material in key_materials:
            conn_params = conn_params.copy()
            conn_params["key_material"] = key_material
            mock = ParamikoSSHClient(**conn_params)

            self.assertRaisesRegex(
                paramiko.ssh_exception.SSHException, expected_msg, mock.connect
            )

    @patch("paramiko.SSHClient", Mock)
    @patch.object(
        ParamikoSSHClient,
        "_is_key_file_needs_passphrase",
        MagicMock(return_value=False),
    )
    def test_create_with_key(self):
        conn_params = {
            "hostname": "dummy.host.org",
            "username": "ubuntu",
            "key_files": "id_rsa",
        }
        mock = ParamikoSSHClient(**conn_params)
        mock.connect()

        expected_conn = {
            "username": "ubuntu",
            "allow_agent": False,
            "hostname": "dummy.host.org",
            "look_for_keys": False,
            "key_filename": "id_rsa",
            "timeout": 30,
            "port": 22,
        }
        mock.client.connect.assert_called_once_with(**expected_conn)

    @patch("paramiko.SSHClient", Mock)
    @patch.object(
        ParamikoSSHClient,
        "_is_key_file_needs_passphrase",
        MagicMock(return_value=False),
    )
    def test_create_with_key_via_bastion(self):
        conn_params = {
            "hostname": "dummy.host.org",
            "bastion_host": "bastion.host.org",
            "username": "ubuntu",
            "key_files": "id_rsa",
        }
        mock = ParamikoSSHClient(**conn_params)
        mock.connect()

        expected_bastion_conn = {
            "username": "ubuntu",
            "allow_agent": False,
            "hostname": "bastion.host.org",
            "look_for_keys": False,
            "key_filename": "id_rsa",
            "timeout": 30,
            "port": 22,
        }
        mock.bastion_client.connect.assert_called_once_with(**expected_bastion_conn)

        expected_conn = {
            "username": "ubuntu",
            "allow_agent": False,
            "hostname": "dummy.host.org",
            "look_for_keys": False,
            "key_filename": "id_rsa",
            "timeout": 30,
            "port": 22,
            "sock": mock.bastion_socket,
        }
        mock.client.connect.assert_called_once_with(**expected_conn)

    @patch("paramiko.SSHClient", Mock)
    @patch.object(
        ParamikoSSHClient,
        "_is_key_file_needs_passphrase",
        MagicMock(return_value=False),
    )
    def test_create_with_password_and_key(self):
        conn_params = {
            "hostname": "dummy.host.org",
            "username": "ubuntu",
            "password": "ubuntu",
            "key_files": "id_rsa",
        }
        mock = ParamikoSSHClient(**conn_params)
        mock.connect()

        expected_conn = {
            "username": "ubuntu",
            "password": "ubuntu",
            "allow_agent": False,
            "hostname": "dummy.host.org",
            "look_for_keys": False,
            "key_filename": "id_rsa",
            "timeout": 30,
            "port": 22,
        }
        mock.client.connect.assert_called_once_with(**expected_conn)

    @patch("paramiko.SSHClient", Mock)
    @patch.object(
        ParamikoSSHClient,
        "_is_key_file_needs_passphrase",
        MagicMock(return_value=False),
    )
    def test_create_without_credentials(self):
        """
        Initialize object with no credentials.

        Just to have better coverage, initialize the object
        without 'password' neither 'key'. Now that we only reconcile
        the final parameters at the last moment when we explicitly
        try to connect, all the credentials should be set to None.
        """
        conn_params = {"hostname": "dummy.host.org", "username": "ubuntu"}
        mock = ParamikoSSHClient(**conn_params)

        self.assertEqual(mock.password, None)
        self.assertEqual(mock.key_material, None)
        self.assertEqual(mock.key_files, None)

    @patch("paramiko.SSHClient", Mock)
    @patch.object(
        ParamikoSSHClient,
        "_is_key_file_needs_passphrase",
        MagicMock(return_value=False),
    )
    def test_create_without_credentials_use_default_key(self):
        # No credentials are provided by default stanley ssh key exists so it should use that
        cfg.CONF.set_override(
            name="ssh_key_file", override="stanley_rsa", group="system_user"
        )

        conn_params = {"hostname": "dummy.host.org", "username": "ubuntu"}
        mock = ParamikoSSHClient(**conn_params)
        mock.connect()

        expected_conn = {
            "username": "ubuntu",
            "hostname": "dummy.host.org",
            "key_filename": "stanley_rsa",
            "allow_agent": False,
            "look_for_keys": False,
            "timeout": 30,
            "port": 22,
        }
        mock.client.connect.assert_called_once_with(**expected_conn)

    @patch("paramiko.SSHClient", Mock)
    @patch.object(
        ParamikoSSHClient, "_consume_stdout", MagicMock(return_value=StringIO(""))
    )
    @patch.object(
        ParamikoSSHClient, "_consume_stderr", MagicMock(return_value=StringIO(""))
    )
    @patch.object(os.path, "exists", MagicMock(return_value=True))
    @patch.object(os, "stat", MagicMock(return_value=None))
    @patch.object(
        ParamikoSSHClient,
        "_is_key_file_needs_passphrase",
        MagicMock(return_value=False),
    )
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
        expected_conn = {
            "username": "ubuntu",
            "key_filename": "~/.ssh/ubuntu_ssh",
            "allow_agent": False,
            "hostname": "dummy.host.org",
            "look_for_keys": False,
            "timeout": 28,
            "port": 8822,
        }
        mock_cli.connect.assert_called_once_with(**expected_conn)

        mock.put(sd, sd, mirror_local_mode=False)
        mock_cli.open_sftp().put.assert_called_once_with(sd, sd)

        mock.run(sd)

        # Make assertions over 'run' method
        mock_cli.get_transport().open_session().exec_command.assert_called_once_with(sd)

        mock.close()

    @patch("paramiko.SSHClient", Mock)
    @patch.object(
        ParamikoSSHClient,
        "_is_key_file_needs_passphrase",
        MagicMock(return_value=False),
    )
    def test_delete_script(self):
        """
        Provide a basic test with 'delete' action.
        """
        mock = self.ssh_cli
        # script to execute
        sd = "/root/random_script.sh"

        mock.connect()

        mock.delete_file(sd)
        # Make assertions over the 'delete' method
        mock.client.open_sftp().unlink.assert_called_with(sd)

        mock.close()

    @patch("paramiko.SSHClient", Mock)
    @patch.object(
        ParamikoSSHClient,
        "_is_key_file_needs_passphrase",
        MagicMock(return_value=False),
    )
    @patch.object(ParamikoSSHClient, "exists", return_value=False)
    def test_put_dir(self, *args):
        mock = self.ssh_cli
        mock.connect()

        local_dir = os.path.join(get_resources_base_path(), "packs")
        mock.put_dir(local_path=local_dir, remote_path="/tmp")

        mock_cli = mock.client  # The actual mocked object: SSHClient

        # Assert that expected dirs are created on remote box.
        calls = [
            call("/tmp/packs/pythonactions"),
            call("/tmp/packs/pythonactions/actions"),
        ]
        mock_cli.open_sftp().mkdir.assert_has_calls(calls, any_order=True)

        # Assert that expected files are copied to remote box.
        local_file = os.path.join(
            get_resources_base_path(), "packs/pythonactions/actions/pascal_row.py"
        )
        remote_file = os.path.join("/tmp", "packs/pythonactions/actions/pascal_row.py")

        calls = [call(local_file, remote_file)]
        mock_cli.open_sftp().put.assert_has_calls(calls, any_order=True)

    @patch("paramiko.SSHClient", Mock)
    @patch.object(
        ParamikoSSHClient,
        "_is_key_file_needs_passphrase",
        MagicMock(return_value=False),
    )
    def test_consume_stdout(self):
        # Test utf-8 decoding of ``stdout`` still works fine when reading CHUNK_SIZE splits a
        # multi-byte utf-8 character in the middle. We should wait to collect all bytes
        # and finally decode.
        conn_params = {"hostname": "dummy.host.org", "username": "ubuntu"}
        mock = ParamikoSSHClient(**conn_params)
        mock.CHUNK_SIZE = 1
        chan = Mock()
        chan.recv_ready.side_effect = [True, True, True, True, False]

        chan.recv.side_effect = [b"\xF0", b"\x90", b"\x8D", b"\x88"]
        try:
            b"\xF0".decode("utf-8")
            self.fail("Test fixture is not right.")
        except UnicodeDecodeError:
            pass
        stdout = mock._consume_stdout(chan)

        self.assertEqual("\U00010348", stdout.getvalue())

    @patch("paramiko.SSHClient", Mock)
    @patch.object(
        ParamikoSSHClient,
        "_is_key_file_needs_passphrase",
        MagicMock(return_value=False),
    )
    def test_consume_stderr(self):
        # Test utf-8 decoding of ``stderr`` still works fine when reading CHUNK_SIZE splits a
        # multi-byte utf-8 character in the middle. We should wait to collect all bytes
        # and finally decode.
        conn_params = {"hostname": "dummy.host.org", "username": "ubuntu"}
        mock = ParamikoSSHClient(**conn_params)
        mock.CHUNK_SIZE = 1
        chan = Mock()
        chan.recv_stderr_ready.side_effect = [True, True, True, True, False]

        chan.recv_stderr.side_effect = [b"\xF0", b"\x90", b"\x8D", b"\x88"]
        try:
            b"\xF0".decode("utf-8")
            self.fail("Test fixture is not right.")
        except UnicodeDecodeError:
            pass
        stderr = mock._consume_stderr(chan)
        self.assertEqual("\U00010348", stderr.getvalue())

    @patch("paramiko.SSHClient", Mock)
    @patch.object(
        ParamikoSSHClient, "_consume_stdout", MagicMock(return_value=StringIO(""))
    )
    @patch.object(
        ParamikoSSHClient, "_consume_stderr", MagicMock(return_value=StringIO(""))
    )
    @patch.object(os.path, "exists", MagicMock(return_value=True))
    @patch.object(os, "stat", MagicMock(return_value=None))
    @patch.object(
        ParamikoSSHClient,
        "_is_key_file_needs_passphrase",
        MagicMock(return_value=False),
    )
    def test_sftp_connection_is_only_established_if_required(self):
        # Verify that SFTP connection is lazily established only if and when needed.
        conn_params = {
            "hostname": "dummy.host.org",
            "username": "ubuntu",
            "password": "ubuntu",
        }

        # Verify sftp connection and client hasn't been established yet
        client = ParamikoSSHClient(**conn_params)
        client.connect()

        self.assertIsNone(client.sftp_client)

        # run method doesn't require sftp access so it shouldn't establish connection
        client = ParamikoSSHClient(**conn_params)
        client.connect()
        client.run(cmd="whoami")

        self.assertIsNone(client.sftp_client)

        # Methods below require SFTP access so they should cause SFTP connection to be established
        # put
        client = ParamikoSSHClient(**conn_params)
        client.connect()
        path = "/root/random_script.sh"
        client.put(path, path, mirror_local_mode=False)

        self.assertIsNotNone(client.sftp_client)

        # exists
        client = ParamikoSSHClient(**conn_params)
        client.connect()
        client.exists("/root/somepath.txt")

        self.assertIsNotNone(client.sftp_client)

        # mkdir
        client = ParamikoSSHClient(**conn_params)
        client.connect()
        client.mkdir("/root/somedirfoo")

        self.assertIsNotNone(client.sftp_client)

        # Verify close doesn't throw if SFTP connection is not established
        client = ParamikoSSHClient(**conn_params)
        client.connect()

        self.assertIsNone(client.sftp_client)
        client.close()

        # Verify SFTP connection is closed if it's opened
        client = ParamikoSSHClient(**conn_params)
        client.connect()
        client.mkdir("/root/somedirfoo")

        self.assertIsNotNone(client.sftp_client)
        client.close()

        self.assertEqual(client.sftp_client.close.call_count, 1)

    @patch("paramiko.SSHClient", Mock)
    @patch.object(os.path, "exists", MagicMock(return_value=True))
    @patch.object(os, "stat", MagicMock(return_value=None))
    def test_handle_stdout_and_stderr_line_funcs(self):
        mock_handle_stdout_line_func = mock.Mock()
        mock_handle_stderr_line_func = mock.Mock()

        conn_params = {
            "hostname": "dummy.host.org",
            "username": "ubuntu",
            "password": "ubuntu",
            "handle_stdout_line_func": mock_handle_stdout_line_func,
            "handle_stderr_line_func": mock_handle_stderr_line_func,
        }
        client = ParamikoSSHClient(**conn_params)
        client.connect()

        mock_get_transport = mock.Mock()
        mock_chan = mock.Mock()

        client.client.get_transport = mock.Mock()
        client.client.get_transport.return_value = mock_get_transport
        mock_get_transport.open_session.return_value = mock_chan

        def mock_recv_ready_factory(chan):
            chan.recv_counter = 0

            def mock_recv_ready():
                chan.recv_counter += 1
                if chan.recv_counter < 2:
                    return True

                return False

            return mock_recv_ready

        def mock_recv_stderr_ready_factory(chan):
            chan.recv_stderr_counter = 0

            def mock_recv_stderr_ready():
                chan.recv_stderr_counter += 1
                if chan.recv_stderr_counter < 2:
                    return True

                return False

            return mock_recv_stderr_ready

        mock_chan.recv_ready = mock_recv_ready_factory(mock_chan)
        mock_chan.recv_stderr_ready = mock_recv_stderr_ready_factory(mock_chan)
        mock_chan.recv.return_value = "stdout 1\nstdout 2\nstdout 3"
        mock_chan.recv_stderr.return_value = "stderr 1\nstderr 2\nstderr 3"

        # call_line_handler_func is False so handler functions shouldn't be called
        client.run(cmd='echo "test"', call_line_handler_func=False)

        self.assertEqual(mock_handle_stdout_line_func.call_count, 0)
        self.assertEqual(mock_handle_stderr_line_func.call_count, 0)

        # Reset counters
        mock_chan.recv_counter = 0
        mock_chan.recv_stderr_counter = 0

        # call_line_handler_func is True so handler functions should be called for each line
        client.run(cmd='echo "test"', call_line_handler_func=True)

        self.assertEqual(mock_handle_stdout_line_func.call_count, 3)
        self.assertEqual(
            mock_handle_stdout_line_func.call_args_list[0][1]["line"], "stdout 1\n"
        )
        self.assertEqual(
            mock_handle_stdout_line_func.call_args_list[1][1]["line"], "stdout 2\n"
        )
        self.assertEqual(
            mock_handle_stdout_line_func.call_args_list[2][1]["line"], "stdout 3\n"
        )
        self.assertEqual(mock_handle_stderr_line_func.call_count, 3)
        self.assertEqual(
            mock_handle_stdout_line_func.call_args_list[0][1]["line"], "stdout 1\n"
        )
        self.assertEqual(
            mock_handle_stdout_line_func.call_args_list[1][1]["line"], "stdout 2\n"
        )
        self.assertEqual(
            mock_handle_stdout_line_func.call_args_list[2][1]["line"], "stdout 3\n"
        )

    @patch("paramiko.SSHClient")
    def test_use_ssh_config_port_value_provided_in_the_config(self, mock_sshclient):
        cfg.CONF.set_override(name="use_ssh_config", override=True, group="ssh_runner")

        ssh_config_file_path = os.path.join(
            get_resources_base_path(), "ssh", "empty_config"
        )
        cfg.CONF.set_override(
            name="ssh_config_file_path",
            override=ssh_config_file_path,
            group="ssh_runner",
        )

        # 1. Default port is used (not explicitly provided)
        mock_client = mock.Mock()
        mock_sshclient.return_value = mock_client
        conn_params = {
            "hostname": "dummy.host.org",
            "username": "ubuntu",
            "password": "pass",
            "timeout": "600",
        }
        ssh_client = ParamikoSSHClient(**conn_params)
        ssh_client.connect()

        call_kwargs = mock_client.connect.call_args[1]
        self.assertEqual(call_kwargs["port"], 22)

        mock_client = mock.Mock()
        mock_sshclient.return_value = mock_client
        conn_params = {
            "hostname": "dummy.host.org",
            "username": "ubuntu",
            "password": "pass",
            "port": None,
            "timeout": "600",
        }
        ssh_client = ParamikoSSHClient(**conn_params)
        ssh_client.connect()

        call_kwargs = mock_client.connect.call_args[1]
        self.assertEqual(call_kwargs["port"], 22)

        # 2. Default port is used (explicitly provided)
        mock_client = mock.Mock()
        mock_sshclient.return_value = mock_client
        conn_params = {
            "hostname": "dummy.host.org",
            "username": "ubuntu",
            "password": "pass",
            "port": DEFAULT_SSH_PORT,
            "timeout": "600",
        }
        ssh_client = ParamikoSSHClient(**conn_params)
        ssh_client.connect()

        call_kwargs = mock_client.connect.call_args[1]
        self.assertEqual(call_kwargs["port"], DEFAULT_SSH_PORT)
        self.assertEqual(call_kwargs["port"], 22)

        # 3. Custom port is used (explicitly provided)
        mock_client = mock.Mock()
        mock_sshclient.return_value = mock_client
        conn_params = {
            "hostname": "dummy.host.org",
            "username": "ubuntu",
            "password": "pass",
            "port": 5555,
            "timeout": "600",
        }
        ssh_client = ParamikoSSHClient(**conn_params)
        ssh_client.connect()

        call_kwargs = mock_client.connect.call_args[1]
        self.assertEqual(call_kwargs["port"], 5555)

        # 4. Custom port is specified in the ssh config (it has precedence over default port)
        ssh_config_file_path = os.path.join(
            get_resources_base_path(), "ssh", "ssh_config_custom_port"
        )
        cfg.CONF.set_override(
            name="ssh_config_file_path",
            override=ssh_config_file_path,
            group="ssh_runner",
        )

        mock_client = mock.Mock()
        mock_sshclient.return_value = mock_client
        conn_params = {
            "hostname": "dummy.host.org",
            "username": "ubuntu",
            "password": "pass",
        }
        ssh_client = ParamikoSSHClient(**conn_params)
        ssh_client.connect()

        call_kwargs = mock_client.connect.call_args[1]
        self.assertEqual(call_kwargs["port"], 6677)

        mock_client = mock.Mock()
        mock_sshclient.return_value = mock_client
        conn_params = {
            "hostname": "dummy.host.org",
            "username": "ubuntu",
            "password": "pass",
            "port": DEFAULT_SSH_PORT,
        }
        ssh_client = ParamikoSSHClient(**conn_params)
        ssh_client.connect()

        call_kwargs = mock_client.connect.call_args[1]
        self.assertEqual(call_kwargs["port"], 6677)

        # 5. Custom port is specified in ssh config, but one is also provided via runner parameter
        # (runner parameter one has precedence)
        ssh_config_file_path = os.path.join(
            get_resources_base_path(), "ssh", "ssh_config_custom_port"
        )
        cfg.CONF.set_override(
            name="ssh_config_file_path",
            override=ssh_config_file_path,
            group="ssh_runner",
        )

        mock_client = mock.Mock()
        mock_sshclient.return_value = mock_client
        conn_params = {
            "hostname": "dummy.host.org",
            "username": "ubuntu",
            "password": "pass",
            "port": 9999,
        }
        ssh_client = ParamikoSSHClient(**conn_params)
        ssh_client.connect()

        call_kwargs = mock_client.connect.call_args[1]
        self.assertEqual(call_kwargs["port"], 9999)

    @patch.object(
        ParamikoSSHClient,
        "_is_key_file_needs_passphrase",
        MagicMock(return_value=False),
    )
    def test_socket_closed(self):
        conn_params = {
            "hostname": "dummy.host.org",
            "username": "ubuntu",
            "password": "pass",
            "timeout": "600",
        }
        ssh_client = ParamikoSSHClient(**conn_params)

        # Make sure .close() doesn't actually call anything real
        ssh_client.client = Mock()
        ssh_client.sftp_client = Mock()
        ssh_client.bastion_client = Mock()

        ssh_client.socket = Mock()
        ssh_client.bastion_socket = Mock()

        # Make sure we havent called any close methods at this point
        # TODO: Replace these with .assert_not_called() once it's Python 3.6+ only
        self.assertEqual(ssh_client.socket.close.call_count, 0)
        self.assertEqual(ssh_client.client.close.call_count, 0)
        self.assertEqual(ssh_client.sftp_client.close.call_count, 0)
        self.assertEqual(ssh_client.bastion_socket.close.call_count, 0)
        self.assertEqual(ssh_client.bastion_client.close.call_count, 0)

        # Call the function that has changed
        ssh_client.close()

        # TODO: Replace these with .assert_called_once() once it's Python 3.6+ only
        self.assertEqual(ssh_client.socket.close.call_count, 1)
        self.assertEqual(ssh_client.client.close.call_count, 1)
        self.assertEqual(ssh_client.sftp_client.close.call_count, 1)
        self.assertEqual(ssh_client.bastion_socket.close.call_count, 1)
        self.assertEqual(ssh_client.bastion_client.close.call_count, 1)

    @patch.object(
        ParamikoSSHClient,
        "_is_key_file_needs_passphrase",
        MagicMock(return_value=False),
    )
    def test_socket_not_closed_if_none(self):
        conn_params = {
            "hostname": "dummy.host.org",
            "username": "ubuntu",
            "password": "pass",
            "timeout": "600",
        }
        ssh_client = ParamikoSSHClient(**conn_params)

        # Make sure .close() doesn't actually call anything real
        ssh_client.client = None
        ssh_client.sftp_client = None
        ssh_client.bastion_client = None

        ssh_client.socket = None
        ssh_client.bastion_socket = None

        # Call the function, this should not throw an exception
        ssh_client.close()

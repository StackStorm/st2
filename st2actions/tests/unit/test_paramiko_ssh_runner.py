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

import unittest
import mock

from st2common.runners.paramiko_ssh_runner import BaseParallelSSHRunner
from st2common.runners.paramiko_ssh_runner import RUNNER_HOSTS
from st2common.runners.paramiko_ssh_runner import RUNNER_USERNAME
from st2common.runners.paramiko_ssh_runner import RUNNER_PASSWORD
from st2common.runners.paramiko_ssh_runner import RUNNER_PRIVATE_KEY
from st2common.runners.paramiko_ssh_runner import RUNNER_PASSPHRASE
from st2common.runners.paramiko_ssh_runner import RUNNER_SSH_PORT

import st2tests.config as tests_config
from st2tests.fixturesloader import get_resources_base_path


class Runner(BaseParallelSSHRunner):
    def run(self):
        pass


class ParamikoSSHRunnerTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        tests_config.parse_args()

    @mock.patch("st2common.runners.paramiko_ssh_runner.ParallelSSHClient")
    def test_pre_run(self, mock_client):
        # Test case which verifies that ParamikoSSHClient is instantiated with the correct arguments
        private_key_path = os.path.join(get_resources_base_path(), "ssh", "dummy_rsa")

        with open(private_key_path, "r") as fp:
            private_key = fp.read()

        # Username and password provided
        runner = Runner("id")
        runner.context = {}
        runner_parameters = {
            RUNNER_HOSTS: "localhost",
            RUNNER_USERNAME: "someuser1",
            RUNNER_PASSWORD: "somepassword",
        }
        runner.runner_parameters = runner_parameters
        runner.pre_run()

        expected_kwargs = {
            "hosts": ["localhost"],
            "user": "someuser1",
            "password": "somepassword",
            "port": None,
            "concurrency": 1,
            "bastion_host": None,
            "raise_on_any_error": False,
            "connect": True,
            "handle_stdout_line_func": mock.ANY,
            "handle_stderr_line_func": mock.ANY,
        }
        mock_client.assert_called_with(**expected_kwargs)

        # Private key provided as raw key material
        runner = Runner("id")
        runner.context = {}
        runner_parameters = {
            RUNNER_HOSTS: "localhost",
            RUNNER_USERNAME: "someuser2",
            RUNNER_PRIVATE_KEY: private_key,
            RUNNER_SSH_PORT: 22,
        }
        runner.runner_parameters = runner_parameters
        runner.pre_run()

        expected_kwargs = {
            "hosts": ["localhost"],
            "user": "someuser2",
            "pkey_material": private_key,
            "port": 22,
            "concurrency": 1,
            "bastion_host": None,
            "raise_on_any_error": False,
            "connect": True,
            "handle_stdout_line_func": mock.ANY,
            "handle_stderr_line_func": mock.ANY,
        }
        mock_client.assert_called_with(**expected_kwargs)

        # Private key provided as raw key material + passphrase
        runner = Runner("id")
        runner.context = {}
        runner_parameters = {
            RUNNER_HOSTS: "localhost21",
            RUNNER_USERNAME: "someuser21",
            RUNNER_PRIVATE_KEY: private_key,
            RUNNER_PASSPHRASE: "passphrase21",
            RUNNER_SSH_PORT: 22,
        }
        runner.runner_parameters = runner_parameters
        runner.pre_run()

        expected_kwargs = {
            "hosts": ["localhost21"],
            "user": "someuser21",
            "pkey_material": private_key,
            "passphrase": "passphrase21",
            "port": 22,
            "concurrency": 1,
            "bastion_host": None,
            "raise_on_any_error": False,
            "connect": True,
            "handle_stdout_line_func": mock.ANY,
            "handle_stderr_line_func": mock.ANY,
        }
        mock_client.assert_called_with(**expected_kwargs)

        # Private key provided as path to the private key file
        runner = Runner("id")
        runner.context = {}
        runner_parameters = {
            RUNNER_HOSTS: "localhost",
            RUNNER_USERNAME: "someuser3",
            RUNNER_PRIVATE_KEY: private_key_path,
            RUNNER_SSH_PORT: 22,
        }
        runner.runner_parameters = runner_parameters
        runner.pre_run()

        expected_kwargs = {
            "hosts": ["localhost"],
            "user": "someuser3",
            "pkey_file": private_key_path,
            "port": 22,
            "concurrency": 1,
            "bastion_host": None,
            "raise_on_any_error": False,
            "connect": True,
            "handle_stdout_line_func": mock.ANY,
            "handle_stderr_line_func": mock.ANY,
        }
        mock_client.assert_called_with(**expected_kwargs)

        # Private key provided as path to the private key file + passphrase
        runner = Runner("id")
        runner.context = {}
        runner_parameters = {
            RUNNER_HOSTS: "localhost31",
            RUNNER_USERNAME: "someuser31",
            RUNNER_PRIVATE_KEY: private_key_path,
            RUNNER_PASSPHRASE: "passphrase31",
            RUNNER_SSH_PORT: 22,
        }
        runner.runner_parameters = runner_parameters
        runner.pre_run()

        expected_kwargs = {
            "hosts": ["localhost31"],
            "user": "someuser31",
            "pkey_file": private_key_path,
            "passphrase": "passphrase31",
            "port": 22,
            "concurrency": 1,
            "bastion_host": None,
            "raise_on_any_error": False,
            "connect": True,
            "handle_stdout_line_func": mock.ANY,
            "handle_stderr_line_func": mock.ANY,
        }
        mock_client.assert_called_with(**expected_kwargs)

        # No password or private key provided, should default to system user private key
        runner = Runner("id")
        runner.context = {}
        runner_parameters = {RUNNER_HOSTS: "localhost4", RUNNER_SSH_PORT: 22}
        runner.runner_parameters = runner_parameters
        runner.pre_run()

        expected_kwargs = {
            "hosts": ["localhost4"],
            "user": None,
            "pkey_file": None,
            "port": 22,
            "concurrency": 1,
            "bastion_host": None,
            "raise_on_any_error": False,
            "connect": True,
            "handle_stdout_line_func": mock.ANY,
            "handle_stderr_line_func": mock.ANY,
        }
        mock_client.assert_called_with(**expected_kwargs)

    @mock.patch("st2common.runners.paramiko_ssh_runner.ParallelSSHClient")
    def test_post_run(self, mock_client):
        # Verify that the SSH connections are closed on post_run
        runner = Runner("id")
        runner.context = {}
        runner_parameters = {
            RUNNER_HOSTS: "localhost",
            RUNNER_USERNAME: "someuser1",
            RUNNER_PASSWORD: "somepassword",
        }
        runner.runner_parameters = runner_parameters
        runner.pre_run()

        expected_kwargs = {
            "hosts": ["localhost"],
            "user": "someuser1",
            "password": "somepassword",
            "port": None,
            "concurrency": 1,
            "bastion_host": None,
            "raise_on_any_error": False,
            "connect": True,
            "handle_stdout_line_func": mock.ANY,
            "handle_stderr_line_func": mock.ANY,
        }
        mock_client.assert_called_with(**expected_kwargs)
        self.assertEqual(runner._parallel_ssh_client.close.call_count, 0)

        runner.post_run(result=None, status=None)

        # Verify connections are closed
        self.assertEqual(runner._parallel_ssh_client.close.call_count, 1)

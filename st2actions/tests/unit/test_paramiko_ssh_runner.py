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

import unittest2
import mock
from oslo_config import cfg

from st2actions.runners.ssh.paramiko_ssh_runner import BaseParallelSSHRunner
from st2actions.runners.ssh.paramiko_ssh_runner import RUNNER_HOSTS
from st2actions.runners.ssh.paramiko_ssh_runner import RUNNER_USERNAME
from st2actions.runners.ssh.paramiko_ssh_runner import RUNNER_PASSWORD
from st2actions.runners.ssh.paramiko_ssh_runner import RUNNER_PRIVATE_KEY
from st2actions.runners.ssh.paramiko_ssh_runner import RUNNER_PASSPHRASE

import st2tests.config as tests_config
from st2tests.fixturesloader import get_resources_base_path
tests_config.parse_args()


class Runner(BaseParallelSSHRunner):
    def run(self):
        pass


class ParamikoSSHRunnerTestCase(unittest2.TestCase):
    @mock.patch('st2actions.runners.ssh.paramiko_ssh_runner.ParallelSSHClient')
    def test_pre_run(self, mock_client):
        # Test case which verifies that ParamikoSSHClient is instantiated with the correct arguments
        private_key_path = os.path.join(get_resources_base_path(),
                                       'ssh', 'dummy_rsa')

        with open(private_key_path, 'r') as fp:
            private_key = fp.read()

        # Username and password provided
        runner = Runner('id')
        runner.context = {}
        runner_parameters = {
            RUNNER_HOSTS: 'localhost',
            RUNNER_USERNAME: 'someuser1',
            RUNNER_PASSWORD: 'somepassword'
        }
        runner.runner_parameters = runner_parameters
        runner.pre_run()

        expected_kwargs = {
            'hosts': ['localhost'],
            'user': 'someuser1',
            'password': 'somepassword',
            'port': 22,
            'concurrency': 1,
            'bastion_host': None,
            'raise_on_any_error': False,
            'connect': True
        }
        mock_client.assert_called_with(**expected_kwargs)

        # Private key provided as raw key material
        runner = Runner('id')
        runner.context = {}
        runner_parameters = {
            RUNNER_HOSTS: 'localhost',
            RUNNER_USERNAME: 'someuser2',
            RUNNER_PRIVATE_KEY: private_key
        }
        runner.runner_parameters = runner_parameters
        runner.pre_run()

        expected_kwargs = {
            'hosts': ['localhost'],
            'user': 'someuser2',
            'pkey_material': private_key,
            'port': 22,
            'concurrency': 1,
            'bastion_host': None,
            'raise_on_any_error': False,
            'connect': True
        }
        mock_client.assert_called_with(**expected_kwargs)

        # Private key provided as raw key material + passphrase
        runner = Runner('id')
        runner.context = {}
        runner_parameters = {
            RUNNER_HOSTS: 'localhost21',
            RUNNER_USERNAME: 'someuser21',
            RUNNER_PRIVATE_KEY: private_key,
            RUNNER_PASSPHRASE: 'passphrase21'
        }
        runner.runner_parameters = runner_parameters
        runner.pre_run()

        expected_kwargs = {
            'hosts': ['localhost21'],
            'user': 'someuser21',
            'pkey_material': private_key,
            'passphrase': 'passphrase21',
            'port': 22,
            'concurrency': 1,
            'bastion_host': None,
            'raise_on_any_error': False,
            'connect': True
        }
        mock_client.assert_called_with(**expected_kwargs)

        # Private key provided as path to the private key file
        runner = Runner('id')
        runner.context = {}
        runner_parameters = {
            RUNNER_HOSTS: 'localhost',
            RUNNER_USERNAME: 'someuser3',
            RUNNER_PRIVATE_KEY: private_key_path
        }
        runner.runner_parameters = runner_parameters
        runner.pre_run()

        expected_kwargs = {
            'hosts': ['localhost'],
            'user': 'someuser3',
            'pkey_file': private_key_path,
            'port': 22,
            'concurrency': 1,
            'bastion_host': None,
            'raise_on_any_error': False,
            'connect': True
        }
        mock_client.assert_called_with(**expected_kwargs)

        # Private key provided as path to the private key file + passpharse
        runner = Runner('id')
        runner.context = {}
        runner_parameters = {
            RUNNER_HOSTS: 'localhost31',
            RUNNER_USERNAME: 'someuser31',
            RUNNER_PRIVATE_KEY: private_key_path,
            RUNNER_PASSPHRASE: 'passphrase31'
        }
        runner.runner_parameters = runner_parameters
        runner.pre_run()

        expected_kwargs = {
            'hosts': ['localhost31'],
            'user': 'someuser31',
            'pkey_file': private_key_path,
            'passphrase': 'passphrase31',
            'port': 22,
            'concurrency': 1,
            'bastion_host': None,
            'raise_on_any_error': False,
            'connect': True
        }
        mock_client.assert_called_with(**expected_kwargs)

        # No password or private key provided, should default to system user private key
        runner = Runner('id')
        runner.context = {}
        runner_parameters = {
            RUNNER_HOSTS: 'localhost4',
        }
        runner.runner_parameters = runner_parameters
        runner.pre_run()

        expected_kwargs = {
            'hosts': ['localhost4'],
            'user': cfg.CONF.system_user.user,
            'pkey_file': cfg.CONF.system_user.ssh_key_file,
            'port': 22,
            'concurrency': 1,
            'bastion_host': None,
            'raise_on_any_error': False,
            'connect': True
        }
        mock_client.assert_called_with(**expected_kwargs)

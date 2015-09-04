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

import bson
from mock import patch, Mock, MagicMock
import unittest2

# XXX: There is an import dependency. Config needs to setup
# before importing remote_script_runner classes.
import st2tests.config as tests_config
tests_config.parse_args()

from st2actions.runners.remote_script_runner import ParamikoRemoteScriptRunner
from st2actions.runners.ssh.parallel_ssh import ParallelSSHClient
from st2common.exceptions.ssh import InvalidCredentialsException
from st2common.exceptions.ssh import NoHostsConnectedToException
from st2common.models.system.action import RemoteScriptAction
import st2common.util.jsonify as jsonify


class ParamikoScriptRunnerTestCase(unittest2.TestCase):

    @patch('st2actions.runners.ssh.parallel_ssh.ParallelSSHClient', Mock)
    @patch.object(jsonify, 'json_loads', MagicMock(return_value={}))
    @patch.object(ParallelSSHClient, 'run', MagicMock(return_value={}))
    @patch.object(ParallelSSHClient, 'connect', MagicMock(return_value={}))
    def test_cwd_used_correctly(self):
        remote_action = RemoteScriptAction(
            'foo-script', bson.ObjectId(),
            script_local_path_abs='/home/stanley/shiz_storm.py',
            script_local_libs_path_abs=None,
            named_args={}, positional_args=['blank space'], env_vars={},
            on_behalf_user='svetlana', user='stanley',
            private_key='---SOME RSA KEY---',
            remote_dir='/tmp', hosts=['localhost'], cwd='/test/cwd/'
        )
        paramiko_runner = ParamikoRemoteScriptRunner('runner_1')
        paramiko_runner._parallel_ssh_client = ParallelSSHClient(['localhost'], 'stanley')
        paramiko_runner._run_script_on_remote_host(remote_action)
        ParallelSSHClient.run.assert_called_with("/tmp/shiz_storm.py 'blank space'",
                                                 cwd='/test/cwd/', timeout=None)

    @patch('st2actions.runners.ssh.parallel_ssh.ParallelSSHClient', Mock)
    @patch.object(ParallelSSHClient, 'run', MagicMock(return_value={}))
    @patch.object(ParallelSSHClient, 'connect', MagicMock(return_value={}))
    def test_username_only_ssh(self):
        paramiko_runner = ParamikoRemoteScriptRunner('runner_1')

        paramiko_runner.runner_parameters = {'username': 'test_user', 'hosts': 'localhost'}
        self.assertRaises(InvalidCredentialsException, paramiko_runner.pre_run)

    def test_username_invalid_private_key(self):
        paramiko_runner = ParamikoRemoteScriptRunner('runner_1')

        paramiko_runner.runner_parameters = {
            'username': 'test_user',
            'hosts': 'localhost',
            'private_key': 'invalid private key',
        }
        paramiko_runner.context = {}
        self.assertRaises(NoHostsConnectedToException, paramiko_runner.pre_run)

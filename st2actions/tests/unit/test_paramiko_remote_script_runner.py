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

from st2common.util import jsonify
from st2actions.runners.remote_script_runner import ParamikoRemoteScriptRunner
from st2actions.runners.ssh.parallel_ssh import ParallelSSHClient
from st2common.exceptions.ssh import InvalidCredentialsException
from st2common.exceptions.ssh import NoHostsConnectedToException
from st2common.models.system.paramiko_script_action import ParamikoRemoteScriptAction
from st2common.constants.action import LIVEACTION_STATUS_FAILED
from st2tests.fixturesloader import FixturesLoader

__all__ = [
    'ParamikoScriptRunnerTestCase'
]

FIXTURES_PACK = 'generic'
TEST_MODELS = {
    'actions': ['a1.yaml']
}

MODELS = FixturesLoader().load_models(fixtures_pack=FIXTURES_PACK,
                                      fixtures_dict=TEST_MODELS)
ACTION_1 = MODELS['actions']['a1.yaml']


class ParamikoScriptRunnerTestCase(unittest2.TestCase):
    @patch('st2actions.runners.ssh.parallel_ssh.ParallelSSHClient', Mock)
    @patch.object(jsonify, 'json_loads', MagicMock(return_value={}))
    @patch.object(ParallelSSHClient, 'run', MagicMock(return_value={}))
    @patch.object(ParallelSSHClient, 'connect', MagicMock(return_value={}))
    def test_cwd_used_correctly(self):
        remote_action = ParamikoRemoteScriptAction(
            'foo-script', bson.ObjectId(),
            script_local_path_abs='/home/stanley/shiz_storm.py',
            script_local_libs_path_abs=None,
            named_args={}, positional_args=['blank space'], env_vars={},
            on_behalf_user='svetlana', user='stanley',
            private_key='---SOME RSA KEY---',
            remote_dir='/tmp', hosts=['127.0.0.1'], cwd='/test/cwd/'
        )
        paramiko_runner = ParamikoRemoteScriptRunner('runner_1')
        paramiko_runner._parallel_ssh_client = ParallelSSHClient(['127.0.0.1'], 'stanley')
        paramiko_runner._run_script_on_remote_host(remote_action)
        exp_cmd = "cd /test/cwd/ && /tmp/shiz_storm.py 'blank space'"
        ParallelSSHClient.run.assert_called_with(exp_cmd,
                                                 timeout=None)

    @patch('st2actions.runners.ssh.parallel_ssh.ParallelSSHClient', Mock)
    @patch.object(ParallelSSHClient, 'run', MagicMock(return_value={}))
    @patch.object(ParallelSSHClient, 'connect', MagicMock(return_value={}))
    def test_username_only_ssh(self):
        paramiko_runner = ParamikoRemoteScriptRunner('runner_1')

        paramiko_runner.runner_parameters = {'username': 'test_user', 'hosts': '127.0.0.1'}
        self.assertRaises(InvalidCredentialsException, paramiko_runner.pre_run)

    def test_username_invalid_private_key(self):
        paramiko_runner = ParamikoRemoteScriptRunner('runner_1')

        paramiko_runner.runner_parameters = {
            'username': 'test_user',
            'hosts': '127.0.0.1',
            'private_key': 'invalid private key',
        }
        paramiko_runner.context = {}
        self.assertRaises(NoHostsConnectedToException, paramiko_runner.pre_run)

    @patch('st2actions.runners.ssh.parallel_ssh.ParallelSSHClient', Mock)
    @patch.object(ParallelSSHClient, 'run', MagicMock(return_value={}))
    @patch.object(ParallelSSHClient, 'connect', MagicMock(return_value={}))
    def test_top_level_error_is_correctly_reported(self):
        # Verify that a top-level error doesn't cause an exception to be thrown.
        # In a top-level error case, result dict doesn't contain entry per host
        paramiko_runner = ParamikoRemoteScriptRunner('runner_1')

        paramiko_runner.runner_parameters = {
            'username': 'test_user',
            'hosts': '127.0.0.1'
        }
        paramiko_runner.action = ACTION_1
        paramiko_runner.liveaction_id = 'foo'
        paramiko_runner.entry_point = 'foo'
        paramiko_runner.context = {}
        paramiko_runner._cwd = '/tmp'
        paramiko_runner._copy_artifacts = Mock(side_effect=Exception('fail!'))
        status, result, _ = paramiko_runner.run(action_parameters={})

        self.assertEqual(status, LIVEACTION_STATUS_FAILED)
        self.assertEqual(result['failed'], True)
        self.assertEqual(result['succeeded'], False)
        self.assertTrue('Failed copying content to remote boxes' in result['error'])

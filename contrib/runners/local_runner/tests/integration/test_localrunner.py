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

import mock

import st2tests.config as tests_config
tests_config.parse_args()

from unittest2 import TestCase
from st2actions.container.service import RunnerContainerService
from st2common.constants import action as action_constants
from st2tests.fixturesloader import FixturesLoader
from st2tests.fixturesloader import get_fixtures_base_path
from st2common.util.api import get_full_public_api_url
from st2common.util.green import shell
from st2common.constants.runners import LOCAL_RUNNER_DEFAULT_ACTION_TIMEOUT
import local_runner


class LocalShellCommandRunnerTestCase(TestCase):
    fixtures_loader = FixturesLoader()

    def test_shell_command_action_basic(self):
        models = self.fixtures_loader.load_models(
            fixtures_pack='generic', fixtures_dict={'actions': ['local.yaml']})
        action_db = models['actions']['local.yaml']
        runner = self._get_runner(action_db, cmd='echo 10')
        runner.pre_run()
        status, result, _ = runner.run({})
        runner.post_run(status, result)
        self.assertEquals(status, action_constants.LIVEACTION_STATUS_SUCCEEDED)
        self.assertEquals(result['stdout'], 10)

    def test_shell_script_action(self):
        models = self.fixtures_loader.load_models(
            fixtures_pack='localrunner_pack', fixtures_dict={'actions': ['text_gen.yml']})
        action_db = models['actions']['text_gen.yml']
        entry_point = self.fixtures_loader.get_fixture_file_path_abs(
            'localrunner_pack', 'actions', 'text_gen.py')
        runner = self._get_runner(action_db, entry_point=entry_point)
        runner.pre_run()
        status, result, _ = runner.run({'chars': 1000})
        runner.post_run(status, result)
        self.assertEquals(status, action_constants.LIVEACTION_STATUS_SUCCEEDED)
        self.assertEquals(len(result['stdout']), 1000)

    def test_timeout(self):
        models = self.fixtures_loader.load_models(
            fixtures_pack='generic', fixtures_dict={'actions': ['local.yaml']})
        action_db = models['actions']['local.yaml']
        # smaller timeout == faster tests.
        runner = self._get_runner(action_db, cmd='sleep 10', timeout=0.01)
        runner.pre_run()
        status, result, _ = runner.run({})
        runner.post_run(status, result)
        self.assertEquals(status, action_constants.LIVEACTION_STATUS_TIMED_OUT)

    @mock.patch.object(
        shell, 'run_command',
        mock.MagicMock(return_value=(-15, '', '', False)))
    def test_shutdown(self):
        models = self.fixtures_loader.load_models(
            fixtures_pack='generic', fixtures_dict={'actions': ['local.yaml']})
        action_db = models['actions']['local.yaml']
        runner = self._get_runner(action_db, cmd='sleep 0.1')
        runner.pre_run()
        status, result, _ = runner.run({})
        self.assertEquals(status, action_constants.LIVEACTION_STATUS_ABANDONED)

    def test_large_stdout(self):
        models = self.fixtures_loader.load_models(
            fixtures_pack='localrunner_pack', fixtures_dict={'actions': ['text_gen.yml']})
        action_db = models['actions']['text_gen.yml']
        entry_point = self.fixtures_loader.get_fixture_file_path_abs(
            'localrunner_pack', 'actions', 'text_gen.py')
        runner = self._get_runner(action_db, entry_point=entry_point)
        runner.pre_run()
        char_count = 10 ** 6  # Note 10^7 succeeds but ends up being slow.
        status, result, _ = runner.run({'chars': char_count})
        runner.post_run(status, result)
        self.assertEquals(status, action_constants.LIVEACTION_STATUS_SUCCEEDED)
        self.assertEquals(len(result['stdout']), char_count)

    def test_common_st2_env_vars_are_available_to_the_action(self):
        models = self.fixtures_loader.load_models(
            fixtures_pack='generic', fixtures_dict={'actions': ['local.yaml']})
        action_db = models['actions']['local.yaml']

        runner = self._get_runner(action_db, cmd='echo $ST2_ACTION_API_URL')
        runner.pre_run()
        status, result, _ = runner.run({})
        runner.post_run(status, result)

        self.assertEquals(status, action_constants.LIVEACTION_STATUS_SUCCEEDED)
        self.assertEqual(result['stdout'].strip(), get_full_public_api_url())

        runner = self._get_runner(action_db, cmd='echo $ST2_ACTION_AUTH_TOKEN')
        runner.pre_run()
        status, result, _ = runner.run({})
        runner.post_run(status, result)

        self.assertEquals(status, action_constants.LIVEACTION_STATUS_SUCCEEDED)
        self.assertEqual(result['stdout'].strip(), 'mock-token')

    def test_sudo_and_env_variable_preservation(self):
        # Verify that the environment environment are correctly preserved when running as a
        # root / non-system user
        # Note: This test will fail if SETENV option is not present in the sudoers file
        models = self.fixtures_loader.load_models(
            fixtures_pack='generic', fixtures_dict={'actions': ['local.yaml']})
        action_db = models['actions']['local.yaml']

        cmd = 'echo `whoami` ; echo ${VAR1}'
        env = {'VAR1': 'poniesponies'}
        runner = self._get_runner(action_db, cmd=cmd, sudo=True, env=env)
        runner.pre_run()
        status, result, _ = runner.run({})
        runner.post_run(status, result)

        self.assertEquals(status, action_constants.LIVEACTION_STATUS_SUCCEEDED)
        self.assertEqual(result['stdout'].strip(), 'root\nponiesponies')

    @staticmethod
    def _get_runner(action_db,
                    entry_point=None,
                    cmd=None,
                    on_behalf_user=None,
                    user=None,
                    kwarg_op=local_runner.DEFAULT_KWARG_OP,
                    timeout=LOCAL_RUNNER_DEFAULT_ACTION_TIMEOUT,
                    sudo=False,
                    env=None):
        runner = local_runner.LocalShellRunner(uuid.uuid4().hex)
        runner.container_service = RunnerContainerService()
        runner.action = action_db
        runner.action_name = action_db.name
        runner.liveaction_id = uuid.uuid4().hex
        runner.entry_point = entry_point
        runner.runner_parameters = {local_runner.RUNNER_COMMAND: cmd,
                                    local_runner.RUNNER_SUDO: sudo,
                                    local_runner.RUNNER_ENV: env,
                                    local_runner.RUNNER_ON_BEHALF_USER: user,
                                    local_runner.RUNNER_KWARG_OP: kwarg_op,
                                    local_runner.RUNNER_TIMEOUT: timeout}
        runner.context = dict()
        runner.callback = dict()
        runner.libs_dir_path = None
        runner.auth_token = mock.Mock()
        runner.auth_token.token = 'mock-token'
        return runner


class LocalShellScriptRunner(TestCase):
    fixtures_loader = FixturesLoader()

    def test_script_with_paramters_parameter_serialization(self):
        models = self.fixtures_loader.load_models(
            fixtures_pack='generic', fixtures_dict={'actions': ['local_script_with_params.yaml']})
        action_db = models['actions']['local_script_with_params.yaml']
        entry_point = os.path.join(get_fixtures_base_path(),
                                   'generic/actions/local_script_with_params.sh')

        action_parameters = {
            'param_string': 'test string',
            'param_integer': 1,
            'param_float': 2.55,
            'param_boolean': True,
            'param_list': ['a', 'b', 'c'],
            'param_object': {'foo': 'bar'}
        }

        runner = self._get_runner(action_db=action_db, entry_point=entry_point)
        runner.pre_run()
        status, result, _ = runner.run(action_parameters=action_parameters)
        runner.post_run(status, result)

        self.assertEqual(status, action_constants.LIVEACTION_STATUS_SUCCEEDED)
        self.assertTrue('PARAM_STRING=test string' in result['stdout'])
        self.assertTrue('PARAM_INTEGER=1' in result['stdout'])
        self.assertTrue('PARAM_FLOAT=2.55' in result['stdout'])
        self.assertTrue('PARAM_BOOLEAN=1' in result['stdout'])
        self.assertTrue('PARAM_LIST=a,b,c' in result['stdout'])
        self.assertTrue('PARAM_OBJECT={"foo": "bar"}' in result['stdout'])

        action_parameters = {
            'param_string': 'test string',
            'param_integer': 1,
            'param_float': 2.55,
            'param_boolean': False,
            'param_list': ['a', 'b', 'c'],
            'param_object': {'foo': 'bar'}
        }

        runner = self._get_runner(action_db=action_db, entry_point=entry_point)
        runner.pre_run()
        status, result, _ = runner.run(action_parameters=action_parameters)
        runner.post_run(status, result)

        self.assertEqual(status, action_constants.LIVEACTION_STATUS_SUCCEEDED)
        self.assertTrue('PARAM_BOOLEAN=0' in result['stdout'])

        action_parameters = {
            'param_string': '',
            'param_integer': None,
            'param_float': None,
        }

        runner = self._get_runner(action_db=action_db, entry_point=entry_point)
        runner.pre_run()
        status, result, _ = runner.run(action_parameters=action_parameters)
        runner.post_run(status, result)

        self.assertEqual(status, action_constants.LIVEACTION_STATUS_SUCCEEDED)
        self.assertTrue('PARAM_STRING=\n' in result['stdout'])
        self.assertTrue('PARAM_INTEGER=\n' in result['stdout'])
        self.assertTrue('PARAM_FLOAT=\n' in result['stdout'])

    def _get_runner(self, action_db, entry_point):
        runner = local_runner.LocalShellRunner(uuid.uuid4().hex)
        runner.container_service = RunnerContainerService()
        runner.action = action_db
        runner.action_name = action_db.name
        runner.liveaction_id = uuid.uuid4().hex
        runner.entry_point = entry_point
        runner.runner_parameters = {}
        runner.context = dict()
        runner.callback = dict()
        runner.libs_dir_path = None
        runner.auth_token = mock.Mock()
        runner.auth_token.token = 'mock-token'
        return runner

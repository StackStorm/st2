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
from oslo_config import cfg

import st2tests.config as tests_config
tests_config.parse_args()

from st2actions.container.service import RunnerContainerService
from st2common.constants import action as action_constants
from st2common.persistence.execution import ActionExecutionStdoutOutput
from st2common.persistence.execution import ActionExecutionStderrOutput
from st2tests.fixturesloader import FixturesLoader
from st2tests.fixturesloader import get_fixtures_base_path
from st2common.util.api import get_full_public_api_url
from st2common.util.green import shell
from st2common.constants.runners import LOCAL_RUNNER_DEFAULT_ACTION_TIMEOUT
from st2tests.base import RunnerTestCase
from st2tests.base import CleanDbTestCase
from st2tests.base import blocking_eventlet_spawn
from st2tests.base import make_mock_stream_readline
import local_runner

__all__ = [
    'LocalShellCommandRunnerTestCase',
    'LocalShellScriptRunnerTestCase'
]

MOCK_EXECUTION = mock.Mock()
MOCK_EXECUTION.id = '598dbf0c0640fd54bffc688b'


class LocalShellCommandRunnerTestCase(RunnerTestCase, CleanDbTestCase):
    fixtures_loader = FixturesLoader()

    def setUp(self):
        super(LocalShellCommandRunnerTestCase, self).setUp()

        # False is a default behavior so end result should be the same
        cfg.CONF.set_override(name='stream_output', group='actionrunner', override=False)

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

        # End result should be the same when streaming is enabled
        cfg.CONF.set_override(name='stream_output', group='actionrunner', override=True)

        # Verify initial state
        stdout_dbs = ActionExecutionStdoutOutput.get_all()
        self.assertEqual(len(stdout_dbs), 0)

        stderr_dbs = ActionExecutionStderrOutput.get_all()
        self.assertEqual(len(stderr_dbs), 0)

        runner = self._get_runner(action_db, cmd='echo 10')
        runner.pre_run()
        status, result, _ = runner.run({})
        runner.post_run(status, result)

        self.assertEquals(status, action_constants.LIVEACTION_STATUS_SUCCEEDED)
        self.assertEquals(result['stdout'], 10)

        stdout_dbs = ActionExecutionStdoutOutput.get_all()
        self.assertEqual(len(stdout_dbs), 1)
        self.assertEqual(stdout_dbs[0].line, '10\n')

        stderr_dbs = ActionExecutionStderrOutput.get_all()
        self.assertEqual(len(stderr_dbs), 0)

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

    @mock.patch('st2common.util.green.shell.subprocess.Popen')
    @mock.patch('st2common.util.green.shell.eventlet.spawn')
    def test_action_stdout_and_stderr_is_stored_in_the_db(self, mock_spawn, mock_popen):
        # Feature is enabled
        cfg.CONF.set_override(name='stream_output', group='actionrunner', override=True)

        # Note: We need to mock spawn function so we can test everything in single event loop
        # iteration
        mock_spawn.side_effect = blocking_eventlet_spawn

        # No output to stdout and no result (implicit None)
        mock_stdout = [
            'stdout line 1\n',
            'stdout line 2\n',
        ]
        mock_stderr = [
            'stderr line 1\n',
            'stderr line 2\n',
            'stderr line 3\n'
        ]

        mock_process = mock.Mock()
        mock_process.returncode = 0
        mock_popen.return_value = mock_process
        mock_process.stdout.closed = False
        mock_process.stderr.closed = False
        mock_process.stdout.readline = make_mock_stream_readline(mock_process.stdout, mock_stdout,
                                                                 stop_counter=2)
        mock_process.stderr.readline = make_mock_stream_readline(mock_process.stderr, mock_stderr,
                                                                 stop_counter=3)

        models = self.fixtures_loader.load_models(
            fixtures_pack='generic', fixtures_dict={'actions': ['local.yaml']})
        action_db = models['actions']['local.yaml']

        runner = self._get_runner(action_db, cmd='echo $ST2_ACTION_API_URL')
        runner.pre_run()
        status, result, _ = runner.run({})
        runner.post_run(status, result)

        self.assertEquals(status, action_constants.LIVEACTION_STATUS_SUCCEEDED)

        self.assertEqual(result['stdout'], 'stdout line 1\nstdout line 2')
        self.assertEqual(result['stderr'], 'stderr line 1\nstderr line 2\nstderr line 3')
        self.assertEqual(result['return_code'], 0)

        # Verify stdout and stderr lines have been correctly stored in the db
        stdout_dbs = ActionExecutionStdoutOutput.get_all()
        self.assertEqual(len(stdout_dbs), 2)
        self.assertEqual(stdout_dbs[0].line, mock_stdout[0])
        self.assertEqual(stdout_dbs[1].line, mock_stdout[1])

        stderr_dbs = ActionExecutionStderrOutput.get_all()
        self.assertEqual(len(stderr_dbs), 3)
        self.assertEqual(stderr_dbs[0].line, mock_stderr[0])
        self.assertEqual(stderr_dbs[1].line, mock_stderr[1])
        self.assertEqual(stderr_dbs[2].line, mock_stderr[2])

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
        runner.execution = MOCK_EXECUTION
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


class LocalShellScriptRunnerTestCase(RunnerTestCase, CleanDbTestCase):
    fixtures_loader = FixturesLoader()

    def setUp(self):
        super(LocalShellScriptRunnerTestCase, self).setUp()

        # False is a default behavior so end result should be the same
        cfg.CONF.set_override(name='stream_output', group='actionrunner', override=False)

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

        # End result should be the same when streaming is enabled
        cfg.CONF.set_override(name='stream_output', group='actionrunner', override=True)

        # Verify initial state
        stdout_dbs = ActionExecutionStdoutOutput.get_all()
        self.assertEqual(len(stdout_dbs), 0)

        stderr_dbs = ActionExecutionStderrOutput.get_all()
        self.assertEqual(len(stderr_dbs), 0)

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
        print result

        self.assertEqual(status, action_constants.LIVEACTION_STATUS_SUCCEEDED)
        self.assertTrue('PARAM_STRING=test string' in result['stdout'])
        self.assertTrue('PARAM_INTEGER=1' in result['stdout'])
        self.assertTrue('PARAM_FLOAT=2.55' in result['stdout'])
        self.assertTrue('PARAM_BOOLEAN=1' in result['stdout'])
        self.assertTrue('PARAM_LIST=a,b,c' in result['stdout'])
        self.assertTrue('PARAM_OBJECT={"foo": "bar"}' in result['stdout'])

        stdout_dbs = ActionExecutionStdoutOutput.get_all()
        self.assertEqual(len(stdout_dbs), 6)
        self.assertEqual(stdout_dbs[0].line, 'PARAM_STRING=test string\n')
        self.assertEqual(stdout_dbs[5].line, 'PARAM_OBJECT={"foo": "bar"}\n')

        stderr_dbs = ActionExecutionStderrOutput.get_all()
        self.assertEqual(len(stderr_dbs), 0)

    @mock.patch('st2common.util.green.shell.subprocess.Popen')
    @mock.patch('st2common.util.green.shell.eventlet.spawn')
    def test_action_stdout_and_stderr_is_stored_in_the_db(self, mock_spawn, mock_popen):
        # Feature is enabled
        cfg.CONF.set_override(name='stream_output', group='actionrunner', override=True)

        # Note: We need to mock spawn function so we can test everything in single event loop
        # iteration
        mock_spawn.side_effect = blocking_eventlet_spawn

        # No output to stdout and no result (implicit None)
        mock_stdout = [
            'stdout line 1\n',
            'stdout line 2\n',
            'stdout line 3\n',
            'stdout line 4\n'
        ]
        mock_stderr = [
            'stderr line 1\n',
            'stderr line 2\n',
            'stderr line 3\n'
        ]

        mock_process = mock.Mock()
        mock_process.returncode = 0
        mock_popen.return_value = mock_process
        mock_process.stdout.closed = False
        mock_process.stderr.closed = False
        mock_process.stdout.readline = make_mock_stream_readline(mock_process.stdout, mock_stdout,
                                                                 stop_counter=4)
        mock_process.stderr.readline = make_mock_stream_readline(mock_process.stderr, mock_stderr,
                                                                 stop_counter=3)

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

        self.assertEqual(result['stdout'],
                         'stdout line 1\nstdout line 2\nstdout line 3\nstdout line 4')
        self.assertEqual(result['stderr'], 'stderr line 1\nstderr line 2\nstderr line 3')
        self.assertEqual(result['return_code'], 0)

        # Verify stdout and stderr lines have been correctly stored in the db
        stdout_dbs = ActionExecutionStdoutOutput.get_all()
        self.assertEqual(len(stdout_dbs), 4)
        self.assertEqual(stdout_dbs[0].line, mock_stdout[0])
        self.assertEqual(stdout_dbs[1].line, mock_stdout[1])
        self.assertEqual(stdout_dbs[2].line, mock_stdout[2])
        self.assertEqual(stdout_dbs[3].line, mock_stdout[3])

        stderr_dbs = ActionExecutionStderrOutput.get_all()
        self.assertEqual(len(stderr_dbs), 3)
        self.assertEqual(stderr_dbs[0].line, mock_stderr[0])
        self.assertEqual(stderr_dbs[1].line, mock_stderr[1])
        self.assertEqual(stderr_dbs[2].line, mock_stderr[2])

    def _get_runner(self, action_db, entry_point):
        runner = local_runner.LocalShellRunner(uuid.uuid4().hex)
        runner.container_service = RunnerContainerService()
        runner.execution = MOCK_EXECUTION
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

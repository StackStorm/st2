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
import uuid

import mock
from oslo_config import cfg

import st2tests.config as tests_config
from six.moves import range

tests_config.parse_args()

from st2common.constants import action as action_constants
from st2common.persistence.execution import ActionExecutionOutput
from st2tests.fixturesloader import FixturesLoader
from st2tests.fixturesloader import get_fixtures_base_path
from st2common.util.api import get_full_public_api_url
from st2common.util.green import shell
from st2common.constants.runners import LOCAL_RUNNER_DEFAULT_ACTION_TIMEOUT
from st2tests.base import RunnerTestCase
from st2tests.base import CleanDbTestCase
from st2tests.base import blocking_eventlet_spawn
from st2tests.base import make_mock_stream_readline
from st2tests.fixtures.generic.fixture import PACK_NAME as GENERIC_PACK
from st2tests.fixtures.localrunner_pack.fixture import PACK_NAME as LOCALRUNNER_PACK

from local_runner import base as local_runner
from local_runner.local_shell_command_runner import LocalShellCommandRunner
from local_runner.local_shell_script_runner import LocalShellScriptRunner

__all__ = ["LocalShellCommandRunnerTestCase", "LocalShellScriptRunnerTestCase"]

ST2_CI = os.environ.get("ST2_CI", "false").lower() == "true"

MOCK_EXECUTION = mock.Mock()
MOCK_EXECUTION.id = "598dbf0c0640fd54bffc688b"


class LocalShellCommandRunnerTestCase(RunnerTestCase, CleanDbTestCase):
    fixtures_loader = FixturesLoader()

    def setUp(self):
        super(LocalShellCommandRunnerTestCase, self).setUp()

        # False is a default behavior so end result should be the same
        cfg.CONF.set_override(
            name="stream_output", group="actionrunner", override=False
        )

    def test_shell_command_action_basic(self):
        models = self.fixtures_loader.load_models(
            fixtures_pack=GENERIC_PACK, fixtures_dict={"actions": ["local.yaml"]}
        )
        action_db = models["actions"]["local.yaml"]

        runner = self._get_runner(action_db, cmd="echo 10")
        runner.pre_run()
        status, result, _ = runner.run({})
        runner.post_run(status, result)

        self.assertEqual(status, action_constants.LIVEACTION_STATUS_SUCCEEDED)
        self.assertEqual(result["stdout"], 10)

        # End result should be the same when streaming is enabled
        cfg.CONF.set_override(name="stream_output", group="actionrunner", override=True)

        # Verify initial state
        output_dbs = ActionExecutionOutput.get_all()
        self.assertEqual(len(output_dbs), 0)

        runner = self._get_runner(action_db, cmd="echo 10")
        runner.pre_run()
        status, result, _ = runner.run({})
        runner.post_run(status, result)

        self.assertEqual(status, action_constants.LIVEACTION_STATUS_SUCCEEDED)
        self.assertEqual(result["stdout"], 10)

        output_dbs = ActionExecutionOutput.get_all()
        self.assertEqual(len(output_dbs), 1)
        self.assertEqual(output_dbs[0].output_type, "stdout")
        self.assertEqual(output_dbs[0].data, "10\n")

    # This test depends on passwordless sudo. Don't require that for local development.
    @unittest.skipIf(
        not ST2_CI,
        'Skipping tests because ST2_CI environment variable is not set to "true"',
    )
    def test_timeout(self):
        models = self.fixtures_loader.load_models(
            fixtures_pack=GENERIC_PACK, fixtures_dict={"actions": ["local.yaml"]}
        )
        action_db = models["actions"]["local.yaml"]
        # smaller timeout == faster tests.
        runner = self._get_runner(action_db, cmd="sleep 10", timeout=0.01)
        runner.pre_run()
        status, result, _ = runner.run({})
        runner.post_run(status, result)
        self.assertEqual(status, action_constants.LIVEACTION_STATUS_TIMED_OUT)

    @mock.patch.object(
        shell, "run_command", mock.MagicMock(return_value=(-15, "", "", False))
    )
    def test_shutdown(self):
        models = self.fixtures_loader.load_models(
            fixtures_pack=GENERIC_PACK, fixtures_dict={"actions": ["local.yaml"]}
        )
        action_db = models["actions"]["local.yaml"]
        runner = self._get_runner(action_db, cmd="sleep 0.1")
        runner.pre_run()
        status, result, _ = runner.run({})
        self.assertEqual(status, action_constants.LIVEACTION_STATUS_ABANDONED)

    def test_common_st2_env_vars_are_available_to_the_action(self):
        models = self.fixtures_loader.load_models(
            fixtures_pack=GENERIC_PACK, fixtures_dict={"actions": ["local.yaml"]}
        )
        action_db = models["actions"]["local.yaml"]

        runner = self._get_runner(action_db, cmd="echo $ST2_ACTION_API_URL")
        runner.pre_run()
        status, result, _ = runner.run({})
        runner.post_run(status, result)

        self.assertEqual(status, action_constants.LIVEACTION_STATUS_SUCCEEDED)
        self.assertEqual(result["stdout"].strip(), get_full_public_api_url())

        runner = self._get_runner(action_db, cmd="echo $ST2_ACTION_AUTH_TOKEN")
        runner.pre_run()
        status, result, _ = runner.run({})
        runner.post_run(status, result)

        self.assertEqual(status, action_constants.LIVEACTION_STATUS_SUCCEEDED)
        self.assertEqual(result["stdout"].strip(), "mock-token")

    # This test depends on passwordless sudo. Don't require that for local development.
    @unittest.skipIf(
        not ST2_CI,
        'Skipping tests because ST2_CI environment variable is not set to "true"',
    )
    def test_sudo_and_env_variable_preservation(self):
        # Verify that the environment vars are correctly preserved when running as a
        # root / non-system user
        # Note: This test will fail if SETENV option is not present in the sudoers file
        models = self.fixtures_loader.load_models(
            fixtures_pack=GENERIC_PACK, fixtures_dict={"actions": ["local.yaml"]}
        )
        action_db = models["actions"]["local.yaml"]

        cmd = "echo `whoami` ; echo ${VAR1}"
        env = {"VAR1": "poniesponies"}
        runner = self._get_runner(action_db, cmd=cmd, sudo=True, env=env)
        runner.pre_run()
        status, result, _ = runner.run({})
        runner.post_run(status, result)

        self.assertEqual(status, action_constants.LIVEACTION_STATUS_SUCCEEDED)
        self.assertEqual(result["stdout"].strip(), "root\nponiesponies")

    @mock.patch("st2common.util.concurrency.subprocess_popen")
    @mock.patch("st2common.util.concurrency.spawn")
    def test_action_stdout_and_stderr_is_stored_in_the_db(self, mock_spawn, mock_popen):
        # Feature is enabled
        cfg.CONF.set_override(name="stream_output", group="actionrunner", override=True)

        # Note: We need to mock spawn function so we can test everything in single event loop
        # iteration
        mock_spawn.side_effect = blocking_eventlet_spawn

        # No output to stdout and no result (implicit None)
        mock_stdout = [
            "stdout line 1\n",
            "stdout line 2\n",
        ]
        mock_stderr = ["stderr line 1\n", "stderr line 2\n", "stderr line 3\n"]

        mock_process = mock.Mock()
        mock_process.returncode = 0
        mock_popen.return_value = mock_process
        mock_process.stdout.closed = False
        mock_process.stderr.closed = False
        mock_process.stdout.readline = make_mock_stream_readline(
            mock_process.stdout, mock_stdout, stop_counter=2
        )
        mock_process.stderr.readline = make_mock_stream_readline(
            mock_process.stderr, mock_stderr, stop_counter=3
        )

        models = self.fixtures_loader.load_models(
            fixtures_pack=GENERIC_PACK, fixtures_dict={"actions": ["local.yaml"]}
        )
        action_db = models["actions"]["local.yaml"]

        runner = self._get_runner(action_db, cmd="echo $ST2_ACTION_API_URL")
        runner.pre_run()
        status, result, _ = runner.run({})
        runner.post_run(status, result)

        self.assertEqual(status, action_constants.LIVEACTION_STATUS_SUCCEEDED)

        self.assertEqual(result["stdout"], "stdout line 1\nstdout line 2")
        self.assertEqual(
            result["stderr"], "stderr line 1\nstderr line 2\nstderr line 3"
        )
        self.assertEqual(result["return_code"], 0)

        # Verify stdout and stderr lines have been correctly stored in the db
        output_dbs = ActionExecutionOutput.query(output_type="stdout")
        self.assertEqual(len(output_dbs), 2)
        self.assertEqual(output_dbs[0].data, mock_stdout[0])
        self.assertEqual(output_dbs[1].data, mock_stdout[1])

        output_dbs = ActionExecutionOutput.query(output_type="stderr")
        self.assertEqual(len(output_dbs), 3)
        self.assertEqual(output_dbs[0].data, mock_stderr[0])
        self.assertEqual(output_dbs[1].data, mock_stderr[1])
        self.assertEqual(output_dbs[2].data, mock_stderr[2])

    @mock.patch("st2common.util.concurrency.subprocess_popen")
    @mock.patch("st2common.util.concurrency.spawn")
    def test_action_stdout_and_stderr_is_stored_in_the_db_short_running_action(
        self, mock_spawn, mock_popen
    ):
        # Verify that we correctly retrieve all the output and wait for stdout and stderr reading
        # threads for short running actions.
        models = self.fixtures_loader.load_models(
            fixtures_pack=GENERIC_PACK, fixtures_dict={"actions": ["local.yaml"]}
        )
        action_db = models["actions"]["local.yaml"]

        # Feature is enabled
        cfg.CONF.set_override(name="stream_output", group="actionrunner", override=True)

        # Note: We need to mock spawn function so we can test everything in single event loop
        # iteration
        mock_spawn.side_effect = blocking_eventlet_spawn

        # No output to stdout and no result (implicit None)
        mock_stdout = ["stdout line 1\n", "stdout line 2\n"]
        mock_stderr = ["stderr line 1\n", "stderr line 2\n"]

        # We add a sleep to simulate action process exiting before we finish reading data from
        mock_process = mock.Mock()
        mock_process.returncode = 0
        mock_popen.return_value = mock_process
        mock_process.stdout.closed = False
        mock_process.stderr.closed = False
        mock_process.stdout.readline = make_mock_stream_readline(
            mock_process.stdout, mock_stdout, stop_counter=2, sleep_delay=1
        )
        mock_process.stderr.readline = make_mock_stream_readline(
            mock_process.stderr, mock_stderr, stop_counter=2
        )

        for index in range(1, 4):
            mock_process.stdout.closed = False
            mock_process.stderr.closed = False

            mock_process.stdout.counter = 0
            mock_process.stderr.counter = 0

            runner = self._get_runner(action_db, cmd='echo "foobar"')
            runner.pre_run()
            status, result, _ = runner.run({})

            self.assertEqual(status, action_constants.LIVEACTION_STATUS_SUCCEEDED)

            self.assertEqual(result["stdout"], "stdout line 1\nstdout line 2")
            self.assertEqual(result["stderr"], "stderr line 1\nstderr line 2")
            self.assertEqual(result["return_code"], 0)

            # Verify stdout and stderr lines have been correctly stored in the db
            output_dbs = ActionExecutionOutput.query(output_type="stdout")

            if index == 1:
                db_index_1 = 0
                db_index_2 = 1
            elif index == 2:
                db_index_1 = 2
                db_index_2 = 3
            elif index == 3:
                db_index_1 = 4
                db_index_2 = 5
            elif index == 4:
                db_index_1 = 6
                db_index_2 = 7

            self.assertEqual(len(output_dbs), (index * 2))
            self.assertEqual(output_dbs[db_index_1].data, mock_stdout[0])
            self.assertEqual(output_dbs[db_index_2].data, mock_stdout[1])

            output_dbs = ActionExecutionOutput.query(output_type="stderr")
            self.assertEqual(len(output_dbs), (index * 2))
            self.assertEqual(output_dbs[db_index_1].data, mock_stderr[0])
            self.assertEqual(output_dbs[db_index_2].data, mock_stderr[1])

    # This test depends on passwordless sudo. Don't require that for local development.
    @unittest.skipIf(
        not ST2_CI,
        'Skipping tests because ST2_CI environment variable is not set to "true"',
    )
    def test_shell_command_sudo_password_is_passed_to_sudo_binary(self):
        # Verify that sudo password is correctly passed to sudo binary via stdin
        models = self.fixtures_loader.load_models(
            fixtures_pack=GENERIC_PACK, fixtures_dict={"actions": ["local.yaml"]}
        )
        action_db = models["actions"]["local.yaml"]

        sudo_passwords = ["pass 1", "sudopass", "$sudo p@ss 2"]

        cmd = "{ read sudopass; echo $sudopass; }"

        # without sudo
        for sudo_password in sudo_passwords:
            runner = self._get_runner(action_db, cmd=cmd)
            runner.pre_run()
            runner._sudo_password = sudo_password
            status, result, _ = runner.run({})
            runner.post_run(status, result)

            self.assertEqual(status, action_constants.LIVEACTION_STATUS_SUCCEEDED)
            self.assertEqual(result["stdout"], sudo_password)

        # with sudo
        for sudo_password in sudo_passwords:
            runner = self._get_runner(action_db, cmd=cmd)
            runner.pre_run()
            runner._sudo = True
            runner._sudo_password = sudo_password
            status, result, _ = runner.run({})
            runner.post_run(status, result)

            self.assertEqual(status, action_constants.LIVEACTION_STATUS_SUCCEEDED)
            self.assertEqual(result["stdout"], sudo_password)

        # Verify new process which provides password via stdin to the command is created
        with mock.patch(
            "st2common.util.concurrency.subprocess_popen"
        ) as mock_subproc_popen:
            index = 0
            for sudo_password in sudo_passwords:
                runner = self._get_runner(action_db, cmd=cmd)
                runner.pre_run()
                runner._sudo = True
                runner._sudo_password = sudo_password
                status, result, _ = runner.run({})
                runner.post_run(status, result)

                if index == 0:
                    call_args = mock_subproc_popen.call_args_list[index]
                else:
                    call_args = mock_subproc_popen.call_args_list[index * 2]

                index += 1

                self.assertEqual(call_args[0][0], ["echo", "%s\n" % (sudo_password)])

        self.assertEqual(index, len(sudo_passwords))

    def test_shell_command_invalid_stdout_password(self):
        # Simulate message printed to stderr by sudo when invalid sudo password is provided
        models = self.fixtures_loader.load_models(
            fixtures_pack=GENERIC_PACK, fixtures_dict={"actions": ["local.yaml"]}
        )
        action_db = models["actions"]["local.yaml"]

        cmd = (
            'echo  "[sudo] password for bar: Sorry, try again.\n[sudo] password for bar:'
            " Sorry, try again.\n[sudo] password for bar: \nsudo: 2 incorrect password "
            'attempts" 1>&2; exit 1'
        )
        runner = self._get_runner(action_db, cmd=cmd)
        runner.pre_run()
        runner._sudo_password = "pass"
        status, result, _ = runner.run({})
        runner.post_run(status, result)

        expected_error = (
            "Invalid sudo password provided or sudo is not configured for this "
            "user (bar)"
        )
        self.assertEqual(status, action_constants.LIVEACTION_STATUS_FAILED)
        self.assertEqual(result["error"], expected_error)
        self.assertEqual(result["stdout"], "")

    @staticmethod
    def _get_runner(
        action_db,
        entry_point=None,
        cmd=None,
        on_behalf_user=None,
        user=None,
        kwarg_op=local_runner.DEFAULT_KWARG_OP,
        timeout=LOCAL_RUNNER_DEFAULT_ACTION_TIMEOUT,
        sudo=False,
        env=None,
    ):
        runner = LocalShellCommandRunner(uuid.uuid4().hex)
        runner.execution = MOCK_EXECUTION
        runner.action = action_db
        runner.action_name = action_db.name
        runner.liveaction_id = uuid.uuid4().hex
        runner.entry_point = entry_point
        runner.runner_parameters = {
            local_runner.RUNNER_COMMAND: cmd,
            local_runner.RUNNER_SUDO: sudo,
            local_runner.RUNNER_ENV: env,
            local_runner.RUNNER_ON_BEHALF_USER: user,
            local_runner.RUNNER_KWARG_OP: kwarg_op,
            local_runner.RUNNER_TIMEOUT: timeout,
        }
        runner.context = dict()
        runner.callback = dict()
        runner.libs_dir_path = None
        runner.auth_token = mock.Mock()
        runner.auth_token.token = "mock-token"
        return runner


class LocalShellScriptRunnerTestCase(RunnerTestCase, CleanDbTestCase):
    fixtures_loader = FixturesLoader()

    def setUp(self):
        super(LocalShellScriptRunnerTestCase, self).setUp()

        # False is a default behavior so end result should be the same
        cfg.CONF.set_override(
            name="stream_output", group="actionrunner", override=False
        )

    def test_script_with_parameters_parameter_serialization(self):
        models = self.fixtures_loader.load_models(
            fixtures_pack=GENERIC_PACK,
            fixtures_dict={"actions": ["local_script_with_params.yaml"]},
        )
        action_db = models["actions"]["local_script_with_params.yaml"]
        entry_point = os.path.join(
            get_fixtures_base_path(), "generic/actions/local_script_with_params.sh"
        )

        action_parameters = {
            "param_string": "test string",
            "param_integer": 1,
            "param_float": 2.55,
            "param_boolean": True,
            "param_list": ["a", "b", "c"],
            "param_object": {"foo": "bar"},
        }

        runner = self._get_runner(action_db=action_db, entry_point=entry_point)
        runner.pre_run()
        status, result, _ = runner.run(action_parameters=action_parameters)
        runner.post_run(status, result)
        self.assertEqual(status, action_constants.LIVEACTION_STATUS_SUCCEEDED)
        self.assertIn("PARAM_STRING=test string", result["stdout"])
        self.assertIn("PARAM_INTEGER=1", result["stdout"])
        self.assertIn("PARAM_FLOAT=2.55", result["stdout"])
        self.assertIn("PARAM_BOOLEAN=1", result["stdout"])
        self.assertIn("PARAM_LIST=a,b,c", result["stdout"])
        self.assertIn('PARAM_OBJECT={"foo":"bar"}', result["stdout"])

        action_parameters = {
            "param_string": "test string",
            "param_integer": 1,
            "param_float": 2.55,
            "param_boolean": False,
            "param_list": ["a", "b", "c"],
            "param_object": {"foo": "bar"},
        }

        runner = self._get_runner(action_db=action_db, entry_point=entry_point)
        runner.pre_run()
        status, result, _ = runner.run(action_parameters=action_parameters)
        runner.post_run(status, result)

        self.assertEqual(status, action_constants.LIVEACTION_STATUS_SUCCEEDED)
        self.assertIn("PARAM_BOOLEAN=0", result["stdout"])

        action_parameters = {
            "param_string": "",
            "param_integer": None,
            "param_float": None,
        }

        runner = self._get_runner(action_db=action_db, entry_point=entry_point)
        runner.pre_run()
        status, result, _ = runner.run(action_parameters=action_parameters)
        runner.post_run(status, result)

        self.assertEqual(status, action_constants.LIVEACTION_STATUS_SUCCEEDED)
        self.assertIn("PARAM_STRING=\n", result["stdout"])
        self.assertIn("PARAM_INTEGER=\n", result["stdout"])
        self.assertIn("PARAM_FLOAT=\n", result["stdout"])

        # End result should be the same when streaming is enabled
        cfg.CONF.set_override(name="stream_output", group="actionrunner", override=True)

        # Verify initial state
        output_dbs = ActionExecutionOutput.get_all()
        self.assertEqual(len(output_dbs), 0)

        action_parameters = {
            "param_string": "test string",
            "param_integer": 1,
            "param_float": 2.55,
            "param_boolean": True,
            "param_list": ["a", "b", "c"],
            "param_object": {"foo": "bar"},
        }

        runner = self._get_runner(action_db=action_db, entry_point=entry_point)
        runner.pre_run()
        status, result, _ = runner.run(action_parameters=action_parameters)
        runner.post_run(status, result)

        self.assertEqual(status, action_constants.LIVEACTION_STATUS_SUCCEEDED)
        self.assertIn("PARAM_STRING=test string", result["stdout"])
        self.assertIn("PARAM_INTEGER=1", result["stdout"])
        self.assertIn("PARAM_FLOAT=2.55", result["stdout"])
        self.assertIn("PARAM_BOOLEAN=1", result["stdout"])
        self.assertIn("PARAM_LIST=a,b,c", result["stdout"])
        self.assertIn('PARAM_OBJECT={"foo":"bar"}', result["stdout"])

        output_dbs = ActionExecutionOutput.query(output_type="stdout")
        self.assertEqual(len(output_dbs), 6)
        self.assertEqual(output_dbs[0].data, "PARAM_STRING=test string\n")
        self.assertEqual(output_dbs[5].data, 'PARAM_OBJECT={"foo":"bar"}\n')

        output_dbs = ActionExecutionOutput.query(output_type="stderr")
        self.assertEqual(len(output_dbs), 0)

    @mock.patch("st2common.util.concurrency.subprocess_popen")
    @mock.patch("st2common.util.concurrency.spawn")
    def test_action_stdout_and_stderr_is_stored_in_the_db(self, mock_spawn, mock_popen):
        # Feature is enabled
        cfg.CONF.set_override(name="stream_output", group="actionrunner", override=True)

        # Note: We need to mock spawn function so we can test everything in single event loop
        # iteration
        mock_spawn.side_effect = blocking_eventlet_spawn

        # No output to stdout and no result (implicit None)
        mock_stdout = [
            "stdout line 1\n",
            "stdout line 2\n",
            "stdout line 3\n",
            "stdout line 4\n",
        ]
        mock_stderr = ["stderr line 1\n", "stderr line 2\n", "stderr line 3\n"]

        mock_process = mock.Mock()
        mock_process.returncode = 0
        mock_popen.return_value = mock_process
        mock_process.stdout.closed = False
        mock_process.stderr.closed = False
        mock_process.stdout.readline = make_mock_stream_readline(
            mock_process.stdout, mock_stdout, stop_counter=4
        )
        mock_process.stderr.readline = make_mock_stream_readline(
            mock_process.stderr, mock_stderr, stop_counter=3
        )

        models = self.fixtures_loader.load_models(
            fixtures_pack=GENERIC_PACK,
            fixtures_dict={"actions": ["local_script_with_params.yaml"]},
        )
        action_db = models["actions"]["local_script_with_params.yaml"]
        entry_point = os.path.join(
            get_fixtures_base_path(), "generic/actions/local_script_with_params.sh"
        )

        action_parameters = {
            "param_string": "test string",
            "param_integer": 1,
            "param_float": 2.55,
            "param_boolean": True,
            "param_list": ["a", "b", "c"],
            "param_object": {"foo": "bar"},
        }

        runner = self._get_runner(action_db=action_db, entry_point=entry_point)
        runner.pre_run()
        status, result, _ = runner.run(action_parameters=action_parameters)
        runner.post_run(status, result)

        self.assertEqual(
            result["stdout"],
            "stdout line 1\nstdout line 2\nstdout line 3\nstdout line 4",
        )
        self.assertEqual(
            result["stderr"], "stderr line 1\nstderr line 2\nstderr line 3"
        )
        self.assertEqual(result["return_code"], 0)

        # Verify stdout and stderr lines have been correctly stored in the db
        output_dbs = ActionExecutionOutput.query(output_type="stdout")
        self.assertEqual(len(output_dbs), 4)
        self.assertEqual(output_dbs[0].data, mock_stdout[0])
        self.assertEqual(output_dbs[1].data, mock_stdout[1])
        self.assertEqual(output_dbs[2].data, mock_stdout[2])
        self.assertEqual(output_dbs[3].data, mock_stdout[3])

        output_dbs = ActionExecutionOutput.query(output_type="stderr")
        self.assertEqual(len(output_dbs), 3)
        self.assertEqual(output_dbs[0].data, mock_stderr[0])
        self.assertEqual(output_dbs[1].data, mock_stderr[1])
        self.assertEqual(output_dbs[2].data, mock_stderr[2])

    def test_shell_script_action(self):
        models = self.fixtures_loader.load_models(
            fixtures_pack=LOCALRUNNER_PACK,
            fixtures_dict={"actions": ["text_gen.yml"]},
        )
        action_db = models["actions"]["text_gen.yml"]
        entry_point = self.fixtures_loader.get_fixture_file_path_abs(
            LOCALRUNNER_PACK, "actions", "text_gen.py"
        )
        runner = self._get_runner(action_db, entry_point=entry_point)
        runner.pre_run()
        status, result, _ = runner.run({"chars": 1000})
        runner.post_run(status, result)
        self.assertEqual(status, action_constants.LIVEACTION_STATUS_SUCCEEDED)
        self.assertEqual(len(result["stdout"]), 1000)

    def test_large_stdout(self):
        models = self.fixtures_loader.load_models(
            fixtures_pack=LOCALRUNNER_PACK,
            fixtures_dict={"actions": ["text_gen.yml"]},
        )
        action_db = models["actions"]["text_gen.yml"]
        entry_point = self.fixtures_loader.get_fixture_file_path_abs(
            LOCALRUNNER_PACK, "actions", "text_gen.py"
        )
        runner = self._get_runner(action_db, entry_point=entry_point)
        runner.pre_run()
        char_count = 10**6  # Note 10^7 succeeds but ends up being slow.
        status, result, _ = runner.run({"chars": char_count})
        runner.post_run(status, result)
        self.assertEqual(status, action_constants.LIVEACTION_STATUS_SUCCEEDED)
        self.assertEqual(len(result["stdout"]), char_count)

    def _get_runner(self, action_db, entry_point):
        runner = LocalShellScriptRunner(uuid.uuid4().hex)
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
        runner.auth_token.token = "mock-token"
        return runner

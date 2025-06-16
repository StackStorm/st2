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
import re
import sys

import six
import mock
from oslo_config import cfg

from python_runner import python_runner
from st2actions.container.base import RunnerContainer
from st2common.runners.base_action import Action
from st2common.runners.utils import get_action_class_instance
from st2common.services import config as config_service
from st2common.constants.action import ACTION_OUTPUT_RESULT_DELIMITER
from st2common.constants.action import (
    LIVEACTION_STATUS_SUCCEEDED,
    LIVEACTION_STATUS_FAILED,
)
from st2common.constants.action import LIVEACTION_STATUS_TIMED_OUT
from st2common.constants.action import MAX_PARAM_LENGTH
from st2common.constants.pack import COMMON_LIB_DIR
from st2common.constants.pack import SYSTEM_PACK_NAMES
from st2common.persistence.execution import ActionExecutionOutput
from python_runner.python_action_wrapper import PythonActionWrapper
from st2tests.base import RunnerTestCase
from st2tests.base import CleanDbTestCase
from st2tests.base import blocking_eventlet_spawn
from st2tests.base import make_mock_stream_readline
from st2tests.fixtures.packs.dummy_pack_1.fixture import PACK_NAME as DUMMY_PACK_1
from st2tests.fixtures.packs.dummy_pack_5.fixture import PACK_NAME as DUMMY_PACK_5
from st2tests.fixtures.packs.dummy_pack_9.fixture import PACK_PATH as DUMMY_PACK_9_PATH
from st2tests.fixtures.packs.test_content_version_fixture.fixture import (
    PACK_NAME as TEST_CONTENT_VERSION,
    PACK_PATH as TEST_CONTENT_VERSION_PATH,
)
from st2tests.fixturesloader import assert_submodules_are_checked_out
import st2tests.base as tests_base


PASCAL_ROW_ACTION_PATH = os.path.join(
    tests_base.get_resources_path(), "packs", "pythonactions/actions/pascal_row.py"
)
ECHOER_ACTION_PATH = os.path.join(
    tests_base.get_resources_path(), "packs", "pythonactions/actions/echoer.py"
)
TEST_ACTION_PATH = os.path.join(
    tests_base.get_resources_path(), "packs", "pythonactions/actions/test.py"
)
PATHS_ACTION_PATH = os.path.join(
    tests_base.get_resources_path(), "packs", "pythonactions/actions/python_paths.py"
)
ACTION_1_PATH = os.path.join(DUMMY_PACK_9_PATH, "actions/list_repos_doesnt_exist.py")
ACTION_2_PATH = os.path.join(DUMMY_PACK_9_PATH, "actions/invalid_syntax.py")
NON_SIMPLE_TYPE_ACTION = os.path.join(
    tests_base.get_resources_path(), "packs", "pythonactions/actions/non_simple_type.py"
)
PRINT_VERSION_ACTION = os.path.join(
    TEST_CONTENT_VERSION_PATH,
    "actions/print_version.py",
)
PRINT_VERSION_LOCAL_MODULE_ACTION = os.path.join(
    TEST_CONTENT_VERSION_PATH,
    "actions/print_version_local_import.py",
)

PRINT_CONFIG_ITEM_ACTION = os.path.join(
    tests_base.get_resources_path(),
    "packs",
    "pythonactions/actions/print_config_item_doesnt_exist.py",
)
PRINT_TO_STDOUT_STDERR_ACTION = os.path.join(
    tests_base.get_resources_path(),
    "packs",
    "pythonactions/actions/print_to_stdout_and_stderr.py",
)


# Note: runner inherits parent args which doesn't work with tests since test pass additional
# unrecognized args
mock_sys = mock.Mock()
mock_sys.argv = []
mock_sys.executable = sys.executable

MOCK_EXECUTION = mock.Mock()
MOCK_EXECUTION.id = "598dbf0c0640fd54bffc688b"


# Use DUMMY_PACK_1 instead of depending on everything in the core (SYSTEM_PACK_NAME) pack.
@mock.patch(
    "st2common.util.sandboxing.SYSTEM_PACK_NAMES", [DUMMY_PACK_1, *SYSTEM_PACK_NAMES]
)
@mock.patch("python_runner.python_runner.sys", mock_sys)
class PythonRunnerTestCase(RunnerTestCase, CleanDbTestCase):
    register_packs = True
    register_pack_configs = True

    @classmethod
    def setUpClass(cls):
        super(PythonRunnerTestCase, cls).setUpClass()
        assert_submodules_are_checked_out()

    def test_runner_creation(self):
        runner = python_runner.get_runner()
        self.assertIsNotNone(runner, "Creation failed. No instance.")
        self.assertEqual(
            type(runner), python_runner.PythonRunner, "Creation failed. No instance."
        )

    def test_action_returns_non_serializable_result(self):
        # Actions returns non-simple type which can't be serialized, verify result is simple str()
        # representation of the result
        runner = self._get_mock_runner_obj()
        runner.entry_point = NON_SIMPLE_TYPE_ACTION
        runner.pre_run()
        (status, output, _) = runner.run({})

        self.assertEqual(status, LIVEACTION_STATUS_SUCCEEDED)
        self.assertIsNotNone(output)

        if six.PY2:
            expected_result_re = (
                r"\[{'a': '1'}, {'h': 3, 'c': 2}, {'e': "
                r"<non_simple_type.Test object at .*?>}\]"
            )
        else:
            expected_result_re = (
                r"\[{'a': '1'}, {'c': 2, 'h': 3}, {'e': "
                r"<non_simple_type.Test object at .*?>}\]"
            )

        match = re.match(expected_result_re, output["result"])
        self.assertTrue(match)

    def test_simple_action_with_result_no_status(self):
        runner = self._get_mock_runner_obj()
        runner.entry_point = PASCAL_ROW_ACTION_PATH
        runner.pre_run()
        (status, output, _) = runner.run({"row_index": 5})
        self.assertEqual(status, LIVEACTION_STATUS_SUCCEEDED)
        self.assertIsNotNone(output)
        self.assertEqual(output["result"], [1, 5, 10, 10, 5, 1])

    def test_simple_action_with_result_as_None_no_status(self):
        runner = self._get_mock_runner_obj()
        runner.entry_point = PASCAL_ROW_ACTION_PATH
        runner.pre_run()
        (status, output, _) = runner.run({"row_index": "b"})
        self.assertEqual(status, LIVEACTION_STATUS_SUCCEEDED)
        self.assertIsNotNone(output)
        self.assertEqual(output["exit_code"], 0)
        self.assertEqual(output["result"], None)

    def test_simple_action_timeout(self):
        timeout = 0
        runner = self._get_mock_runner_obj()
        runner.runner_parameters = {python_runner.RUNNER_TIMEOUT: timeout}
        runner.entry_point = PASCAL_ROW_ACTION_PATH
        runner.pre_run()
        (status, output, _) = runner.run({"row_index": 4})
        self.assertEqual(status, LIVEACTION_STATUS_TIMED_OUT)
        self.assertIsNotNone(output)
        self.assertEqual(output["result"], "None")
        self.assertEqual(output["error"], "Action failed to complete in 0 seconds")
        self.assertEqual(output["exit_code"], -9)

    def test_simple_action_with_status_succeeded(self):
        runner = self._get_mock_runner_obj()
        runner.entry_point = PASCAL_ROW_ACTION_PATH
        runner.pre_run()
        (status, output, _) = runner.run({"row_index": 4})
        self.assertEqual(status, LIVEACTION_STATUS_SUCCEEDED)
        self.assertIsNotNone(output)
        self.assertEqual(output["result"], [1, 4, 6, 4, 1])

    def test_simple_action_with_status_failed(self):
        runner = self._get_mock_runner_obj()
        runner.entry_point = PASCAL_ROW_ACTION_PATH
        runner.pre_run()
        (status, output, _) = runner.run({"row_index": "a"})
        self.assertEqual(status, LIVEACTION_STATUS_FAILED)
        self.assertIsNotNone(output)
        self.assertEqual(output["result"], "This is suppose to fail don't worry!!")

    def test_simple_action_with_status_complex_type_returned_for_result(self):
        # Result containing a complex type shouldn't break the returning a tuple with status
        # behavior
        runner = self._get_mock_runner_obj()
        runner.entry_point = PASCAL_ROW_ACTION_PATH
        runner.pre_run()
        (status, output, _) = runner.run({"row_index": "complex_type"})

        self.assertEqual(status, LIVEACTION_STATUS_FAILED)
        self.assertIsNotNone(output)
        self.assertIn("<pascal_row.PascalRowAction object at", output["result"])

    def test_simple_action_with_status_failed_result_none(self):
        runner = self._get_mock_runner_obj()
        runner.entry_point = PASCAL_ROW_ACTION_PATH
        runner.pre_run()
        (status, output, _) = runner.run({"row_index": "c"})
        self.assertEqual(status, LIVEACTION_STATUS_FAILED)
        self.assertIsNotNone(output)
        self.assertEqual(output["result"], None)

    def test_exception_in_simple_action_with_invalid_status(self):
        runner = self._get_mock_runner_obj()
        runner.entry_point = PASCAL_ROW_ACTION_PATH
        runner.pre_run()
        self.assertRaises(ValueError, runner.run, action_parameters={"row_index": "d"})

    def test_simple_action_no_status_backward_compatibility(self):
        runner = self._get_mock_runner_obj()
        runner.entry_point = PASCAL_ROW_ACTION_PATH
        runner.pre_run()
        (status, output, _) = runner.run({"row_index": "e"})
        self.assertEqual(status, LIVEACTION_STATUS_SUCCEEDED)
        self.assertIsNotNone(output)
        self.assertEqual(output["result"], [1, 2])

    def test_simple_action_config_value_provided_overriden_in_datastore(self):
        user = "joe"

        # No values provided in the datastore
        runner = self._get_mock_runner_obj_from_container(pack=DUMMY_PACK_5, user=user)
        self.assertEqual(runner._config["api_key"], "some_api_key")  # static value
        self.assertEqual(runner._config["regions"], ["us-west-1"])  # static value
        self.assertEqual(runner._config["api_secret"], None)
        self.assertEqual(runner._config["private_key_path"], None)

        # api_secret overriden in the datastore (user scoped value)
        config_service.set_datastore_value_for_config_key(
            pack_name=DUMMY_PACK_5,
            key_name="api_secret",
            user=user,
            value="foosecret",
            secret=True,
        )

        # private_key_path overriden in the datastore (global / non-user scoped value)
        config_service.set_datastore_value_for_config_key(
            pack_name=DUMMY_PACK_5, key_name="private_key_path", value="foopath"
        )

        runner = self._get_mock_runner_obj_from_container(pack=DUMMY_PACK_5, user=user)
        self.assertEqual(runner._config["api_key"], "some_api_key")  # static value
        self.assertEqual(runner._config["regions"], ["us-west-1"])  # static value
        self.assertEqual(runner._config["api_secret"], "foosecret")
        self.assertEqual(runner._config["private_key_path"], "foopath")

    def test_simple_action_fail(self):
        runner = self._get_mock_runner_obj()
        runner.entry_point = PASCAL_ROW_ACTION_PATH
        runner.pre_run()
        (status, result, _) = runner.run({"row_index": "4"})
        self.assertIsNotNone(result)
        self.assertEqual(status, LIVEACTION_STATUS_FAILED)

    def test_simple_action_no_file(self):
        runner = self._get_mock_runner_obj()
        runner.entry_point = "foo.py"
        runner.pre_run()
        (status, result, _) = runner.run({})
        self.assertIsNotNone(result)
        self.assertEqual(status, LIVEACTION_STATUS_FAILED)

    def test_simple_action_no_entry_point(self):
        runner = self._get_mock_runner_obj()
        runner.entry_point = ""

        expected_msg = "Action .*? is missing entry_point attribute"
        self.assertRaisesRegex(Exception, expected_msg, runner.run, {})

    @mock.patch("st2common.util.concurrency.subprocess_popen")
    def test_action_with_user_supplied_env_vars(self, mock_popen):
        env_vars = {"key1": "val1", "key2": "val2", "PYTHONPATH": "foobar"}

        mock_process = mock.Mock()
        mock_process.communicate.return_value = ("", "")
        mock_popen.return_value = mock_process

        runner = self._get_mock_runner_obj()
        runner.runner_parameters = {"env": env_vars}
        runner.entry_point = PASCAL_ROW_ACTION_PATH
        runner.pre_run()
        (_, _, _) = runner.run({"row_index": 4})

        _, call_kwargs = mock_popen.call_args
        actual_env = call_kwargs["env"]

        for key, value in env_vars.items():
            # Verify that a blacklsited PYTHONPATH has been filtered out
            if key == "PYTHONPATH":
                self.assertTrue(actual_env[key] != value)
            else:
                self.assertEqual(actual_env[key], value)

    @mock.patch("st2common.util.concurrency.subprocess_popen")
    @mock.patch("st2common.util.concurrency.spawn")
    def test_action_stdout_and_stderr_is_not_stored_in_db_by_default(
        self, mock_spawn, mock_popen
    ):
        # Feature should be disabled by default
        values = {"delimiter": ACTION_OUTPUT_RESULT_DELIMITER}

        # Note: We need to mock spawn function so we can test everything in single event loop
        # iteration
        mock_spawn.side_effect = blocking_eventlet_spawn

        # No output to stdout and no result (implicit None)
        mock_stdout = [
            "pre result line 1\n",
            "%(delimiter)sTrue%(delimiter)s" % values,
            "post result line 1",
        ]
        mock_stderr = ["stderr line 1\n", "stderr line 2\n", "stderr line 3\n"]

        mock_process = mock.Mock()
        mock_process.returncode = 0
        mock_popen.return_value = mock_process
        mock_process.stdout.closed = False
        mock_process.stderr.closed = False
        mock_process.stdout.readline = make_mock_stream_readline(
            mock_process.stdout, mock_stdout, stop_counter=3
        )
        mock_process.stderr.readline = make_mock_stream_readline(
            mock_process.stderr, mock_stderr, stop_counter=3
        )

        runner = self._get_mock_runner_obj()
        runner.entry_point = PASCAL_ROW_ACTION_PATH
        runner.pre_run()
        (_, output, _) = runner.run({"row_index": 4})

        self.assertMultiLineEqual(
            output["stdout"], "pre result line 1\npost result line 1"
        )
        self.assertMultiLineEqual(
            output["stderr"], "stderr line 1\nstderr line 2\nstderr line 3\n"
        )
        self.assertEqual(output["result"], "True")
        self.assertEqual(output["exit_code"], 0)

        output_dbs = ActionExecutionOutput.get_all()
        self.assertEqual(len(output_dbs), 0)

        # False is a default behavior so end result should be the same
        cfg.CONF.set_override(
            name="stream_output", group="actionrunner", override=False
        )

        mock_process = mock.Mock()
        mock_process.returncode = 0
        mock_popen.return_value = mock_process
        mock_process.stdout.closed = False
        mock_process.stderr.closed = False
        mock_process.stdout.readline = make_mock_stream_readline(
            mock_process.stdout, mock_stdout, stop_counter=3
        )
        mock_process.stderr.readline = make_mock_stream_readline(
            mock_process.stderr, mock_stderr, stop_counter=3
        )

        runner.pre_run()
        (_, output, _) = runner.run({"row_index": 4})

        self.assertMultiLineEqual(
            output["stdout"], "pre result line 1\npost result line 1"
        )
        self.assertMultiLineEqual(
            output["stderr"], "stderr line 1\nstderr line 2\nstderr line 3\n"
        )
        self.assertEqual(output["result"], "True")
        self.assertEqual(output["exit_code"], 0)

        output_dbs = ActionExecutionOutput.get_all()
        self.assertEqual(len(output_dbs), 0)

    @mock.patch("st2common.util.concurrency.subprocess_popen")
    @mock.patch("st2common.util.concurrency.spawn")
    def test_action_stdout_and_stderr_is_stored_in_the_db(self, mock_spawn, mock_popen):
        # Feature is enabled
        cfg.CONF.set_override(name="stream_output", group="actionrunner", override=True)

        values = {"delimiter": ACTION_OUTPUT_RESULT_DELIMITER}

        # Note: We need to mock spawn function so we can test everything in single event loop
        # iteration
        mock_spawn.side_effect = blocking_eventlet_spawn

        # No output to stdout and no result (implicit None)
        mock_stdout = [
            "pre result line 1\n",
            "pre result line 2\n",
            "%(delimiter)sTrue%(delimiter)s" % values,
            "post result line 1",
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

        runner = self._get_mock_runner_obj()
        runner.entry_point = PASCAL_ROW_ACTION_PATH
        runner.pre_run()
        (_, output, _) = runner.run({"row_index": 4})

        self.assertMultiLineEqual(
            output["stdout"], "pre result line 1\npre result line 2\npost result line 1"
        )
        self.assertMultiLineEqual(
            output["stderr"], "stderr line 1\nstderr line 2\nstderr line 3\n"
        )
        self.assertEqual(output["result"], "True")
        self.assertEqual(output["exit_code"], 0)

        # Verify stdout and stderr lines have been correctly stored in the db
        # Note - result delimiter should not be stored in the db
        output_dbs = ActionExecutionOutput.query(output_type="stdout")
        self.assertEqual(len(output_dbs), 3)
        self.assertEqual(output_dbs[0].runner_ref, "python-script")
        self.assertEqual(output_dbs[0].data, mock_stdout[0])
        self.assertEqual(output_dbs[1].data, mock_stdout[1])
        self.assertEqual(output_dbs[2].data, mock_stdout[3])

        output_dbs = ActionExecutionOutput.query(output_type="stderr")
        self.assertEqual(len(output_dbs), 3)
        self.assertEqual(output_dbs[0].runner_ref, "python-script")
        self.assertEqual(output_dbs[0].data, mock_stderr[0])
        self.assertEqual(output_dbs[1].data, mock_stderr[1])
        self.assertEqual(output_dbs[2].data, mock_stderr[2])

    def test_real_time_output_streaming_bufsize(self):
        # Test various values for bufsize and verify it works / doesn't hang the process
        cfg.CONF.set_override(name="stream_output", group="actionrunner", override=True)

        bufsize_values = [-100, -2, -1, 0, 1, 2, 1024, 2048, 4096, 10000]

        for index, bufsize in enumerate(bufsize_values, 1):
            cfg.CONF.set_override(
                name="stream_output_buffer_size", override=bufsize, group="actionrunner"
            )

            output_dbs = ActionExecutionOutput.get_all()
            # Unexpected third party warnings will also inflate this number
            self.assertGreaterEqual(len(output_dbs), (index - 1) * 4)

            runner = self._get_mock_runner_obj()
            runner.entry_point = PRINT_TO_STDOUT_STDERR_ACTION
            runner.pre_run()
            (_, output, _) = runner.run({"stdout_count": 2, "stderr_count": 2})

            # assertMultiLineEqual displays a diff if the two don't match
            self.assertMultiLineEqual(
                output["stdout"], "stdout line 0\nstdout line 1\n"
            )
            # Third party packages can unexpectedly emit warnings and add more
            # output to the streamed stderr, so we check that the expected
            # lines occurred, but we allow additional lines to exist
            self.assertIn("stderr line 0\n", output["stderr"])
            self.assertIn("stderr line 1\n", output["stderr"])
            self.assertEqual(output["exit_code"], 0)

            output_dbs = ActionExecutionOutput.get_all()
            # Unexpected third party warnings will also inflate this number
            self.assertGreaterEqual(len(output_dbs), (index) * 4)

    @mock.patch("st2common.util.concurrency.subprocess_popen")
    def test_stdout_interception_and_parsing(self, mock_popen):
        values = {"delimiter": ACTION_OUTPUT_RESULT_DELIMITER}

        # No output to stdout and no result (implicit None)
        mock_stdout = ["%(delimiter)sNone%(delimiter)s" % values]
        mock_stderr = ["foo stderr"]

        mock_process = mock.Mock()
        mock_process.returncode = 0
        mock_popen.return_value = mock_process
        mock_process.stdout.closed = False
        mock_process.stderr.closed = False
        mock_process.stdout.readline = make_mock_stream_readline(
            mock_process.stdout, mock_stdout
        )
        mock_process.stderr.readline = make_mock_stream_readline(
            mock_process.stderr, mock_stderr
        )

        runner = self._get_mock_runner_obj()
        runner.entry_point = PASCAL_ROW_ACTION_PATH
        runner.pre_run()
        (_, output, _) = runner.run({"row_index": 4})

        self.assertEqual(output["stdout"], "")
        self.assertEqual(output["stderr"], mock_stderr[0])
        self.assertEqual(output["result"], "None")
        self.assertEqual(output["exit_code"], 0)

        # Output to stdout, no result (implicit None), return_code 1 and status failed
        mock_stdout = ["pre result%(delimiter)sNone%(delimiter)spost result" % values]
        mock_stderr = ["foo stderr"]

        mock_process = mock.Mock()
        mock_process.returncode = 1
        mock_popen.return_value = mock_process
        mock_process.stdout.closed = False
        mock_process.stderr.closed = False
        mock_process.stdout.readline = make_mock_stream_readline(
            mock_process.stdout, mock_stdout
        )
        mock_process.stderr.readline = make_mock_stream_readline(
            mock_process.stderr, mock_stderr
        )

        runner = self._get_mock_runner_obj()
        runner.entry_point = PASCAL_ROW_ACTION_PATH
        runner.pre_run()
        (status, output, _) = runner.run({"row_index": 4})

        self.assertEqual(output["stdout"], "pre resultpost result")
        self.assertEqual(output["stderr"], mock_stderr[0])
        self.assertEqual(output["result"], "None")
        self.assertEqual(output["exit_code"], 1)
        self.assertEqual(status, "failed")

        # Output to stdout, no result (implicit None), return_code 1 and status succeeded
        mock_stdout = ["pre result%(delimiter)sNone%(delimiter)spost result" % values]
        mock_stderr = ["foo stderr"]

        mock_process = mock.Mock()
        mock_process.returncode = 0
        mock_popen.return_value = mock_process
        mock_process.stdout.closed = False
        mock_process.stderr.closed = False
        mock_process.stdout.readline = make_mock_stream_readline(
            mock_process.stdout, mock_stdout
        )
        mock_process.stderr.readline = make_mock_stream_readline(
            mock_process.stderr, mock_stderr
        )

        runner = self._get_mock_runner_obj()
        runner.entry_point = PASCAL_ROW_ACTION_PATH
        runner.pre_run()
        (status, output, _) = runner.run({"row_index": 4})

        self.assertEqual(output["stdout"], "pre resultpost result")
        self.assertEqual(output["stderr"], mock_stderr[0])
        self.assertEqual(output["result"], "None")
        self.assertEqual(output["exit_code"], 0)
        self.assertEqual(status, "succeeded")

    @mock.patch("st2common.util.concurrency.subprocess_popen")
    def test_common_st2_env_vars_are_available_to_the_action(self, mock_popen):
        mock_process = mock.Mock()
        mock_process.communicate.return_value = ("", "")
        mock_popen.return_value = mock_process

        runner = self._get_mock_runner_obj()
        runner.auth_token = mock.Mock()
        runner.auth_token.token = "ponies"
        runner.entry_point = PASCAL_ROW_ACTION_PATH
        runner.pre_run()
        (_, _, _) = runner.run({"row_index": 4})

        _, call_kwargs = mock_popen.call_args
        actual_env = call_kwargs["env"]
        self.assertCommonSt2EnvVarsAvailableInEnv(env=actual_env)

    @mock.patch("st2common.util.concurrency.subprocess_popen")
    def test_pythonpath_env_var_contains_common_libs_config_enabled(self, mock_popen):
        mock_process = mock.Mock()
        mock_process.communicate.return_value = ("", "")
        mock_popen.return_value = mock_process

        runner = self._get_mock_runner_obj()
        runner._enable_common_pack_libs = True
        runner.auth_token = mock.Mock()
        runner.auth_token.token = "ponies"
        runner.entry_point = PASCAL_ROW_ACTION_PATH
        runner.pre_run()
        (_, _, _) = runner.run({"row_index": 4})

        _, call_kwargs = mock_popen.call_args
        actual_env = call_kwargs["env"]
        pack_common_lib_path = f"fixtures/packs/{DUMMY_PACK_1}/lib"
        self.assertIn("PYTHONPATH", actual_env)
        self.assertIn(pack_common_lib_path, actual_env["PYTHONPATH"])

    @mock.patch("st2common.util.concurrency.subprocess_popen")
    def test_pythonpath_env_var_not_contains_common_libs_config_disabled(
        self, mock_popen
    ):
        mock_process = mock.Mock()
        mock_process.communicate.return_value = ("", "")
        mock_popen.return_value = mock_process

        runner = self._get_mock_runner_obj()
        runner._enable_common_pack_libs = False
        runner.auth_token = mock.Mock()
        runner.auth_token.token = "ponies"
        runner.entry_point = PASCAL_ROW_ACTION_PATH
        runner.pre_run()
        (_, _, _) = runner.run({"row_index": 4})

        _, call_kwargs = mock_popen.call_args
        actual_env = call_kwargs["env"]
        pack_common_lib_path = (
            f"/mnt/src/storm/st2/st2tests/st2tests/fixtures/packs/{DUMMY_PACK_1}/lib"
        )
        self.assertIn("PYTHONPATH", actual_env)
        self.assertNotIn(pack_common_lib_path, actual_env["PYTHONPATH"])

    def test_action_class_instantiation_action_service_argument(self):
        class Action1(Action):
            # Constructor not overriden so no issue here
            pass

            def run(self):
                pass

        class Action2(Action):
            # Constructor overriden, but takes action_service argument
            def __init__(self, config, action_service=None):
                super(Action2, self).__init__(
                    config=config, action_service=action_service
                )

            def run(self):
                pass

        class Action3(Action):
            # Constructor overriden, but doesn't take to action service
            def __init__(self, config):
                super(Action3, self).__init__(config=config)

            def run(self):
                pass

        config = {"a": 1, "b": 2}
        action_service = "ActionService!"

        action1 = get_action_class_instance(
            action_cls=Action1, config=config, action_service=action_service
        )
        self.assertEqual(action1.config, config)
        self.assertEqual(action1.action_service, action_service)

        action2 = get_action_class_instance(
            action_cls=Action2, config=config, action_service=action_service
        )
        self.assertEqual(action2.config, config)
        self.assertEqual(action2.action_service, action_service)

        action3 = get_action_class_instance(
            action_cls=Action3, config=config, action_service=action_service
        )
        self.assertEqual(action3.config, config)
        self.assertEqual(action3.action_service, action_service)

    def test_action_with_same_module_name_as_module_in_stdlib(self):
        runner = self._get_mock_runner_obj()
        runner.entry_point = TEST_ACTION_PATH
        runner.pre_run()
        (status, output, _) = runner.run({})
        self.assertEqual(status, LIVEACTION_STATUS_SUCCEEDED)
        self.assertIsNotNone(output)
        self.assertEqual(output["result"], "test action")

    def test_python_action_wrapper_script_doesnt_get_added_to_sys_path(self):
        # Validate that the directory where python_action_wrapper.py script is located
        # (st2common/runners) doesn't get added to sys.path
        runner = self._get_mock_runner_obj()
        runner.entry_point = PATHS_ACTION_PATH
        runner.pre_run()
        (status, output, _) = runner.run({})

        self.assertEqual(status, LIVEACTION_STATUS_SUCCEEDED)
        self.assertIsNotNone(output)

        lines = output["stdout"].split("\n")
        process_sys_path = lines[0]
        process_pythonpath = lines[1]

        assert "sys.path" in process_sys_path
        assert "PYTHONPATH" in process_pythonpath

        wrapper_script_path = "st2common/runners"

        assertion_msg = "Found python wrapper script path in subprocess path"
        self.assertNotIn(wrapper_script_path, process_sys_path, assertion_msg)
        self.assertNotIn(wrapper_script_path, process_pythonpath, assertion_msg)

    def test_python_action_wrapper_action_script_file_doesnt_exist_friendly_error(self):
        # File in a directory which is not a Python package
        wrapper = PythonActionWrapper(
            pack=DUMMY_PACK_5, file_path="/tmp/doesnt.exist", user="joe"
        )

        expected_msg = (
            'File "/tmp/doesnt.exist" has no action class or the file doesn\'t exist.'
        )
        self.assertRaisesRegex(Exception, expected_msg, wrapper._get_action_instance)

        # File in a directory which is a Python package
        wrapper = PythonActionWrapper(
            pack=DUMMY_PACK_5, file_path=ACTION_1_PATH, user="joe"
        )

        expected_msg = (
            r'Failed to load action class from file ".*?list_repos_doesnt_exist.py" '
            r"\(action file most likely doesn\'t exist or contains invalid syntax\): "
            r"\[Errno 2\] No such file or directory"
        )
        self.assertRaisesRegex(Exception, expected_msg, wrapper._get_action_instance)

    def test_python_action_wrapper_action_script_file_contains_invalid_syntax_friendly_error(
        self,
    ):
        wrapper = PythonActionWrapper(
            pack=DUMMY_PACK_5, file_path=ACTION_2_PATH, user="joe"
        )
        expected_msg = (
            r'Failed to load action class from file ".*?invalid_syntax.py" '
            r"\(action file most likely doesn\'t exist or contains invalid syntax\): "
            r"No module named \'?invalid\'?"
        )
        self.assertRaisesRegex(Exception, expected_msg, wrapper._get_action_instance)

    def test_simple_action_log_messages_and_log_level_runner_param(self):
        expected_msg_1 = (
            "st2.actions.python.PascalRowAction: DEBUG    Creating new Client object."
        )
        expected_msg_2 = "Retrieving all the values from the datastore"

        expected_msg_3 = (
            "st2.actions.python.PascalRowAction: INFO     test info log message"
        )
        expected_msg_4 = (
            "st2.actions.python.PascalRowAction: DEBUG    test debug log message"
        )
        expected_msg_5 = (
            "st2.actions.python.PascalRowAction: ERROR    test error log message"
        )

        runner = self._get_mock_runner_obj()
        runner.entry_point = PASCAL_ROW_ACTION_PATH
        runner.pre_run()
        (status, output, _) = runner.run({"row_index": "e"})
        self.assertEqual(status, LIVEACTION_STATUS_SUCCEEDED)
        self.assertIsNotNone(output)
        self.assertEqual(output["result"], [1, 2])

        self.assertIn(expected_msg_1, output["stderr"])
        self.assertIn(expected_msg_2, output["stderr"])
        self.assertIn(expected_msg_3, output["stderr"])
        self.assertIn(expected_msg_4, output["stderr"])
        self.assertIn(expected_msg_5, output["stderr"])

        stderr = output["stderr"].strip().split("\n")
        expected_count = 5

        # Remove lines we don't care about
        lines = []
        for line in stderr:
            if "configuration option is not configured" in line:
                continue

            if "No handlers could be found for logger" in line:
                continue

            lines.append(line)

        msg = 'Expected %s lines, got %s - "%s"' % (
            expected_count,
            len(lines),
            str(lines),
        )
        # Dependencies can inject their own warnings, which increases the
        # number of lines to more than we expect with simple equality checks
        self.assertGreaterEqual(len(lines), expected_count, msg)

        # Only log messages with level info and above should be displayed
        runner = self._get_mock_runner_obj()
        runner.entry_point = PASCAL_ROW_ACTION_PATH
        runner.runner_parameters = {"log_level": "info"}
        runner.pre_run()
        (status, output, _) = runner.run({"row_index": "e"})
        self.assertEqual(status, LIVEACTION_STATUS_SUCCEEDED)
        self.assertIsNotNone(output)
        self.assertEqual(output["result"], [1, 2])

        self.assertIn(expected_msg_3, output["stderr"])
        self.assertNotIn(expected_msg_4, output["stderr"])
        self.assertIn(expected_msg_5, output["stderr"])

        # Only log messages with level error and above should be displayed
        runner = self._get_mock_runner_obj()
        runner.entry_point = PASCAL_ROW_ACTION_PATH
        runner.runner_parameters = {"log_level": "error"}
        runner.pre_run()
        (status, output, _) = runner.run({"row_index": "e"})
        self.assertEqual(status, LIVEACTION_STATUS_SUCCEEDED)
        self.assertIsNotNone(output)
        self.assertEqual(output["result"], [1, 2])

        self.assertNotIn(expected_msg_3, output["stderr"])
        self.assertNotIn(expected_msg_4, output["stderr"])
        self.assertIn(expected_msg_5, output["stderr"])

        # Default log level is changed in st2.config
        cfg.CONF.set_override(
            name="python_runner_log_level", override="INFO", group="actionrunner"
        )

        runner = self._get_mock_runner_obj()
        runner.entry_point = PASCAL_ROW_ACTION_PATH
        runner.runner_parameters = {}
        runner.pre_run()
        (status, output, _) = runner.run({"row_index": "e"})
        self.assertEqual(status, LIVEACTION_STATUS_SUCCEEDED)
        self.assertIsNotNone(output)
        self.assertEqual(output["result"], [1, 2])

        self.assertIn(expected_msg_3, output["stderr"])
        self.assertNotIn(expected_msg_4, output["stderr"])
        self.assertIn(expected_msg_5, output["stderr"])

    def test_traceback_messages_are_not_duplicated_in_stderr(self):
        # Verify tracebacks are not duplicated
        runner = self._get_mock_runner_obj()
        runner.entry_point = PASCAL_ROW_ACTION_PATH
        runner.pre_run()
        (status, output, _) = runner.run({"row_index": "f"})
        self.assertEqual(status, LIVEACTION_STATUS_FAILED)
        self.assertIsNotNone(output)

        expected_msg_1 = "Traceback (most recent"
        expected_msg_2 = "ValueError: Duplicate traceback test"

        self.assertIn(expected_msg_1, output["stderr"])
        self.assertIn(expected_msg_2, output["stderr"])

        self.assertEqual(output["stderr"].count(expected_msg_1), 1)
        self.assertEqual(output["stderr"].count(expected_msg_2), 1)

    def test_execution_with_very_large_parameter(self):
        runner = self._get_mock_runner_obj()
        runner.entry_point = ECHOER_ACTION_PATH
        runner.pre_run()
        large_value = "".join(["1" for _ in range(MAX_PARAM_LENGTH)])
        (status, output, _) = runner.run({"action_input": large_value})
        self.assertEqual(status, LIVEACTION_STATUS_SUCCEEDED)
        self.assertIsNotNone(output)
        self.assertEqual(output["result"]["action_input"], large_value)

    def test_execution_with_close_to_very_large_parameter(self):
        runner = self._get_mock_runner_obj()
        runner.entry_point = ECHOER_ACTION_PATH
        runner.pre_run()
        # 21 is the minimum overhead required to make the param fall back to
        # param based payload. The linux max includes all parts of the param
        # not just the value portion. So we need to subtract the remaining
        # overhead from the initial padding.
        large_value = "".join(["1" for _ in range(MAX_PARAM_LENGTH - 21)])
        (status, output, _) = runner.run({"action_input": large_value})
        self.assertEqual(status, LIVEACTION_STATUS_SUCCEEDED)
        self.assertIsNotNone(output)
        self.assertEqual(output["result"]["action_input"], large_value)

    @mock.patch("python_runner.python_runner.get_sandbox_virtualenv_path")
    def test_content_version_success(self, mock_get_sandbox_virtualenv_path):
        mock_get_sandbox_virtualenv_path.return_value = None

        # 1. valid version - 0.2.0
        runner = self._get_mock_runner_obj(pack=TEST_CONTENT_VERSION, sandbox=False)
        runner.entry_point = PRINT_VERSION_ACTION
        runner.runner_parameters = {"content_version": "v0.2.0"}
        runner.pre_run()

        (status, output, _) = runner.run({})

        self.assertEqual(status, LIVEACTION_STATUS_SUCCEEDED)
        self.assertEqual(output["result"], "v0.2.0")
        self.assertEqual(output["stdout"].strip(), "v0.2.0")

        # 2. valid version - 0.23.0
        runner = self._get_mock_runner_obj(pack=TEST_CONTENT_VERSION, sandbox=False)
        runner.entry_point = PRINT_VERSION_ACTION
        runner.runner_parameters = {"content_version": "v0.3.0"}
        runner.pre_run()

        (status, output, _) = runner.run({})

        self.assertEqual(status, LIVEACTION_STATUS_SUCCEEDED)
        self.assertEqual(output["result"], "v0.3.0")
        self.assertEqual(output["stdout"].strip(), "v0.3.0")

        # 3. invalid version = 0.30.0
        runner = self._get_mock_runner_obj(pack=TEST_CONTENT_VERSION, sandbox=False)
        runner.entry_point = PRINT_VERSION_ACTION
        runner.runner_parameters = {"content_version": "v0.30.0"}

        expected_msg = (
            r'Failed to create git worktree for pack "test_content_version": '
            "Invalid content_version "
            '"v0.30.0" provided. Make sure that git repository is up '
            "to date and contains that revision."
        )
        self.assertRaisesRegex(ValueError, expected_msg, runner.pre_run)

    @mock.patch("python_runner.python_runner.get_sandbox_virtualenv_path")
    @mock.patch("st2common.util.concurrency.subprocess_popen")
    def test_content_version_contains_common_libs_config_enabled(
        self, mock_popen, mock_get_sandbox_virtualenv_path
    ):
        # Verify that the common libs path correctly reflects directory in git worktree
        mock_get_sandbox_virtualenv_path.return_value = None

        mock_process = mock.Mock()
        mock_process.communicate.return_value = ("", "")
        mock_popen.return_value = mock_process

        runner = self._get_mock_runner_obj(pack=TEST_CONTENT_VERSION, sandbox=False)
        runner._enable_common_pack_libs = True
        runner.auth_token = mock.Mock()
        runner.auth_token.token = "ponies"
        runner.runner_parameters = {"content_version": "v0.3.0"}
        runner.entry_point = PRINT_VERSION_ACTION
        runner.pre_run()
        (_, _, _) = runner.run({"row_index": 4})

        _, call_kwargs = mock_popen.call_args
        actual_env = call_kwargs["env"]
        pack_common_lib_path = os.path.join(runner.git_worktree_path, COMMON_LIB_DIR)
        self.assertIn("PYTHONPATH", actual_env)
        self.assertIn(pack_common_lib_path, actual_env["PYTHONPATH"])

    @mock.patch("python_runner.python_runner.get_sandbox_virtualenv_path")
    def test_content_version_success_local_modules_work_fine(
        self, mock_get_sandbox_virtualenv_path
    ):
        # Verify that local module import correctly use git worktree directory
        mock_get_sandbox_virtualenv_path.return_value = None

        runner = self._get_mock_runner_obj(pack=TEST_CONTENT_VERSION, sandbox=False)
        runner.entry_point = PRINT_VERSION_LOCAL_MODULE_ACTION
        runner.runner_parameters = {"content_version": "v0.2.0"}
        runner.pre_run()

        (status, output, _) = runner.run({})

        self.assertEqual(status, LIVEACTION_STATUS_SUCCEEDED)
        self.assertEqual(output["result"], "v0.2.0")

        # Verify local_module has been correctly loaded from git work tree directory
        expected_stdout = (
            "<module '?local_module'? from '?%s/actions/local_module.py'?>.*"
            % runner.git_worktree_path
        )
        self.assertRegex(output["stdout"].strip(), expected_stdout)

    @mock.patch("st2common.runners.base.run_command")
    def test_content_version_old_git_version(self, mock_run_command):
        mock_stdout = ""
        mock_stderr = """
git: 'worktree' is not a git command. See 'git --help'.
"""
        mock_stderr = six.text_type(mock_stderr)
        mock_run_command.return_value = 1, mock_stdout, mock_stderr, False

        runner = self._get_mock_runner_obj()
        runner.entry_point = PASCAL_ROW_ACTION_PATH
        runner.runner_parameters = {"content_version": "v0.10.0"}

        expected_msg = (
            rf'Failed to create git worktree for pack "{DUMMY_PACK_1}": Installed git version '
            "doesn't support git worktree command. To be able to utilize this "
            "functionality you need to use git >= 2.5.0."
        )
        self.assertRaisesRegex(ValueError, expected_msg, runner.pre_run)

    @mock.patch("st2common.runners.base.run_command")
    def test_content_version_pack_repo_not_git_repository(self, mock_run_command):
        mock_stdout = ""
        mock_stderr = """
fatal: Not a git repository (or any parent up to mount point /home)
Stopping at filesystem boundary (GIT_DISCOVERY_ACROSS_FILESYSTEM not set).
"""
        mock_stderr = six.text_type(mock_stderr)
        mock_run_command.return_value = 1, mock_stdout, mock_stderr, False

        runner = self._get_mock_runner_obj()
        runner.entry_point = PASCAL_ROW_ACTION_PATH
        runner.runner_parameters = {"content_version": "v0.10.0"}

        expected_msg = (
            rf'Failed to create git worktree for pack "{DUMMY_PACK_1}": Pack directory '
            '".*" is not a '
            "git repository. To utilize this functionality, pack directory needs to "
            "be a git repository."
        )
        self.assertRaisesRegex(ValueError, expected_msg, runner.pre_run)

    @mock.patch("st2common.runners.base.run_command")
    def test_content_version_invalid_git_revision(self, mock_run_command):
        mock_stdout = ""
        mock_stderr = """
fatal: invalid reference: vinvalid
"""
        mock_stderr = six.text_type(mock_stderr)
        mock_run_command.return_value = 1, mock_stdout, mock_stderr, False

        runner = self._get_mock_runner_obj()
        runner.entry_point = PASCAL_ROW_ACTION_PATH
        runner.runner_parameters = {"content_version": "vinvalid"}

        expected_msg = (
            rf'Failed to create git worktree for pack "{DUMMY_PACK_1}": Invalid content_version '
            '"vinvalid" provided. Make sure that git repository is up '
            "to date and contains that revision."
        )
        self.assertRaisesRegex(ValueError, expected_msg, runner.pre_run)

    def test_missing_config_item_user_friendly_error(self):
        runner = self._get_mock_runner_obj()
        runner.entry_point = PRINT_CONFIG_ITEM_ACTION
        runner.pre_run()
        (status, output, _) = runner.run({})

        self.assertEqual(status, LIVEACTION_STATUS_FAILED)
        self.assertIsNotNone(output)
        self.assertIn("{}", output["stdout"])
        self.assertIn("default_value", output["stdout"])
        self.assertIn(
            f'Config for pack "{DUMMY_PACK_1}" is missing key "key"', output["stderr"]
        )
        self.assertIn(
            'make sure you run "st2ctl reload --register-configs"', output["stderr"]
        )

    def _get_mock_runner_obj(self, pack=None, sandbox=None):
        runner = python_runner.get_runner()
        runner.execution = MOCK_EXECUTION
        runner.action = self._get_mock_action_obj()
        runner.runner_parameters = {}

        if pack:
            runner.action.pack = pack

        if sandbox is not None:
            runner._sandbox = sandbox

        return runner

    @mock.patch("st2actions.container.base.ActionExecution.get", mock.Mock())
    def _get_mock_runner_obj_from_container(self, pack, user, sandbox=None):
        container = RunnerContainer()

        runnertype_db = mock.Mock()
        runnertype_db.name = "python-script"
        runnertype_db.runner_package = "python_runner"
        runnertype_db.runner_module = "python_runner"
        action_db = mock.Mock()
        action_db.pack = pack
        action_db.entry_point = "foo.py"
        liveaction_db = mock.Mock()
        liveaction_db.id = "123"
        liveaction_db.context = {"user": user}
        runner = container._get_runner(
            runner_type_db=runnertype_db,
            action_db=action_db,
            liveaction_db=liveaction_db,
        )
        runner.execution = MOCK_EXECUTION
        runner.action = action_db
        runner.runner_parameters = {}

        if sandbox is not None:
            runner._sandbox = sandbox

        return runner

    def _get_mock_action_obj(self):
        """
        Return mock action object.

        Pack gets set to the system pack so the action doesn't require a separate virtualenv.
        """
        action = mock.Mock()
        action.ref = "dummy.action"
        action.pack = DUMMY_PACK_1
        action.entry_point = "foo.py"
        action.runner_type = {"name": "python-script"}
        return action

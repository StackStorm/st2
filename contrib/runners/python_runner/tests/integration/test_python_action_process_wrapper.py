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

"""
Test case which tests that Python runner action wrapper finishes in <= 200ms. If the process takes
more time to finish, this means it probably directly or in-directly imports some modules which have
side affects and are very slow to import.

Examples of such modules include:
* jsonschema
* pecan
* jinja2
* kombu
* mongoengine
* oslo.config

If the tests fail, look at the recent changes and analyze the import graph using the following
command:

profimp "from python_runner.python_runner import python_action_wrapper" --html > report.html
"""

from __future__ import absolute_import
import os
import json

import unittest
import pytest
from shutil import which as shutil_which

from st2common.util.shell import run_command
from six.moves import range

__all__ = ["PythonRunnerActionWrapperProcessTestCase"]

# Maximum limit for the process wrapper script execution time (in seconds)
WRAPPER_PROCESS_RUN_TIME_UPPER_LIMIT = 0.70

ASSERTION_ERROR_MESSAGE = """
Python wrapper process script took more than %s seconds to execute (%s). This most likely means
that a direct or in-direct import of a module which takes a long time to load has been added (e.g.
jsonschema, pecan, kombu, etc).

Please review recently changed and added code for potential slow import issues and refactor /
re-organize code if possible.
""".strip()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
WRAPPER_SCRIPT_PATH = os.path.join(
    BASE_DIR, "../../../python_runner/python_runner/python_action_wrapper.py"
)
WRAPPER_SCRIPT_PATH = os.path.abspath(WRAPPER_SCRIPT_PATH)
TIME_BINARY_PATH = shutil_which("time")
TIME_BINARY_AVAILABLE = TIME_BINARY_PATH is not None


@pytest.mark.skipif(not TIME_BINARY_PATH, reason="time binary not available")
class PythonRunnerActionWrapperProcessTestCase(unittest.TestCase):
    def test_process_wrapper_exits_in_reasonable_timeframe(self):
        # 1. Verify wrapper script path is correct and file exists
        self.assertTrue(os.path.isfile(WRAPPER_SCRIPT_PATH))

        # 2. First run it without time to verify path is valid
        command_string = "python %s --file-path=foo.py" % (WRAPPER_SCRIPT_PATH)
        _, _, stderr = run_command(command_string, shell=True)
        self.assertIn("usage: python_action_wrapper.py", stderr)

        expected_msg_1 = "python_action_wrapper.py: error: argument --pack is required"
        expected_msg_2 = (
            "python_action_wrapper.py: error: the following arguments are "
            "required: --pack"
        )

        self.assertTrue(expected_msg_1 in stderr or expected_msg_2 in stderr)

        # 3. Now time it
        command_string = '%s -f "%%e" python %s' % (
            TIME_BINARY_PATH,
            WRAPPER_SCRIPT_PATH,
        )

        # Do multiple runs and average it
        run_times = []

        count = 8
        for i in range(0, count):
            _, _, stderr = run_command(command_string, shell=True)
            stderr = stderr.strip().split("\n")[-1]
            run_time_seconds = float(stderr)
            run_times.append(run_time_seconds)

        avg_run_time_seconds = sum(run_times) / count
        assertion_msg = ASSERTION_ERROR_MESSAGE % (
            WRAPPER_PROCESS_RUN_TIME_UPPER_LIMIT,
            avg_run_time_seconds,
        )
        self.assertTrue(
            avg_run_time_seconds <= WRAPPER_PROCESS_RUN_TIME_UPPER_LIMIT, assertion_msg
        )

    def test_config_with_a_lot_of_items_and_a_lot_of_parameters_work_fine(self):
        # Test case which verifies that actions with large configs and a lot of parameters work
        # fine. Config and parameters are passed to wrapper as command line argument so there is an
        # upper limit on the size.
        config = {}
        for index in range(0, 50):
            config["key_%s" % (index)] = "value value foo %s" % (index)
        config = json.dumps(config)

        parameters = {}
        for index in range(0, 30):
            parameters["param_foo_%s" % (index)] = "some param value %s" % (index)
        parameters = json.dumps(parameters)

        file_path = os.path.join(BASE_DIR, "../../../../examples/actions/noop.py")

        command_string = (
            "python %s --pack=dummy --file-path=%s --config='%s' "
            "--parameters='%s'" % (WRAPPER_SCRIPT_PATH, file_path, config, parameters)
        )
        exit_code, stdout, stderr = run_command(command_string, shell=True)
        self.assertEqual(exit_code, 0)
        self.assertIn('"status"', stdout)

    def test_stdin_params_timeout_no_stdin_data_provided(self):
        config = {}
        file_path = os.path.join(BASE_DIR, "../../../../examples/actions/noop.py")

        # try running in a sub-shell to ensure that the stdin is empty
        command_string = (
            "python %s --pack=dummy --file-path=%s --config='%s' "
            "--stdin-parameters" % (WRAPPER_SCRIPT_PATH, file_path, config)
        )
        exit_code, stdout, stderr = run_command(
            command_string, shell=True, close_fds=True
        )

        # Depending on how tests are spawned, sys.stdin may be opened and this will cause issues
        # with this tests so we simply check for two different errors which are considered
        # acceptable.
        expected_msg_1 = (
            "ValueError: No input received and timed out while waiting for parameters "
            "from stdin"
        )
        expected_msg_2 = "ValueError: Received no valid parameters data from sys.stdin"

        self.assertEqual(exit_code, 1)
        self.assertTrue(expected_msg_1 in stderr or expected_msg_2 in stderr)

    def test_stdin_params_invalid_format_friendly_error(self):
        config = {}
        file_path = os.path.join(BASE_DIR, "../../../contrib/examples/actions/noop.py")
        # Not a valid JSON string
        command_string = (
            "echo \"invalid\" | python %s --pack=dummy --file-path=%s --config='%s' "
            "--stdin-parameters" % (WRAPPER_SCRIPT_PATH, file_path, config)
        )
        exit_code, stdout, stderr = run_command(command_string, shell=True)

        expected_msg = (
            "ValueError: Failed to parse parameters from stdin. Expected a JSON "
            'object with "parameters" attribute'
        )
        self.assertEqual(exit_code, 1)
        self.assertIn(expected_msg, stderr)

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
import sys

import mock
import jsonschema

from python_runner import python_runner
from st2common.constants.action import LIVEACTION_STATUS_SUCCEEDED
from st2common.constants.pack import SYSTEM_PACK_NAME
from st2common.util import output_schema
from st2tests.base import RunnerTestCase
from st2tests.base import CleanDbTestCase
from st2tests.fixturesloader import assert_submodules_are_checked_out
import st2tests.base as tests_base


BASE_DIR = os.path.dirname(os.path.abspath(__file__))

PASCAL_ROW_ACTION_PATH = os.path.join(
    tests_base.get_resources_path(), "packs", "pythonactions/actions/pascal_row.py"
)

MOCK_SYS = mock.Mock()
MOCK_SYS.argv = []
MOCK_SYS.executable = sys.executable

MOCK_EXECUTION = mock.Mock()
MOCK_EXECUTION.id = "598dbf0c0640fd54bffc688b"

FAIL_OUTPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "notvalid": {
            "type": "string",
        },
    },
    "additionalProperties": False,
}


@mock.patch("python_runner.python_runner.sys", MOCK_SYS)
class PythonRunnerTestCase(RunnerTestCase, CleanDbTestCase):
    register_packs = True
    register_pack_configs = True

    @classmethod
    def setUpClass(cls):
        super(PythonRunnerTestCase, cls).setUpClass()
        assert_submodules_are_checked_out()

    def test_adherence_to_output_schema(self):
        config = self.loader(os.path.join(BASE_DIR, "../../python_runner/runner.yaml"))
        runner = self._get_mock_runner_obj()
        runner.entry_point = PASCAL_ROW_ACTION_PATH
        runner.pre_run()
        (status, output, _) = runner.run({"row_index": 5})
        output_schema._validate_runner(config[0]["output_schema"], output)
        self.assertEqual(status, LIVEACTION_STATUS_SUCCEEDED)
        self.assertIsNotNone(output)
        self.assertEqual(output["result"], [1, 5, 10, 10, 5, 1])

    def test_fail_incorrect_output_schema(self):
        runner = self._get_mock_runner_obj()
        runner.entry_point = PASCAL_ROW_ACTION_PATH
        runner.pre_run()
        (status, output, _) = runner.run({"row_index": 5})
        with self.assertRaises(jsonschema.ValidationError):
            output_schema._validate_runner(FAIL_OUTPUT_SCHEMA, output)

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

    def _get_mock_action_obj(self):
        """
        Return mock action object.

        Pack gets set to the system pack so the action doesn't require a separate virtualenv.
        """
        action = mock.Mock()
        action.ref = "dummy.action"
        action.pack = SYSTEM_PACK_NAME
        action.entry_point = "foo.py"
        action.runner_type = {"name": "python-script"}
        return action

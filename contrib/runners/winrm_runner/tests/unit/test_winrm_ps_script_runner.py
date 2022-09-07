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

import mock
import os.path
from st2common.runners.base import ActionRunner
from st2tests.base import RunnerTestCase
from winrm_runner import winrm_ps_script_runner
from winrm_runner.winrm_base import WinRmBaseRunner

from .fixtures import FIXTURES_PATH

POWERSHELL_SCRIPT_PATH = os.path.join(FIXTURES_PATH, "TestScript.ps1")


class WinRmPsScriptRunnerTestCase(RunnerTestCase):
    def setUp(self):
        super(WinRmPsScriptRunnerTestCase, self).setUpClass()
        self._runner = winrm_ps_script_runner.get_runner()

    def test_init(self):
        runner = winrm_ps_script_runner.WinRmPsScriptRunner("abcdef")
        self.assertIsInstance(runner, WinRmBaseRunner)
        self.assertIsInstance(runner, ActionRunner)
        self.assertEqual(runner.runner_id, "abcdef")

    @mock.patch(
        "winrm_runner.winrm_ps_script_runner.WinRmPsScriptRunner._get_script_args"
    )
    @mock.patch("winrm_runner.winrm_ps_script_runner.WinRmPsScriptRunner.run_ps")
    def test_run(self, mock_run_ps, mock_get_script_args):
        mock_run_ps.return_value = "expected"
        pos_args = [1, "abc"]
        named_args = {"d": {"test": ["\r", True, 3]}}
        mock_get_script_args.return_value = (pos_args, named_args)

        self._runner.entry_point = POWERSHELL_SCRIPT_PATH
        self._runner.runner_parameters = {}
        self._runner._kwarg_op = "-"

        result = self._runner.run({})

        self.assertEqual(result, "expected")
        mock_run_ps.assert_called_with(
            """[CmdletBinding()]
Param(
  [bool]$p_bool,
  [int]$p_integer,
  [double]$p_number,
  [string]$p_str,
  [array]$p_array,
  [hashtable]$p_obj,
  [Parameter(Position=0)]
  [string]$p_pos0,
  [Parameter(Position=1)]
  [string]$p_pos1
)


Write-Output "p_bool = $p_bool"
Write-Output "p_integer = $p_integer"
Write-Output "p_number = $p_number"
Write-Output "p_str = $p_str"
Write-Output "p_array = $($p_array | ConvertTo-Json -Compress)"
Write-Output "p_obj = $($p_obj | ConvertTo-Json -Compress)"
Write-Output "p_pos0 = $p_pos0"
Write-Output "p_pos1 = $p_pos1"
""",
            '-d @{"test" = @("`r", $true, 3)} 1 "abc"',
        )

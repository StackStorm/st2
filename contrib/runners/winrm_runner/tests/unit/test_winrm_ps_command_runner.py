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
from st2common.runners.base import ActionRunner
from st2tests.base import RunnerTestCase
from winrm_runner import winrm_ps_command_runner
from winrm_runner.winrm_base import WinRmBaseRunner


class WinRmPsCommandRunnerTestCase(RunnerTestCase):
    def setUp(self):
        super(WinRmPsCommandRunnerTestCase, self).setUpClass()
        self._runner = winrm_ps_command_runner.get_runner()

    def test_init(self):
        runner = winrm_ps_command_runner.WinRmPsCommandRunner("abcdef")
        self.assertIsInstance(runner, WinRmBaseRunner)
        self.assertIsInstance(runner, ActionRunner)
        self.assertEqual(runner.runner_id, "abcdef")

    @mock.patch("winrm_runner.winrm_ps_command_runner.WinRmPsCommandRunner.run_ps")
    def test_run(self, mock_run_ps):
        mock_run_ps.return_value = "expected"

        self._runner.runner_parameters = {"cmd": "Get-ADUser stanley"}
        result = self._runner.run({})

        self.assertEqual(result, "expected")
        mock_run_ps.assert_called_with("Get-ADUser stanley")

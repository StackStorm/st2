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

import uuid

from st2common.models.system.action import ShellScriptAction
from st2common.runners.base import GitWorktreeActionRunner
from st2common.runners.base import get_metadata as get_runner_metadata

from local_runner.base import BaseLocalShellRunner

__all__ = ["LocalShellScriptRunner", "get_runner", "get_metadata"]


class LocalShellScriptRunner(BaseLocalShellRunner, GitWorktreeActionRunner):
    def run(self, action_parameters):
        if not self.entry_point:
            raise ValueError("Missing entry_point action metadata attribute")

        script_local_path_abs = self.entry_point
        positional_args, named_args = self._get_script_args(action_parameters)
        named_args = self._transform_named_args(named_args)

        action = ShellScriptAction(
            name=self.action_name,
            action_exec_id=str(self.liveaction_id),
            script_local_path_abs=script_local_path_abs,
            named_args=named_args,
            positional_args=positional_args,
            user=self._user,
            env_vars=self._env,
            sudo=self._sudo,
            timeout=self._timeout,
            cwd=self._cwd,
            sudo_password=self._sudo_password,
        )

        return self._run(action=action)


def get_runner():
    return LocalShellScriptRunner(str(uuid.uuid4()))


def get_metadata():
    metadata = get_runner_metadata("local_runner")
    metadata = [
        runner
        for runner in metadata
        if runner["runner_module"] == __name__.split(".")[-1]
    ][0]
    return metadata

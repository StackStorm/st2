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
from st2common import log as logging
from st2common.models.system.action import RemoteScriptAction
from st2common.models.system.action import SUDO_COMMON_OPTIONS
from st2common.util.shell import quote_unix

__all__ = [
    "ParamikoRemoteScriptAction",
]


LOG = logging.getLogger(__name__)


class ParamikoRemoteScriptAction(RemoteScriptAction):
    def _format_command(self):
        script_arguments = self._get_script_arguments(
            named_args=self.named_args, positional_args=self.positional_args
        )
        env_str = self._get_env_vars_export_string()
        cwd = quote_unix(self.get_cwd())
        script_path = quote_unix(self.remote_script)

        if self.sudo:
            if script_arguments:
                if env_str:
                    command = quote_unix(
                        "%s && cd %s && %s %s"
                        % (env_str, cwd, script_path, script_arguments)
                    )
                else:
                    command = quote_unix(
                        "cd %s && %s %s" % (cwd, script_path, script_arguments)
                    )
            else:
                if env_str:
                    command = quote_unix(
                        "%s && cd %s && %s" % (env_str, cwd, script_path)
                    )
                else:
                    command = quote_unix("cd %s && %s" % (cwd, script_path))

            sudo_arguments = " ".join(self._get_common_sudo_arguments())
            command = "sudo %s -- bash -c %s" % (sudo_arguments, command)

            if self.sudo_password:
                command = "set +o history ; echo -e %s | %s" % (
                    quote_unix("%s\n" % (self.sudo_password)),
                    command,
                )
        else:
            if script_arguments:
                if env_str:
                    command = "%s && cd %s && %s %s" % (
                        env_str,
                        cwd,
                        script_path,
                        script_arguments,
                    )
                else:
                    command = "cd %s && %s %s" % (cwd, script_path, script_arguments)
            else:
                if env_str:
                    command = "%s && cd %s && %s" % (env_str, cwd, script_path)
                else:
                    command = "cd %s && %s" % (cwd, script_path)

        return command

    def _get_common_sudo_arguments(self):
        """
        Retrieve a list of flags which are passed to sudo on every invocation.

        :rtype: ``list``
        """
        flags = []

        if self.sudo_password:
            flags.append("-S")

        flags = flags + SUDO_COMMON_OPTIONS

        return flags

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

from st2common import log as logging
from st2common.models.system.action import RemoteScriptAction
from st2common.util.shell import quote_unix

__all__ = [
    'ParamikoRemoteScriptAction',
]


LOG = logging.getLogger(__name__)


class ParamikoRemoteScriptAction(RemoteScriptAction):
    def _format_command(self):
        script_arguments = self._get_script_arguments(named_args=self.named_args,
                                                      positional_args=self.positional_args)

        command = self._get_quoted_command_string(self.remote_script, script_arguments)

        if self.sudo:
            command = 'sudo -E -- bash -c %s' % command

        return command

    @staticmethod
    def _get_quoted_command_string(remote_script_path, script_arguments):
        if script_arguments:
            command = quote_unix('%s %s' % (remote_script_path, script_arguments))
        else:
            command = quote_unix(remote_script_path)

        return command

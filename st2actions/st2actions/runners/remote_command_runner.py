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

import uuid

from oslo_config import cfg

from st2common import log as logging
from st2actions.runners.ssh.paramiko_ssh_runner import RUNNER_COMMAND
from st2actions.runners.ssh.paramiko_ssh_runner import BaseParallelSSHRunner
from st2common.models.system.paramiko_command_action import ParamikoRemoteCommandAction

__all__ = [
    'get_runner',

    'ParamikoRemoteCommandRunner'
]

LOG = logging.getLogger(__name__)


def get_runner():
    return ParamikoRemoteCommandRunner(str(uuid.uuid4()))


class ParamikoRemoteCommandRunner(BaseParallelSSHRunner):
    def run(self, action_parameters):
        remote_action = self._get_remote_action(action_parameters)

        LOG.debug('Executing remote command action.', extra={'_action_params': remote_action})
        result = self._run(remote_action)
        LOG.debug('Executed remote_action.', extra={'_result': result})
        status = self._get_result_status(result, cfg.CONF.ssh_runner.allow_partial_failure)

        return (status, result, None)

    def _run(self, remote_action):
        command = remote_action.get_full_command_string()
        return self._parallel_ssh_client.run(command, timeout=remote_action.get_timeout())

    def _get_remote_action(self, action_paramaters):
        # remote script actions with entry_point don't make sense, user probably wanted to use
        # "remote-shell-script" action
        if self.entry_point:
            msg = ('Action "%s" specified "entry_point" attribute. Perhaps wanted to use '
                   '"remote-shell-script" runner?' % (self.action_name))
            raise Exception(msg)

        command = self.runner_parameters.get(RUNNER_COMMAND, None)
        env_vars = self._get_env_vars()
        return ParamikoRemoteCommandAction(self.action_name,
                                           str(self.liveaction_id),
                                           command,
                                           env_vars=env_vars,
                                           on_behalf_user=self._on_behalf_user,
                                           user=self._username,
                                           password=self._password,
                                           private_key=self._private_key,
                                           passphrase=self._passphrase,
                                           hosts=self._hosts,
                                           parallel=self._parallel,
                                           sudo=self._sudo,
                                           timeout=self._timeout,
                                           cwd=self._cwd)

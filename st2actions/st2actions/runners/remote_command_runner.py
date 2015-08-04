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
from st2actions.runners.fabric_runner import BaseFabricRunner
from st2actions.runners.fabric_runner import RUNNER_COMMAND
from st2actions.runners.paramiko_ssh_runner import BaseParallelSSHRunner
from st2common.models.system.action import (FabricRemoteAction, RemoteAction)

__all__ = [
    'get_runner',
    'ParamikoRemoteCommandRunner',
    'RemoteCommandRunner'
]

LOG = logging.getLogger(__name__)


def get_runner():
    if cfg.CONF.ssh_runner.use_paramiko_ssh_runner:
        return ParamikoRemoteCommandRunner(str(uuid.uuid4()))
    return RemoteCommandRunner(str(uuid.uuid4()))


class RemoteCommandRunner(BaseFabricRunner):
    def run(self, action_parameters):
        remote_action = self._get_remote_action(action_parameters)

        LOG.debug('Will execute remote_action: %s.', str(remote_action))
        result = self._run(remote_action)
        LOG.debug('Executed remote_action: %s. Result is: %s.', remote_action, result)
        status = self._get_result_status(result, cfg.CONF.ssh_runner.allow_partial_failure)

        return (status, result, None)

    def _get_remote_action(self, action_paramaters):
        command = self.runner_parameters.get(RUNNER_COMMAND, None)
        env_vars = self._get_env_vars()
        return FabricRemoteAction(self.action_name,
                                  str(self.liveaction_id),
                                  command,
                                  env_vars=env_vars,
                                  on_behalf_user=self._on_behalf_user,
                                  user=self._username,
                                  password=self._password,
                                  private_key=self._private_key,
                                  hosts=self._hosts,
                                  parallel=self._parallel,
                                  sudo=self._sudo,
                                  timeout=self._timeout,
                                  cwd=self._cwd)


class ParamikoRemoteCommandRunner(BaseParallelSSHRunner):
    def run(self, action_parameters):
        remote_action = self._get_remote_action(action_parameters)

        LOG.debug('Will execute remote_action: %s.', str(remote_action))
        result = self._run(remote_action)
        LOG.debug('Executed remote_action: %s. Result is: %s.', str(remote_action), result)
        status = self._get_result_status(result, cfg.CONF.ssh_runner.allow_partial_failure)

        return (status, result, None)

    def _run(self, remote_action):
        return self._parallel_ssh_client.run(remote_action.get_command())

    def _get_remote_action(self, action_paramaters):
        command = self.runner_parameters.get(RUNNER_COMMAND, None)
        env_vars = self._get_env_vars()
        return RemoteAction(self.action_name,
                            str(self.liveaction_id),
                            command,
                            env_vars=env_vars,
                            on_behalf_user=self._on_behalf_user,
                            user=self._username,
                            password=self._password,
                            private_key=self._private_key,
                            hosts=self._hosts,
                            parallel=self._parallel,
                            sudo=self._sudo,
                            timeout=self._timeout,
                            cwd=self._cwd)

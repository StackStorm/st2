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

import os
import uuid

from oslo_config import cfg

from st2common import log as logging
from st2actions.runners.fabric_runner import BaseFabricRunner
from st2actions.runners.fabric_runner import RUNNER_REMOTE_DIR
from st2common.models.system.action import FabricRemoteScriptAction

__all__ = [
    'get_runner',
    'RemoteScriptRunner'
]

LOG = logging.getLogger(__name__)


def get_runner():
    return RemoteScriptRunner(str(uuid.uuid4()))


class RemoteScriptRunner(BaseFabricRunner):
    def run(self, action_parameters):
        remote_action = self._get_remote_action(action_parameters)

        LOG.debug('Will execute remote_action : %s.', str(remote_action))
        result = self._run(remote_action)
        LOG.debug('Executed remote_action: %s. Result is : %s.', remote_action, result)
        status = self._get_result_status(result, cfg.CONF.ssh_runner.allow_partial_failure)

        return (status, result, None)

    def _get_remote_action(self, action_parameters):
        # remote script actions without entry_point don't make sense, user probably wanted to use
        # "run-remote" action
        if not self.entry_point:
            msg = ('Action "%s" is missing entry_point attribute. Perhaps wanted to use '
                   '"run-remote" runner?')
            raise Exception(msg % (self.action_name))

        script_local_path_abs = self.entry_point
        pos_args, named_args = self._get_script_args(action_parameters)
        named_args = self._transform_named_args(named_args)
        env_vars = self._get_env_vars()
        remote_dir = self.runner_parameters.get(RUNNER_REMOTE_DIR,
                                                cfg.CONF.ssh_runner.remote_dir)
        remote_dir = os.path.join(remote_dir, self.liveaction_id)
        return FabricRemoteScriptAction(self.action_name,
                                        str(self.liveaction_id),
                                        script_local_path_abs,
                                        self.libs_dir_path,
                                        named_args=named_args,
                                        positional_args=pos_args,
                                        env_vars=env_vars,
                                        on_behalf_user=self._on_behalf_user,
                                        user=self._username,
                                        password=self._password,
                                        private_key=self._private_key,
                                        remote_dir=remote_dir,
                                        hosts=self._hosts,
                                        parallel=self._parallel,
                                        sudo=self._sudo,
                                        timeout=self._timeout,
                                        cwd=self._cwd)

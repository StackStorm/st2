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
import six

from st2actions.runners import ShellRunnerMixin
from st2actions.runners import ActionRunner
from st2common import log as logging
from st2common.constants.action import LIVEACTION_STATUS_SUCCEEDED, LIVEACTION_STATUS_FAILED
from st2common.constants.runners import FABRIC_RUNNER_DEFAULT_ACTION_TIMEOUT
from st2common.exceptions.actionrunner import ActionRunnerPreRunError
from st2common.ssh.parallel_ssh import ParallelSSHClient

LOG = logging.getLogger(__name__)

# constants to lookup in runner_parameters.
RUNNER_HOSTS = 'hosts'
RUNNER_USERNAME = 'username'
RUNNER_PASSWORD = 'password'
RUNNER_PRIVATE_KEY = 'private_key'
RUNNER_PARALLEL = 'parallel'
RUNNER_SUDO = 'sudo'
RUNNER_ON_BEHALF_USER = 'user'
RUNNER_REMOTE_DIR = 'dir'
RUNNER_COMMAND = 'cmd'
RUNNER_CWD = 'cwd'
RUNNER_ENV = 'env'
RUNNER_KWARG_OP = 'kwarg_op'
RUNNER_TIMEOUT = 'timeout'


class BaseParallelSSHRunner(ActionRunner, ShellRunnerMixin):

    def __init__(self, runner_id):
        super(BaseParallelSSHRunner, self).__init__(runner_id=runner_id)
        self._hosts = None
        self._parallel = True
        self._sudo = False
        self._on_behalf_user = None
        self._username = None
        self._password = None
        self._private_key = None
        self._kwarg_op = '--'
        self._cwd = None
        self._env = None
        self._timeout = None
        self._on_behalf_user = cfg.CONF.system_user.user

        self._ssh_key_file = None
        ssh_key_file = cfg.CONF.system_user.ssh_key_file
        if ssh_key_file:
            ssh_key_file = os.path.expanduser(ssh_key_file)
            if os.path.exists(ssh_key_file):
                self._ssh_key_file = ssh_key_file

        self._parallel_ssh_client = None

    def pre_run(self):
        LOG.debug('Entering BaseParallelSSHRunner.pre_run() for liveaction_id="%s"',
                  self.liveaction_id)
        hosts = self.runner_parameters.get(RUNNER_HOSTS, '').split(',')
        self._hosts = [h.strip() for h in hosts if len(h) > 0]
        if len(self._hosts) < 1:
            raise ActionRunnerPreRunError('No hosts specified to run action for action %s.',
                                          self.liveaction_id)
        self._username = self.runner_parameters.get(RUNNER_USERNAME, cfg.CONF.system_user.user)
        self._username = self._username or cfg.CONF.system_user.user
        self._password = self.runner_parameters.get(RUNNER_PASSWORD, None)
        self._private_key = self.runner_parameters.get(RUNNER_PRIVATE_KEY, self._ssh_key_file)
        self._parallel = self.runner_parameters.get(RUNNER_PARALLEL, True)
        self._sudo = self.runner_parameters.get(RUNNER_SUDO, False)
        self._sudo = self._sudo if self._sudo else False
        self._on_behalf_user = self.context.get(RUNNER_ON_BEHALF_USER, self._on_behalf_user)
        self._cwd = self.runner_parameters.get(RUNNER_CWD, None)
        self._env = self.runner_parameters.get(RUNNER_ENV, {})
        self._kwarg_op = self.runner_parameters.get(RUNNER_KWARG_OP, '--')
        self._timeout = self.runner_parameters.get(RUNNER_TIMEOUT,
                                                   FABRIC_RUNNER_DEFAULT_ACTION_TIMEOUT)

        LOG.info('[BaseParallelSSHRunner="%s", liveaction_id="%s"] Finished pre_run.',
                 self.runner_id, self.liveaction_id)

        concurrency = int(len(self._hosts) / 3) + 1 if self._parallel else 1
        self._parallel_ssh_client = ParallelSSHClient(
            hosts=self._hosts,
            user=self._username, pkey=self._ssh_key_file, password=self._password,
            port=22, concurrency=concurrency, raise_on_error=False,
            connect=True
        )

    def _get_env_vars(self):
        """
        :rtype: ``dict``
        """
        env_vars = {}

        if self._env:
            env_vars.update(self._env)

        # Include common st2 env vars
        st2_env_vars = self._get_common_action_env_variables()
        env_vars.update(st2_env_vars)

        return env_vars

    @staticmethod
    def _get_result_status(result, allow_partial_failure):
        success = not allow_partial_failure
        for r in six.itervalues(result):
            r_succeess = r.get('succeeded', False) if r else False
            if allow_partial_failure:
                success |= r_succeess
                if success:
                    return LIVEACTION_STATUS_SUCCEEDED
            else:
                success &= r_succeess
                if not success:
                    return LIVEACTION_STATUS_FAILED
        return LIVEACTION_STATUS_SUCCEEDED if success else LIVEACTION_STATUS_FAILED


def get_runner():
    return BaseParallelSSHRunner(str(uuid.uuid4()))

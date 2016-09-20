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

from oslo_config import cfg
import six

from st2actions.runners import ShellRunnerMixin
from st2actions.runners import ActionRunner
from st2common.constants.runners import REMOTE_RUNNER_PRIVATE_KEY_HEADER
from st2actions.runners.ssh.parallel_ssh import ParallelSSHClient
from st2common import log as logging
from st2common.constants.action import LIVEACTION_STATUS_SUCCEEDED
from st2common.constants.action import LIVEACTION_STATUS_TIMED_OUT
from st2common.constants.action import LIVEACTION_STATUS_FAILED
from st2common.constants.runners import REMOTE_RUNNER_DEFAULT_ACTION_TIMEOUT
from st2common.exceptions.actionrunner import ActionRunnerPreRunError
from st2common.exceptions.ssh import InvalidCredentialsException

__all__ = [
    'BaseParallelSSHRunner'
]

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
RUNNER_SSH_PORT = 'port'
RUNNER_BASTION_HOST = 'bastion_host'
RUNNER_PASSPHRASE = 'passphrase'


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
        self._passphrase = None
        self._kwarg_op = '--'
        self._cwd = None
        self._env = None
        self._timeout = None
        self._bastion_host = None
        self._on_behalf_user = cfg.CONF.system_user.user

        self._ssh_key_file = None
        ssh_key_file = cfg.CONF.system_user.ssh_key_file
        if ssh_key_file:
            ssh_key_file = os.path.expanduser(ssh_key_file)
            if os.path.exists(ssh_key_file):
                self._ssh_key_file = ssh_key_file

        self._parallel_ssh_client = None
        self._max_concurrency = cfg.CONF.ssh_runner.max_parallel_actions

    def pre_run(self):
        super(BaseParallelSSHRunner, self).pre_run()

        LOG.debug('Entering BaseParallelSSHRunner.pre_run() for liveaction_id="%s"',
                  self.liveaction_id)
        hosts = self.runner_parameters.get(RUNNER_HOSTS, '').split(',')
        self._hosts = [h.strip() for h in hosts if len(h) > 0]
        if len(self._hosts) < 1:
            raise ActionRunnerPreRunError('No hosts specified to run action for action %s.',
                                          self.liveaction_id)
        self._username = self.runner_parameters.get(RUNNER_USERNAME, None)
        self._password = self.runner_parameters.get(RUNNER_PASSWORD, None)
        self._private_key = self.runner_parameters.get(RUNNER_PRIVATE_KEY, None)
        self._passphrase = self.runner_parameters.get(RUNNER_PASSPHRASE, None)

        if self._username:
            if not self._password and not self._private_key:
                msg = ('Either password or private_key data needs to be supplied for user: %s' %
                       self._username)
                raise InvalidCredentialsException(msg)

        self._username = self._username or cfg.CONF.system_user.user
        self._ssh_port = self.runner_parameters.get(RUNNER_SSH_PORT, 22)
        self._ssh_key_file = self._private_key or self._ssh_key_file
        self._parallel = self.runner_parameters.get(RUNNER_PARALLEL, True)
        self._sudo = self.runner_parameters.get(RUNNER_SUDO, False)
        self._sudo = self._sudo if self._sudo else False
        self._on_behalf_user = self.context.get(RUNNER_ON_BEHALF_USER, self._on_behalf_user)
        self._cwd = self.runner_parameters.get(RUNNER_CWD, None)
        self._env = self.runner_parameters.get(RUNNER_ENV, {})
        self._kwarg_op = self.runner_parameters.get(RUNNER_KWARG_OP, '--')
        self._timeout = self.runner_parameters.get(RUNNER_TIMEOUT,
                                                   REMOTE_RUNNER_DEFAULT_ACTION_TIMEOUT)
        self._bastion_host = self.runner_parameters.get(RUNNER_BASTION_HOST, None)

        LOG.info('[BaseParallelSSHRunner="%s", liveaction_id="%s"] Finished pre_run.',
                 self.runner_id, self.liveaction_id)

        concurrency = int(len(self._hosts) / 3) + 1 if self._parallel else 1
        if concurrency > self._max_concurrency:
            LOG.debug('Limiting parallel SSH concurrency to %d.', concurrency)
            concurrency = self._max_concurrency

        client_kwargs = {
            'hosts': self._hosts,
            'user': self._username,
            'port': self._ssh_port,
            'concurrency': concurrency,
            'bastion_host': self._bastion_host,
            'raise_on_any_error': False,
            'connect': True
        }

        if self._password:
            client_kwargs['password'] = self._password
        elif self._private_key:
            # Determine if the private_key is a path to the key file or the raw key material
            is_key_material = self._is_private_key_material(private_key=self._private_key)

            if is_key_material:
                # Raw key material
                client_kwargs['pkey_material'] = self._private_key
            else:
                # Assume it's a path to the key file, verify the file exists
                client_kwargs['pkey_file'] = self._private_key

            if self._passphrase:
                client_kwargs['passphrase'] = self._passphrase
        else:
            # Default to stanley key file specified in the config
            client_kwargs['pkey_file'] = self._ssh_key_file

        self._parallel_ssh_client = ParallelSSHClient(**client_kwargs)

    def _is_private_key_material(self, private_key):
        return private_key and REMOTE_RUNNER_PRIVATE_KEY_HEADER in private_key.lower()

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

        if 'error' in result and 'traceback' in result:
            # Assume this is a global failure where the result dictionary doesn't contain entry
            # per host
            timeout = False
            success = result.get('succeeded', False)
            status = BaseParallelSSHRunner._get_status_for_success_and_timeout(success=success,
                                                                               timeout=timeout)
            return status

        success = not allow_partial_failure
        timeout = True

        for r in six.itervalues(result):
            r_succeess = r.get('succeeded', False) if r else False
            r_timeout = r.get('timeout', False) if r else False

            timeout &= r_timeout

            if allow_partial_failure:
                success |= r_succeess
                if success:
                    break
            else:
                success &= r_succeess
                if not success:
                    break

        status = BaseParallelSSHRunner._get_status_for_success_and_timeout(success=success,
                                                                           timeout=timeout)

        return status

    @staticmethod
    def _get_status_for_success_and_timeout(success, timeout):
        if success:
            status = LIVEACTION_STATUS_SUCCEEDED
        elif timeout:
            # Note: Right now we only set status to timeout if all the hosts have timed out
            status = LIVEACTION_STATUS_TIMED_OUT
        else:
            status = LIVEACTION_STATUS_FAILED
        return status

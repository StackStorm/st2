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

from fabric.api import (env, execute)
from oslo.config import cfg
import six

from st2actions.runners import ActionRunner
from st2actions.runners import ShellRunnerMixin
from st2common import log as logging
from st2common.exceptions.actionrunner import ActionRunnerPreRunError
from st2common.exceptions.fabricrunner import FabricExecutionFailureException
from st2common.constants.action import LIVEACTION_STATUS_SUCCEEDED, LIVEACTION_STATUS_FAILED
from st2common.constants.runners import FABRIC_RUNNER_DEFAULT_ACTION_TIMEOUT
from st2common.models.system.action import (FabricRemoteAction, FabricRemoteScriptAction)

# Replace with container call to get logger.
LOG = logging.getLogger(__name__)


# Fabric environment level settings.
# XXX: Note fabric env is a global singleton.
env.parallel = True  # By default, execute things in parallel. Uses multiprocessing under the hood.
env.user = cfg.CONF.system_user.user
ssh_key_file = cfg.CONF.system_user.ssh_key_file

if ssh_key_file:
    ssh_key_file = os.path.expanduser(ssh_key_file)

if ssh_key_file and os.path.exists(ssh_key_file):
    env.key_filename = ssh_key_file

env.timeout = 10  # Timeout for connections (in seconds)
env.command_timeout = FABRIC_RUNNER_DEFAULT_ACTION_TIMEOUT  # timeout for commands (in seconds)
env.combine_stderr = False
env.group = 'staff'
env.abort_exception = FabricExecutionFailureException

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


def get_runner():
    return FabricRunner(str(uuid.uuid4()))


class FabricRunner(ActionRunner, ShellRunnerMixin):
    def __init__(self, runner_id):
        super(FabricRunner, self).__init__(runner_id=runner_id)
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

    def pre_run(self):
        LOG.debug('Entering FabricRunner.pre_run() for liveaction_id="%s"',
                  self.liveaction_id)
        LOG.debug('    runner_parameters = %s', self.runner_parameters)
        hosts = self.runner_parameters.get(RUNNER_HOSTS, '').split(',')
        self._hosts = [h.strip() for h in hosts if len(h) > 0]
        if len(self._hosts) < 1:
            raise ActionRunnerPreRunError('No hosts specified to run action for action %s.',
                                          self.liveaction_id)
        self._username = self.runner_parameters.get(RUNNER_USERNAME, cfg.CONF.system_user.user)
        self._username = self._username or cfg.CONF.system_user.user
        self._password = self.runner_parameters.get(RUNNER_PASSWORD, None)
        self._private_key = self.runner_parameters.get(RUNNER_PRIVATE_KEY, None)
        self._parallel = self.runner_parameters.get(RUNNER_PARALLEL, True)
        self._sudo = self.runner_parameters.get(RUNNER_SUDO, False)
        self._sudo = self._sudo if self._sudo else False
        self._on_behalf_user = self.context.get(RUNNER_ON_BEHALF_USER, env.user)
        self._cwd = self.runner_parameters.get(RUNNER_CWD, None)
        self._env = self.runner_parameters.get(RUNNER_ENV, {})
        self._kwarg_op = self.runner_parameters.get(RUNNER_KWARG_OP, '--')
        self._timeout = self.runner_parameters.get(RUNNER_TIMEOUT,
                                                   FABRIC_RUNNER_DEFAULT_ACTION_TIMEOUT)

        LOG.info('[FabricRunner="%s", liveaction_id="%s"] Finished pre_run.',
                 self.runner_id, self.liveaction_id)

    def run(self, action_parameters):
        LOG.debug('    action_parameters = %s', action_parameters)

        runner_type = self.action.runner_type['name']

        if runner_type == 'run-remote-script':
            remote_action = self._get_fabric_remote_script_action(action_parameters)
        elif runner_type == 'run-remote':
            remote_action = self._get_fabric_remote_action(action_parameters)
        else:
            raise Exception('Invalid runner: %s' % (runner_type))

        LOG.debug('Will execute remote_action : %s.', str(remote_action))
        result = self._run(remote_action)
        LOG.debug('Executed remote_action : %s. Result is : %s.', remote_action, result)
        status = FabricRunner._get_result_status(
            result, cfg.CONF.ssh_runner.allow_partial_failure)

        # TODO (manas) : figure out the right boolean representation.
        self._log_action_completion(logger=LOG, result=result, status=status)
        return (status, result, None)

    def _run(self, remote_action):
        LOG.info('Executing action via FabricRunner :%s for user: %s.',
                 self.runner_id, remote_action.get_on_behalf_user())
        LOG.info(('[Action info] name: %s, Id: %s, command: %s, on behalf user: %s, '
                  'actual user: %s, sudo: %s'),
                 remote_action.name, remote_action.action_exec_id, remote_action.get_command(),
                 remote_action.get_on_behalf_user(), remote_action.get_user(),
                 remote_action.is_sudo())
        results = execute(remote_action.get_fabric_task(), hosts=remote_action.hosts)
        return results

    def _get_fabric_remote_action(self, action_paramaters):
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

    def _get_fabric_remote_script_action(self, action_parameters):
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

    def _get_env_vars(self):
        """
        :rtype: ``dict``
        """
        env_vars = {}

        if self.auth_token:
            env_vars['st2_auth_token'] = self.auth_token.token

        if self._env:
            env_vars.update(self._env)

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


# XXX: Write proper tests.
if __name__ == '__main__':

    print('!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!')
    print('!!!!!!!!!!!!!!!!!!!!! NORMAL CMD !!!!!!!!!!!!!!!!!!!!!!!!!!')
    print('!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!')
    runner = FabricRunner(str(uuid.uuid4()))
    remote_action = FabricRemoteAction('UNAME', 'action_exec_id' + str(uuid.uuid4()), 'uname -a',
                                       'narcissist', 'stanley', hosts=['54.191.85.86',
                                       '54.191.17.38', '54.200.102.55'])
    print(str(remote_action))
    results = runner._run(remote_action)

    print('!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!')
    print('!!!!!!!!!!!!!!!!!!!!! RESULTS !!!!!!!!!!!!!!!!!!!!!!!!!!!!!')
    print('!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!')

    print(results)

    print('!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!')
    print('!!!!!!!!!!!!!!!!!!!!! SUDO CMD !!!!!!!!!!!!!!!!!!!!!!!!!!')
    print('!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!')
    runner = FabricRunner(str(uuid.uuid4()))
    remote_action = FabricRemoteAction('UNAME', 'action_exec_id' + str(uuid.uuid4()), 'uname -a',
                                       'narcissist', 'stanley', hosts=['54.191.85.86',
                                       '54.191.17.38', '54.200.102.55'], parallel=True, sudo=True)
    results = runner._run(remote_action)

    print('!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!')
    print('!!!!!!!!!!!!!!!!!!!!! RESULTS !!!!!!!!!!!!!!!!!!!!!!!!!!!!!')
    print('!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!')

    print(results)

    print('!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!')
    print('!!!!!!!!!!!!!!!!!!!!! SCRIPT DAWG !!!!!!!!!!!!!!!!!!!!!!!!!!!')
    print('!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!')
    script_action = FabricRemoteScriptAction('UNAME', 'action_exec_id' + str(uuid.uuid4()),
                                             '/tmp/ls-script.sh', named_args={},
                                             positional_args='/tmp', on_behalf_user='narcissist',
                                             user='stanley', hosts=['54.191.85.86'],
                                             parallel=True, sudo=False)
    results = runner._run(script_action)

    print('!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!')
    print('!!!!!!!!!!!!!!!!!!!!! RESULTS !!!!!!!!!!!!!!!!!!!!!!!!!!!!!')
    print('!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!')

    print(results)

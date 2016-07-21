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
import pwd
import uuid

from oslo_config import cfg
from eventlet.green import subprocess

from st2common import log as logging
from st2actions.runners import ActionRunner
from st2actions.runners import ShellRunnerMixin
from st2common.models.system.action import ShellCommandAction
from st2common.models.system.action import ShellScriptAction
from st2common.constants.action import LIVEACTION_STATUS_SUCCEEDED
from st2common.constants.action import LIVEACTION_STATUS_FAILED
from st2common.constants.action import LIVEACTION_STATUS_TIMED_OUT
from st2common.constants.runners import LOCAL_RUNNER_DEFAULT_ACTION_TIMEOUT
from st2common.util.misc import strip_shell_chars
from st2common.util.green.shell import run_command
from st2common.util.shell import kill_process
import st2common.util.jsonify as jsonify

__all__ = [
    'get_runner'
]

LOG = logging.getLogger(__name__)

DEFAULT_KWARG_OP = '--'
LOGGED_USER_USERNAME = pwd.getpwuid(os.getuid())[0]

# constants to lookup in runner_parameters.
RUNNER_SUDO = 'sudo'
RUNNER_ON_BEHALF_USER = 'user'
RUNNER_COMMAND = 'cmd'
RUNNER_CWD = 'cwd'
RUNNER_ENV = 'env'
RUNNER_KWARG_OP = 'kwarg_op'
RUNNER_TIMEOUT = 'timeout'


def get_runner():
    return LocalShellRunner(str(uuid.uuid4()))


class LocalShellRunner(ActionRunner, ShellRunnerMixin):
    """
    Runner which executes actions locally using the user under which the action runner service is
    running or under the provided user.

    Note: The user under which the action runner service is running (stanley user by default) needs
    to have pasworless sudo access set up.
    """
    KEYS_TO_TRANSFORM = ['stdout', 'stderr']

    def __init__(self, runner_id):
        super(LocalShellRunner, self).__init__(runner_id=runner_id)

    def pre_run(self):
        super(LocalShellRunner, self).pre_run()

        self._sudo = self.runner_parameters.get(RUNNER_SUDO, False)
        self._on_behalf_user = self.context.get(RUNNER_ON_BEHALF_USER, LOGGED_USER_USERNAME)
        self._user = cfg.CONF.system_user.user
        self._cwd = self.runner_parameters.get(RUNNER_CWD, None)
        self._env = self.runner_parameters.get(RUNNER_ENV, {})
        self._env = self._env or {}
        self._kwarg_op = self.runner_parameters.get(RUNNER_KWARG_OP, DEFAULT_KWARG_OP)
        self._timeout = self.runner_parameters.get(RUNNER_TIMEOUT,
                                                   LOCAL_RUNNER_DEFAULT_ACTION_TIMEOUT)

    def run(self, action_parameters):
        env_vars = self._env

        if not self.entry_point:
            script_action = False
            command = self.runner_parameters.get(RUNNER_COMMAND, None)
            action = ShellCommandAction(name=self.action_name,
                                        action_exec_id=str(self.liveaction_id),
                                        command=command,
                                        user=self._user,
                                        env_vars=env_vars,
                                        sudo=self._sudo,
                                        timeout=self._timeout)
        else:
            script_action = True
            script_local_path_abs = self.entry_point
            positional_args, named_args = self._get_script_args(action_parameters)
            named_args = self._transform_named_args(named_args)

            action = ShellScriptAction(name=self.action_name,
                                       action_exec_id=str(self.liveaction_id),
                                       script_local_path_abs=script_local_path_abs,
                                       named_args=named_args,
                                       positional_args=positional_args,
                                       user=self._user,
                                       env_vars=env_vars,
                                       sudo=self._sudo,
                                       timeout=self._timeout,
                                       cwd=self._cwd)

        args = action.get_full_command_string()

        # For consistency with the old Fabric based runner, make sure the file is executable
        if script_action:
            args = 'chmod +x %s ; %s' % (script_local_path_abs, args)

        env = os.environ.copy()

        # Include user provided env vars (if any)
        env.update(env_vars)

        # Include common st2 env vars
        st2_env_vars = self._get_common_action_env_variables()
        env.update(st2_env_vars)

        LOG.info('Executing action via LocalRunner: %s', self.runner_id)
        LOG.info('[Action info] name: %s, Id: %s, command: %s, user: %s, sudo: %s' %
                 (action.name, action.action_exec_id, args, action.user, action.sudo))

        # Make sure os.setsid is called on each spawned process so that all processes
        # are in the same group.

        # Process is started as sudo -u {{system_user}} -- bash -c {{command}}. Introduction of the
        # bash means that multiple independent processes are spawned without them being
        # children of the process we have access to and this requires use of pkill.
        # Ideally os.killpg should have done the trick but for some reason that failed.
        # Note: pkill will set the returncode to 143 so we don't need to explicitly set
        # it to some non-zero value.
        exit_code, stdout, stderr, timed_out = run_command(cmd=args, stdin=None,
                                                           stdout=subprocess.PIPE,
                                                           stderr=subprocess.PIPE,
                                                           shell=True,
                                                           cwd=self._cwd,
                                                           env=env,
                                                           timeout=self._timeout,
                                                           preexec_func=os.setsid,
                                                           kill_func=kill_process)

        error = None

        if timed_out:
            error = 'Action failed to complete in %s seconds' % (self._timeout)
            exit_code = -9

        succeeded = (exit_code == 0)

        result = {
            'failed': not succeeded,
            'succeeded': succeeded,
            'return_code': exit_code,
            'stdout': strip_shell_chars(stdout),
            'stderr': strip_shell_chars(stderr)
        }

        if error:
            result['error'] = error

        if exit_code == 0:
            status = LIVEACTION_STATUS_SUCCEEDED
        elif timed_out:
            status = LIVEACTION_STATUS_TIMED_OUT
        else:
            status = LIVEACTION_STATUS_FAILED

        return (status, jsonify.json_loads(result, LocalShellRunner.KEYS_TO_TRANSFORM), None)

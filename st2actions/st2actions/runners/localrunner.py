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

from oslo.config import cfg
from eventlet.green import subprocess

from st2common import log as logging
from st2actions.runners import ActionRunner
from st2actions.runners import ShellRunnerMixin
from st2common.models.system.action import ShellCommandAction
from st2common.models.system.action import ShellScriptAction
from st2common.constants.action import ACTIONEXEC_STATUS_SUCCEEDED
from st2common.constants.action import ACTIONEXEC_STATUS_FAILED

__all__ = [
    'get_runner'
]

LOG = logging.getLogger(__name__)

DEFAULT_ACTION_TIMEOUT = 60
LOGGED_USER_USERNAME = pwd.getpwuid(os.getuid())[0]

# constants to lookup in runner_parameters.
RUNNER_SUDO = 'sudo'
RUNNER_ON_BEHALF_USER = 'user'
RUNNER_COMMAND = 'cmd'
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

    def __init__(self, runner_id):
        super(LocalShellRunner, self).__init__(runner_id=runner_id)

    def pre_run(self):
        self._sudo = self.runner_parameters.get(RUNNER_SUDO, False)
        self._on_behalf_user = self.context.get(RUNNER_ON_BEHALF_USER, LOGGED_USER_USERNAME)
        self._user = cfg.CONF.system_user.user
        self._kwarg_op = self.runner_parameters.get(RUNNER_KWARG_OP, '--')
        self._timeout = self.runner_parameters.get(RUNNER_TIMEOUT, DEFAULT_ACTION_TIMEOUT)

    def run(self, action_parameters):
        LOG.debug('    action_parameters = %s', action_parameters)

        if not self.entry_point:
            script_action = False
            command = self.runner_parameters.get(RUNNER_COMMAND, None)
            action = ShellCommandAction(name=self.action_name,
                                        action_exec_id=str(self.action_execution_id),
                                        command=command,
                                        user=self._user,
                                        env_vars={},
                                        sudo=self._sudo,
                                        timeout=self._timeout)
        else:
            script_action = True
            script_local_path_abs = self.entry_point
            positional_args, named_args = self._get_script_args(action_parameters)
            named_args = self._transform_named_args(named_args)

            action = ShellScriptAction(name=self.action_name,
                                       action_exec_id=str(self.action_execution_id),
                                       script_local_path_abs=script_local_path_abs,
                                       named_args=named_args,
                                       positional_args=positional_args,
                                       user=self._user,
                                       env_vars={},
                                       sudo=self._sudo,
                                       timeout=self._timeout)

        args = action.get_full_command_string()

        # For consistency with the old Fabric based runner, make sure the file is executable
        if script_action:
            args = 'chmod +x %s ; %s' % (script_local_path_abs, args)

        env = os.environ.copy()
        process = subprocess.Popen(args=args, stdin=None, stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE, shell=True, env=env)

        try:
            exit_code = process.wait(timeout=self._timeout)
        except subprocess.TimeoutExpired:
            # Action has timed out, kill the process and propagate the error
            # Note: process.kill() will set the returncode to -9 so we don't
            # need to explicitly set it to some non-zero value
            process.kill()
            error = 'Action failed to complete in %s seconds' % (self._timeout)
        else:
            error = None

        stdout, stderr = process.communicate()
        exit_code = process.returncode
        succeeded = (exit_code == 0)

        result = {
            'failed': not succeeded,
            'succeeded': succeeded,
            'return_code': exit_code,
            'stdout': stdout,
            'stderr': stderr
        }

        if error:
            result['localhost']['error'] = error

        status = ACTIONEXEC_STATUS_SUCCEEDED if exit_code == 0 else ACTIONEXEC_STATUS_FAILED
        self.container_service.report_result(result)
        self.container_service.report_status(status)
        return result is not None

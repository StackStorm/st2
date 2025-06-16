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

import os
import re
import abc
import pwd
import functools

import six
from oslo_config import cfg
from six.moves import StringIO

from st2common.constants import action as action_constants
from st2common.constants import exit_codes as exit_code_constants
from st2common.constants import runners as runner_constants
from st2common import log as logging
from st2common.runners.base import ActionRunner
from st2common.runners.base import ShellRunnerMixin
from st2common.util.misc import strip_shell_chars
from st2common.util.green import shell
from st2common.util.shell import kill_process
from st2common.util import jsonify
from st2common.util import concurrency
from st2common.services.action import store_execution_output_data
from st2common.runners.utils import make_read_and_store_stream_func

__all__ = ["BaseLocalShellRunner", "RUNNER_COMMAND"]

LOG = logging.getLogger(__name__)

DEFAULT_KWARG_OP = "--"
LOGGED_USER_USERNAME = pwd.getpwuid(os.getuid())[0]

# constants to lookup in runner_parameters.
RUNNER_SUDO = "sudo"
RUNNER_SUDO_PASSWORD = "sudo_password"
RUNNER_ON_BEHALF_USER = "user"
RUNNER_COMMAND = "cmd"
RUNNER_CWD = "cwd"
RUNNER_ENV = "env"
RUNNER_KWARG_OP = "kwarg_op"
RUNNER_TIMEOUT = "timeout"

PROC_EXIT_CODE_TO_LIVEACTION_STATUS_MAP = {
    str(
        exit_code_constants.SUCCESS_EXIT_CODE
    ): action_constants.LIVEACTION_STATUS_SUCCEEDED,
    str(
        exit_code_constants.FAILURE_EXIT_CODE
    ): action_constants.LIVEACTION_STATUS_FAILED,
    str(
        -1 * exit_code_constants.SIGKILL_EXIT_CODE
    ): action_constants.LIVEACTION_STATUS_TIMED_OUT,
    str(
        -1 * exit_code_constants.SIGTERM_EXIT_CODE
    ): action_constants.LIVEACTION_STATUS_ABANDONED,
}


@six.add_metaclass(abc.ABCMeta)
class BaseLocalShellRunner(ActionRunner, ShellRunnerMixin):
    """
    Runner which executes actions locally using the user under which the action runner service is
    running or under the provided user.

    Note: The user under which the action runner service is running (stanley user by default) needs
    to have pasworless sudo access set up.
    """

    KEYS_TO_TRANSFORM = ["stdout", "stderr"]

    def __init__(self, runner_id):
        super(BaseLocalShellRunner, self).__init__(runner_id=runner_id)

    def pre_run(self):
        super(BaseLocalShellRunner, self).pre_run()

        self._sudo = self.runner_parameters.get(RUNNER_SUDO, False)
        self._sudo_password = self.runner_parameters.get(RUNNER_SUDO_PASSWORD, None)
        self._on_behalf_user = self.context.get(
            RUNNER_ON_BEHALF_USER, LOGGED_USER_USERNAME
        )
        self._user = cfg.CONF.system_user.user
        self._cwd = self.runner_parameters.get(RUNNER_CWD, None)
        self._env = self.runner_parameters.get(RUNNER_ENV, {})
        self._env = self._env or {}
        self._kwarg_op = self.runner_parameters.get(RUNNER_KWARG_OP, DEFAULT_KWARG_OP)
        self._timeout = self.runner_parameters.get(
            RUNNER_TIMEOUT, runner_constants.LOCAL_RUNNER_DEFAULT_ACTION_TIMEOUT
        )

    def _run(self, action):
        env_vars = self._env

        if not self.entry_point:
            script_action = False
        else:
            script_action = True

        args = action.get_full_command_string()
        sanitized_args = action.get_sanitized_full_command_string()

        # For consistency with the old Fabric based runner, make sure the file is executable
        # Also check to ensure not Read-only file system
        if script_action and not bool(
            os.statvfs(self.entry_point).f_flag & os.ST_RDONLY
        ):
            script_local_path_abs = self.entry_point
            args = "chmod +x %s ; %s" % (script_local_path_abs, args)
            sanitized_args = "chmod +x %s ; %s" % (
                script_local_path_abs,
                sanitized_args,
            )

        env = os.environ.copy()

        # Include user provided env vars (if any)
        env.update(env_vars)

        # Include common st2 env vars
        st2_env_vars = self._get_common_action_env_variables()
        env.update(st2_env_vars)

        LOG.info("Executing action via LocalRunner: %s", self.runner_id)
        LOG.info(
            "[Action info] name: %s, Id: %s, command: %s, user: %s, sudo: %s"
            % (
                action.name,
                action.action_exec_id,
                sanitized_args,
                action.user,
                action.sudo,
            )
        )

        stdout = StringIO()
        stderr = StringIO()

        store_execution_stdout_line = functools.partial(
            store_execution_output_data, output_type="stdout"
        )
        store_execution_stderr_line = functools.partial(
            store_execution_output_data, output_type="stderr"
        )

        read_and_store_stdout = make_read_and_store_stream_func(
            execution_db=self.execution,
            action_db=self.action,
            store_data_func=store_execution_stdout_line,
        )
        read_and_store_stderr = make_read_and_store_stream_func(
            execution_db=self.execution,
            action_db=self.action,
            store_data_func=store_execution_stderr_line,
        )

        subprocess = concurrency.get_subprocess_module()

        # If sudo password is provided, pass it to the subprocess via stdin>
        # Note: We don't need to explicitly escape the argument because we pass command as a list
        # to subprocess.Popen and all the arguments are escaped by the function.
        if self._sudo_password:
            LOG.debug("Supplying sudo password via stdin")
            echo_process = concurrency.subprocess_popen(
                ["echo", self._sudo_password + "\n"], stdout=subprocess.PIPE
            )
            stdin = echo_process.stdout
        else:
            stdin = None

        # Make sure os.setsid is called on each spawned process so that all processes
        # are in the same group.

        # Process is started as sudo -u {{system_user}} -- bash -c {{command}}. Introduction of the
        # bash means that multiple independent processes are spawned without them being
        # children of the process we have access to and this requires use of pkill.
        # Ideally os.killpg should have done the trick but for some reason that failed.
        # Note: pkill will set the returncode to 143 so we don't need to explicitly set
        # it to some non-zero value.
        exit_code, stdout, stderr, timed_out = shell.run_command(
            cmd=args,
            stdin=stdin,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            shell=True,
            cwd=self._cwd,
            env=env,
            timeout=self._timeout,
            preexec_func=os.setsid,
            kill_func=kill_process,
            read_stdout_func=read_and_store_stdout,
            read_stderr_func=read_and_store_stderr,
            read_stdout_buffer=stdout,
            read_stderr_buffer=stderr,
        )

        error = None

        if timed_out:
            error = "Action failed to complete in %s seconds" % (self._timeout)
            exit_code = -1 * exit_code_constants.SIGKILL_EXIT_CODE

        # Detect if user provided an invalid sudo password or sudo is not configured for that user
        if self._sudo_password:
            if re.search(r"sudo: \d+ incorrect password attempts", stderr):
                match = re.search(r"\[sudo\] password for (.+?)\:", stderr)

                if match:
                    username = match.groups()[0]
                else:
                    username = "unknown"

                error = (
                    "Invalid sudo password provided or sudo is not configured for this user "
                    "(%s)" % (username)
                )
                exit_code = -1

        succeeded = exit_code == exit_code_constants.SUCCESS_EXIT_CODE

        result = {
            "failed": not succeeded,
            "succeeded": succeeded,
            "return_code": exit_code,
            "stdout": strip_shell_chars(stdout),
            "stderr": strip_shell_chars(stderr),
        }

        if error:
            result["error"] = error

        status = PROC_EXIT_CODE_TO_LIVEACTION_STATUS_MAP.get(
            str(exit_code), action_constants.LIVEACTION_STATUS_FAILED
        )

        return (
            status,
            jsonify.json_loads(result, BaseLocalShellRunner.KEYS_TO_TRANSFORM),
            None,
        )

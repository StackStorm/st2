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
from os.path import basename
import sys
import json
import uuid
from subprocess import list2cmdline

from eventlet.green import subprocess

from st2common import log as logging
from st2common.runners.base import ActionRunner
from st2common.util.green.shell import run_command
from st2common.constants.action import ACTION_OUTPUT_RESULT_DELIMITER
from st2common.constants.action import LIVEACTION_STATUS_SUCCEEDED
from st2common.constants.action import LIVEACTION_STATUS_FAILED
from st2common.constants.action import LIVEACTION_STATUS_TIMED_OUT
from st2common.constants.runners import GO_RUNNER_INVALID_ACTION_STATUS_EXIT_CODE
# from st2common.constants.error_messages import PACK_VIRTUALENV_DOESNT_EXIST
from st2common.constants.runners import GO_RUNNER_DEFAULT_ACTION_TIMEOUT
from st2common.constants.system import API_URL_ENV_VARIABLE_NAME
from st2common.constants.system import AUTH_TOKEN_ENV_VARIABLE_NAME
from st2common.util.api import get_full_public_api_url
# from st2common.util.sandboxing import get_sandbox_path
# from st2common.util.sandboxing import get_sandbox_python_path
# from st2common.util.sandboxing import get_sandbox_python_binary_path
# from st2common.util.sandboxing import get_sandbox_virtualenv_path
from st2common.runners import python_action_wrapper

LOG = logging.getLogger(__name__)

__all__ = [
    'get_runner',
    'GoRunner',
]

# constants to lookup in runner_parameters.
RUNNER_ENV = 'env'
RUNNER_TIMEOUT = 'timeout'

# Environment variables which can't be specified by the user
BLACKLISTED_ENV_VARS = [
    # TODO(mierdin): Consider GOPATH, etc
]

BASE_DIR = os.path.dirname(os.path.abspath(python_action_wrapper.__file__))
WRAPPER_SCRIPT_NAME = 'python_action_wrapper.py'
WRAPPER_SCRIPT_PATH = os.path.join(BASE_DIR, WRAPPER_SCRIPT_NAME)


def get_runner():
    'RunnerTestCase',
    return GoRunner(str(uuid.uuid4()))


class GoRunner(ActionRunner):

    def __init__(self, runner_id, timeout=GO_RUNNER_DEFAULT_ACTION_TIMEOUT):
        """
        :param timeout: Action execution timeout in seconds.
        :type timeout: ``int``
        """
        super(GoRunner, self).__init__(runner_id=runner_id)
        self._timeout = timeout

    def pre_run(self):
        super(GoRunner, self).pre_run()

        # TODO :This is awful, but the way "runner_parameters" and other variables get
        # assigned on the runner instance is even worse. Those arguments should
        # be passed to the constructor.
        self._env = self.runner_parameters.get(RUNNER_ENV, {})
        self._timeout = self.runner_parameters.get(RUNNER_TIMEOUT, self._timeout)

        LOG.debug("Checking if Go is installed")
        try:
            args = [
                "go",
                "--version"
            ]
            exit_code, stdout, stderr, timed_out = run_command(cmd=args, stdout=subprocess.PIPE,
                                                               stderr=subprocess.PIPE, shell=False,
                                                               env=self._env, timeout=self._timeout)
        except Exception:

            error_msg = "Error checking that Go is installed. Please ensure a valid Go " \
                        "installation exists on the system and is present in the PATH"

            LOG.error(error_msg)
            raise Exception(error_msg)

        #TODO(mierdin): Add directory to GOPATH seamlessly 
        #export GOPATH=$GOPATH:$(pwd)/actions

        #You will also need to add the resulting bin/ directory to path, or refer to it directly

        LOG.debug('Checking entry_point')
        if not self.entry_point:
            # /opt/stackstorm/packs/influxdb/actions/go_example.go
            error_msg = 'Action "%s" is missing entry_point attribute' % (self.action.name)
            LOG.error(error_msg)
            raise Exception(error_msg)
        LOG.debug('entry_point is %s' % self.entry_point)

        # User has structured project in "go gettable" format. Respect this.
        #
        # TODO(mierdin): This isn't the most attractive way of detecting this choice. However,
        # because of the necessary precautions in st2/st2common/st2common/content/utils.py,
        # function "get_pack_file_abs_path", an exact file must be provided to the entry_point
        # field in action metadata.
        #
        # This means, if we have a "go get" style structure in place, the path we must use (if
        # we are to know which binary this action intends to use) must look like this:
        #
        # src/vendor_example/cmd/print_cyan/main.go
        #
        # It might be worth revisiting this - as this is obviously not ideal UX, but I can deal
        # with it for the sake of getting a PoC out there for this runner.
        if self.entry_point[-8:] == "/main.go":
            entry_parent = os.path.abspath(os.path.dirname(self.entry_point) + "/..")

            # LOG.debug("entry_parent - %s" % entry_parent)

            env = os.environ.copy()
            LOG.debug("GOPATH - %s" % env['GOPATH'])

            if entry_parent.split("/")[-1] != "cmd":
                error_msg = "Go project not structured correctly - cannot compile"
                LOG.error(error_msg)
                raise Exception(error_msg)

            install_param = entry_parent + "/..."
            self.binary_name = os.path.dirname(self.entry_point).split("/")[-1]

        # Treat the entry point as a random script - compile this file directly
        else:
            install_param = self.entry_point
            self.binary_name = os.path.splitext(basename(self.entry_point))[0]

        LOG.debug("Compiling program")
        try:
            args = [
                "go",
                "install",
                install_param
            ]
            LOG.debug("Running command '%s'" % " ".join(args))
            exit_code, stdout, stderr, timed_out = run_command(cmd=args, stdout=subprocess.PIPE,
                                                               stderr=subprocess.PIPE, shell=False,
                                                               env=self._env, timeout=self._timeout)
        except Exception:
            error_msg = "Error compiling action. Please ensure your program can compile and has access to its dependencies."
            LOG.error(error_msg)
            raise Exception(error_msg)

        # TODO handle (virtualenv)vagrant@st2dev:~/st2$ go install /opt/stackstorm/packs/goexamples/actions/src/vendor_example/cmd/...
        # warning: "/opt/stackstorm/packs/goexamples/actions/src/vendor_example/cmd/..." matched no packages

        if exit_code != 0:
            error_msg = "Error compiling action. Please ensure your program can compile and has access to its dependencies."
            LOG.error(error_msg)
            raise Exception(error_msg)

        LOG.exception("Compiled successfully. Binary name is %s" % self.binary_name)

    def run(self, action_parameters):
        """Run the compiled Go action

        All "go" stuff should be done at this point. At this point we should have a compiled
        binary ready to work with.
        """

        LOG.debug('Running action via Go runner.')

        pack = self.get_pack_name()
        LOG.debug('Retrieved pack name - %s' % pack)

        user = self.get_user()
        LOG.debug('Retrieved user - %s' % user)

        serialized_parameters = json.dumps(action_parameters) if action_parameters else ''
        LOG.debug('Serializing parameters - %s' % serialized_parameters)

        try:

            args = [
                self.binary_name
            ]

            exit_code, stdout, stderr, timed_out = run_command(cmd=args, stdout=subprocess.PIPE,
                                                               stderr=subprocess.PIPE, shell=False,
                                                               env=self._env, timeout=self._timeout)

        except Exception:
            error_msg = "Error running Go action."
            LOG.error(error_msg)
            raise

        if exit_code != 0:
            LOG.error(stderr)
            raise Exception("Go action returned with error")

        # Potentially useful stuff from python runner, keeping here for quick reference
        #
        # LOG.debug('Setting args.')
        # args = [
        #     python_path,
        #     WRAPPER_SCRIPT_PATH,
        #     '--pack=%s' % (pack),
        #     '--file-path=%s' % (self.entry_point),
        #     '--parameters=%s' % (serialized_parameters),
        #     '--user=%s' % (user),
        #     '--parent-args=%s' % (json.dumps(sys.argv[1:]))
        # ]

        # # We need to ensure all the st2 dependencies are also available to the
        # # subprocess
        # LOG.debug('Setting env.')
        # env = os.environ.copy()
        # env['PATH'] = get_sandbox_path(virtualenv_path=virtualenv_path)
        # env['PYTHONPATH'] = get_sandbox_python_path(inherit_from_parent=True,
        #                                             inherit_parent_virtualenv=True)

        # # Include user provided environment variables (if any)
        # user_env_vars = self._get_env_vars()
        # env.update(user_env_vars)

        # # Include common st2 environment variables
        # st2_env_vars = self._get_common_action_env_variables()
        # env.update(st2_env_vars)
        # datastore_env_vars = self._get_datastore_access_env_vars()
        # env.update(datastore_env_vars)

        # command_string = list2cmdline(args)
        # LOG.debug('Running command: PATH=%s PYTHONPATH=%s %s' % (env['PATH'], env['PYTHONPATH'],
        #                                                          command_string))
        # exit_code, stdout, stderr, timed_out = run_command(cmd=args, stdout=subprocess.PIPE,
        #                                                    stderr=subprocess.PIPE, shell=False,
        #                                                    env=env, timeout=self._timeout)
        # LOG.debug('Returning values: %s, %s, %s, %s' % (exit_code, stdout, stderr, timed_out))
        # LOG.debug('Returning.')

        return self._get_output_values(exit_code, stdout, stderr, timed_out)




        # return self._get_output_values(0, "", "", False)

    def _get_output_values(self, exit_code, stdout, stderr, timed_out):
        """
        Return sanitized output values.

        :return: Tuple with status, output and None

        :rtype: ``tuple``
        """
        if timed_out:
            error = 'Action failed to complete in %s seconds' % (self._timeout)
        else:
            error = None

        if exit_code == GO_RUNNER_INVALID_ACTION_STATUS_EXIT_CODE:
            # TODO: Mark as failed instead
            raise ValueError(stderr)

        if ACTION_OUTPUT_RESULT_DELIMITER in stdout:
            split = stdout.split(ACTION_OUTPUT_RESULT_DELIMITER)
            assert len(split) == 3
            action_result = split[1].strip()
            stdout = split[0] + split[2]
        else:
            action_result = None

        # Parse the serialized action result object
        try:
            action_result = json.loads(action_result)
        except:
            pass

        if action_result and isinstance(action_result, dict):
            result = action_result.get('result', None)
            status = action_result.get('status', None)
        else:
            result = 'None'
            status = None

        output = {
            'stdout': stdout,
            'stderr': stderr,
            'exit_code': exit_code,
            'result': result
        }

        if error:
            output['error'] = error

        status = self._get_final_status(action_status=status, timed_out=timed_out,
                                        exit_code=exit_code)
        return (status, output, None)

    def _get_final_status(self, action_status, timed_out, exit_code):
        """
        Return final status based on action's status, time out value and
        exit code. Example: succeeded, failed, timeout.

        :return: status

        :rtype: ``str``
        """
        if action_status is not None:
            if exit_code == 0 and action_status is True:
                status = LIVEACTION_STATUS_SUCCEEDED
            elif exit_code == 0 and action_status is False:
                status = LIVEACTION_STATUS_FAILED
            else:
                status = LIVEACTION_STATUS_FAILED
        else:
            if exit_code == 0:
                status = LIVEACTION_STATUS_SUCCEEDED
            else:
                status = LIVEACTION_STATUS_FAILED

        if timed_out:
            status = LIVEACTION_STATUS_TIMED_OUT

        return status

    def _get_env_vars(self):
        """
        Return sanitized environment variables which will be used when launching
        a subprocess.

        :rtype: ``dict``
        """
        env_vars = {}

        if self._env:
            env_vars.update(self._env)

        # Remove "blacklisted" environment variables
        to_delete = []
        for key, value in env_vars.items():
            if key.lower() in BLACKLISTED_ENV_VARS:
                to_delete.append(key)

        for key in to_delete:
            LOG.debug('User specified environment variable "%s" which is being ignored...' %
                      (key))
            del env_vars[key]

        return env_vars

    def _get_datastore_access_env_vars(self):
        """
        Return environment variables so datastore access using client (from st2client)
        is possible with actions. This is done to be compatible with sensors.

        :rtype: ``dict``
        """
        env_vars = {}
        if self.auth_token:
            env_vars[AUTH_TOKEN_ENV_VARIABLE_NAME] = self.auth_token.token
        env_vars[API_URL_ENV_VARIABLE_NAME] = get_full_public_api_url()

        return env_vars

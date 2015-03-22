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
from distutils.spawn import find_executable

from eventlet.green import subprocess

from st2actions.runners import ActionRunner
from st2common import log as logging
from st2common.constants.action import LIVEACTION_STATUS_SUCCEEDED, LIVEACTION_STATUS_FAILED
from st2common.constants.runners import PYTHON_RUNNER_DEFAULT_ACTION_TIMEOUT

LOG = logging.getLogger(__name__)

WINEXE_EXISTS = find_executable('winexe') is not None

# constants to lookup in runner_parameters
RUNNER_USERNAME = 'username'
RUNNER_PASSWORD = 'password'
RUNNER_HOST = 'host'
RUNNER_COMMAND = 'cmd'
RUNNER_TIMEOUT = 'timeout'


def get_runner():
    return WindowsRunner(str(uuid.uuid4()))


class WindowsRunner(ActionRunner):

    def __init__(self, runner_id, timeout=PYTHON_RUNNER_DEFAULT_ACTION_TIMEOUT):
        """
        :param timeout: Action execution timeout in seconds.
        :type timeout: ``int``
        """
        super(WindowsRunner, self).__init__(runner_id=runner_id)
        self._timeout = timeout

    def pre_run(self):
        # TODO :This is awful, but the way "runner_parameters" and other variables get
        # assigned on the runner instance is even worse. Those arguments should
        # be passed to the constructor.
        self._username = self.runner_parameters.get(RUNNER_USERNAME, None)
        self._password = self.runner_parameters.get(RUNNER_PASSWORD, None)
        self._host = self.runner_parameters.get(RUNNER_HOST, None)
        self._command = self.runner_parameters.get(RUNNER_COMMAND, None)
        self._timeout = self.runner_parameters.get(RUNNER_TIMEOUT, self._timeout)

    def run(self, action_parameters):
        if not WINEXE_EXISTS:
            msg = 'Could not find "winexe" binary. Make sure it\'s installed and available.'
            raise Exception(msg)

        args = self._get_winexe_command_args(host=self._host, username=self._username,
                                             password=self._password,
                                             command=self._command)

        # Note: We are using eventlet friendly implementation of subprocess
        # which uses GreenPipe so it doesn't block
        process = subprocess.Popen(args=args, stdin=None, stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE, shell=False)

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

        result = stdout

        output = {
            'stdout': stdout,
            'stderr': stderr,
            'exit_code': exit_code,
            'result': result
        }

        if error:
            output['error'] = error

        status = LIVEACTION_STATUS_SUCCEEDED if exit_code == 0 else LIVEACTION_STATUS_FAILED
        LOG.debug('Action output : %s. exit_code : %s. status : %s', str(output), exit_code, status)
        return (status, output, None)

    def _get_winexe_command_args(self, host, username, password, command, domain=None):
        args = ['winexe']

        if domain:
            args += ['-U', '%s\%s' % (domain, username)]
        else:
            args += ['-U', username]

        args += ['--password', password]
        args += ['//%s' % (host)]
        args += [command]

        return args

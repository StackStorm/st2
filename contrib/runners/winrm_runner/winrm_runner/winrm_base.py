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

from __future__ import absolute_import

from base64 import b64encode
from st2common import log as logging
from st2common.constants import action as action_constants
from st2common.constants import exit_codes as exit_code_constants
from st2common.runners.base import ActionRunner
from st2common.util import jsonify
from winrm import Session, Response
from winrm.exceptions import WinRMOperationTimeoutError
import time

__all__ = [
    'WinRmBaseRunner',
]

LOG = logging.getLogger(__name__)

RUNNER_CWD = 'cwd'
RUNNER_ENV = 'env'
RUNNER_HOST = "host"
RUNNER_PASSWORD = "password"
RUNNER_PORT = "port"
RUNNER_SCHEME = "scheme"
RUNNER_TIMEOUT = "timeout"
RUNNER_TRANSPORT = "transport"
RUNNER_USERNAME = "username"
RUNNER_VERIFY_SSL = "verify_ssl_cert"

WINRM_HTTPS_PORT = 5986
WINRM_HTTP_PORT = 5985
# explicity made so that it does not equal SUCCESS so a failure is returned
WINRM_TIMEOUT_EXIT_CODE = exit_code_constants.SUCCESS_EXIT_CODE - 1

DEFAULT_PORT = WINRM_HTTPS_PORT
DEFAULT_SCHEME = "https"
DEFAULT_TIMEOUT = 60
DEFAULT_TRANSPORT = "ntlm"
DEFAULT_VERIFY_SSL = True


class WinRMRunnerTimoutError(Exception):

    def __init__(self, response):
        self.response = response


class WinRmBaseRunner(ActionRunner):
    KEYS_TO_TRANSFORM = ['stdout', 'stderr']

    def _create_session(self, action_parameters):
        # common connection parameters
        host = self.runner_parameters[RUNNER_HOST]
        username = self.runner_parameters[RUNNER_USERNAME]
        password = self.runner_parameters[RUNNER_PASSWORD]
        timeout = self.runner_parameters.get(RUNNER_TIMEOUT, DEFAULT_TIMEOUT)
        read_timeout = timeout + 1  # read_timeout must be > operation_timeout

        # default to https port 5986 over ntlm
        port = self.runner_parameters.get(RUNNER_PORT, DEFAULT_PORT)
        scheme = self.runner_parameters.get(RUNNER_SCHEME, DEFAULT_SCHEME)
        transport = self.runner_parameters.get(RUNNER_TRANSPORT, DEFAULT_TRANSPORT)

        # if connecting to the HTTP port then we must use "http" as the scheme
        # in the URL
        if port == WINRM_HTTP_PORT:
            scheme = "http"

        # default to verifying SSL certs
        verify_ssl = self.runner_parameters.get(RUNNER_VERIFY_SSL, DEFAULT_VERIFY_SSL)
        winrm_cert_validate = "validate" if verify_ssl else "ignore"

        # create the session
        winrm_url = '{}://{}:{}/wsman'.format(scheme, host, port)
        LOG.info("Connecting via WinRM to url: {}".format(winrm_url))
        session = Session(winrm_url,
                          auth=(username, password),
                          transport=transport,
                          server_cert_validation=winrm_cert_validate,
                          operation_timeout_sec=timeout,
                          read_timeout_sec=read_timeout)
        return session

    def _winrm_get_command_output(self, protocol, shell_id, command_id):
        # NOTE: this is copied from pywinrm because it doesn't support
        # timeouts
        stdout_buffer, stderr_buffer = [], []
        return_code = 0
        command_done = False
        timeout = self.runner_parameters[RUNNER_TIMEOUT]
        start_time = time.time()
        while not command_done:
            # check if we need to timeout (StackStorm custom)
            current_time = time.time()
            elapsed_time = (current_time - start_time)
            if timeout and (elapsed_time > timeout):
                raise WinRMRunnerTimoutError(Response((b''.join(stdout_buffer),
                                                       b''.join(stderr_buffer),
                                                       WINRM_TIMEOUT_EXIT_CODE)))
            # end stackstorm custom

            try:
                stdout, stderr, return_code, command_done = \
                    protocol._raw_get_command_output(shell_id, command_id)
                stdout_buffer.append(stdout)
                stderr_buffer.append(stderr)
            except WinRMOperationTimeoutError as e:
                # this is an expected error when waiting for a long-running process,
                # just silently retry
                pass
        return b''.join(stdout_buffer), b''.join(stderr_buffer), return_code

    def _winrm_run_cmd(self, session, command, args=(), env=None, cwd=None):
        # NOTE: this is copied from pywinrm because it doesn't support
        # passing env and working_directory from the Session.run_cmd
        shell_id = session.protocol.open_shell(env_vars=env,
                                               working_directory=cwd)
        command_id = session.protocol.run_command(shell_id, command, args)
        # try/catch is for custom timeout handing (StackStorm custom)
        try:
            stdout, stderr, return_code = self._winrm_get_command_output(session.protocol,
                                                                         shell_id,
                                                                         command_id)
            rs = Response(stdout, stderr, return_code)
            rs.timeout = False
        except WinRMRunnerTimoutError as e:
            rs = e.response
            rs.timeout  = True
        # end stackstorm custom
        session.protocol.cleanup_command(shell_id, command_id)
        session.protocol.close_shell(shell_id)
        return rs

    def _winrm_run_ps(self, session, script, env=None, cwd=None):
        # NOTE: this is copied from pywinrm because it doesn't support
        # passing env and working_directory from the Session.run_ps
        encoded_ps = b64encode(script.encode('utf_16_le')).decode('ascii')
        rs = self._winrm_run_cmd(session,
                                 'powershell -encodedcommand {0}'.format(encoded_ps),
                                 env=env,
                                 cwd=cwd)
        if len(rs.std_err):
            # if there was an error message, clean it it up and make it human
            # readable
            rs.std_err = session._clean_error_msg(rs.std_err)
        return rs

    def _run_ps(self, action_parameters, powershell):
        env = self.runner_parameters.get(RUNNER_ENV, None)
        cwd = self.runner_parameters.get(RUNNER_CWD, None)

        # connect
        session = self._create_session(action_parameters)
        # execute
        response = self._winrm_run_ps(session, powershell, env=env, cwd=cwd)
        # create triplet from WinRM response
        return self._translate_response(response)

    def _translate_response(self, response):
        # check exit status for errors
        succeeded = (response.status_code == exit_code_constants.SUCCESS_EXIT_CODE)
        status = action_constants.LIVEACTION_STATUS_SUCCEEDED
        if response.timeout:
            status = action_constants.LIVEACTION_STATUS_TIMED_OUT
        elif not succeeded:
            status = action_constants.LIVEACTION_STATUS_FAILED

        # create result
        result = {
            'failed': not succeeded,
            'succeeded': succeeded,
            'return_code': response.status_code,
            'stdout': response.std_out,
            'stderr': response.std_err
        }

        # automatically convert result stdout/stderr from JSON strings to
        # objects so they can be used natively
        return (status, jsonify.json_loads(result, WinRmBaseRunner.KEYS_TO_TRANSFORM), None)

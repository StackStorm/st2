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

import re
import six
import time

from base64 import b64encode
from st2common import log as logging
from st2common.constants import action as action_constants
from st2common.constants import exit_codes as exit_code_constants
from st2common.runners.base import ActionRunner
from st2common.util import jsonify
from winrm import Session, Response
from winrm.exceptions import WinRMOperationTimeoutError

__all__ = [
    'WinRmBaseRunner',
]

LOG = logging.getLogger(__name__)

RUNNER_CWD = "cwd"
RUNNER_ENV = "env"
RUNNER_HOST = "host"
RUNNER_KWARG_OP = "kwarg_op"
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

DEFAULT_KWARG_OP = "-"
DEFAULT_PORT = WINRM_HTTPS_PORT
DEFAULT_SCHEME = "https"
DEFAULT_TIMEOUT = 60
DEFAULT_TRANSPORT = "ntlm"
DEFAULT_VERIFY_SSL = True

RESULT_KEYS_TO_TRANSFORM = ["stdout", "stderr"]

# key = value in linux/bash to escape
# value = powershell escaped equivalent
#
# Compiled list from the following sources:
# https://ss64.com/ps/syntax-esc.html
# https://www.techotopia.com/index.php/Windows_PowerShell_1.0_String_Quoting_and_Escape_Sequences#PowerShell_Special_Escape_Sequences
PS_ESCAPE_SEQUENCES = {'\n': '`n',
                       '\r': '`r',
                       '\t': '`t',
                       '\a': '`a',
                       '\b': '`b',
                       '\f': '`f',
                       '\v': '`v',
                       '"': '`"',
                       '\'': '`\'',
                       '`': '``',
                       '\0': '`0',
                       '$': '`$'}


class WinRmRunnerTimoutError(Exception):

    def __init__(self, response):
        self.response = response


class WinRmBaseRunner(ActionRunner):

    def pre_run(self):
        super(WinRmBaseRunner, self).pre_run()

        # common connection parameters
        self._host = self.runner_parameters[RUNNER_HOST]
        self._username = self.runner_parameters[RUNNER_USERNAME]
        self._password = self.runner_parameters[RUNNER_PASSWORD]
        self._timeout = self.runner_parameters.get(RUNNER_TIMEOUT, DEFAULT_TIMEOUT)
        self._read_timeout = self._timeout + 1  # read_timeout must be > operation_timeout

        # default to https port 5986 over ntlm
        self._port = self.runner_parameters.get(RUNNER_PORT, DEFAULT_PORT)
        self._scheme = self.runner_parameters.get(RUNNER_SCHEME, DEFAULT_SCHEME)
        self._transport = self.runner_parameters.get(RUNNER_TRANSPORT, DEFAULT_TRANSPORT)

        # if connecting to the HTTP port then we must use "http" as the scheme
        # in the URL
        if self._port == WINRM_HTTP_PORT:
            self._scheme = "http"

        # construct the URL for connecting to WinRM on the host
        self._winrm_url = "{}://{}:{}/wsman".format(self._scheme, self._host, self._port)

        # default to verifying SSL certs
        self._verify_ssl = self.runner_parameters.get(RUNNER_VERIFY_SSL, DEFAULT_VERIFY_SSL)
        self._server_cert_validation = "validate" if self._verify_ssl else "ignore"

        # additional parameters
        self._cwd = self.runner_parameters.get(RUNNER_CWD, None)
        self._env = self.runner_parameters.get(RUNNER_ENV, {})
        self._env = self._env or {}
        self._kwarg_op = self.runner_parameters.get(RUNNER_KWARG_OP, DEFAULT_KWARG_OP)

    def _create_session(self):
        # create the session
        LOG.info("Connecting via WinRM to url: {}".format(self._winrm_url))
        session = Session(self._winrm_url,
                          auth=(self._username, self._password),
                          transport=self._transport,
                          server_cert_validation=self._server_cert_validation,
                          operation_timeout_sec=self._timeout,
                          read_timeout_sec=self._read_timeout)
        return session

    def _winrm_get_command_output(self, protocol, shell_id, command_id):
        # NOTE: this is copied from pywinrm because it doesn't support
        # timeouts
        stdout_buffer, stderr_buffer = [], []
        return_code = 0
        command_done = False
        start_time = time.time()
        while not command_done:
            # check if we need to timeout (StackStorm custom)
            current_time = time.time()
            elapsed_time = (current_time - start_time)
            if self._timeout and (elapsed_time > self._timeout):
                raise WinRmRunnerTimoutError(Response((b''.join(stdout_buffer),
                                                       b''.join(stderr_buffer),
                                                       WINRM_TIMEOUT_EXIT_CODE)))
            # end stackstorm custom

            try:
                stdout, stderr, return_code, command_done = \
                    protocol._raw_get_command_output(shell_id, command_id)
                stdout_buffer.append(stdout)
                stderr_buffer.append(stderr)
            except WinRMOperationTimeoutError:
                # this is an expected error when waiting for a long-running process,
                # just silently retry
                pass
        return b''.join(stdout_buffer), b''.join(stderr_buffer), return_code

    def _winrm_run_cmd(self, session, command, args=(), env=None, cwd=None):
        # NOTE: this is copied from pywinrm because it doesn't support
        # passing env and working_directory from the Session.run_cmd.
        # It also doesn't support timeouts. All of these things have been
        # added
        shell_id = session.protocol.open_shell(env_vars=env,
                                               working_directory=cwd)
        command_id = session.protocol.run_command(shell_id, command, args)
        # try/catch is for custom timeout handing (StackStorm custom)
        try:
            rs = Response(self._winrm_get_command_output(session.protocol,
                                                         shell_id,
                                                         command_id))
            rs.timeout = False
        except WinRmRunnerTimoutError as e:
            rs = e.response
            rs.timeout = True
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

    def _translate_response(self, response):
        # check exit status for errors
        succeeded = (response.status_code == exit_code_constants.SUCCESS_EXIT_CODE)
        status = action_constants.LIVEACTION_STATUS_SUCCEEDED
        status_code = response.status_code
        if response.timeout:
            status = action_constants.LIVEACTION_STATUS_TIMED_OUT
            status_code = WINRM_TIMEOUT_EXIT_CODE
        elif not succeeded:
            status = action_constants.LIVEACTION_STATUS_FAILED

        # create result
        result = {
            'failed': not succeeded,
            'succeeded': succeeded,
            'return_code': status_code,
            'stdout': response.std_out,
            'stderr': response.std_err
        }

        # automatically convert result stdout/stderr from JSON strings to
        # objects so they can be used natively
        return (status, jsonify.json_loads(result, RESULT_KEYS_TO_TRANSFORM), None)

    def _run_ps(self, powershell):
        # connect
        session = self._create_session()
        # execute
        response = self._winrm_run_ps(session, powershell, env=self._env, cwd=self._cwd)
        # create triplet from WinRM response
        return self._translate_response(response)

    def _multireplace(self, string, replacements):
        """
        Given a string and a replacement map, it returns the replaced string.
        Source = https://gist.github.com/bgusach/a967e0587d6e01e889fd1d776c5f3729
        Reference = https://stackoverflow.com/questions/6116978/how-to-replace-multiple-substrings-of-a-string  # noqa
        :param str string: string to execute replacements on
        :param dict replacements: replacement dictionary {value to find: value to replace}
        :rtype: str
        """
        # Place longer ones first to keep shorter substrings from matching where
        # the longer ones should take place
        # For instance given the replacements {'ab': 'AB', 'abc': 'ABC'} against
        # the string 'hey abc', it should produce 'hey ABC' and not 'hey ABc'
        substrs = sorted(replacements, key=len, reverse=True)

        # Create a big OR regex that matches any of the substrings to replace
        regexp = re.compile('|'.join([re.escape(s) for s in substrs]))

        # For each match, look up the new string in the replacements
        return regexp.sub(lambda match: replacements[match.group(0)], string)

    def _param_to_ps(self, param):
        ps_str = ""
        if isinstance(param, six.string_types):
            ps_str = '"' + self._multireplace(param, PS_ESCAPE_SEQUENCES) + '"'
        elif isinstance(param, bool):
            ps_str = "$true" if param else "$false"
        elif isinstance(param, list):
            ps_str = "@("
            ps_str += ", ".join([self._param_to_ps(p) for p in param])
            ps_str += ")"
        elif isinstance(param, dict):
            ps_str = "@{"
            ps_str += "; ".join([(self._param_to_ps(k) + ' = ' + self._param_to_ps(v))
                                 for k, v in six.iteritems(param)])
            ps_str += "}"
        else:
            ps_str = str(param)
        return ps_str

    def transform_params_to_ps(self, positional_args, named_args):
        for i, arg in enumerate(positional_args):
            positional_args[i] = self._param_to_ps(arg)

        for key, value in six.iteritems(named_args):
            named_args[key] = self._param_to_ps(value)

        return positional_args, named_args

    def create_ps_params_string(self, positional_args, named_args):
        ps_params_str = ""
        ps_params_str += " " .join([(k + " " + v) for k, v in six.iteritems(named_args)])
        ps_params_str += " "
        ps_params_str += " ".join(positional_args)
        return ps_params_str

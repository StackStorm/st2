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

import base64
import os
import re
import time

from base64 import b64encode
from contextlib import contextmanager
from st2common import log as logging
from st2common.constants import action as action_constants
from st2common.constants import exit_codes as exit_code_constants
from st2common.runners.base import ActionRunner
from st2common.util import jsonify
from winrm import Session, Response
from winrm.exceptions import WinRMOperationTimeoutError

__all__ = [
    "WinRmBaseRunner",
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

WINRM_DEFAULT_TMP_DIR_PS = "[System.IO.Path]::GetTempPath()"
# maximum cmdline length for systems >= Windows XP
# https://support.microsoft.com/en-us/help/830473/command-prompt-cmd-exe-command-line-string-limitation
WINRM_MAX_CMD_LENGTH = 8191
WINRM_HTTPS_PORT = 5986
WINRM_HTTP_PORT = 5985
# explicity made so that it does not equal SUCCESS so a failure is returned
WINRM_TIMEOUT_EXIT_CODE = exit_code_constants.SUCCESS_EXIT_CODE - 1
# number of bytes in each chunk when uploading data via WinRM to a target host
# this was chosen arbitrarily and could probably use some tuning
WINRM_UPLOAD_CHUNK_SIZE_BYTES = 2048

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
PS_ESCAPE_SEQUENCES = {
    "\n": "`n",
    "\r": "`r",
    "\t": "`t",
    "\a": "`a",
    "\b": "`b",
    "\f": "`f",
    "\v": "`v",
    '"': '`"',
    "'": "`'",
    "`": "``",
    "\0": "`0",
    "$": "`$",
}


class WinRmRunnerTimoutError(Exception):
    def __init__(self, response):
        self.response = response


class WinRmBaseRunner(ActionRunner):
    def pre_run(self):
        # pylint: disable=unsubscriptable-object
        super(WinRmBaseRunner, self).pre_run()

        # common connection parameters
        self._session = None
        self._host = self.runner_parameters[RUNNER_HOST]
        self._username = self.runner_parameters[RUNNER_USERNAME]
        self._password = self.runner_parameters[RUNNER_PASSWORD]
        self._timeout = self.runner_parameters.get(RUNNER_TIMEOUT, DEFAULT_TIMEOUT)
        self._read_timeout = (
            self._timeout + 1
        )  # read_timeout must be > operation_timeout

        # default to https port 5986 over ntlm
        self._port = self.runner_parameters.get(RUNNER_PORT, DEFAULT_PORT)
        self._scheme = self.runner_parameters.get(RUNNER_SCHEME, DEFAULT_SCHEME)
        self._transport = self.runner_parameters.get(
            RUNNER_TRANSPORT, DEFAULT_TRANSPORT
        )

        # if connecting to the HTTP port then we must use "http" as the scheme
        # in the URL
        if self._port == WINRM_HTTP_PORT:
            self._scheme = "http"

        # construct the URL for connecting to WinRM on the host
        self._winrm_url = "{}://{}:{}/wsman".format(
            self._scheme, self._host, self._port
        )

        # default to verifying SSL certs
        self._verify_ssl = self.runner_parameters.get(
            RUNNER_VERIFY_SSL, DEFAULT_VERIFY_SSL
        )
        self._server_cert_validation = "validate" if self._verify_ssl else "ignore"

        # additional parameters
        self._cwd = self.runner_parameters.get(RUNNER_CWD, None)
        self._env = self.runner_parameters.get(RUNNER_ENV, {})
        self._env = self._env or {}
        self._kwarg_op = self.runner_parameters.get(RUNNER_KWARG_OP, DEFAULT_KWARG_OP)

    def _get_session(self):
        # cache session (only create if it doesn't exist yet)
        if not self._session:
            LOG.debug("Connecting via WinRM to url: {}".format(self._winrm_url))
            self._session = Session(
                self._winrm_url,
                auth=(self._username, self._password),
                transport=self._transport,
                server_cert_validation=self._server_cert_validation,
                operation_timeout_sec=self._timeout,
                read_timeout_sec=self._read_timeout,
            )
        return self._session

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
            elapsed_time = current_time - start_time
            if self._timeout and (elapsed_time > self._timeout):
                raise WinRmRunnerTimoutError(
                    Response(
                        (
                            b"".join(stdout_buffer),
                            b"".join(stderr_buffer),
                            WINRM_TIMEOUT_EXIT_CODE,
                        )
                    )
                )
            # end stackstorm custom

            try:
                (
                    stdout,
                    stderr,
                    return_code,
                    command_done,
                ) = protocol._raw_get_command_output(shell_id, command_id)
                stdout_buffer.append(stdout)
                stderr_buffer.append(stderr)
            except WinRMOperationTimeoutError:
                # this is an expected error when waiting for a long-running process,
                # just silently retry
                pass
        return b"".join(stdout_buffer), b"".join(stderr_buffer), return_code

    def _winrm_run_cmd(self, session, command, args=(), env=None, cwd=None):
        """Run a command on the remote host and return the standard output and
        error as a tuple.

        Extended from pywinrm to support passing env and cwd to open_shell,
        as well as enforcing the UTF-8 codepage. Also supports timeouts.

        """
        shell_id = session.protocol.open_shell(
            working_directory=cwd,
            env_vars=env,
            codepage=65001,
        )
        command_id = session.protocol.run_command(shell_id, command, args)
        # try/catch is for custom timeout handing (StackStorm custom)
        try:
            rs = Response(
                self._winrm_get_command_output(session.protocol, shell_id, command_id)
            )
            rs.timeout = False
        except WinRmRunnerTimoutError as e:
            rs = e.response
            rs.timeout = True
        # end stackstorm custom
        session.protocol.cleanup_command(shell_id, command_id)
        session.protocol.close_shell(shell_id)
        return rs

    def _winrm_encode(self, script):
        return b64encode(script.encode("utf_16_le")).decode("ascii")

    def _winrm_ps_cmd(self, encoded_ps):
        return "powershell -encodedcommand {0}".format(encoded_ps)

    def _winrm_run_ps(self, session, script, env=None, cwd=None, is_b64=False):
        # NOTE: this is copied from pywinrm because it doesn't support
        # passing env and working_directory from the Session.run_ps

        # encode the script in UTF only if it isn't passed in encoded
        LOG.debug("_winrm_run_ps() - script size = {}".format(len(script)))
        encoded_ps = script if is_b64 else self._winrm_encode(script)
        ps_cmd = self._winrm_ps_cmd(encoded_ps)
        LOG.debug("_winrm_run_ps() - ps cmd size = {}".format(len(ps_cmd)))
        rs = self._winrm_run_cmd(session, ps_cmd, env=env, cwd=cwd)
        if len(rs.std_err):
            # if there was an error message, clean it it up and make it human
            # readable
            rs.std_err = session._clean_error_msg(rs.std_err)
        return rs

    def _translate_response(self, response):
        # check exit status for errors
        succeeded = response.status_code == exit_code_constants.SUCCESS_EXIT_CODE
        status = action_constants.LIVEACTION_STATUS_SUCCEEDED
        status_code = response.status_code
        if response.timeout:
            status = action_constants.LIVEACTION_STATUS_TIMED_OUT
            status_code = WINRM_TIMEOUT_EXIT_CODE
        elif not succeeded:
            status = action_constants.LIVEACTION_STATUS_FAILED

        # create result
        result = {
            "failed": not succeeded,
            "succeeded": succeeded,
            "return_code": status_code,
            "stdout": response.std_out,
            "stderr": response.std_err,
        }

        # Ensure stdout and stderr is always a string
        if isinstance(result["stdout"], bytes):
            result["stdout"] = result["stdout"].decode("utf-8")

        if isinstance(result["stderr"], bytes):
            result["stderr"] = result["stderr"].decode("utf-8")

        # automatically convert result stdout/stderr from JSON strings to
        # objects so they can be used natively
        return (status, jsonify.json_loads(result, RESULT_KEYS_TO_TRANSFORM), None)

    def _make_tmp_dir(self, parent):
        LOG.debug(
            "Creating temporary directory for WinRM script in parent: {}".format(parent)
        )
        ps = """$parent = {parent}
$name = [System.IO.Path]::GetRandomFileName()
$path = Join-Path $parent $name
New-Item -ItemType Directory -Path $path | Out-Null
$path""".format(
            parent=parent
        )
        result = self._run_ps_or_raise(
            ps, ("Unable to make temporary directory for" " powershell script")
        )
        # strip to remove trailing newline and whitespace (if any)
        return result["stdout"].strip()

    def _rm_dir(self, directory):
        ps = 'Remove-Item -Force -Recurse -Path "{}"'.format(directory)
        self._run_ps_or_raise(
            ps, "Unable to remove temporary directory for powershell script"
        )

    def _upload(self, src_path_or_data, dst_path):
        src_data = None
        # detect if this is a path or a string containing data
        # if this is a path, then read the data from the path
        if os.path.exists(src_path_or_data):
            LOG.debug("WinRM uploading local file: {}".format(src_path_or_data))
            with open(src_path_or_data, "r") as src_file:
                src_data = src_file.read()
        else:
            LOG.debug("WinRM uploading data from a string")
            src_data = src_path_or_data

        # upload the data in chunks such that each chunk doesn't exceed the
        # max command size of the windows command line
        for i in range(0, len(src_data), WINRM_UPLOAD_CHUNK_SIZE_BYTES):
            LOG.debug(
                "WinRM uploading data bytes: {}-{}".format(
                    i, (i + WINRM_UPLOAD_CHUNK_SIZE_BYTES)
                )
            )
            self._upload_chunk(
                dst_path, src_data[i : (i + WINRM_UPLOAD_CHUNK_SIZE_BYTES)]
            )

    def _upload_chunk(self, dst_path, src_data):
        # adapted from https://github.com/diyan/pywinrm/issues/18
        if not isinstance(src_data, bytes):
            src_data = src_data.encode("utf-8")

        ps = """$filePath = "{dst_path}"
$s = @"
{b64_data}
"@
$data = [System.Convert]::FromBase64String($s)
Add-Content -value $data -encoding byte -path $filePath
""".format(
            dst_path=dst_path, b64_data=base64.b64encode(src_data).decode("utf-8")
        )

        LOG.debug("WinRM uploading chunk, size = {}".format(len(ps)))
        self._run_ps_or_raise(ps, "Failed to upload chunk of powershell script")

    @contextmanager
    def _tmp_script(self, parent, script):
        tmp_dir = None
        try:
            LOG.info("WinRM Script - Making temporary directory")
            tmp_dir = self._make_tmp_dir(parent)
            LOG.debug("WinRM Script - Tmp directory created: {}".format(tmp_dir))
            LOG.info("WinRM Script = Upload starting")
            tmp_script = tmp_dir + "\\script.ps1"
            LOG.debug("WinRM Uploading script to: {}".format(tmp_script))
            self._upload(script, tmp_script)
            LOG.info("WinRM Script - Upload complete")
            yield tmp_script
        finally:
            if tmp_dir:
                LOG.debug("WinRM Script - Removing script: {}".format(tmp_dir))
                self._rm_dir(tmp_dir)

    def run_cmd(self, cmd):
        # connect
        session = self._get_session()
        # execute
        response = self._winrm_run_cmd(session, cmd, env=self._env, cwd=self._cwd)
        # create triplet from WinRM response
        return self._translate_response(response)

    def run_ps(self, script, params=None):
        # temporary directory for the powershell script
        if params:
            powershell = "& {%s} %s" % (script, params)
        else:
            powershell = script
        encoded_ps = self._winrm_encode(powershell)
        ps_cmd = self._winrm_ps_cmd(encoded_ps)

        # if the powershell script is small enough to fit in one command
        # then run it as a single command (faster)
        # else we need to upload the script to a temporary file and execute it,
        # then remove the temporary file
        if len(ps_cmd) <= WINRM_MAX_CMD_LENGTH:
            LOG.info(
                (
                    "WinRM powershell command size {} is > {}, the max size of a"
                    " powershell command. Converting to a script execution."
                ).format(WINRM_MAX_CMD_LENGTH, len(ps_cmd))
            )
            return self._run_ps(encoded_ps, is_b64=True)
        else:
            return self._run_ps_script(script, params)

    def _run_ps(self, powershell, is_b64=False):
        """Executes a powershell command, no checks for length are done in this version.
        The lack of checks here is intentional so that we don't run into an infinte loop
        when converting a long command to a script"""
        # connect
        session = self._get_session()
        # execute
        response = self._winrm_run_ps(
            session, powershell, env=self._env, cwd=self._cwd, is_b64=is_b64
        )
        # create triplet from WinRM response
        return self._translate_response(response)

    def _run_ps_script(self, script, params=None):
        tmp_dir = WINRM_DEFAULT_TMP_DIR_PS
        # creates a temporary file,
        # upload the contents of 'script' to the temporary file
        # handle deletion of the temporary file on exit of the with block
        with self._tmp_script(tmp_dir, script) as tmp_script:
            # the following wraps the script (from the file) in a script block ( {} )
            # executes it, passing in the parameters built above.
            # https://docs.microsoft.com/en-us/powershell/scripting/core-powershell/console/powershell.exe-command-line-help
            ps = tmp_script
            if params:
                ps += " " + params
            return self._run_ps(ps)

    def _run_ps_or_raise(self, ps, error_msg):
        response = self._run_ps(ps)
        # response is a tuple: (status, result, None)
        result = response[1]
        if result["failed"]:
            raise RuntimeError(
                ("{}:\n" "stdout = {}\n\n" "stderr = {}").format(
                    error_msg, result["stdout"], result["stderr"]
                )
            )
        return result

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
        regexp = re.compile("|".join([re.escape(s) for s in substrs]))

        # For each match, look up the new string in the replacements
        return regexp.sub(lambda match: replacements[match.group(0)], string)

    def _param_to_ps(self, param):
        ps_str = ""
        if param is None:
            ps_str = "$null"
        elif isinstance(param, str):
            ps_str = '"' + self._multireplace(param, PS_ESCAPE_SEQUENCES) + '"'
        elif isinstance(param, bool):
            ps_str = "$true" if param else "$false"
        elif isinstance(param, list):
            ps_str = "@("
            ps_str += ", ".join([self._param_to_ps(p) for p in param])
            ps_str += ")"
        elif isinstance(param, dict):
            ps_str = "@{"
            ps_str += "; ".join(
                [
                    (self._param_to_ps(k) + " = " + self._param_to_ps(v))
                    for k, v in param.items()
                ]
            )
            ps_str += "}"
        else:
            ps_str = str(param)
        return ps_str

    def _transform_params_to_ps(self, positional_args, named_args):
        if positional_args:
            for i, arg in enumerate(positional_args):
                positional_args[i] = self._param_to_ps(arg)

        if named_args:
            for key, value in named_args.items():
                named_args[key] = self._param_to_ps(value)

        return positional_args, named_args

    def create_ps_params_string(self, positional_args, named_args):
        # convert the script parameters into powershell strings
        positional_args, named_args = self._transform_params_to_ps(
            positional_args, named_args
        )
        # concatenate them into a long string
        ps_params_str = ""
        if named_args:
            ps_params_str += " ".join([(k + " " + v) for k, v in named_args.items()])
            ps_params_str += " "
        if positional_args:
            ps_params_str += " ".join(positional_args)
        return ps_params_str

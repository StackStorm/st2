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
import re
import uuid

import six

from eventlet.green import subprocess

from st2common import log as logging
from st2common.util.green.shell import run_command
from st2common.util.shell import quote_windows
from st2common.constants.action import LIVEACTION_STATUS_SUCCEEDED
from st2common.constants.action import LIVEACTION_STATUS_FAILED
from st2common.constants.runners import WINDOWS_RUNNER_DEFAULT_ACTION_TIMEOUT
from st2actions.runners.windows_runner import BaseWindowsRunner
from st2actions.runners import ShellRunnerMixin

__all__ = [
    'get_runner',

    'WindowsScriptRunner'
]

LOG = logging.getLogger(__name__)

PATH_SEPARATOR = '\\'

# constants to lookup in runner_parameters
RUNNER_HOST = 'host'
RUNNER_USERNAME = 'username'
RUNNER_PASSWORD = 'password'
RUNNER_COMMAND = 'cmd'
RUNNER_TIMEOUT = 'timeout'
RUNNER_SHARE_NAME = 'share'

# Timeouts for different steps
UPLOAD_FILE_TIMEOUT = 30
CREATE_DIRECTORY_TIMEOUT = 10
DELETE_FILE_TIMEOUT = 10
DELETE_DIRECTORY_TIMEOUT = 10

POWERSHELL_COMMAND = 'powershell.exe -InputFormat None'


def get_runner():
    return WindowsScriptRunner(str(uuid.uuid4()))


class WindowsScriptRunner(BaseWindowsRunner, ShellRunnerMixin):
    """
    Runner which executes PowerShell scripts on a remote Windows machine.
    """

    def __init__(self, runner_id, timeout=WINDOWS_RUNNER_DEFAULT_ACTION_TIMEOUT):
        """
        :param timeout: Action execution timeout in seconds.
        :type timeout: ``int``
        """
        super(WindowsScriptRunner, self).__init__(runner_id=runner_id)
        self._timeout = timeout

    def pre_run(self):
        super(WindowsScriptRunner, self).pre_run()

        # TODO :This is awful, but the way "runner_parameters" and other variables get
        # assigned on the runner instance is even worse. Those arguments should
        # be passed to the constructor.
        self._host = self.runner_parameters.get(RUNNER_HOST, None)
        self._username = self.runner_parameters.get(RUNNER_USERNAME, None)
        self._password = self.runner_parameters.get(RUNNER_PASSWORD, None)
        self._command = self.runner_parameters.get(RUNNER_COMMAND, None)
        self._timeout = self.runner_parameters.get(RUNNER_TIMEOUT, self._timeout)

        self._share = self.runner_parameters.get(RUNNER_SHARE_NAME, 'C$')

    def run(self, action_parameters):
        # Make sure the dependencies are available
        self._verify_winexe_exists()
        self._verify_smbclient_exists()

        # Parse arguments, if any
        pos_args, named_args = self._get_script_args(action_parameters)
        args = self._get_script_arguments(named_args=named_args, positional_args=pos_args)

        # 1. Retrieve full absolute path for the share name
        # TODO: Cache resolved paths
        base_path = self._get_share_absolute_path(share=self._share)

        # 2. Upload script file to a temporary location
        local_path = self.entry_point
        script_path, temporary_directory_path = self._upload_file(local_path=local_path,
                                                                  base_path=base_path)

        # 3. Execute the script
        exit_code, stdout, stderr, timed_out = self._run_script(script_path=script_path,
                                                                arguments=args)

        # 4. Delete temporary directory
        self._delete_directory(directory_path=temporary_directory_path)

        if timed_out:
            error = 'Action failed to complete in %s seconds' % (self._timeout)
        else:
            error = None

        if exit_code != 0:
            error = self._parse_winexe_error(stdout=stdout, stderr=stderr)

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
        return (status, output, None)

    def _run_script(self, script_path, arguments=None):
        """
        :param script_path: Full path to the script on the remote server.
        :type script_path: ``str``

        :param arguments: The arguments to pass to the script.
        :type arguments: ``str``
        """
        if arguments is not None:
            command = '%s %s %s' % (POWERSHELL_COMMAND, quote_windows(script_path), arguments)
        else:
            command = '%s %s' % (POWERSHELL_COMMAND, quote_windows(script_path))
        args = self._get_winexe_command_args(host=self._host, username=self._username,
                                             password=self._password,
                                             command=command)

        LOG.debug('Running script "%s"' % (script_path))

        # Note: We don't send anything over stdin, we just create an unused pipe
        # to avoid some obscure failures
        exit_code, stdout, stderr, timed_out = run_command(cmd=args,
                                                           stdin=subprocess.PIPE,
                                                           stdout=subprocess.PIPE,
                                                           stderr=subprocess.PIPE,
                                                           shell=False,
                                                           timeout=self._timeout)

        extra = {'exit_code': exit_code, 'stdout': stdout, 'stderr': stderr}
        LOG.debug('Command returned', extra=extra)

        return exit_code, stdout, stderr, timed_out

    def _get_script_arguments(self, named_args=None, positional_args=None):
        """
        Builds a string of named and positional arguments in PowerShell format,
        which are passed to the script.

        :param named_args: Dictionary with named arguments
        :type named_args: ``dict``.

        :param positional_args: List of positional arguments
        :type positional_args: ``str``

        :rtype: ``str``
        """
        cmd_parts = []
        if positional_args:
            cmd_parts.append(positional_args)
        if named_args:
            for (arg, value) in six.iteritems(named_args):
                arg = quote_windows(arg)
                if value is None or (isinstance(value, six.string_types) and len(value) < 1):
                    LOG.debug('Ignoring arg %s as its value is %s.', arg, value)
                    continue
                if isinstance(value, bool):
                    if value:
                        cmd_parts.append('-%s' % (arg))
                    else:
                        cmd_parts.append('-%s:$false' % (arg))
                elif isinstance(value, (list, tuple)) or hasattr(value, '__iter__'):
                    # Array support, pass parameters to shell script
                    cmd_parts.append('-%s %s' % (arg, ','.join(value)))
                else:
                    cmd_parts.append('-%s %s' % (arg, quote_windows(str(value))))
        return ' '.join(cmd_parts)

    def _upload_file(self, local_path, base_path):
        """
        Upload provided file to the remote server in a temporary directory.

        :param local_path: Local path to the file to upload.
        :type local_path: ``str``

        :param base_path: Absolute base path for the share.
        :type base_path: ``str``
        """
        file_name = os.path.basename(local_path)

        temporary_directory_name = str(uuid.uuid4())
        command = 'mkdir %s' % (quote_windows(temporary_directory_name))

        # 1. Create a temporary dir for out scripts (ignore errors if it already exists)
        # Note: We don't necessary have access to $TEMP so we create a temporary directory for our
        # us in the root of the share we are using and have access to
        args = self._get_smbclient_command_args(host=self._host, username=self._username,
                                                password=self._password, command=command,
                                                share=self._share)

        LOG.debug('Creating temp directory "%s"' % (temporary_directory_name))

        exit_code, stdout, stderr, timed_out = run_command(cmd=args, stdout=subprocess.PIPE,
                                                           stderr=subprocess.PIPE, shell=False,
                                                           timeout=CREATE_DIRECTORY_TIMEOUT)

        extra = {'exit_code': exit_code, 'stdout': stdout, 'stderr': stderr}
        LOG.debug('Directory created', extra=extra)

        # 2. Upload file to temporary directory
        remote_path = PATH_SEPARATOR.join([temporary_directory_name, file_name])

        values = {
            'local_path': quote_windows(local_path),
            'remote_path': quote_windows(remote_path)
        }
        command = 'put %(local_path)s %(remote_path)s' % values
        args = self._get_smbclient_command_args(host=self._host, username=self._username,
                                                password=self._password, command=command,
                                                share=self._share)

        extra = {'local_path': local_path, 'remote_path': remote_path}
        LOG.debug('Uploading file to "%s"' % (remote_path))

        exit_code, stdout, stderr, timed_out = run_command(cmd=args, stdout=subprocess.PIPE,
                                                           stderr=subprocess.PIPE, shell=False,
                                                           timeout=UPLOAD_FILE_TIMEOUT)

        extra = {'exit_code': exit_code, 'stdout': stdout, 'stderr': stderr}
        LOG.debug('File uploaded to "%s"' % (remote_path), extra=extra)

        full_remote_file_path = base_path + '\\' + remote_path
        full_temporary_directory_path = base_path + '\\' + temporary_directory_name

        return full_remote_file_path, full_temporary_directory_path

    def _get_share_absolute_path(self, share):
        """
        Retrieve full absolute path for a share with the provided name.

        :param share: Share name.
        :type share: ``str``
        """
        command = 'net share %s' % (quote_windows(share))
        args = self._get_winexe_command_args(host=self._host, username=self._username,
                                             password=self._password,
                                             command=command)

        LOG.debug('Retrieving full absolute path for share "%s"' % (share))
        exit_code, stdout, stderr, timed_out = run_command(cmd=args, stdout=subprocess.PIPE,
                                                           stderr=subprocess.PIPE, shell=False,
                                                           timeout=self._timeout)

        if exit_code != 0:
            msg = 'Failed to retrieve absolute path for share "%s"' % (share)
            raise Exception(msg)

        share_info = self._parse_share_information(stdout=stdout)
        share_path = share_info.get('path', None)

        if not share_path:
            msg = 'Failed to retrieve absolute path for share "%s"' % (share)
            raise Exception(msg)

        return share_path

    def _parse_share_information(self, stdout):
        """
        Parse share information retrieved using "net share <share name>".

        :rtype: ``dict``
        """
        lines = stdout.split('\n')

        result = {}

        for line in lines:
            line = line.strip()
            split = re.split('\s{3,}', line)

            if len(split) not in [1, 2]:
                # Invalid line, skip it
                continue

            key = split[0]
            key = key.lower().replace(' ', '_')

            if len(split) == 2:
                value = split[1].strip()
            else:
                value = None

            result[key] = value

        return result

    def _delete_file(self, file_path):
        command = 'rm %(file_path)s' % {'file_path': quote_windows(file_path)}
        args = self._get_smbclient_command_args(host=self._host, username=self._username,
                                                password=self._password, command=command,
                                                share=self._share)

        exit_code, _, _, _ = run_command(cmd=args, stdout=subprocess.PIPE,
                                         stderr=subprocess.PIPE, shell=False,
                                         timeout=DELETE_FILE_TIMEOUT)

        return exit_code == 0

    def _delete_directory(self, directory_path):
        command = 'rmdir %(directory_path)s' % {'directory_path': quote_windows(directory_path)}
        args = self._get_smbclient_command_args(host=self._host, username=self._username,
                                                password=self._password, command=command,
                                                share=self._share)

        LOG.debug('Removing directory "%s"' % (directory_path))
        exit_code, _, _, _ = run_command(cmd=args, stdout=subprocess.PIPE,
                                         stderr=subprocess.PIPE, shell=False,
                                         timeout=DELETE_DIRECTORY_TIMEOUT)

        return exit_code == 0

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

from distutils.spawn import find_executable

from st2actions.runners import ActionRunner

__all__ = [
    'BaseWindowsRunner',

    'WINEXE_EXISTS',
    'SMBCLIENT_EXISTS'
]

WINEXE_EXISTS = find_executable('winexe') is not None
SMBCLIENT_EXISTS = find_executable('smbclient') is not None

# Constants which map winexe error codes to user-friendly error messages
ERROR_CODE_TO_MESSAGE_MAP = {
    'NT_STATUS_LOGON_FAILURE': 'Invalid or missing authentication credentials.',
    'NT_STATUS_IO_TIMEOUT': 'Connection timeout.',
    'NT_STATUS_NETWORK_UNREACHABLE': 'Network unavailable, unable to connect.',
    'NT_STATUS_NO_MEMORY': 'Failed to run the command.'
}


class BaseWindowsRunner(ActionRunner):
    def _verify_winexe_exists(self):
        if not WINEXE_EXISTS:
            msg = ('Could not find "winexe" binary. Make sure it\'s installed and available'
                   'in $PATH')
            raise Exception(msg)

    def _verify_smbclient_exists(self):
        if not SMBCLIENT_EXISTS:
            msg = ('Could not find "smbclient" binary. Make sure it\'s installed and available'
                   'in $PATH')
            raise Exception(msg)

    def _get_winexe_command_args(self, host, username, password, command, domain=None):
        args = ['winexe']

        # Disable interactive mode
        args += ['--interactive', '0']

        if domain:
            args += ['-U', '%s\%s' % (domain, username)]
        else:
            args += ['-U', username]

        args += ['--password', password]
        args += ['//%s' % (host)]
        args += [command]

        return args

    def _get_smbclient_command_args(self, host, username, password, command, share='C$',
                                    domain=None):
        """
        :param command: Samba command string.
        :type command: ``str``

        :param share: Samba share name.
        :type share: ``str``
        """
        args = ['smbclient']

        values = {'domain': domain, 'username': username, 'password': password}
        if domain:
            auth_string = '%(domain)s\%(username)s%%%(password)s' % values
        else:
            auth_string = '%(username)s%%%(password)s' % values

        # Authentication info
        args += ['-U', auth_string]

        # Host and share
        args += ['//%(host)s/%(share)s' % {'host': host, 'share': share}]

        # Command
        args += ['-c', command]
        return args

    def _parse_winexe_error(self, stdout, stderr):
        for code, message in ERROR_CODE_TO_MESSAGE_MAP.items():
            if code in stdout:
                return message

        return None

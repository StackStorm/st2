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
# pylint: disable=not-context-manager

import os
import pwd
import six
import sys
import copy
import traceback

from oslo_config import cfg

from st2common import log as logging
from st2common.models.base import DictSerializableClassMixin
from st2common.util.shell import quote_unix
from st2common.constants.action import LIBS_DIR as ACTION_LIBS_DIR
from st2common.util.secrets import get_secret_parameters
from st2common.util.secrets import mask_secret_parameters

__all__ = [
    'ShellCommandAction',
    'ShellScriptAction',
    'RemoteAction',
    'RemoteScriptAction',
    'ResolvedActionParameters'
]

LOG = logging.getLogger(__name__)

LOGGED_USER_USERNAME = pwd.getpwuid(os.getuid())[0]

# Flags which are passed to every sudo invocation
SUDO_COMMON_OPTIONS = [
    '-E'  # we want to preserve the environment of the user which ran sudo
]

# Flags which are only passed to sudo when not running as current user and when
# -u flag is used
SUDO_DIFFERENT_USER_OPTIONS = [
    '-H'  # we want $HOME to reflect the home directory of the requested / target user
]


class ShellCommandAction(object):
    EXPORT_CMD = 'export'

    def __init__(self, name, action_exec_id, command, user, env_vars=None, sudo=False,
                 timeout=None, cwd=None):
        self.name = name
        self.action_exec_id = action_exec_id
        self.command = command
        self.env_vars = env_vars or {}
        self.user = user
        self.sudo = sudo
        self.timeout = timeout
        self.cwd = cwd

    def get_full_command_string(self):
        # Note: We pass -E to sudo because we want to preserve user provided environment variables
        if self.sudo:
            command = quote_unix(self.command)
            sudo_arguments = ' '.join(self._get_common_sudo_arguments())
            command = 'sudo %s -- bash -c %s' % (sudo_arguments, command)
        else:
            if self.user and self.user != LOGGED_USER_USERNAME:
                # Need to use sudo to run as a different (requested) user
                user = quote_unix(self.user)
                sudo_arguments = ' '.join(self._get_user_sudo_arguments(user=user))
                command = quote_unix(self.command)
                command = 'sudo %s -- bash -c %s' % (sudo_arguments, command)
            else:
                command = self.command

        return command

    def get_timeout(self):
        return self.timeout

    def get_cwd(self):
        return self.cwd

    def _get_common_sudo_arguments(self):
        """
        Retrieve a list of flags which are passed to sudo on every invocation.

        :rtype: ``list``
        """
        flags = copy.copy(SUDO_COMMON_OPTIONS)
        return flags

    def _get_user_sudo_arguments(self, user):
        """
        Retrieve a list of flags which are passed to sudo when running as a different user and "-u"
        flag is used.

        :rtype: ``list``
        """
        flags = self._get_common_sudo_arguments()
        flags += copy.copy(SUDO_DIFFERENT_USER_OPTIONS)
        flags += ['-u', user]
        return flags

    def _get_env_vars_export_string(self):
        if self.env_vars:
            # Envrionment variables could contain spaces and open us to shell
            # injection attacks. Always quote the key and the value.
            exports = ' '.join(
                '%s=%s' % (quote_unix(k), quote_unix(v))
                for k, v in self.env_vars.iteritems()
            )
            shell_env_str = '%s %s' % (ShellCommandAction.EXPORT_CMD, exports)
        else:
            shell_env_str = ''

        return shell_env_str

    def _get_command_string(self, cmd, args):
        """
        Escape the command arguments and form a command string.

        :type cmd: ``str``
        :type args: ``list``

        :rtype: ``str``
        """
        assert isinstance(args, (list, tuple))

        args = [quote_unix(arg) for arg in args]
        args = ' '.join(args)
        result = '%s %s' % (cmd, args)
        return result

    def _get_error_result(self):
        """
        Prepares a structured error result based on the exception.

        :type e: ``Exception``

        :rtype: ``dict``
        """
        _, exc_value, exc_traceback = sys.exc_info()

        exc_value = str(exc_value)
        exc_traceback = ''.join(traceback.format_tb(exc_traceback))

        result = {}
        result['failed'] = True
        result['succeeded'] = False
        result['error'] = exc_value
        result['traceback'] = exc_traceback
        return result


class ShellScriptAction(ShellCommandAction):
    def __init__(self, name, action_exec_id, script_local_path_abs, named_args=None,
                 positional_args=None, env_vars=None, user=None, sudo=False, timeout=None,
                 cwd=None):
        super(ShellScriptAction, self).__init__(name=name, action_exec_id=action_exec_id,
                                                command=None, user=user, env_vars=env_vars,
                                                sudo=sudo, timeout=timeout, cwd=cwd)
        self.script_local_path_abs = script_local_path_abs
        self.named_args = named_args
        self.positional_args = positional_args

    def get_full_command_string(self):
        return self._format_command()

    def _format_command(self):
        script_arguments = self._get_script_arguments(named_args=self.named_args,
                                                      positional_args=self.positional_args)
        if self.sudo:
            if script_arguments:
                command = quote_unix('%s %s' % (self.script_local_path_abs, script_arguments))
            else:
                command = quote_unix(self.script_local_path_abs)

            sudo_arguments = ' '.join(self._get_common_sudo_arguments())
            command = 'sudo %s -- bash -c %s' % (sudo_arguments, command)
        else:
            if self.user and self.user != LOGGED_USER_USERNAME:
                # Need to use sudo to run as a different user
                user = quote_unix(self.user)

                if script_arguments:
                    command = quote_unix('%s %s' % (self.script_local_path_abs, script_arguments))
                else:
                    command = quote_unix(self.script_local_path_abs)

                sudo_arguments = ' '.join(self._get_user_sudo_arguments(user=user))
                command = 'sudo %s -- bash -c %s' % (sudo_arguments, command)
            else:
                script_path = quote_unix(self.script_local_path_abs)

                if script_arguments:
                    command = '%s %s' % (script_path, script_arguments)
                else:
                    command = script_path
        return command

    def _get_script_arguments(self, named_args=None, positional_args=None):
        """
        Build a string of named and positional arguments which are passed to the
        script.

        :param named_args: Dictionary with named arguments.
        :type named_args: ``dict``.

        :param positional_args: List with positional arguments.
        :type positional_args: ``dict``.

        :rtype: ``str``
        """
        command_parts = []

        # add all named_args in the format <kwarg_op>name=value (e.g. --name=value)
        if named_args is not None:
            for (arg, value) in six.iteritems(named_args):
                if value is None or (isinstance(value, (str, unicode)) and len(value) < 1):
                    LOG.debug('Ignoring arg %s as its value is %s.', arg, value)
                    continue

                if isinstance(value, bool):
                    if value is True:
                        command_parts.append(arg)
                else:
                    command_parts.append('%s=%s' % (quote_unix(arg), quote_unix(str(value))))

        # add the positional args
        if positional_args:
            quoted_pos_args = [quote_unix(pos_arg) for pos_arg in positional_args]
            pos_args_string = ' '.join(quoted_pos_args)
            command_parts.append(pos_args_string)
        return ' '.join(command_parts)


class SSHCommandAction(ShellCommandAction):
    def __init__(self, name, action_exec_id, command, env_vars, user, password=None, pkey=None,
                 hosts=None, parallel=True, sudo=False, timeout=None, cwd=None, passphrase=None):
        super(SSHCommandAction, self).__init__(name=name, action_exec_id=action_exec_id,
                                               command=command, env_vars=env_vars, user=user,
                                               sudo=sudo, timeout=timeout, cwd=cwd)
        self.hosts = hosts
        self.parallel = parallel
        self.pkey = pkey
        self.passphrase = passphrase
        self.password = password

    def is_parallel(self):
        return self.parallel

    def is_sudo(self):
        return self.sudo

    def get_user(self):
        return self.user

    def get_hosts(self):
        return self.hosts

    def is_pkey_authentication(self):
        return self.pkey is not None

    def get_pkey(self):
        return self.pkey

    def get_password(self):
        return self.password

    def get_command(self):
        return self.command

    def __str__(self):
        str_rep = []
        str_rep.append('%s@%s(name: %s' % (self.__class__.__name__, id(self), self.name))
        str_rep.append('id: %s' % self.action_exec_id)
        str_rep.append('command: %s' % self.command)
        str_rep.append('user: %s' % self.user)
        str_rep.append('sudo: %s' % str(self.sudo))
        str_rep.append('parallel: %s' % str(self.parallel))
        str_rep.append('hosts: %s)' % str(self.hosts))
        return ', '.join(str_rep)


class RemoteAction(SSHCommandAction):
    def __init__(self, name, action_exec_id, command, env_vars=None, on_behalf_user=None,
                 user=None, password=None, private_key=None, hosts=None, parallel=True, sudo=False,
                 timeout=None, cwd=None, passphrase=None):
        super(RemoteAction, self).__init__(name=name, action_exec_id=action_exec_id,
                                           command=command, env_vars=env_vars, user=user,
                                           hosts=hosts, parallel=parallel, sudo=sudo,
                                           timeout=timeout, cwd=cwd, passphrase=passphrase)
        self.password = password
        self.private_key = private_key
        self.passphrase = passphrase
        self.on_behalf_user = on_behalf_user  # Used for audit purposes.
        self.timeout = timeout

    def get_on_behalf_user(self):
        return self.on_behalf_user

    def __str__(self):
        str_rep = []
        str_rep.append('%s@%s(name: %s' % (self.__class__.__name__, id(self), self.name))
        str_rep.append('id: %s' % self.action_exec_id)
        str_rep.append('command: %s' % self.command)
        str_rep.append('user: %s' % self.user)
        str_rep.append('on_behalf_user: %s' % self.on_behalf_user)
        str_rep.append('sudo: %s' % str(self.sudo))
        str_rep.append('parallel: %s' % str(self.parallel))
        str_rep.append('hosts: %s)' % str(self.hosts))
        str_rep.append('timeout: %s)' % str(self.timeout))

        return ', '.join(str_rep)


class RemoteScriptAction(ShellScriptAction):
    def __init__(self, name, action_exec_id, script_local_path_abs, script_local_libs_path_abs,
                 named_args=None, positional_args=None, env_vars=None, on_behalf_user=None,
                 user=None, password=None, private_key=None, remote_dir=None, hosts=None,
                 parallel=True, sudo=False, timeout=None, cwd=None):
        super(RemoteScriptAction, self).__init__(name=name, action_exec_id=action_exec_id,
                                                 script_local_path_abs=script_local_path_abs,
                                                 user=user,
                                                 named_args=named_args,
                                                 positional_args=positional_args, env_vars=env_vars,
                                                 sudo=sudo, timeout=timeout, cwd=cwd)
        self.script_local_libs_path_abs = script_local_libs_path_abs
        self.script_local_dir, self.script_name = os.path.split(self.script_local_path_abs)
        self.remote_dir = remote_dir if remote_dir is not None else '/tmp'
        self.remote_libs_path_abs = os.path.join(self.remote_dir, ACTION_LIBS_DIR)
        self.on_behalf_user = on_behalf_user
        self.password = password
        self.private_key = private_key
        self.remote_script = os.path.join(self.remote_dir, quote_unix(self.script_name))
        self.hosts = hosts
        self.parallel = parallel
        self.command = self._format_command()
        LOG.debug('RemoteScriptAction: command to run on remote box: %s', self.command)

    def get_remote_script_abs_path(self):
        return self.remote_script

    def get_local_script_abs_path(self):
        return self.script_local_path_abs

    def get_remote_libs_path_abs(self):
        return self.remote_libs_path_abs

    def get_local_libs_path_abs(self):
        return self.script_local_libs_path_abs

    def get_remote_base_dir(self):
        return self.remote_dir

    def _format_command(self):
        script_arguments = self._get_script_arguments(named_args=self.named_args,
                                                      positional_args=self.positional_args)

        if script_arguments:
            command = '%s %s' % (self.remote_script, script_arguments)
        else:
            command = self.remote_script

        return command

    def __str__(self):
        str_rep = []
        str_rep.append('%s@%s(name: %s' % (self.__class__.__name__, id(self), self.name))
        str_rep.append('id: %s' % self.action_exec_id)
        str_rep.append('local_script: %s' % self.script_local_path_abs)
        str_rep.append('local_libs: %s' % self.script_local_libs_path_abs)
        str_rep.append('remote_dir: %s' % self.remote_dir)
        str_rep.append('remote_libs: %s' % self.remote_libs_path_abs)
        str_rep.append('named_args: %s' % self.named_args)
        str_rep.append('positional_args: %s' % self.positional_args)
        str_rep.append('user: %s' % self.user)
        str_rep.append('on_behalf_user: %s' % self.on_behalf_user)
        str_rep.append('sudo: %s' % self.sudo)
        str_rep.append('parallel: %s' % self.parallel)
        str_rep.append('hosts: %s)' % self.hosts)

        return ', '.join(str_rep)


class ResolvedActionParameters(DictSerializableClassMixin):
    """
    Class which contains resolved runner and action parameters for a particular action.
    """

    def __init__(self, action_db, runner_type_db, runner_parameters=None, action_parameters=None):
        self._action_db = action_db
        self._runner_type_db = runner_type_db
        self._runner_parameters = runner_parameters
        self._action_parameters = action_parameters

    def mask_secrets(self, value):
        result = copy.deepcopy(value)

        runner_parameters = result['runner_parameters']
        action_parameters = result['action_parameters']

        runner_parameters_specs = self._runner_type_db.runner_parameters
        action_parameters_sepcs = self._action_db.parameters

        secret_runner_parameters = get_secret_parameters(parameters=runner_parameters_specs)
        secret_action_parameters = get_secret_parameters(parameters=action_parameters_sepcs)

        runner_parameters = mask_secret_parameters(parameters=runner_parameters,
                                                   secret_parameters=secret_runner_parameters)
        action_parameters = mask_secret_parameters(parameters=action_parameters,
                                                   secret_parameters=secret_action_parameters)
        result['runner_parameters'] = runner_parameters
        result['action_parameters'] = action_parameters

        return result

    def to_serializable_dict(self, mask_secrets=False):
        result = {}
        result['runner_parameters'] = self._runner_parameters
        result['action_parameters'] = self._action_parameters

        if mask_secrets and cfg.CONF.log.mask_secrets:
            result = self.mask_secrets(value=result)

        return result

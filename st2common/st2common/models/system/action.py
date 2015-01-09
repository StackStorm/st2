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
import pipes

import six
from fabric.api import (put, run, sudo)
from fabric.context_managers import shell_env
from fabric.context_managers import settings
from fabric.tasks import WrappedCallableTask

from st2common.constants.action import LIBS_DIR as ACTION_LIBS_DIR
from st2common import log as logging
import st2common.util.jsonify as jsonify

__all__ = [
    'ShellCommandAction',
    'ShellScriptAction',
    'RemoteAction',
    'RemoteScriptAction',
    'ParamikoSSHCommandAction',
    'FabricRemoteAction',
    'FabricRemoteScriptAction'
]


LOG = logging.getLogger(__name__)

LOGGED_USER_USERNAME = pwd.getpwuid(os.getuid())[0]


class ShellCommandAction(object):
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
        if self.sudo:
            command = pipes.quote(self.command)
            command = 'sudo -- bash -c %s' % (command)
        else:
            if self.user and self.user != LOGGED_USER_USERNAME:
                # Need to use sudo to run as a different user
                user = pipes.quote(self.user)
                command = pipes.quote(self.command)
                command = 'sudo -u %s -- bash -c %s' % (user, command)
            else:
                command = self.command

        return command

    def _get_command_string(self, cmd, args):
        """
        Escape the command arguments and form a command string.

        :type cmd: ``str``
        :type args: ``list``

        :rtype: ``str``
        """
        assert isinstance(args, (list, tuple))

        args = [pipes.quote(arg) for arg in args]
        args = ' '.join(args)
        result = '%s %s' % (cmd, args)
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
        script_arguments = self._get_script_arguments(named_args=self.named_args,
                                                      positional_args=self.positional_args)

        if self.sudo:
            if script_arguments:
                command = pipes.quote('%s %s' % (self.script_local_path_abs, script_arguments))
            else:
                command = pipes.quote(self.script_local_path_abs)

            command = 'sudo -- bash -c %s' % (command)
        else:
            if self.user and self.user != LOGGED_USER_USERNAME:
                # Need to use sudo to run as a different user
                user = pipes.quote(self.user)

                if script_arguments:
                    command = pipes.quote('%s %s' % (self.script_local_path_abs, script_arguments))
                else:
                    command = pipes.quote(self.script_local_path_abs)

                command = 'sudo -u %s -- bash -c %s' % (user, command)
            else:
                script_path = pipes.quote(self.script_local_path_abs)

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
                    command_parts.append('%s=%s' % (arg, pipes.quote(str(value))))

        # add the positional args
        if positional_args:
            command_parts.append(positional_args)
        return ' '.join(command_parts)


class SSHCommandAction(ShellCommandAction):
    def __init__(self, name, action_exec_id, command, env_vars, user, password=None, pkey=None,
                 hosts=None, parallel=True, sudo=False, timeout=None):
        super(SSHCommandAction, self).__init__(name=name, action_exec_id=action_exec_id,
                                               command=command, env_vars=env_vars, user=user,
                                               sudo=sudo, timeout=timeout)
        self.hosts = hosts
        self.parallel = parallel
        self.pkey = pkey
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
                 user=None, hosts=None, parallel=True, sudo=False, timeout=None):
        super(RemoteAction, self).__init__(name=name, action_exec_id=action_exec_id,
                                           command=command, env_vars=env_vars, user=user,
                                           hosts=hosts, parallel=parallel, sudo=sudo,
                                           timeout=timeout)
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

        return ', '.join(str_rep)


class RemoteScriptAction(ShellScriptAction):
    def __init__(self, name, action_exec_id, script_local_path_abs, script_local_libs_path_abs,
                 named_args=None, positional_args=None, env_vars=None, on_behalf_user=None,
                 user=None, remote_dir=None, hosts=None, parallel=True, sudo=False, timeout=None):
        super(RemoteScriptAction, self).__init__(name=name, action_exec_id=action_exec_id,
                                                 script_local_path_abs=script_local_path_abs,
                                                 named_args=named_args,
                                                 positional_args=positional_args, env_vars=env_vars,
                                                 user=user, sudo=sudo, timeout=timeout)
        self.script_local_libs_path_abs = script_local_libs_path_abs
        self.script_local_dir, self.script_name = os.path.split(self.script_local_path_abs)
        self.remote_dir = remote_dir if remote_dir is not None else '/tmp'
        self.remote_libs_path_abs = os.path.join(self.remote_dir, ACTION_LIBS_DIR)
        self.on_behalf_user = on_behalf_user
        self.remote_script = os.path.join(self.remote_dir, pipes.quote(self.script_name))
        self.hosts = hosts
        self.parallel = parallel
        self.command = self._format_command()
        LOG.debug('RemoteScriptAction: command to run on remote box: %s', self.command)

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


class ParamikoSSHCommandAction(SSHCommandAction):
    pass


class FabricRemoteAction(RemoteAction):
    KEYS_TO_TRANSFORM = ['stdout', 'stderr']

    def get_fabric_task(self):
        action_method = self._get_action_method()
        LOG.debug('action_method is %s', action_method)
        task = WrappedCallableTask(action_method, name=self.name, alias=self.action_exec_id,
                                   parallel=self.parallel, sudo=self.sudo)

        # We need to explicitly set that since WrappedCallableTask abuses kwargs
        # and doesn't do anything with "parallel" and "serial" kwarg.
        # We also need to explicitly set serial since we default to
        # parallel=True in the environment so just "parallel" won't do.
        task.parallel = self.parallel
        task.serial = not self.parallel
        return task

    def _get_action_method(self):
        if (self.sudo):
            return self._sudo
        return self._run

    def _run(self):
        with shell_env(**self.env_vars), settings(command_timeout=self.timeout):
            output = run(self.command, combine_stderr=False, pty=False, quiet=True)
        result = {
            'stdout': output.stdout,
            'stderr': output.stderr,
            'return_code': output.return_code,
            'succeeded': output.succeeded,
            'failed': output.failed
        }
        return jsonify.json_loads(result, FabricRemoteAction.KEYS_TO_TRANSFORM)

    def _sudo(self):
        with shell_env(**self.env_vars), settings(command_timeout=self.timeout):
            output = sudo(self.command, combine_stderr=False, pty=True, quiet=True)
        result = {
            'stdout': output.stdout,
            'stderr': output.stderr,
            'return_code': output.return_code,
            'succeeded': output.succeeded,
            'failed': output.failed
        }

        # XXX: For sudo, fabric requires to set pty=True. This basically combines stdout and
        # stderr into a single stdout stream. So if the command fails, we explictly set stderr
        # to stdout and stdout to ''.
        if result['failed']:
            result['stderr'] = result['stdout']
            result['stdout'] = ''

        return jsonify.json_loads(result, FabricRemoteAction.KEYS_TO_TRANSFORM)


class FabricRemoteScriptAction(RemoteScriptAction, FabricRemoteAction):
    def get_fabric_task(self):
        return self._get_script_action_method()

    def _get_script_action_method(self):
        task = WrappedCallableTask(self._run_script, name=self.name, alias=self.action_exec_id,
                                   parallel=self.parallel, sudo=self.sudo)
        task.parallel = self.parallel
        task.serial = not self.parallel
        return task

    def _run_script(self):
        try:
            self._execute_remote_command('mkdir %s' % self.remote_dir)

            # Copy script.
            output_put = self._put(self.script_local_path_abs,
                                   mirror_local_mode=False, mode=0744)
            if output_put.get('failed'):
                return output_put

            # Copy libs.
            if self.script_local_libs_path_abs and os.path.exists(self.script_local_libs_path_abs):
                output_put_libs = self._put(self.script_local_libs_path_abs)
                if output_put_libs.get('failed'):
                    return output_put_libs

            # Execute action.
            action_method = self._get_action_method()
            result = action_method()

            # Cleanup.
            cmd1 = self._get_command_string(cmd='rm', args=[self.remote_script])
            cmd2 = self._get_command_string(cmd='rm -rf', args=[self.remote_dir])
            self._execute_remote_command(cmd1)
            self._execute_remote_command(cmd2)
        except Exception as e:
            LOG.exception('Failed executing remote action.')
            result = {}
            result.failed = True
            result.succeeded = False
            result.exception = str(e)
        finally:
            return result

    def _get_command_string(self, cmd, args):
        """
        Escape the command arguments and form a command string.

        :type cmd: ``str``
        :type args: ``list``

        :rtype: ``str``
        """
        assert isinstance(args, (list, tuple))

        args = [pipes.quote(arg) for arg in args]
        args = ' '.join(args)
        result = '%s %s' % (cmd, args)
        return result

    def _execute_remote_command(self, command):
        action_method = sudo if self.sudo else run
        output = action_method(command, combine_stderr=False, pty=False, quiet=True)

        if output.failed:
            msg = 'Remote command %s failed.' % command
            LOG.error(msg)
            raise Exception(msg)

        LOG.debug('Remote command %s succeeded.', command)
        return True

    def _put(self, file_or_dir, mirror_local_mode=True, mode=None):
        output = put(file_or_dir, self.remote_dir, use_sudo=self.sudo,
                     mirror_local_mode=mirror_local_mode, mode=mode)

        result = {
            'succeeded': output.succeeded,
            'failed': output.failed
        }

        if output.failed:
            msg = 'Failed copying %s to %s on remote box' % (file_or_dir, self.remote_dir)
            LOG.error(msg)
            result['error'] = msg
        return result

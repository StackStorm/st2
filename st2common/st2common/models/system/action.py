import os

from fabric.api import (put, run, sudo)
from fabric.tasks import WrappedCallableTask

# XXX: This should be read from the config file.
# Set the default user for remote actions.
ENV_USER = 'lakshmi'


class SSHCommandAction(object):
    def __init__(self, name, action_exec_id, command, user, password=None, pkey=None, hosts=None,
                 parallel=True, sudo=False):
        self.name = name
        self.command = command
        self.id = action_exec_id
        self.hosts = hosts
        self.parallel = parallel
        self.sudo = sudo
        self.user = user
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
        str_rep.append('name: ' + self.name)
        str_rep.append('id: ' + self.id)
        str_rep.append('command: ' + self.command)
        str_rep.append('user: ' + self.user)
        str_rep.append('sudo: ' + str(self.sudo))
        str_rep.append('parallel: ' + str(self.parallel))
        str_rep.append('hosts: ' + str(self.hosts))

        return '[' + ', '.join(str_rep) + ']'


class RemoteAction(SSHCommandAction):
    def __init__(self, name, action_exec_id, command, on_behalf_user, hosts=None, parallel=True,
                 sudo=False):
        super(RemoteAction, self).__init__(name, action_exec_id, command, ENV_USER,
                                           hosts=hosts, parallel=parallel, sudo=sudo)
        self.on_behalf_user = on_behalf_user  # Used for audit purposes.

    def get_on_behalf_user(self):
        return self.user

    def __str__(self):
        str_rep = []
        str_rep.append('name: ' + self.name)
        str_rep.append('id: ' + self.id)
        str_rep.append('command: ' + self.command)
        str_rep.append('user: ' + self.user)
        str_rep.append('on_behalf_user: ' + self.on_behalf_user)
        str_rep.append('sudo: ' + str(self.sudo))
        str_rep.append('parallel: ' + str(self.parallel))
        str_rep.append('hosts: ' + str(self.hosts))

        return '[' + ', '.join(str_rep) + ']'


class RemoteScriptAction(RemoteAction):
    def __init__(self, name, action_exec_id, script_local_path_abs,
                 on_behalf_user, remote_dir=None, hosts=None, parallel=True, sudo=False):
        super(RemoteScriptAction, self).__init__(name, action_exec_id, '', ENV_USER,
                                           hosts=hosts, parallel=parallel, sudo=sudo)
        self.script_local_path_abs = script_local_path_abs
        self.script_local_dir, self.script_name = os.path.split(self.script_local_path_abs)

        self.remote_dir = '/tmp'
        if remote_dir is not None:
            self.remote_dir = remote_dir
        self.command = os.path.join(self.remote_dir, self.script_name)


class ParamikoSSHCommandAction(SSHCommandAction):
    pass


class FabricRemoteAction(RemoteAction):
    def get_fabric_task(self):
        action_method = self._get_action_method()
        return WrappedCallableTask(action_method, name=self.name, alias=self.id,
            parallel=self.parallel, sudo=self.sudo)

    def _get_action_method(self):
        if (self.sudo):
            return self._sudo
        return self._run

    def _run(self):
        output = run(self.command, combine_stderr=False, pty=False, quiet=True)
        result = {
            'stdout': output.stdout,
            'stderr': output.stderr,
            'return_code': output.return_code,
            'succeeded': output.succeeded,
            'failed': output.failed
        }
        return result

    def _sudo(self):
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

        return result


class FabricRemoteScriptAction(RemoteScriptAction, FabricRemoteAction):
    def get_fabric_task(self):
        action_method = self._get_script_action_method()
        return WrappedCallableTask(action_method, name=self.name, alias=self.id,
            parallel=self.parallel, sudo=self.sudo)

    def _get_script_action_method(self):
        return WrappedCallableTask(self._run_script, name=self.name, alias=self.id,
            parallel=self.parallel, sudo=self.sudo)

    def _run_script(self):
        output_put = self._put()
        if output_put.get('failed'):
            return output_put
        action_method = self._get_action_method()
        return action_method()

    def _put(self):
        output = put(self.script_local_path_abs, self.remote_dir, use_sudo=self.sudo,
                     mirror_local_mode=True)

        result = {
            'succeeded': output.succeeded,
            'failed': output.failed
        }

        if output.failed:
            result['error'] = 'Failed copying file %s to %s on remote box' % (
                self.script_local_path_abs, self.remote_path)
        return result

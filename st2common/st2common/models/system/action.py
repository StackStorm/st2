import os
import pipes
import uuid

from fabric.api import (put, run, sudo)
from fabric.tasks import WrappedCallableTask

from st2common import log as logging


LOG = logging.getLogger(__name__)


class Writer(object):
    def __init__(self):
        self._id = str(uuid.uuid4())

    def write(self, text):
        text = text or ''
        LOG.info('[Writer: %s] %s', self._id, text)

    def flush(self):
        pass


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
        str_rep.append('%s@%s(name: %s' % (self.__class__.__name__, id(self), self.name))
        str_rep.append('id: %s' % self.id)
        str_rep.append('command: %s' % self.command)
        str_rep.append('user: %s' % self.user)
        str_rep.append('sudo: %s' % str(self.sudo))
        str_rep.append('parallel: %s' % str(self.parallel))
        str_rep.append('hosts: %s)' % str(self.hosts))

        return ', '.join(str_rep)


class RemoteAction(SSHCommandAction):
    def __init__(self, name, action_exec_id, command, on_behalf_user=None, user=None, hosts=None,
                 parallel=True, sudo=False):
        super(RemoteAction, self).__init__(name, action_exec_id, command, user,
                                           hosts=hosts, parallel=parallel, sudo=sudo)
        self.on_behalf_user = on_behalf_user  # Used for audit purposes.

    def get_on_behalf_user(self):
        return self.on_behalf_user

    def __str__(self):
        str_rep = []
        str_rep.append('%s@%s(name: %s' % (self.__class__.__name__, id(self), self.name))
        str_rep.append('id: %s' % self.id)
        str_rep.append('command: %s' % self.command)
        str_rep.append('user: %s' % self.user)
        str_rep.append('on_behalf_user: %s' % self.on_behalf_user)
        str_rep.append('sudo: %s' % str(self.sudo))
        str_rep.append('parallel: %s' % str(self.parallel))
        str_rep.append('hosts: %s)' % str(self.hosts))

        return ', '.join(str_rep)


class RemoteScriptAction(RemoteAction):
    def __init__(self, name, action_exec_id, script_local_path_abs, named_args=None,
                 positional_args=None, on_behalf_user=None, user=None, remote_dir=None, hosts=None,
                 parallel=True, sudo=False):
        super(RemoteScriptAction, self).__init__(name, action_exec_id, '', on_behalf_user, user,
                                                 hosts=hosts, parallel=parallel, sudo=sudo)
        self.script_local_path_abs = script_local_path_abs
        self.script_local_dir, self.script_name = os.path.split(self.script_local_path_abs)
        self.named_args = named_args
        self.positional_args = positional_args

        self.remote_dir = remote_dir if remote_dir is not None else '/tmp'
        self.remote_script = os.path.join(self.remote_dir, pipes.quote(self.script_name))
        self.command = self._format_command()
        LOG.debug('RemoteScriptAction: command to run on remote box: %s', self.command)

    def _format_command(self):
        command_parts = []
        command_parts.append(self.remote_script)
        # add all named_args in the format name=value
        if self.named_args is not None:
            for (arg, value) in self.named_args.items():
                if value is None or len(value) < 1:
                    LOG.debug('Ignoring named arg %s as its value is %s.', arg, value)
                    continue
                command_parts.append('%s=%s' % (arg, pipes.quote(value)))
        # add the positional args
        if self.positional_args:
            command_parts.append(self.positional_args)
        return ' '.join(command_parts)

    def __str__(self):
        str_rep = []
        str_rep.append('%s@%s(name: %s' % (self.__class__.__name__, id(self), self.name))
        str_rep.append('id: %s' % self.id)
        str_rep.append('local_script: %s' % self.script_local_path_abs)
        str_rep.append('remote_dir: %s' % self.remote_dir)
        str_rep.append('named_args: %s' % self.named_args)
        str_rep.append('positional_args: %s' % self.positional_args)
        str_rep.append('command: %s' % self.command)
        str_rep.append('user: %s' % self.user)
        str_rep.append('on_behalf_user: %s' % self.on_behalf_user)
        str_rep.append('sudo: %s' % self.sudo)
        str_rep.append('parallel: %s' % self.parallel)
        str_rep.append('hosts: %s)' % self.hosts)

        return ', '.join(str_rep)


class ParamikoSSHCommandAction(SSHCommandAction):
    pass


class FabricRemoteAction(RemoteAction):
    def get_fabric_task(self):
        action_method = self._get_action_method()
        LOG.info('action_method is %s' % action_method)
        return WrappedCallableTask(action_method, name=self.name, alias=self.id,
                                   parallel=self.parallel, sudo=self.sudo)

    def _get_action_method(self):
        if (self.sudo):
            return self._sudo
        return self._run

    def _run(self):
        output = run(self.command, combine_stderr=False, pty=False, quiet=False,
                     stdout=Writer(), stderr=Writer())
        result = {
            'stdout': output.stdout,
            'stderr': output.stderr,
            'return_code': output.return_code,
            'succeeded': output.succeeded,
            'failed': output.failed
        }
        return result

    def _sudo(self):
        output = sudo(self.command, combine_stderr=False, pty=True, quiet=False,
                     stdout=Writer(), stderr=Writer())
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
        return self._get_script_action_method()

    def _get_script_action_method(self):
        return WrappedCallableTask(self._run_script, name=self.name, alias=self.id,
                                   parallel=self.parallel, sudo=self.sudo)

    def _run_script(self):
        try:
            output_put = self._put()
            if output_put.get('failed'):
                return output_put
            action_method = self._get_action_method()
            result = action_method()
            self._rm()
        except Exception as e:
            result = {}
            result.failed = True
            result.succeeded = False
            result.exception = str(e)
        finally:
            return result

    def _put(self):
        output = put(self.script_local_path_abs, self.remote_dir, use_sudo=self.sudo,
                     mirror_local_mode=True)

        result = {
            'succeeded': output.succeeded,
            'failed': output.failed
        }

        if output.failed:
            LOG.error('Failed copying file %s to remote host.', self.script_local_path_abs)
            result['error'] = 'Failed copying file %s to %s on remote box' % (
                self.script_local_path_abs, self.remote_dir)
        return result

    def _rm(self):
        action_method = sudo if self.sudo else run
        rm_command = 'rm %s' % self.remote_script
        output = action_method(rm_command, combine_stderr=False, pty=False, quiet=True)
        if output.failed:
            LOG.error('Failed to remove file %s from remote host.', self.remote_script)
        else:
            LOG.debug('Succesfully cleaned up file %s from remote host.', self.remote_script)

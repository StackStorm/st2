import os
import uuid

# from st2common import log as logging

from fabric.api import (env, execute, put, run, sudo)
from fabric.tasks import WrappedCallableTask

# Replace with container call to get logger.
# LOG = logging.getLogger('st2actions.runner.fabric_runner')

# Fabric environment level settings.
# XXX: Note fabric env is a global singleton.
env.parallel = True  # By default, execute things in parallel. Uses multiprocessing under the hood.
env.user = 'lakshmi'  # Detect who is the owner of this process and use his ssh keys.
env.timeout = 60  # Timeout for commands. 1 minute.
env.combine_stderr = False
env.group = 'staff'


class FabricRunner(object):
    def __init__(self, id):
        self.runner_id = id

    def run(self, remote_action):
        print('Executing action via FabricRunner :%s for user: %s.' %
              (self.runner_id, remote_action.on_behalf_user))
        print('Action info:: Name: %s, Id: %s, command: %s, actual user: %s' % (remote_action.name,
            remote_action.id, remote_action.command, env.user))
        results = execute(remote_action.get_fabric_task(), hosts=remote_action.hosts)
        return results


class StanleyCommandAction(object):
    def __init__(self, name, action_exec_id, command, on_behalf_user, hosts=None, parallel=True,
                 sudo=False):
        self.name = name
        self.command = command
        self.id = action_exec_id
        self.hosts = hosts
        self.parallel = parallel
        self.sudo = sudo
        self.on_behalf_user = on_behalf_user

    def get_fabric_task(self):
        action_method = self._get_action_method()
        return WrappedCallableTask(action_method, name=self.name, alias=self.id,
            parallel=self.parallel, sudo=self.sudo)

    def is_parallel(self):
        return self.parallel

    def is_sudo(self):
        return self.sudo

    def get_user(self):
        return self.on_behalf_user

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


class StanleyScriptAction(StanleyCommandAction):
    def __init__(self, name, action_exec_id, script_local_path_abs,
                 on_behalf_user, remote_dir=None, hosts=None, parallel=True, sudo=False):
        super(StanleyScriptAction, self).__init__(name, action_exec_id, '', on_behalf_user,
                                                  hosts, parallel, sudo)
        self.name = name
        self.script_local_path_abs = script_local_path_abs
        self.id = action_exec_id
        self.hosts = hosts
        self.parallel = parallel
        self.sudo = sudo
        self.on_behalf_user = on_behalf_user
        print('Script: %s' % self.script_local_path_abs)
        self.script_local_dir, self.script_name = os.path.split(self.script_local_path_abs)

        print('Script name: %s' % self.script_name)
        self.remote_dir = '/tmp'
        if remote_dir is not None:
            self.remote_dir = remote_dir
        print('Remote dir: %s' % self.remote_dir)
        self.command = os.path.join(self.remote_dir, self.script_name)

    def _get_action_method(self):
        return WrappedCallableTask(self._run_script, name=self.name, alias=self.id,
            parallel=self.parallel, sudo=self.sudo)

    def _run_script(self):
        output_put = self._put()
        if output_put.get('failed'):
            return output_put
        action_method = super(StanleyScriptAction, self)._get_action_method()
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

if __name__ == '__main__':
    print('!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!')
    print('!!!!!!!!!!!!!!!!!!!!! NORMAL CMD !!!!!!!!!!!!!!!!!!!!!!!!!!')
    print('!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!')
    runner = FabricRunner(str(uuid.uuid4()))
    remote_action = StanleyCommandAction('UNAME', 'action_exec_id' + str(uuid.uuid4()), 'unam -a',
                                        'narcissist', hosts=['Ekalavya.local', '54.191.85.86',
                                        '54.191.17.38', '54.200.102.55'])
    results = runner.run(remote_action)

    print('!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!')
    print('!!!!!!!!!!!!!!!!!!!!! RESULTS !!!!!!!!!!!!!!!!!!!!!!!!!!!!!')
    print('!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!')

    print(results)

    print('!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!')
    print('!!!!!!!!!!!!!!!!!!!!! SUDO CMD !!!!!!!!!!!!!!!!!!!!!!!!!!')
    print('!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!')
    runner = FabricRunner(str(uuid.uuid4()))
    remote_action = StanleyCommandAction('UNAME', 'action_exec_id' + str(uuid.uuid4()), 'unam -a',
                                        'narcissist', hosts=['54.191.85.86',
                                        '54.191.17.38', '54.200.102.55'], parallel=True, sudo=True)
    results = runner.run(remote_action)

    print('!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!')
    print('!!!!!!!!!!!!!!!!!!!!! RESULTS !!!!!!!!!!!!!!!!!!!!!!!!!!!!!')
    print('!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!')

    print(results)

    print('!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!')
    print('!!!!!!!!!!!!!!!!!!!!! SCRIPT DAWG !!!!!!!!!!!!!!!!!!!!!!!!!!!')
    print('!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!')
    script_action = StanleyScriptAction('UNAME', 'action_exec_id' + str(uuid.uuid4()),
                                        '/tmp/uname-script.sh', 'narcissist',
                                        hosts=['54.191.85.86'], parallel=True, sudo=False)
    results = runner.run(script_action)

    print('!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!')
    print('!!!!!!!!!!!!!!!!!!!!! RESULTS !!!!!!!!!!!!!!!!!!!!!!!!!!!!!')
    print('!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!')

    print(results)

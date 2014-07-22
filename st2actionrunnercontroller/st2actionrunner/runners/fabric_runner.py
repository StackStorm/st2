import uuid

from fabric.api import (env, execute)

from st2common import log as logging
from st2common.models.system.action import (FabricRemoteAction, FabricRemoteScriptAction)

# Replace with container call to get logger.
LOG = logging.getLogger('st2.actions.runner.fabric_runner')

# Fabric environment level settings.
# XXX: Note fabric env is a global singleton.
env.parallel = True  # By default, execute things in parallel. Uses multiprocessing under the hood.
env.user = 'lakshmi'  # Detect who is the owner of this process and use his ssh keys.
env.timeout = 60  # Timeout for commands. 1 minute.
env.combine_stderr = False
env.group = 'staff'


def get_runner():
    return FabricRunner()


class FabricRunner(object):
    def __init__(self, id):
        self.runner_id = id

    def run(self, remote_action):
        LOG.info('Executing action via FabricRunner :%s for user: %s.',
                 self.runner_id, remote_action.get_on_behalf_user())
        LOG.info('[Action info] name: %s, Id: %s, command: %s, on behalf user: %s, actual user: %s',
                 remote_action.name, remote_action.id, remote_action.get_command(),
                 remote_action.get_on_behalf_user(), remote_action.get_user())
        results = execute(remote_action.get_fabric_task(), hosts=remote_action.hosts)
        return results


# XXX: Write proper tests.

if __name__ == '__main__':
    print('!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!')
    print('!!!!!!!!!!!!!!!!!!!!! NORMAL CMD !!!!!!!!!!!!!!!!!!!!!!!!!!')
    print('!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!')
    runner = FabricRunner(str(uuid.uuid4()))
    remote_action = FabricRemoteAction('UNAME', 'action_exec_id' + str(uuid.uuid4()), 'unam -a',
                                 'narcissist', hosts=['54.191.85.86',
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
    remote_action = FabricRemoteAction('UNAME', 'action_exec_id' + str(uuid.uuid4()), 'unam -a',
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
    script_action = FabricRemoteScriptAction('UNAME', 'action_exec_id' + str(uuid.uuid4()),
                                 '/tmp/uname-script.sh', 'narcissist',
                                 hosts=['54.191.85.86'], parallel=True, sudo=False)
    results = runner.run(script_action)

    print('!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!')
    print('!!!!!!!!!!!!!!!!!!!!! RESULTS !!!!!!!!!!!!!!!!!!!!!!!!!!!!!')
    print('!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!')

    print(results)

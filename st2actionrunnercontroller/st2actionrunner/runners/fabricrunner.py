import os
import uuid

from fabric.api import (env, execute)

from oslo.config import cfg

from st2actionrunner.runners import ActionRunner
from st2common import log as logging
from st2common.exceptions.actionrunner import (ActionRunnerPreRunError, ActionRunnerException)
from st2common.models.system.action import (FabricRemoteAction, FabricRemoteScriptAction)

# Replace with container call to get logger.
LOG = logging.getLogger(__name__)

# Fabric environment level settings.
# XXX: Note fabric env is a global singleton.
env.parallel = True  # By default, execute things in parallel. Uses multiprocessing under the hood.
env.user = cfg.CONF.fabric_runner.user  # Detect who is the owner of this process and use his ssh keys.
env.timeout = 60  # Timeout for commands. 1 minute.
env.combine_stderr = False
env.group = 'staff'

# constants to lookup in runner_parameters.
RUNNER_HOSTS = 'hosts'
RUNNER_PARALLEL = 'parallel'
RUNNER_SUDO = 'sudo'
RUNNER_ON_BEHALF_USER = 'user'
RUNNER_REMOTE_DIR = 'remotedir'
RUNNER_COMMAND = 'command'
ARGS_PARAM = 'args'


class FabricRunner(ActionRunner):
    def __init__(self, id):
        super(FabricRunner, self).__init__()
        self._runner_id = id
        self._hosts = None
        self._parallel = True
        self._sudo = False
        self._on_behalf_user = None
        self._user = None

    def pre_run(self):
        LOG.debug('Entering FabricRunner.pre_run() for liveaction_id="%s"', self.liveaction_id)
        LOG.debug('    runner_parameters = %s', self.runner_parameters)
        hosts = self.runner_parameters.get(RUNNER_HOSTS, '').split(',')
        self._hosts = [h.strip() for h in hosts if len(h) > 0]
        if len(self._hosts) < 1:
            raise ActionRunnerPreRunError('No hosts specified to run action for liveaction %s.',
                                          self.liveaction_id)
        parallel = self.runner_parameters.get(RUNNER_PARALLEL, 'true')
        self._parallel = True if parallel is None else parallel.lower() == 'true'
        sudo = self.runner_parameters.get(RUNNER_SUDO, 'false')
        self._sudo = False if sudo is None else sudo.lower() == 'true'
        self._on_behalf_user = self.runner_parameters.get(RUNNER_ON_BEHALF_USER, env.user)
        self._user = cfg.CONF.fabric_runner.user

        LOG.info('[FabricRunner="%s",liveaction_id="%s"] Finished pre_run.',
                 self._runner_id, self.liveaction_id)

    def run(self, action_parameters):
        LOG.debug('    action_parameters = %s', action_parameters)
        remote_action = self._get_fabric_remote_action(action_parameters) \
            if self.entry_point is None or len(self.entry_point) < 1 \
            else self._get_fabric_remote_script_action(action_parameters)
        LOG.debug('Will execute remote_action : %s.', str(remote_action))
        try:
            result = self._run(remote_action)
        except ActionRunnerException as e:
            LOG.exception('    Failed to run remote_action : %s.', e.message)
            raise
        LOG.debug('Executed remote_action : %s. Result is : %s.', remote_action, result)
        self.container_service.report_result(result)
        # TODO (manas) : figure out the right boolean representation.
        return result is not None

    def post_run(self):
        pass

    def _run(self, remote_action):
        LOG.info('Executing action via FabricRunner :%s for user: %s.',
                 self._runner_id, remote_action.get_on_behalf_user())
        LOG.info('[Action info] name: %s, Id: %s, command: %s, on behalf user: %s, actual user: %s',
                 remote_action.name, remote_action.id, remote_action.get_command(),
                 remote_action.get_on_behalf_user(), remote_action.get_user())
        results = execute(remote_action.get_fabric_task(), hosts=remote_action.hosts)
        return results

    def _get_fabric_remote_action(self, action_paramaters):
        command = self.runner_parameters.get(RUNNER_COMMAND, None)
        return FabricRemoteAction(self.action_name,
                                  str(self.liveaction_id),
                                  command,
                                  on_behalf_user=self._on_behalf_user,
                                  user=self._user,
                                  hosts=self._hosts,
                                  parallel=self._parallel,
                                  sudo=self._sudo)

    def _get_fabric_remote_script_action(self, action_parameters):
        script_args = ''
        if ARGS_PARAM in action_parameters:
            # Use the 'args' param from the action_parameters if it
            # was not provided in runner parameters.
            script_args = action_parameters[ARGS_PARAM]
        script_local_path = os.path.join(self.container_service.get_artifact_repo_path(),
                                         self.entry_point)
        script_local_path_abs = os.path.abspath(script_local_path)
        remote_dir = self.runner_parameters.get(RUNNER_REMOTE_DIR,
                                                cfg.CONF.fabric_runner.remote_dir)
        # TODO(manas) : add support for args to a script.
        # args = action_parameter.get(ACTION_ARGS, '')
        return FabricRemoteScriptAction(self.action_name,
                                        str(self.liveaction_id),
                                        script_local_path_abs,
                                        script_args=script_args,
                                        on_behalf_user=self._on_behalf_user,
                                        user=self._user,
                                        remote_dir=remote_dir,
                                        hosts=self._hosts,
                                        parallel=self._parallel,
                                        sudo=self._sudo)


def get_runner():
    return FabricRunner(str(uuid.uuid4()))


# XXX: Write proper tests.
if __name__ == '__main__':

    print('!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!')
    print('!!!!!!!!!!!!!!!!!!!!! NORMAL CMD !!!!!!!!!!!!!!!!!!!!!!!!!!')
    print('!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!')
    runner = FabricRunner(str(uuid.uuid4()))
    remote_action = FabricRemoteAction('UNAME', 'action_exec_id' + str(uuid.uuid4()), 'uname -a',
                                       'narcissist', 'stanley', hosts=['54.191.85.86',
                                       '54.191.17.38', '54.200.102.55'])
    print(str(remote_action))
    results = runner._run(remote_action)

    print('!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!')
    print('!!!!!!!!!!!!!!!!!!!!! RESULTS !!!!!!!!!!!!!!!!!!!!!!!!!!!!!')
    print('!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!')

    print(results)

    print('!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!')
    print('!!!!!!!!!!!!!!!!!!!!! SUDO CMD !!!!!!!!!!!!!!!!!!!!!!!!!!')
    print('!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!')
    runner = FabricRunner(str(uuid.uuid4()))
    remote_action = FabricRemoteAction('UNAME', 'action_exec_id' + str(uuid.uuid4()), 'uname -a',
                                       'narcissist', 'stanley', hosts=['54.191.85.86',
                                       '54.191.17.38', '54.200.102.55'], parallel=True, sudo=True)
    results = runner._run(remote_action)

    print('!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!')
    print('!!!!!!!!!!!!!!!!!!!!! RESULTS !!!!!!!!!!!!!!!!!!!!!!!!!!!!!')
    print('!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!')

    print(results)

    print('!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!')
    print('!!!!!!!!!!!!!!!!!!!!! SCRIPT DAWG !!!!!!!!!!!!!!!!!!!!!!!!!!!')
    print('!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!')
    script_action = FabricRemoteScriptAction('UNAME', 'action_exec_id' + str(uuid.uuid4()),
                                             '/tmp/ls-script.sh', script_args='/tmp',
                                             on_behalf_user='narcissist',
                                             user='stanley', hosts=['54.191.85.86'],
                                             parallel=True, sudo=False)
    results = runner._run(script_action)

    print('!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!')
    print('!!!!!!!!!!!!!!!!!!!!! RESULTS !!!!!!!!!!!!!!!!!!!!!!!!!!!!!')
    print('!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!')

    print(results)

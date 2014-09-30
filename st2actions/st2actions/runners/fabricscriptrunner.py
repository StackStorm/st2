import os
import uuid

from fabric.api import (env, execute)

from oslo.config import cfg

from st2actions.runners import ActionRunner
from st2common import log as logging
from st2common.exceptions.actionrunner import (ActionRunnerPreRunError, ActionRunnerException)
from st2common.exceptions.fabricrunner import FabricExecutionFailureException
from st2common.models.system.action import FabricRemoteScriptAction
import st2common.util.action_db as action_utils

# Replace with container call to get logger.
LOG = logging.getLogger(__name__)

# Fabric environment level settings.
# XXX: Note fabric env is a global singleton.
env.parallel = True  # By default, execute things in parallel. Uses multiprocessing under the hood.
env.user = cfg.CONF.ssh_runner.user
ssh_key_file = cfg.CONF.ssh_runner.ssh_key_file
if ssh_key_file is not None and os.path.exists(ssh_key_file):
    env.key_filename = ssh_key_file
env.timeout = 60  # Timeout for commands. 1 minute.
env.combine_stderr = False
env.group = 'staff'
env.abort_exception = FabricExecutionFailureException

# constants to lookup in runner_parameters.
RUNNER_HOSTS = 'hosts'
RUNNER_PARALLEL = 'parallel'
RUNNER_SUDO = 'sudo'
RUNNER_ON_BEHALF_USER = 'user'
RUNNER_REMOTE_DIR = 'dir'


def get_runner():
    return FabricScriptRunner(str(uuid.uuid4()))


class FabricScriptRunner(ActionRunner):
    def __init__(self, id):
        super(FabricScriptRunner, self).__init__()
        self._runner_id = id
        self._hosts = None
        self._parallel = True
        self._sudo = False
        self._on_behalf_user = None
        self._user = None

    def pre_run(self):
        LOG.debug('Entering FabricRunner.pre_run() for actionexec_id="%s"',
                  self.action_execution_id)
        LOG.debug('    runner_parameters = %s', self.runner_parameters)
        hosts = self.runner_parameters.get(RUNNER_HOSTS, '').split(',')
        self._hosts = [h.strip() for h in hosts if len(h) > 0]
        if len(self._hosts) < 1:
            raise ActionRunnerPreRunError('No hosts specified to run action for action %s.',
                                          self.action_execution_id)
        self._parallel = self.runner_parameters.get(RUNNER_PARALLEL, True)
        self._sudo = self.runner_parameters.get(RUNNER_SUDO, False)
        self._on_behalf_user = self.runner_parameters.get(RUNNER_ON_BEHALF_USER, env.user)
        self._user = cfg.CONF.ssh_runner.user

        LOG.info('[FabricRunner="%s", actionexec_id="%s"] Finished pre_run.',
                 self._runner_id, self.action_execution_id)

    def run(self, action_parameters):
        LOG.debug('    action_parameters = %s', action_parameters)
        remote_action = self._get_fabric_remote_script_action(action_parameters)
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

    def _run(self, remote_action):
        LOG.info('Executing action via FabricRunner :%s for user: %s.',
                 self._runner_id, remote_action.get_on_behalf_user())
        LOG.info('[Action info] name: %s, Id: %s, command: %s, on behalf user: %s, actual user: %s',
                 remote_action.name, remote_action.id, remote_action.get_command(),
                 remote_action.get_on_behalf_user(), remote_action.get_user())
        results = execute(remote_action.get_fabric_task(), hosts=remote_action.hosts)
        return results

    def _get_fabric_remote_script_action(self, action_parameters):
        script_local_path_abs = self.entry_point
        pos_args, named_args = action_utils.get_args(action_parameters, self.action)
        remote_dir = self.runner_parameters.get(RUNNER_REMOTE_DIR,
                                                cfg.CONF.ssh_runner.remote_dir)
        return FabricRemoteScriptAction(self.action_name,
                                        str(self.action_execution_id),
                                        script_local_path_abs,
                                        named_args=named_args,
                                        positional_args=pos_args,
                                        on_behalf_user=self._on_behalf_user,
                                        user=self._user,
                                        remote_dir=remote_dir,
                                        hosts=self._hosts,
                                        parallel=self._parallel,
                                        sudo=self._sudo)

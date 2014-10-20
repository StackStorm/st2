import os
import uuid

from fabric.api import (env, execute)
from oslo.config import cfg
import six

from st2actions.runners import ActionRunner
from st2common import log as logging
from st2common.exceptions.actionrunner import ActionRunnerPreRunError
from st2common.exceptions.fabricrunner import FabricExecutionFailureException
from st2common.models.api.constants import ACTIONEXEC_STATUS_SUCCEEDED, ACTIONEXEC_STATUS_FAILED
from st2common.models.system.action import (FabricRemoteAction, FabricRemoteScriptAction)
import st2common.util.action_db as action_utils

# Replace with container call to get logger.
LOG = logging.getLogger(__name__)

# Fabric environment level settings.
# XXX: Note fabric env is a global singleton.
env.parallel = True  # By default, execute things in parallel. Uses multiprocessing under the hood.
env.user = cfg.CONF.system_user.user
ssh_key_file = cfg.CONF.system_user.ssh_key_file
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
RUNNER_COMMAND = 'cmd'
RUNNER_KWARG_OP = 'kwarg_op'


def get_runner():
    return FabricRunner(str(uuid.uuid4()))


class FabricRunner(ActionRunner):
    def __init__(self, id):
        super(FabricRunner, self).__init__()
        self._runner_id = id
        self._hosts = None
        self._parallel = True
        self._sudo = False
        self._on_behalf_user = None
        self._user = None
        self._kwarg_op = '--'

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
        self._on_behalf_user = self.context.get(RUNNER_ON_BEHALF_USER, env.user)
        self._user = cfg.CONF.system_user.user
        self._kwarg_op = self.runner_parameters.get(RUNNER_KWARG_OP, '--')

        LOG.info('[FabricRunner="%s", actionexec_id="%s"] Finished pre_run.',
                 self._runner_id, self.action_execution_id)

    def run(self, action_parameters):
        LOG.debug('    action_parameters = %s', action_parameters)
        remote_action = self._get_fabric_remote_action(action_parameters) \
            if self.entry_point is None or len(self.entry_point) < 1 \
            else self._get_fabric_remote_script_action(action_parameters)
        LOG.debug('Will execute remote_action : %s.', str(remote_action))
        result = self._run(remote_action)
        LOG.debug('Executed remote_action : %s. Result is : %s.', remote_action, result)
        self.container_service.report_status(FabricRunner._get_result_status(
            result, cfg.CONF.ssh_runner.allow_partial_failure))
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

    def _get_fabric_remote_action(self, action_paramaters):
        command = self.runner_parameters.get(RUNNER_COMMAND, None)
        env_vars = self._get_env_vars()
        return FabricRemoteAction(self.action_name,
                                  str(self.action_execution_id),
                                  command,
                                  env_vars=env_vars,
                                  on_behalf_user=self._on_behalf_user,
                                  user=self._user,
                                  hosts=self._hosts,
                                  parallel=self._parallel,
                                  sudo=self._sudo)

    def _get_fabric_remote_script_action(self, action_parameters):
        script_local_path_abs = self.entry_point
        pos_args, named_args = self._get_script_args(action_parameters)
        named_args = self._transform_pos_args(named_args)
        env_vars = self._get_env_vars()
        remote_dir = self.runner_parameters.get(RUNNER_REMOTE_DIR,
                                                cfg.CONF.ssh_runner.remote_dir)
        remote_dir = os.path.join(remote_dir, self.action_execution_id)
        return FabricRemoteScriptAction(self.action_name,
                                        str(self.action_execution_id),
                                        script_local_path_abs,
                                        self.libs_dir_path,
                                        named_args=named_args,
                                        positional_args=pos_args,
                                        env_vars=env_vars,
                                        on_behalf_user=self._on_behalf_user,
                                        user=self._user,
                                        remote_dir=remote_dir,
                                        hosts=self._hosts,
                                        parallel=self._parallel,
                                        sudo=self._sudo)

    def _transform_pos_args(self, named_args):
        if named_args:
            return {self._kwarg_op + k: v for (k, v) in six.iteritems(named_args)}
        return None

    def _get_script_args(self, action_parameters):
        is_script_run_as_cmd = self.runner_parameters.get(RUNNER_COMMAND, None)
        pos_args = ''
        named_args = {}
        if is_script_run_as_cmd:
            pos_args = self.runner_parameters.get(RUNNER_COMMAND, '')
            named_args = action_parameters
        else:
            pos_args, named_args = action_utils.get_args(action_parameters, self.action)
        return pos_args, named_args

    def _get_env_vars(self):
        return {'st2_auth_token': self.auth_token.token} if self.auth_token else {}

    @staticmethod
    def _get_result_status(result, allow_partial_failure):
        success = not allow_partial_failure
        for r in six.itervalues(result):
            if allow_partial_failure:
                success |= r.get('succeeded', False)
                if success:
                    return ACTIONEXEC_STATUS_SUCCEEDED
            else:
                success &= r.get('succeeded', False)
                if not success:
                    return ACTIONEXEC_STATUS_FAILED
        return ACTIONEXEC_STATUS_SUCCEEDED if success else ACTIONEXEC_STATUS_FAILED


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
                                             '/tmp/ls-script.sh', named_args={},
                                             positional_args='/tmp', on_behalf_user='narcissist',
                                             user='stanley', hosts=['54.191.85.86'],
                                             parallel=True, sudo=False)
    results = runner._run(script_action)

    print('!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!')
    print('!!!!!!!!!!!!!!!!!!!!! RESULTS !!!!!!!!!!!!!!!!!!!!!!!!!!!!!')
    print('!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!')

    print(results)

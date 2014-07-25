import subprocess

from st2actionrunner.runners import ActionRunner

from st2common import log as logging
from st2actionrunner.container.service import (STDOUT, STDERR)


# Replace with container call to get logger.
LOG = logging.getLogger(__name__)


COMMAND_PARAM = 'command'
CONSUMED_ACTION_PARAMETERS = [COMMAND_PARAM]


class InternalDummyRunner(ActionRunner):
    """
        InternalActionRunner is an action runner for shell commands.

        The expected runner parameters are:
            command:  The shell command to be executed.

        Note: command will be consumed from the action_parameters if
              it is not found in the runner_parameters.

        All action arguments are made available in the shell environment for the action.
    """

    def __init__(self):
        ActionRunner.__init__(self)
        # TODO: runner LOG might be better held in container_service.
        # LOG = self.container_service.get_logger('internaldummy')
        # TODO: Replace with container call to get logger.
        # LOG.info('Internal Dummy Runner logging to logger name: %s', LOG.name)

    def pre_run(self):
        LOG.info('In InternalDummyRunner.pre_run()')
        self._command = self.runner_parameters[COMMAND_PARAM]
        LOG.debug('    [Internal Dummy Runner] "%s" argument is: %s', COMMAND_PARAM, self._command)

    def run(self, action_parameters):
        """
            ActionRunner for "internaldummy" ActionType.
            Implemented as an ActionRunner plugin.

            !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
            !!!!!!!    This is for internal scaffolding use only.    !!!!!!!
            !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!

        """
        LOG.info('In InternalDummyRunner.run()')
        LOG.info('Entering Internal Dummy Runner')

        command_list = self._command
        LOG.debug('    [Internal Dummy Runner] command list is: %s', command_list)

        command_env = dict(action_parameters)
        for name in CONSUMED_ACTION_PARAMETERS:
            if name in command_env:
                del command_env[name]

        LOG.debug('    [Internal Dummy Runner] Launching command as blocking operation.')
        process = subprocess.Popen(command_list, stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE, env=command_env, shell=True)

        command_stdout, command_stderr = process.communicate()
        command_exitcode = process.returncode

        LOG.debug('    [Internal Dummy Runner] command_stdout: %s', command_stdout)
        LOG.debug('    [Internal Dummy Runner] command_stderr: %s', command_stderr)
        LOG.debug('    [Internal Dummy Runner] command_exit: %s', command_exitcode)
        LOG.debug('    [Internal Dummy Runner] TODO: Save output to DB')

        result = {'exit_code': command_exitcode,
                  'std_out': command_stdout,
                  'std_err': command_stderr}

        self.container_service.report_result(result)

        return (command_exitcode, command_stdout, command_stderr)

    def post_run(self):
        LOG.info('In InternalDummyRunner.post_run()')


def get_runner():
    return InternalDummyRunner()

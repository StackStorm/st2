import subprocess

from st2actionrunner.runners import ActionRunner

from st2common import log as logging
from st2actionrunner.container.service import (STDOUT, STDERR)


# Replace with container call to get logger.
LOG = logging.getLogger(__name__)


class InternalDummyRunner(ActionRunner):

    def __init__(self):
        pass

    def pre_run(self):
        # TODO: Replace with container call to get logger.
        # LOG = logging.getLogger(__name__)

        LOG.info('In InternalDummyRunner.pre_run()')
        self._command = self.parameters['command']
        LOG.debug('    [Internal Dummy Runner] command list is: %s', self._command)

    def run(self, action_parameters):
        """
            ActionRunner for "internaldummy" ActionType.

            !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
            !!!!!!!    This is for internal scaffolding use only.    !!!!!!!
            !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!

        """
        LOG.info('In InternalDummyRunner.run()')
        LOG.info('Entering Internal Dummy Runner')

        command_list = self._command
        LOG.debug('    [Internal Dummy Runner] command list is: %s', command_list)

        LOG.debug('    [Internal Dummy Runner] Launching command as blocking operation.')
        process = subprocess.Popen(command_list, stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE, shell=True)

        command_stdout, command_stderr = process.communicate()
        command_exitcode = process.returncode

        LOG.debug('    [Internal Dummy Runner] command_stdout: %s', command_stdout)
        LOG.debug('    [Internal Dummy Runner] command_stderr: %s', command_stderr)
        LOG.debug('    [Internal Dummy Runner] command_exit: %s', command_exitcode)
        LOG.debug('    [Internal Dummy Runner] TODO: Save output to DB')

        self.container_service.report_exit_code(command_exitcode)
        self.container_service.report_output(STDOUT, command_stdout)
        self.container_service.report_output(STDERR, command_stderr)

        return (command_exitcode, command_stdout, command_stderr)

    def post_run(self):
        LOG.info('In InternalDummyRunner.post_run()')


def get_runner():
    return InternalDummyRunner()

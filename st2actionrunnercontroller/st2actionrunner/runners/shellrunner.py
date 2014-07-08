import os
import shlex
import subprocess

from st2actionrunner.runners import ActionRunner

from st2common import log as logging
from st2common.exceptions.actionrunner import ActionRunnerPreRunError
from st2actionrunner.container.service import (STDOUT, STDERR)


# Replace with container call to get logger.
LOG = logging.getLogger(__name__)


UNABLE_TO_CONTINUE_MSG = 'Unable to continue execution of Live Action id=%s'


ARGS_PARAM = 'args'
SHELL_PARAM = 'shell'

CONSUMED_ACTION_PARAMETERS = [ARGS_PARAM, SHELL_PARAM]


class ShellRunner(ActionRunner):
    """
        ShellRunner is an action runner for shell commands.

        The expected runner parameters are:
            shell:  Currently ignored. Planned to specify the shell to execute.
            args:   The argument string for the command executed.

        Note: args will be consumed from the action_parameters if
              it is not found in the runner_parameters.

        All action arguments are made available in the shell environment for the action.
    """

    def __init__(self):
        ActionRunner.__init__(self)

    def pre_run(self):
        LOG.debug('Entering ShellRunner.pre_run() for liveaction_id="%s"', self.liveaction_id)

        self._shell = self.parameters[SHELL_PARAM]
        if ARGS_PARAM in self.parameters:
            self._args = self.parameters[ARGS_PARAM]
        else:
            # Use the 'args' param from the action_parameters if it
            # was not provided in runner parameters.
            self._args = self.action_parameters[ARGS_PARAM]

        if self._args is None:
            LOG.warning('No value for "%s" provided to Shell Runner for liveaction_id="%s".',
                        ARGS_PARAM, self.liveaction_id)
            self._args = ''

        LOG.debug('    [ShellRunner,liveaction_id="%s"] Runner argument "%s" is: "%s"',
                  self.liveaction_id, SHELL_PARAM, self._shell)
        LOG.debug('    [ShellRunner,liveaction_id="%s"] Runner argument "%s" is: "%s"',
                  self.liveaction_id, SHELL_PARAM, self._shell)

        # Create a temporary working directory for action
        self._workingdir = self.container_service.create_runner_folder()

        if not self.container_service.populate_runner_folder(self.artifact_paths):
            error_msg = ('Encountered error while populating Action Runner folder ' +
                         '"%s" for liveaction_id="%s"') % (self._workingdir, self.liveaction_id)
            LOG.error(error_msg)
            raise ActionRunnerPreRunError(error_msg)

        LOG.info('    [ShellRunner,liveaction_id="%s"] Finished pre_run populating temporary '
                 'artifact folder "%s"', self.liveaction_id, self._workingdir)

    def run(self, action_parameters):
        """
            ActionRunner for "shell" ActionType.
        """
        LOG.debug('Entering ShellRunner.run() for liveaction_id="%s"', self.liveaction_id)

        old_dir = os.getcwd()
        os.chdir(self._workingdir)
        command_list = shlex.split(str(self.entry_point) + ' ' + str(self._args))

        # Convert env dictionary to strings rather than unicode strings.
        # Trying to get shell variables working.
        command_env = dict([(str(k), str(v)) for (k,v) in action_parameters.items()])
        for name in CONSUMED_ACTION_PARAMETERS:
            if name in command_env:
                del command_env[name]
        LOG.debug('    [ShellRunner,liveaction_id="%s"] command is: "%s"',
                  self.liveaction_id, command_list)
        LOG.debug('    [ShellRunner,liveaction_id="%s"] command env is: %s',
                  self.liveaction_id, command_env)

        # TODO: run shell command until it exits. periodically collect output
        # TODO: support other shells
        LOG.debug('    [ShellRunner,liveaction_id="%s"] Launching shell "%s" as blocking '
                  'operation for command "%s".', self.liveaction_id, '/usr/bin/bash', command_list)
        process = subprocess.Popen(command_list, env=command_env,
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        command_stdout, command_stderr = process.communicate()
        command_exitcode = process.returncode

        LOG.debug('    [ShellRunner,liveaction_id="%s"] command_stdout: %s',
                  self.liveaction_id, command_stdout)
        LOG.debug('    [ShellRunner,liveaction_id="%s"] command_stderr: %s',
                  self.liveaction_id, command_stderr)
        LOG.debug('    [ShellRunner,liveaction_id="%s"] command_exit: %s',
                  self.liveaction_id, command_exitcode)

        self.container_service.report_exit_code(command_exitcode)
        self.container_service.report_output(STDOUT, command_stdout)
        self.container_service.report_output(STDERR, command_stderr)

        os.chdir(old_dir)

        return (command_exitcode, command_stdout, command_stderr)

    def post_run(self):
        LOG.debug('Entering ShellRunner.post_run() for liveaction_id="%s"', self.liveaction_id)
        self.container_service.destroy_runner_folder()


def get_runner():
    return ShellRunner()

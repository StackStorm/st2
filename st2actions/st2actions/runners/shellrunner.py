import os
import shlex
import subprocess

from st2actions.runners import ActionRunner

from st2common import log as logging

# Replace with container call to get logger.
LOG = logging.getLogger(__name__)


UNABLE_TO_CONTINUE_MSG = 'Unable to continue execution of Live Action id=%s'


CMD_PARAM = 'cmd'
SHELL_PARAM = 'shell'

CONSUMED_ACTION_PARAMETERS = [CMD_PARAM, SHELL_PARAM]


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
        self._shell = None
        self._args = None

    def pre_run(self):
        LOG.debug('Entering ShellRunner.pre_run() for liveaction_id="%s"', self.liveaction_id)

        self._shell = self.runner_parameters.get(SHELL_PARAM, None)
        self._args = self.runner_parameters.get(CMD_PARAM, None)

        # See handling of 'args' from action_parameters in run() method.

        LOG.debug('    [ShellRunner,liveaction_id="%s"] Runner argument "%s" is: "%s"',
                  self.liveaction_id, SHELL_PARAM, self._shell)
        LOG.debug('    [ShellRunner,liveaction_id="%s"] Runner argument "%s" is: "%s"',
                  self.liveaction_id, SHELL_PARAM, self._shell)

        # Identify the working directory for the Action. Entry point is the
        # the relative path from the artifact repo path to the script to be
        # executed. The working directory is the absolute path to the location
        # of the script.
        self._workingdir = self.container_service.get_artifact_working_dir(self.entry_point)

    def run(self, action_parameters):
        """
            ActionRunner for "shell" RunnerType.
        """
        LOG.debug('Entering ShellRunner.run() for liveaction_id="%s"', self.liveaction_id)

        if self._args is None:
            LOG.warning('No value for "%s" provided to Shell Runner for liveaction_id="%s".',
                        CMD_PARAM, self.liveaction_id)
            self._args = ''

        # Execute the shell script at it's location. Change the working
        # directory to the folder where the shell script is located.
        old_dir = os.getcwd()
        os.chdir(self._workingdir)
        # Get the name of the shell script from the entry_point path.
        paths = self.entry_point.rsplit('/', 1)[::-1]
        command_list = shlex.split(str(paths[0]) + ' ' + str(self._args))

        # Convert shell environment dictionary to strings and omit any args that
        # have not been set by the user. (Value is None.)
        command_env = dict([(str(k), str(v))
                            for (k, v) in action_parameters.items() if v is not None])
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

        result = {'exit_code': command_exitcode,
                  'std_out': command_stdout,
                  'std_err': command_stderr}

        self.container_service.report_result(result)

        os.chdir(old_dir)

        return (command_exitcode, command_stdout, command_stderr)


def get_runner():
    return ShellRunner()

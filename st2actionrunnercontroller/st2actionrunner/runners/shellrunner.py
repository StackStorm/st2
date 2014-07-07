import os
import shlex
import shutil
import subprocess
import tempfile

# TODO: fix st2common.log so that it supports all of the python logging API
import logging as pylogging

from st2actionrunner.runners import ActionRunner

from st2common import log as logging
from st2common.exceptions.actionrunner import ActionRunnerPreRunError
from st2actionrunner.container.service import (STDOUT, STDERR)


# Replace with container call to get logger.
LOG = logging.getLogger(__name__)

UNABLE_TO_CONTINUE_MSG = 'Unable to continue execution of Live Action id=%s'

# TODO: Update all messages to report liveaction_id

class ShellRunner(ActionRunner):

    def __init__(self):
        ActionRunner.__init__(self)

    def _copy_artifact(self, src, dest):
            """
                Copy the artifact from src to dest.

                The artifact may be a file or a folder.
            """

            # TODO: Handle error conditions

            LOG.debug('    [Shell Runner] copying artifact: "%s" to working dir: "%s"', src, dest)
            
            old_dir = os.getcwd()
            os.chdir(self.container_service.get_artifact_repo_path())
            for (dirpath, dirs, filenames) in os.walk(src):
                LOG.debug('        Creating parent folders: "%s" in "%s"', dirpath, self._workingdir)
                os.makedirs(os.path.join(self._workingdir, dirpath))

                for directory in dirs:
                    dest_path = os.path.join(self._workingdir, dirpath, directory)
                    LOG.debug('        Creating directory: %', dest_path)
                    os.mkdir(dest_path)

                for filename in filenames:
                    src_path = os.path.join(dirpath, filename)
                    dest_path = os.path.join(self._workingdir, dirpath, filename)
                    LOG.debug('        Copying file: "%s" to "%s"', src_path, dest_path)
                    shutil.copy2(src_path, dest_path)

            os.chdir(old_dir)

    def pre_run(self):
        LOG.info('In ShellRunner.pre_run()')

        self._shell = self.parameters['shell']
        self._args = self.parameters['args']
        self._working_dir_root = self.container_service.get_artifact_working_dir()

        LOG.debug('    [Shell Runner] runner argument "shell" is: "%s"', self._shell)
        LOG.debug('    [Shell Runner] runner argument "args" is: "%s"', self._args)
        LOG.debug('    [Shell Runner] working dir root: "%s"', self._working_dir_root)

        # TODO: have container service maintain a "/tmp/stackstorm" folder
        # TODO: have container service create and clean up the temp folders
        # TODO: Move artifact handling to container service.

        # Create a temporary working directory for action
        self._workingdir = tempfile.mkdtemp(prefix='shellrunner-', dir=self._working_dir_root)

        repo_base = self.container_service.get_artifact_repo_path()
        # Copy artifacts to temp folder
        LOG.debug('here: %s', self)
        for path in self.artifact_paths:
            self._copy_artifact(path, self._workingdir)

        LOG.info('    [Shell Runner] Finished populating temporary artifact folder "%s"', self._workingdir)

    def run(self, action_parameters):
        """
            ActionRunner for "shell" ActionType.
        """
        LOG.info('Entering Shell Runner')

        old_dir = os.getcwd()
        os.chdir(self._workingdir)
        command_list = shlex.split(str(self.entry_point) + ' ' + str(self._args))

        LOG.debug('    [Shell Runner] command is: "%s"', command_list)

        # TODO: run shell command until it exits. periodically collect output
        # TODO: support other shells
        LOG.debug('    [Shell Runner] Launching shell "%s" as blocking operation for command '
                  '"%s".', '/usr/bin/bash', command_list)
        process = subprocess.Popen(command_list, stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE)

        command_stdout, command_stderr = process.communicate()
        command_exitcode = process.returncode

        LOG.debug('    [Shell Runner] command_stdout: %s', command_stdout)
        LOG.debug('    [Shell Runner] command_stderr: %s', command_stderr)
        LOG.debug('    [Shell Runner] command_exit: %s', command_exitcode)

        self.container_service.report_exit_code(command_exitcode)
        self.container_service.report_output(STDOUT, command_stdout)
        self.container_service.report_output(STDERR, command_stderr)

        os.chdir(old_dir)

        return (command_exitcode, command_stdout, command_stderr)

    def post_run(self):
        LOG.info('In ShellRunner.post_run()')
        if not LOG.isEnabledFor(pylogging.DEBUG):
            pass
        else:
            LOG.info('    [Shell Runner] Cleaning up working directory "%s" '
                     'for Live Action id="%s"', self._workingdir, self.liveaction_id)
            # Clean up temp artifact folder if logging level lower than DEBUG
            # TODO: Work out better way to handle errors
            shutil.rmtree(self._workingdir, ignore_errors=True)
            

def get_runner():
    return ShellRunner()

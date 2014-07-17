import os
import shutil
import tempfile

# TODO: fix st2common.log so that it supports all of the python logging API
import logging as pylogging

from oslo.config import cfg

from st2common import log as logging


LOG = logging.getLogger(__name__)


STDOUT = 'stdout'
STDERR = 'stderr'


CLEAN_UP_TEMPDIR = False


class RunnerContainerService():
    """
        The RunnerContainerService class implements the interface
        that ActionRunner implementations use to access services
        provided by the Action Runner Container.
    """

    def __init__(self, container):
        self._container = container
        self._exit_code = None
        self._output = []
        self._payload = {}
        self._action_workingdir = None

    def report_exit_code(self, code):
        self._exit_code = code

    def report_output(self, stream, output):
        self._output.append((stream, output))

    def report_payload(self, name, value):
        self._payload[name] = value

    def get_logger(self, name):
        from st2common import log as logging
        logging.getLogger(__name__ + '.' + name)

    def get_artifact_working_dir_path(self):
        path = cfg.CONF.action_runner.artifact_working_dir_path

        if not os.path.isdir(path):
            os.makedirs(path)

        return path

    def get_artifact_repo_path(self):
        return cfg.CONF.action_runner.artifact_repo_path

    def create_runner_folder(self):
        self._working_dir_root = self.get_artifact_working_dir_path()

        if self._action_workingdir is None:
            self._action_workingdir = tempfile.mkdtemp(prefix='shellrunner-',
                                                       dir=self._working_dir_root)
            LOG.info('Action Runner for created temporary working directory: %s',
                     self._action_workingdir)

        return self._action_workingdir

    def populate_runner_folder(self, artifact_paths):
        if self._action_workingdir is None:
            return False

        LOG.info('Populating temporary action runner folder "%s" with artifacts.',
                 self._action_workingdir)

        # Copy artifacts to temp folder
        for path in artifact_paths:
            self._copy_artifact(path, self._action_workingdir)

        LOG.info('Finished populating temporary action runner folder "%s" '
                 'with artifacts: %s', self._action_workingdir, artifact_paths)
        return True

    def destroy_runner_folder(self):
        if self._action_workingdir is not None:
            if (not CLEAN_UP_TEMPDIR) or LOG.isEnabledFor(pylogging.DEBUG):
                pass
            else:
                LOG.info('Cleaning up working directory "%s"',
                         self._action_workingdir)
                # Clean up temp artifact folder if logging level lower than DEBUG
                # TODO: Work out better way to handle errors
                shutil.rmtree(self._action_workingdir, ignore_errors=True)

            # Cleanup Action Runner object.
            self._action_workingdir = None

        return

    def _copy_artifact(self, src, dest):
            """
                Copy the artifact from src to dest.

                The artifact may be a file or a folder.
            """

            # TODO: Handle error conditions

            LOG.debug('Copying artifact: "%s" to working dir: "%s"', src, dest)

            old_dir = os.getcwd()
            os.chdir(self.get_artifact_repo_path())
            for (dirpath, dirs, filenames) in os.walk(src):
                LOG.debug('    Creating parent folders: "%s" in "%s"',
                          dirpath, self._action_workingdir)
                os.makedirs(os.path.join(self._action_workingdir, dirpath))

                for directory in dirs:
                    dest_path = os.path.join(self._action_workingdir, dirpath, directory)
                    LOG.debug('    Creating directory: %', dest_path)
                    os.mkdir(dest_path)

                for filename in filenames:
                    src_path = os.path.join(dirpath, filename)
                    dest_path = os.path.join(self._action_workingdir, dirpath, filename)
                    LOG.debug('    Copying file: "%s" to "%s"', src_path, dest_path)
                    shutil.copy2(src_path, dest_path)

            os.chdir(old_dir)

            LOG.debug('Artifact "%s" copied to working dir successfully.', src)

    def __str__(self):
        result = []
        result.append('RunnerContainerService@')
        result.append(str(id(self)))
        result.append('(')
        result.append('_container="%s", ' % self._container)
        result.append('_exit_code="%s", ' % self._exit_code)
        result.append('_output="%s", ' % self._output)
        result.append('_payload="%s", ' % self._payload)
        result.append(')')
        return ''.join(result)

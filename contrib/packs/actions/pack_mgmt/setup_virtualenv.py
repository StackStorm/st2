import os
import re
import pipes

from oslo.config import cfg

import st2common.config as config
from st2common.util.shell import run_command
from st2actions.runners.pythonrunner import Action
from st2common.constants.pack import PACK_NAME_WHITELIST
from st2common.constants.pack import BASE_PACK_REQUIREMENTS
from st2common.content.utils import get_system_packs_base_path


class SetupVirtualEnvironmentAction(Action):
    """
    Action which sets up virtual environment for the provided packs.

    Setup consists of the following step:

    1. Create virtual environment for the pack
    2. Install base requirements which are common to all the packs
    3. Install pack-specific requirements (if any)
    """

    def __init__(self, config=None):
        super(SetupVirtualEnvironmentAction, self).__init__(config=config)
        self.initialize()

        self._base_packs_path = get_system_packs_base_path()
        self._base_virtualenvs_path = os.path.join(cfg.CONF.system.base_path,
                                                   'virtualenvs/')

    def initialize(self):
        try:
            config.parse_args()
        except:
            pass

    def run(self, packs):
        """
        :param packs: A list of packs to create the environment for.
        :type: packs: ``list``
        """
        for pack_name in packs:
            self._setup_pack_virtualenv(pack_name=pack_name)

        message = ('Successfuly set up virtualenv for the following packs: %s' %
                   (', '.join(packs)))
        return message

    def _setup_pack_virtualenv(self, pack_name):
        """
        :param pack_name: Pack name.
        :type pack_name: ``str``
        """
        # Prevent directory traversal by whitelisting allowed characters in the
        # pack name
        if not re.match(PACK_NAME_WHITELIST, pack_name):
            raise ValueError('Invalid pack name "%s"' % (pack_name))

        self.logger.debug('Setting up virtualenv for pack "%s"' % (pack_name))

        pack_name = pipes.quote(pack_name)
        pack_path = os.path.join(self._base_packs_path, pack_name)
        virtualenv_path = os.path.join(self._base_virtualenvs_path, pack_name)

        # Ensure virtualenvs directory exists
        if not os.path.isdir(pack_path):
            raise Exception('Pack "%s" is not installed' % (pack_name))

        if not os.path.exists(self._base_virtualenvs_path):
            os.makedirs(self._base_virtualenvs_path)

        # 1. Create virtual environment
        self.logger.debug('Creating virtualenv for pack "%s" in "%s"' %
                          (pack_name, virtualenv_path))
        self._create_virtualenv(virtualenv_path=virtualenv_path)

        # 2. Install base requirements which are common to all the packs
        self.logger.debug('Installing base requirements')
        for requirement in BASE_PACK_REQUIREMENTS:
            self._install_requirement(virtualenv_path=virtualenv_path,
                                      requirement=requirement)

        # 3. Install pack-specific requirements
        requirements_file_path = os.path.join(pack_path, 'requirements.txt')
        has_requirements = os.path.isfile(requirements_file_path)

        if has_requirements:
            self.logger.debug('Installing pack specific requirements from "%s"' %
                              (requirements_file_path))
            self._install_requirements(virtualenv_path, requirements_file_path)
        else:
            self.logger.debug('No pack specific requirements found')

        self.logger.debug('Virtualenv for pack "%s" successfully created in "%s"' %
                          (pack_name, virtualenv_path))

    def _create_virtualenv(self, virtualenv_path):
        python_binary = cfg.CONF.actionrunner.python_binary

        if not os.path.isfile(python_binary):
            raise Exception('Python binary "%s" doesn\'t exist' % (python_binary))

        self.logger.debug('Creating virtualenv in "%s" using Python binary "%s"' %
                          (virtualenv_path, python_binary))

        cmd = ['virtualenv', '-p', python_binary, '--system-site-packages', virtualenv_path]
        exit_code, _, stderr = run_command(cmd=cmd)

        if exit_code != 0:
            raise Exception('Failed to create virtualenv in "%s": %s' %
                            (virtualenv_path, stderr))

        return True

    def _install_requirements(self, virtualenv_path, requirements_file_path):
        """
        Install requirements from a file.
        """
        pip_path = os.path.join(virtualenv_path, 'bin/pip')
        cmd = [pip_path, 'install', '-U', '-r', requirements_file_path]
        env = self._get_env_for_subprocess_command()
        exit_code, stdout, stderr = run_command(cmd=cmd, env=env)

        if exit_code != 0:
            raise Exception('Failed to install requirements from "%s": %s' %
                            (requirements_file_path, stdout))

        return True

    def _install_requirement(self, virtualenv_path, requirement):
        """
        Install a single requirement.
        """
        pip_path = os.path.join(virtualenv_path, 'bin/pip')
        cmd = [pip_path, 'install', requirement]
        env = self._get_env_for_subprocess_command()
        exit_code, stdout, stderr = run_command(cmd=cmd, env=env)

        if exit_code != 0:
            raise Exception('Failed to install requirement "%s": %s' %
                            (requirement, stdout))

        return True

    def _get_env_for_subprocess_command(self):
        """
        Retrieve environment to be used with the subprocess command.

        Note: We remove PYTHONPATH from the environment so the command works
        correctly with the newely created virtualenv.
        """
        env = os.environ.copy()

        if 'PYTHONPATH' in env:
            del env['PYTHONPATH']

        return env

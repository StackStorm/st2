import os
import re
import pipes

from oslo.config import cfg

import st2common.config as config
from st2common.util.shell import run_command
from st2actions.runners.pythonrunner import Action

# TODO: Move into utils, also enforce in other places
PACK_NAME_WHITELIST = r'^[A-Za-z0-9_-]+'

# Requirements which are common to all the packs
BASE_PACK_REQUIREMENTS = [
]


# TODO: Should we only setup virtualenv for packs which at at least one
# Python action and / or sensor?
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

        self._base_packs_path = cfg.CONF.content.packs_base_path
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
        self.logger.debug('Creating virtualenv in "%s"' % (virtualenv_path))

        cmd = ['virtualenv', virtualenv_path]
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
        cmd = [pip_path, 'install', '-r', requirements_file_path]
        exit_code, stdout, stderr = run_command(cmd=cmd)

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
        exit_code, stdout, stderr = run_command(cmd=cmd)

        if exit_code != 0:
            raise Exception('Failed to install requirement "%s": %s' %
                            (requirement, stdout))

        return True

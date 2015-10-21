# Licensed to the StackStorm, Inc ('StackStorm') under one or more
# contributor license agreements.  See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.
# The ASF licenses this file to You under the Apache License, Version 2.0
# (the "License"); you may not use this file except in compliance with
# the License.  You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os
import re
import shutil

from oslo_config import cfg

from st2common.util.shell import run_command
from st2actions.runners.pythonrunner import Action
from st2common.constants.pack import PACK_NAME_WHITELIST
from st2common.constants.pack import BASE_PACK_REQUIREMENTS
from st2common.content.utils import get_packs_base_paths
from st2common.content.utils import get_pack_directory
from st2common.util.shell import quote_unix


class SetupVirtualEnvironmentAction(Action):
    """
    Action which sets up virtual environment for the provided packs.

    Setup consists of the following step:

    1. Create virtual environment for the pack
    2. Install base requirements which are common to all the packs
    3. Install pack-specific requirements (if any)

    If the 'update' parameter is set to True, the setup skips the deletion and
    creation of the virtual environment and performs an update of the
    current dependencies as well as an installation of new dependencies
    """

    def __init__(self, config=None):
        super(SetupVirtualEnvironmentAction, self).__init__(config=config)
        self._base_virtualenvs_path = os.path.join(cfg.CONF.system.base_path,
                                                   'virtualenvs/')

    def run(self, packs, update):
        """
        :param packs: A list of packs to create the environment for.
        :type: packs: ``list``
        """
        for pack_name in packs:
            self._setup_pack_virtualenv(pack_name=pack_name, update=update)

        message = ('Successfuly set up virtualenv for the following packs: %s' %
                   (', '.join(packs)))
        return message

    def _setup_pack_virtualenv(self, pack_name, update):
        """
        Setup virtual environment for the provided pack.

        :param pack_name: Pack name.
        :type pack_name: ``str``
        """
        # Prevent directory traversal by whitelisting allowed characters in the
        # pack name
        if not re.match(PACK_NAME_WHITELIST, pack_name):
            raise ValueError('Invalid pack name "%s"' % (pack_name))

        self.logger.debug('Setting up virtualenv for pack "%s"' % (pack_name))

        virtualenv_path = os.path.join(self._base_virtualenvs_path, quote_unix(pack_name))

        # Ensure pack directory exists in one of the search paths
        pack_path = get_pack_directory(pack_name=pack_name)

        if not pack_path:
            packs_base_paths = get_packs_base_paths()
            search_paths = ', '.join(packs_base_paths)
            msg = 'Pack "%s" is not installed. Looked in: %s' % (pack_name, search_paths)
            raise Exception(msg)

        if not os.path.exists(self._base_virtualenvs_path):
            os.makedirs(self._base_virtualenvs_path)

        if not update:

            # 0. Delete virtual environment if it exists
            self._remove_virtualenv(virtualenv_path=virtualenv_path)

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

        self.logger.debug('Virtualenv for pack "%s" successfully %s in "%s"' %
                          (pack_name,
                           "updated" if update else "created",
                           virtualenv_path))

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

    def _remove_virtualenv(self, virtualenv_path):
        if not os.path.exists(virtualenv_path):
            self.logger.info('Virtualenv path "%s" doesn\'t exist' % virtualenv_path)
            return True

        self.logger.debug('Removing virtualenv in "%s"' % virtualenv_path)
        try:
            shutil.rmtree(virtualenv_path)
        except Exception as error:
            self.logger.error('Error while removing virtualenv at "%s": "%s"' %
                              (virtualenv_path, error))
            raise
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

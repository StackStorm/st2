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

"""
Pack virtual environment related utility functions.
"""

import os
import re
import shutil

from oslo_config import cfg

from st2common import log as logging
from st2common.constants.pack import PACK_NAME_WHITELIST
from st2common.constants.pack import BASE_PACK_REQUIREMENTS
from st2common.util.shell import run_command
from st2common.content.utils import get_packs_base_paths
from st2common.content.utils import get_pack_directory
from st2common.util.shell import quote_unix

__all__ = [
    'setup_pack_virtualenv'
]

LOG = logging.getLogger(__name__)


def setup_pack_virtualenv(pack_name, update=False, logger=None):
    """
    Setup virtual environment for the provided pack.

    :param pack_name: Name of the pack to setup the virtualenv for.
    :type pack_name: ``str``

    :param update: True to update dependencies inside the virtual environment.
    :type update: ``bool``

    :param logger: Optional logger instance to use. If not provided it defaults to the module
                   level logger.
    """
    logger = logger or LOG

    if not re.match(PACK_NAME_WHITELIST, pack_name):
        raise ValueError('Invalid pack name "%s"' % (pack_name))

    base_virtualenvs_path = os.path.join(cfg.CONF.system.base_path, 'virtualenvs/')

    logger.debug('Setting up virtualenv for pack "%s"' % (pack_name))

    virtualenv_path = os.path.join(base_virtualenvs_path, quote_unix(pack_name))

    # Ensure pack directory exists in one of the search paths
    pack_path = get_pack_directory(pack_name=pack_name)

    if not pack_path:
        packs_base_paths = get_packs_base_paths()
        search_paths = ', '.join(packs_base_paths)
        msg = 'Pack "%s" is not installed. Looked in: %s' % (pack_name, search_paths)
        raise Exception(msg)

    # 1. Create virtualenv if it doesn't exist
    if not update or not os.path.exists(virtualenv_path):
        # 0. Delete virtual environment if it exists
        remove_virtualenv(virtualenv_path=virtualenv_path, logger=logger)

        # 1. Create virtual environment
        logger.debug('Creating virtualenv for pack "%s" in "%s"' % (pack_name, virtualenv_path))
        create_virtualenv(virtualenv_path=virtualenv_path, logger=logger)

    # 2. Install base requirements which are common to all the packs
    logger.debug('Installing base requirements')
    for requirement in BASE_PACK_REQUIREMENTS:
        install_requirement(virtualenv_path=virtualenv_path, requirement=requirement)

    # 3. Install pack-specific requirements
    requirements_file_path = os.path.join(pack_path, 'requirements.txt')
    has_requirements = os.path.isfile(requirements_file_path)

    if has_requirements:
        logger.debug('Installing pack specific requirements from "%s"' %
                     (requirements_file_path))
        install_requirements(virtualenv_path=virtualenv_path,
                             requirements_file_path=requirements_file_path)
    else:
        logger.debug('No pack specific requirements found')

    action = 'updated' if update else 'created'
    logger.debug('Virtualenv for pack "%s" successfully %s in "%s"' %
                 (pack_name, action, virtualenv_path))


def create_virtualenv(virtualenv_path, logger=None):
    logger = logger or LOG

    python_binary = cfg.CONF.actionrunner.python_binary
    virtualenv_binary = cfg.CONF.actionrunner.virtualenv_binary
    virtualenv_opts = cfg.CONF.actionrunner.virtualenv_opts

    if not os.path.isfile(python_binary):
        raise Exception('Python binary "%s" doesn\'t exist' % (python_binary))

    if not os.path.isfile(virtualenv_binary):
        raise Exception('Virtualenv binary "%s" doesn\'t exist.' % (virtualenv_binary))

    logger.debug('Creating virtualenv in "%s" using Python binary "%s"' %
                 (virtualenv_path, python_binary))

    cmd = [virtualenv_binary, '-p', python_binary]
    cmd.extend(virtualenv_opts)
    cmd.extend([virtualenv_path])
    logger.debug('Running command "%s" to create virtualenv.', ' '.join(cmd))

    try:
        exit_code, _, stderr = run_command(cmd=cmd)
    except OSError as e:
        raise Exception('Error executing command %s. %s.' % (' '.join(cmd),
                                                             e.message))

    if exit_code != 0:
        raise Exception('Failed to create virtualenv in "%s": %s' %
                        (virtualenv_path, stderr))

    return True


def remove_virtualenv(virtualenv_path, logger=None):
    """
    Remove the provided virtualenv.
    """
    logger = logger or LOG

    if not os.path.exists(virtualenv_path):
        logger.info('Virtualenv path "%s" doesn\'t exist' % virtualenv_path)
        return True

    logger.debug('Removing virtualenv in "%s"' % virtualenv_path)
    try:
        shutil.rmtree(virtualenv_path)
    except Exception as e:
        logger.error('Error while removing virtualenv at "%s": "%s"' % (virtualenv_path, e))
        raise e

    return True


def install_requirements(virtualenv_path, requirements_file_path):
    """
    Install requirements from a file.
    """
    pip_path = os.path.join(virtualenv_path, 'bin/pip')
    cmd = [pip_path, 'install', '-U', '-r', requirements_file_path]
    env = get_env_for_subprocess_command()
    exit_code, stdout, stderr = run_command(cmd=cmd, env=env)

    if exit_code != 0:
        raise Exception('Failed to install requirements from "%s": %s (stderr: %s)' %
                        (requirements_file_path, stdout, stderr))

    return True


def install_requirement(virtualenv_path, requirement):
    """
    Install a single requirement.

    :param requirement: Requirement specifier.
    """
    pip_path = os.path.join(virtualenv_path, 'bin/pip')
    cmd = [pip_path, 'install', requirement]
    env = get_env_for_subprocess_command()
    exit_code, stdout, stderr = run_command(cmd=cmd, env=env)

    if exit_code != 0:
        raise Exception('Failed to install requirement "%s": %s' %
                        (requirement, stdout))

    return True


def get_env_for_subprocess_command():
    """
    Retrieve environment to be used with the subprocess command.

    Note: We remove PYTHONPATH from the environment so the command works
    correctly with the newely created virtualenv.
    """
    env = os.environ.copy()

    if 'PYTHONPATH' in env:
        del env['PYTHONPATH']

    return env

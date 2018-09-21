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
Utility functions for our sandboxing model which is implemented on top of
separate processes and virtualenv.
"""

from __future__ import absolute_import

import os
import sys
import fnmatch
from distutils.sysconfig import get_python_lib

from oslo_config import cfg

from st2common.constants.pack import SYSTEM_PACK_NAMES
from st2common.content.utils import get_pack_base_path

__all__ = [
    'get_sandbox_python_binary_path',
    'get_sandbox_python_path',
    'get_sandbox_python_path_for_python_action',
    'get_sandbox_path',
    'get_sandbox_virtualenv_path',

    'is_pack_virtualenv_using_python3'
]


def get_sandbox_python_binary_path(pack=None):
    """
    Return path to the Python binary for the provided pack.

    :param pack: Pack name.
    :type pack: ``str``
    """
    system_base_path = cfg.CONF.system.base_path
    virtualenv_path = os.path.join(system_base_path, 'virtualenvs', pack)

    if pack in SYSTEM_PACK_NAMES:
        # Use system python for "packs" and "core" actions
        python_path = sys.executable
    else:
        python_path = os.path.join(virtualenv_path, 'bin/python')

    return python_path


def get_sandbox_path(virtualenv_path):
    """
    Return PATH environment variable value for the sandboxed environment.

    This function makes sure that virtualenv/bin directory is in the path and has precedence over
    the global PATH values.

    Note: This function needs to be called from the parent process (one which is spawning a
    sandboxed process).
    """
    sandbox_path = []

    parent_path = os.environ.get('PATH', '')
    if not virtualenv_path:
        return parent_path

    parent_path = parent_path.split(':')
    parent_path = [path for path in parent_path if path]

    # Add virtualenv bin directory
    virtualenv_bin_path = os.path.join(virtualenv_path, 'bin/')
    sandbox_path.append(virtualenv_bin_path)
    sandbox_path.extend(parent_path)

    sandbox_path = ':'.join(sandbox_path)
    return sandbox_path


def get_sandbox_python_path(inherit_from_parent=True, inherit_parent_virtualenv=True):
    """
    Return PYTHONPATH environment variable value for the new sandboxed environment.

    This function takes into account if the current (parent) process is running under virtualenv
    and other things like that.

    Note: This function needs to be called from the parent process (one which is spawning a
    sandboxed process).

    :param inherit_from_parent: True to inheir PYTHONPATH from the current process.
    :type inherit_from_parent: ``str``

    :param inherit_parent_virtualenv: True to inherit virtualenv path if the current process is
                                      running inside virtual environment.
    :type inherit_parent_virtualenv: ``str``
    """
    sandbox_python_path = []
    parent_python_path = os.environ.get('PYTHONPATH', '')

    parent_python_path = parent_python_path.split(':')
    parent_python_path = [path for path in parent_python_path if path]

    if inherit_from_parent:
        sandbox_python_path.extend(parent_python_path)

    if inherit_parent_virtualenv and hasattr(sys, 'real_prefix'):
        # We are running inside virtualenv
        site_packages_dir = get_python_lib()
        assert sys.prefix in site_packages_dir
        sandbox_python_path.append(site_packages_dir)

    sandbox_python_path = ':'.join(sandbox_python_path)
    sandbox_python_path = ':' + sandbox_python_path
    return sandbox_python_path


def get_sandbox_python_path_for_python_action(pack, inherit_from_parent=True,
                                              inherit_parent_virtualenv=True):

    """
    Same as get_sandbox_python_path function, but it's intended to be used for Python runner actions
    and also takes into account if a pack virtual environment uses Python 3.
    """
    sandbox_python_path = get_sandbox_python_path(
        inherit_from_parent=inherit_from_parent,
        inherit_parent_virtualenv=inherit_parent_virtualenv)

    # If python3.? directory exists in pack virtualenv lib/ path it means Python 3 is used by
    # that virtual environment and we take that in to account when constructing PYTHONPATH
    pack_base_path = get_pack_base_path(pack_name=pack)
    virtualenv_path = get_sandbox_virtualenv_path(pack=pack)

    pack_actions_lib_paths = os.path.join(pack_base_path, 'actions/lib/')
    pack_virtualenv_lib_path = os.path.join(virtualenv_path, 'lib')

    uses_python3, virtualenv_directories = is_pack_virtualenv_using_python3(pack=pack)

    if uses_python3:
        # Add Python 3 lib directory (lib/python3.x) in front of the PYTHONPATH. This way we avoid
        # issues with scripts trying to use packages / modules from Python 2.7 site-packages
        # directory instead of the versions from Python 3 stdlib.
        python3_lib_directory = os.path.join(pack_virtualenv_lib_path, virtualenv_directories[0])

        # Add Python 3 site-packages directory (lib/python3.x/site-packages) in front of the Python
        # 2.7 system site-packages This is important because we want Python 3 compatible libraries
        # to be used from the pack virtual environment and not system ones.
        python3_site_packages_directory = os.path.join(pack_virtualenv_lib_path,
                                                       virtualenv_directories[0],
                                                       'site-packages')
        sandbox_python_path = (python3_lib_directory + ':' + python3_site_packages_directory + ':' +
                               pack_actions_lib_paths + ':' + sandbox_python_path)

    return sandbox_python_path


def is_pack_virtualenv_using_python3(pack):
    """
    Return True if a particular pack virtual environment is used Python 3.
    """
    # If python3.? directory exists in pack virtualenv lib/ path it means Python 3 is used by
    # that virtual environment and we take that in to account when constructing PYTHONPATH
    virtualenv_path = get_sandbox_virtualenv_path(pack=pack)

    if virtualenv_path and os.path.isdir(virtualenv_path):
        pack_virtualenv_lib_path = os.path.join(virtualenv_path, 'lib')

        virtualenv_directories = os.listdir(pack_virtualenv_lib_path)
        virtualenv_directories = [dir_name for dir_name in virtualenv_directories if
                                  fnmatch.fnmatch(dir_name, 'python3*')]
        uses_python3 = bool(virtualenv_directories)
    else:
        uses_python3 = False
        virtualenv_directories = None

    return uses_python3, virtualenv_directories


def get_sandbox_virtualenv_path(pack):
    """
    Return a path to the virtual environment for the provided pack.
    """

    if pack in SYSTEM_PACK_NAMES:
        virtualenv_path = None
    else:
        system_base_path = cfg.CONF.system.base_path
        virtualenv_path = os.path.join(system_base_path, 'virtualenvs', pack)

    return virtualenv_path

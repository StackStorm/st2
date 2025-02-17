# Copyright 2020 The StackStorm Authors.
# Copyright 2019 Extreme Networks, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Utility functions for our sandboxing model which is implemented on top of separate processes and
virtual environments.
"""

from __future__ import absolute_import

import fnmatch
import os
import sys
from sysconfig import get_path
from typing import Optional

from oslo_config import cfg

from st2common.constants.action import LIBS_DIR as ACTION_LIBS_DIR
from st2common.constants.pack import SYSTEM_PACK_NAMES
from st2common.content.utils import get_pack_base_path


__all__ = [
    "get_site_packages_dir",
    "get_virtualenv_lib_path",
    "get_sandbox_python_binary_path",
    "get_sandbox_python_path",
    "get_sandbox_python_path_for_python_action",
    "get_sandbox_path",
    "get_sandbox_virtualenv_path",
    "is_in_virtualenv",
]


def get_site_packages_dir() -> str:
    """Returns a string with the python platform lib path (to site-packages)."""
    # This assumes we are running in the primary st2 virtualenv (typically /opt/stackstorm/st2)
    site_packages_dir = get_path("platlib")

    sys_prefix = os.path.abspath(sys.prefix)
    if sys_prefix not in site_packages_dir:
        raise ValueError(
            f'The file with "{sys_prefix}" is not found in "{site_packages_dir}".'
        )

    return site_packages_dir


def get_virtualenv_lib_path(virtualenv_path: str) -> str:
    """Returns the path to a virtualenv's lib/python3.* directory."""
    if not (virtualenv_path and os.path.isdir(virtualenv_path)):
        raise OSError(
            f"virtualenv_path must be an existing directory. virtualenv_path={virtualenv_path}"
        )

    pack_virtualenv_lib_path = os.path.join(virtualenv_path, "lib")

    virtualenv_directories = os.listdir(pack_virtualenv_lib_path)
    virtualenv_directories = [
        dir_name
        for dir_name in virtualenv_directories
        if fnmatch.fnmatch(dir_name, "python*")
    ]

    return os.path.join(pack_virtualenv_lib_path, virtualenv_directories[0])


def get_sandbox_python_binary_path(pack=None):
    """
    Return path to the Python binary for the provided pack.
    :param pack: Pack name.
    :type pack: ``str``
    """
    system_base_path = cfg.CONF.system.base_path
    virtualenv_path = os.path.join(system_base_path, "virtualenvs", pack)

    if pack in SYSTEM_PACK_NAMES:
        # Use system python for "packs" and "core" actions
        python_path = sys.executable
    else:
        python_path = os.path.join(virtualenv_path, "bin/python")

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

    parent_path = os.environ.get("PATH", "")
    if not virtualenv_path:
        return parent_path

    parent_path = parent_path.split(":")
    parent_path = [path for path in parent_path if path]

    # Add virtualenv bin directory
    virtualenv_bin_path = os.path.join(virtualenv_path, "bin/")
    sandbox_path.append(virtualenv_bin_path)
    sandbox_path.extend(parent_path)

    sandbox_path = ":".join(sandbox_path)
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
    parent_python_path = os.environ.get("PYTHONPATH", "")

    parent_python_path = parent_python_path.split(":")
    parent_python_path = [path for path in parent_python_path if path]

    if inherit_from_parent:
        sandbox_python_path.extend(parent_python_path)

    if inherit_parent_virtualenv and is_in_virtualenv():
        # We are running inside virtualenv
        site_packages_dir = get_site_packages_dir()
        sandbox_python_path.append(site_packages_dir)

    sandbox_python_path = ":".join(sandbox_python_path)
    sandbox_python_path = ":" + sandbox_python_path
    return sandbox_python_path


def get_sandbox_python_path_for_python_action(
    pack, inherit_from_parent=True, inherit_parent_virtualenv=True
):
    """
    Return sandbox PYTHONPATH for a particular Python runner action.
    Same as get_sandbox_python_path() function, but it's intended to be used for Python runner
    actions.
    """
    sandbox_python_path = get_sandbox_python_path(
        inherit_from_parent=inherit_from_parent,
        inherit_parent_virtualenv=inherit_parent_virtualenv,
    )

    pack_base_path = get_pack_base_path(pack_name=pack)
    virtualenv_path = get_sandbox_virtualenv_path(pack=pack)

    if virtualenv_path and os.path.isdir(virtualenv_path):
        # Add the pack's lib directory (lib/python3.x) in front of the PYTHONPATH.
        pack_venv_lib_directory = get_virtualenv_lib_path(virtualenv_path)

        # Add the pack's site-packages directory (lib/python3.x/site-packages)
        # in front of the Python system site-packages This is important because
        # we want Python 3 compatible libraries to be used from the pack virtual
        # environment and not system ones.
        pack_venv_site_packages_directory = os.path.join(
            pack_venv_lib_directory, "site-packages"
        )

        # Then add the actions/lib directory in the pack.
        pack_actions_lib_paths = os.path.join(
            pack_base_path, "actions", ACTION_LIBS_DIR
        )

        full_sandbox_python_path = [
            # NOTE: Order here is very important for imports to function correctly
            pack_venv_lib_directory,
            pack_venv_site_packages_directory,
            pack_actions_lib_paths,
            sandbox_python_path,
        ]

        sandbox_python_path = ":".join(full_sandbox_python_path)

    return sandbox_python_path


def get_sandbox_virtualenv_path(pack: str) -> Optional[str]:
    """
    Return a path to the virtual environment for the provided pack.
    """

    if pack in SYSTEM_PACK_NAMES:
        virtualenv_path = None
    else:
        system_base_path = cfg.CONF.system.base_path
        virtualenv_path = str(os.path.join(system_base_path, "virtualenvs", pack))

    return virtualenv_path


def is_in_virtualenv():
    """
    :return: True if we are currently in a virtualenv, else False
    :rtype: ``Boolean``
    """
    # sys.real_prefix is for virtualenv
    # sys.base_prefix != sys.prefix is for venv
    return hasattr(sys, "real_prefix") or (
        hasattr(sys, "base_prefix") and sys.base_prefix != sys.prefix
    )


def get_virtualenv_prefix():
    """
    :return: Returns a tuple where the first element is the name of the attribute
             where we retrieved the virtualenv prefix from. The second element is
             the virtualenv prefix.
    """
    if hasattr(sys, "real_prefix"):
        return ("sys.real_prefix", sys.real_prefix)
    elif hasattr(sys, "base_prefix"):
        return ("sys.base_prefix", sys.base_prefix)
    return (None, None)


def set_virtualenv_prefix(prefix_tuple):
    """
    :return: Sets the virtualenv prefix given a tuple returned from get_virtualenv_prefix()
    """
    if prefix_tuple[0] == "sys.real_prefix" and hasattr(sys, "real_prefix"):
        sys.real_prefix = prefix_tuple[1]
    elif prefix_tuple[0] == "sys.base_prefix" and hasattr(sys, "base_prefix"):
        sys.base_prefix = prefix_tuple[1]


def clear_virtualenv_prefix():
    """
    :return: Unsets / removes / resets the virtualenv prefix
    """
    if hasattr(sys, "real_prefix"):
        del sys.real_prefix
    if hasattr(sys, "base_prefix"):
        sys.base_prefix = sys.prefix

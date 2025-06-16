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
Module for performing eventlet and other monkey patching.
"""

from __future__ import absolute_import

import os
import sys

__all__ = [
    "monkey_patch",
    "use_select_poll_workaround",
    "is_use_debugger_flag_provided",
]

USE_DEBUGGER_FLAG = "--use-debugger"
PARENT_ARGS_FLAG = "--parent-args="
USE_DEBUGGER_ENV_VAR = "ST2_USE_DEBUGGER"


def monkey_patch(patch_thread=None):
    """
    Function which performs eventlet monkey patching and also takes into account "--use-debugger"
    argument in the command line arguments.

    If this argument is found, no monkey patching is performed for the thread module. This allows
    user to use remote debuggers.

    :param patch_thread: True to also patch the thread module. If not provided, thread module is
                         patched unless debugger is used.
    :type patch_thread: ``bool``
    """
    import eventlet

    if patch_thread is None:
        patch_thread = not is_use_debugger_flag_provided()

    # TODO: support gevent.patch_all if .concurrency.CONCURRENCY_LIBRARY = "gevent"
    eventlet.monkey_patch(
        os=True, select=True, socket=True, thread=patch_thread, time=True
    )


def use_select_poll_workaround(nose_only=True):
    """
    Work around for eventlet monkey patched code which relies on select.poll() functionality
    which is blocking and not green / async.

    Keep in mind that this was always the case in old eventlet versions, but v0.20.0 removed
    select.poll() to avoid users shooting themselves in the foot and rely on blocking code.

    This code inserts original blocking select.poll() into the sys.modules so it can be used
    where needed.

    Keep in mind that this code should only be uses in scenarios where blocking is not a problem.

    For example:

    1) Inside tests which rely on subprocess.poll() / select.poll().
    2) Inside code which relies on 3rd party libraries which use select.poll() and are ran
       inside a subprocess so blocking is not an issue (e.g. actions, sensors).

    :param nose_only: True to only perform monkey patch when running tests under nose tests
                      runner.
    :type nose_only: ``bool``
    """
    import sys
    import select
    import subprocess
    import eventlet

    # Work around to get tests to pass with eventlet >= 0.20.0
    if not nose_only or (
        nose_only
        # sys._called_from_test set in conftest.py for pytest runs
        and ("nose" in sys.modules.keys() or hasattr(sys, "_called_from_test"))
    ):
        # Add back blocking poll() to eventlet monkeypatched select
        original_poll = eventlet.patcher.original("select").poll
        select.poll = original_poll

        sys.modules["select"] = select
        subprocess.select = select

        if sys.version_info >= (3, 6, 5):
            # If we also don't patch selectors.select, it will fail with Python >= 3.6.5
            import selectors  # pylint: disable=import-error

            sys.modules["selectors"] = selectors
            selectors.select = sys.modules["select"]


def is_use_debugger_flag_provided():
    # 1. Check sys.argv directly
    if USE_DEBUGGER_FLAG in sys.argv:
        return True

    # 2. Check "parent-args" arguments. This is used for spawned processes such as sensors and
    # Python runner actions

    for arg in sys.argv:
        if arg.startswith(PARENT_ARGS_FLAG) and USE_DEBUGGER_FLAG in arg:
            return True

    # 3. Check for ST2_USE_DEBUGGER env var
    if os.environ.get(USE_DEBUGGER_ENV_VAR, False):
        return True

    return False

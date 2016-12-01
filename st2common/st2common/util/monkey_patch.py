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
#

"""
Module for performing eventlet and other monkey patching.
"""

from __future__ import absolute_import

import sys

__all__ = [
    'monkey_patch',
    'monkey_patch_pkg_resources'
]

USE_DEBUGGER_FLAG = '--use-debugger'
PARENT_ARGS_FLAG = '--parent-args='


def monkey_patch():
    """
    Function which performs eventlet monkey patching and also takes into account "--use-debugger"
    argument in the command line arguments.

    If this argument is found, no monkey patching is performed for the thread module. This allows
    user to use remote debuggers.
    """
    import eventlet

    patch_thread = not is_use_debugger_flag_provided()
    eventlet.monkey_patch(os=True, select=True, socket=True, thread=patch_thread, time=True)


def monkey_patch_pkg_resources():
    # Note: This is a work-around for a very slow "pkg_resources" import.
    # pkg_resources is used by cryptography which is used by eventlet and importing pkg_resources
    # adds ~500-600ms to the import time of any script which uses that code :/
    # See https://github.com/pypa/setuptools/issues/510 for details
    import entrypoints
    sys.modules['pkg_resources'] = entrypoints


def is_use_debugger_flag_provided():
    # 1. Check sys.argv directly
    if USE_DEBUGGER_FLAG in sys.argv:
        return True

    # 2. Check "parent-args" arguments. This is used for spawned processes such as sensors and
    # Python runner actions

    for arg in sys.argv:
        if arg.startswith(PARENT_ARGS_FLAG) and USE_DEBUGGER_FLAG in arg:
            return True

    return False

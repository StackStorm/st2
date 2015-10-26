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
import shlex
import signal
import subprocess
from subprocess import list2cmdline
from ctypes import cdll

import six

from st2common import log as logging

__all__ = [
    'run_command',
    'kill_process',

    'quote_unix',
    'quote_windows'
]

LOG = logging.getLogger(__name__)

# Constant taken from http://linux.die.net/include/linux/prctl.h
PR_SET_PDEATHSIG = 1


# pylint: disable=too-many-function-args
def run_command(cmd, stdin=None, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=False,
                cwd=None, env=None):
    """
    Run the provided command in a subprocess and wait until it completes.

    :param cmd: Command to run.
    :type cmd: ``str`` or ``list``

    :param stdin: Process stdin.
    :type stdin: ``object``

    :param stdout: Process stdout.
    :type stdout: ``object``

    :param stderr: Process stderr.
    :type stderr: ``object``

    :param shell: True to use a shell.
    :type shell ``boolean``

    :param cwd: Optional working directory.
    :type cwd: ``str``

    :param env: Optional environment to use with the command. If not provided,
                environment from the current process is inherited.
    :type env: ``dict``

    :rtype: ``tuple`` (exit_code, stdout, stderr)
    """
    assert isinstance(cmd, (list, tuple) + six.string_types)

    if not env:
        env = os.environ.copy()

    process = subprocess.Popen(cmd, stdin=stdin, stdout=stdout, stderr=stderr,
                               env=env, cwd=cwd, shell=shell)
    stdout, stderr = process.communicate()
    exit_code = process.returncode

    return (exit_code, stdout, stderr)


def kill_process(process):
    """
    Kill the provided process by sending it TERM signal using "pkill" shell
    command.

    Note: This function only works on Linux / Unix based systems.

    :param process: Process object as returned by subprocess.Popen.
    :type process: ``object``
    """
    kill_command = shlex.split('sudo pkill -TERM -s %s' % (process.pid))

    try:
        status = subprocess.call(kill_command)
    except Exception:
        LOG.exception('Unable to pkill process.')

    return status


def quote_unix(value):
    """
    Return a quoted (shell-escaped) version of the value which can be used as one token in a shell
    command line.

    :param value: Value to quote.
    :type value: ``str``

    :rtype: ``str``
    """
    value = six.moves.shlex_quote(value)
    return value


def quote_windows(value):
    """
    Return a quoted (shell-escaped) version of the value which can be used as one token in a
    Windows command line.

    Note (from stdlib): note that not all MS Windows applications interpret the command line the
    same way: list2cmdline() is designed for applications using the same rules as the MS C runtime.

    :param value: Value to quote.
    :type value: ``str``

    :rtype: ``str``
    """
    value = list2cmdline([value])
    return value


def on_parent_exit(signame):
    """
    Return a function to be run in a child process which will trigger SIGNAME to be sent when the
    parent process dies.
    """
    # Based on https://gist.github.com/evansd/2346614
    libc = cdll['libc.so.6']
    if not libc:
        # libc, can't be found (e.g. running on non-Unix system), we cant ensure signal will be
        # triggered
        return

    prctl = libc.prctl
    if not prctl:
        # Function not available
        return

    signum = getattr(signal, signame)

    def set_parent_exit_signal():
        # http://linux.die.net/man/2/prctl
        result = prctl(PR_SET_PDEATHSIG, signum)
        if result != 0:
            raise Exception('prctl failed with error code %s' % result)
    return set_parent_exit_signal

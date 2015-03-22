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
Shell utility functions which use non-blocking and eventlet friendly code.
"""

import os

import six
from eventlet.green import subprocess

__all__ = [
    'run_command'
]


def run_command(cmd, stdin=None, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=False,
                cwd=None, env=None, timeout=60):
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

    :param timeout: How long to wait before timing out.
    :type timeout: ``float``

    :rtype: ``tuple`` (exit_code, stdout, stderr, timed_out)
    """
    assert isinstance(cmd, (list, tuple) + six.string_types)

    if not env:
        env = os.environ.copy()

    # Note: We are using eventlet friendly implementation of subprocess
    # which uses GreenPipe so it doesn't block
    process = subprocess.Popen(args=cmd, stdin=stdin, stdout=stdout, stderr=stderr,
                               env=env, cwd=cwd, shell=shell)

    try:
        exit_code = process.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        # Command has timed out, kill the process and propagate the error
        # Note: process.kill() will set the returncode to -9 so we don't
        # need to explicitly set it to some non-zero value
        process.kill()
        timed_out = True
    else:
        timed_out = False

    stdout, stderr = process.communicate()
    exit_code = process.returncode

    return (exit_code, stdout, stderr, timed_out)

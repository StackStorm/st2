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
import eventlet
from eventlet.green import subprocess

__all__ = [
    'run_command'
]

TIMEOUT_EXIT_CODE = -9


def run_command(cmd, stdin=None, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=False,
                cwd=None, env=None, timeout=60, preexec_func=None, kill_func=None):
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

    :param timeout: How long to wait before timing out. 0 means no timeout.
    :type timeout: ``float``

    :param preexec_func: Optional pre-exec function.
    :type preexec_func: ``callable``

    :param kill_func: Optional function which will be called on timeout to kill the process.
                      If not provided, it defaults to `process.kill`
    :type kill_func: ``callable``


    :rtype: ``tuple`` (exit_code, stdout, stderr, timed_out)
    """
    assert isinstance(cmd, (list, tuple) + six.string_types)

    if not env:
        env = os.environ.copy()

    # Note: We are using eventlet friendly implementation of subprocess
    # which uses GreenPipe so it doesn't block
    process = subprocess.Popen(args=cmd, stdin=stdin, stdout=stdout, stderr=stderr,
                               env=env, cwd=cwd, shell=shell, preexec_fn=preexec_func)

    if not timeout:
        stdout, stderr = process.communicate()
    else:
        def on_timeout_expired(timeout):
            """
            Thread to control subprocess timeout. Kills the process if timeout reached.

            :param timeout: How long to wait before timing out.
            :type: timeout: ``float``
            :return:
            """
            try:
                process.wait(timeout=timeout)
            except subprocess.TimeoutExpired:
                # Command has timed out, kill the process and propagate the error.
                # Note: We explicitly set the returncode to indicate the timeout.
                process.returncode = TIMEOUT_EXIT_CODE

                if kill_func:
                    kill_func(process=process)
                else:
                    process.kill()
        timeout_thread = eventlet.spawn(on_timeout_expired, timeout)
        stdout, stderr = process.communicate()
        timeout_thread.cancel()

    return (process.returncode, stdout, stderr, process.returncode == TIMEOUT_EXIT_CODE)

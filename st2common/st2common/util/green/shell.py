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

from __future__ import absolute_import
import os

import six
import eventlet
from st2common import log as logging
from eventlet.green import subprocess

__all__ = [
    'run_command'
]

TIMEOUT_EXIT_CODE = -9

LOG = logging.getLogger(__name__)


def run_command(cmd, stdin=None, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=False,
                cwd=None, env=None, timeout=60, preexec_func=None, kill_func=None,
                read_stdout_func=None, read_stderr_func=None,
                read_stdout_buffer=None, read_stderr_buffer=None):
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

    :param preexec_func: Optional pre-exec function.
    :type preexec_func: ``callable``

    :param kill_func: Optional function which will be called on timeout to kill the process.
                      If not provided, it defaults to `process.kill`
    :type kill_func: ``callable``

    :param read_stdout_func: Function which is responsible for reading process stdout when
                                 using live read mode.
    :type read_stdout_func: ``func``

    :param read_stdout_func: Function which is responsible for reading process stderr when
                                 using live read mode.
    :type read_stdout_func: ``func``


    :rtype: ``tuple`` (exit_code, stdout, stderr, timed_out)
    """
    LOG.debug('Entering st2common.util.green.run_command.')

    assert isinstance(cmd, (list, tuple) + six.string_types)

    if (read_stdout_func and not read_stderr_func) or (read_stderr_func and not read_stdout_func):
        raise ValueError('Both read_stdout_func and read_stderr_func arguments need '
                         'to be provided.')

    if read_stdout_func and not (read_stdout_buffer or read_stderr_buffer):
        raise ValueError('read_stdout_buffer and read_stderr_buffer arguments need to be provided '
                         'when read_stdout_func is provided')

    if not env:
        LOG.debug('env argument not provided. using process env (os.environ).')
        env = os.environ.copy()

    # Note: We are using eventlet friendly implementation of subprocess
    # which uses GreenPipe so it doesn't block
    LOG.debug('Creating subprocess.')
    process = subprocess.Popen(args=cmd, stdin=stdin, stdout=stdout, stderr=stderr,
                               env=env, cwd=cwd, shell=shell, preexec_fn=preexec_func)

    if read_stdout_func:
        LOG.debug('Spawning read_stdout_func function')
        read_stdout_thread = eventlet.spawn(read_stdout_func, process.stdout, read_stdout_buffer)

    if read_stderr_func:
        LOG.debug('Spawning read_stderr_func function')
        read_stderr_thread = eventlet.spawn(read_stderr_func, process.stderr, read_stderr_buffer)

    def on_timeout_expired(timeout):
        global timed_out

        try:
            LOG.debug('Starting process wait inside timeout handler.')
            process.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            # Command has timed out, kill the process and propagate the error.
            # Note: We explicitly set the returncode to indicate the timeout.
            LOG.debug('Command execution timeout reached.')
            process.returncode = TIMEOUT_EXIT_CODE

            if kill_func:
                LOG.debug('Calling kill_func.')
                kill_func(process=process)
            else:
                LOG.debug('Killing process.')
                process.kill()

            if read_stdout_func and read_stderr_func:
                LOG.debug('Killing read_stdout_thread and read_stderr_thread')
                read_stdout_thread.kill()
                read_stderr_thread.kill()

    LOG.debug('Spawning timeout handler thread.')
    timeout_thread = eventlet.spawn(on_timeout_expired, timeout)
    LOG.debug('Attaching to process.')

    if read_stdout_func and read_stderr_func:
        LOG.debug('Using real-time stdout and stderr read mode, calling process.wait()')
        process.wait()
    else:
        LOG.debug('Using delayed stdout and stderr read mode, calling process.communicate()')
        stdout, stderr = process.communicate()

    timeout_thread.cancel()
    exit_code = process.returncode

    if read_stdout_func and read_stderr_func:
        # Wait on those green threads to finish reading from stdout and stderr before continuing
        read_stdout_thread.wait()
        read_stderr_thread.wait()

        stdout = read_stdout_buffer.getvalue()
        stderr = read_stderr_buffer.getvalue()

    if exit_code == TIMEOUT_EXIT_CODE:
        LOG.debug('Timeout.')
        timed_out = True
    else:
        LOG.debug('No timeout.')
        timed_out = False

    LOG.debug('Returning.')
    return (exit_code, stdout, stderr, timed_out)

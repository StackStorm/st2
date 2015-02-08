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
import subprocess

import six

__all__ = [
    'run_command'
]


def run_command(cmd, cwd=None, env=None, shell=False):
    """
    Run the provided command in a subprocess and wait until it completes.

    :param cmd: Command to run.
    :type cmd: ``str`` or ``list``

    :param cwd: Optional working directory.
    :type cwd: ``str``

    :param env: Optional environment to use with the command. If not provided,
                environment from the current process is inherited.
    :type env: ``dict``

    :param shell: True to use a shell.
    :type shell ``boolean``

    :rtype: ``tuple`` (exit_code, stdout, stderr)
    """
    assert isinstance(cmd, (list, tuple) + six.string_types)

    if not env:
        env = os.environ.copy()

    process = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE, env=env, cwd=cwd,
                               shell=shell)
    stdout, stderr = process.communicate()
    exit_code = process.returncode

    return (exit_code, stdout, stderr)

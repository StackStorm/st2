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

import subprocess

__all__ = [
    'run_command'
]


def run_command(cmd):
    """
    Run the provided command in a subprocess and wait until it completes.

    :param cmd: Command to run.
    :type cmd: ``list``

    :rtype: ``tuple`` (exit_code, stdout, stderr)
    """
    assert isinstance(cmd, (list, str, unicode))

    process = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE)
    stdout, stderr = process.communicate()
    exit_code = process.returncode

    return (exit_code, stdout, stderr)

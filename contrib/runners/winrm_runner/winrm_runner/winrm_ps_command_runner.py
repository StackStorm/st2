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

from __future__ import absolute_import
import uuid

from st2common import log as logging
from st2common.runners.base import get_metadata as get_runner_metadata
from winrm_runner.winrm_base import WinRmBaseRunner

__all__ = [
    'WinRmPsCommandRunner',
    'get_runner',
    'get_metadata'
]

LOG = logging.getLogger(__name__)

RUNNER_COMMAND = 'cmd'


class WinRmPsCommandRunner(WinRmBaseRunner):

    def run(self, action_parameters):
        powershell_command = self.runner_parameters[RUNNER_COMMAND]

        # execute
        return self._run_ps(powershell_command)


def get_runner():
    return WinRmPsCommandRunner(str(uuid.uuid4()))


def get_metadata():
    return get_runner_metadata('winrm_ps_command_runner')

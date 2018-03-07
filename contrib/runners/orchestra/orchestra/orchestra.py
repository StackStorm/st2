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

from st2common.constants import action as action_constants
from st2common import log as logging
from st2common.runners import base as runners


__all__ = [
    'OrchestraRunner',
    'get_runner',
    'get_metadata'
]


LOG = logging.getLogger(__name__)


class OrchestraRunner(runners.AsyncActionRunner):

    def __init__(self, runner_id):
        super(OrchestraRunner, self).__init__(runner_id=runner_id)

    @staticmethod
    def get_workflow_definition(entry_point):
        with open(entry_point, 'r') as def_file:
            return def_file.read()

    def run(self, action_parameters):

        status = action_constants.LIVEACTION_STATUS_RUNNING
        partial_results = {'tasks': []}
        exec_context = self.context

        return (status, partial_results, exec_context)


def get_runner():
    return OrchestraRunner(str(uuid.uuid4()))


def get_metadata():
    return runners.get_metadata('orchestra')

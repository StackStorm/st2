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

import copy
import uuid

from orchestra import exceptions as wf_lib_exc

from st2common.constants import action as ac_const
from st2common import log as logging
from st2common.runners import base as runners
from st2common.services import workflows as wf_svc


__all__ = [
    'OrchestraRunner',
    'get_runner',
    'get_metadata'
]


LOG = logging.getLogger(__name__)


class OrchestraRunner(runners.AsyncActionRunner):

    @staticmethod
    def get_workflow_definition(entry_point):
        with open(entry_point, 'r') as def_file:
            return def_file.read()

    def _construct_context(self, wf_ex):
        ctx = copy.deepcopy(self.context)
        ctx['workflow_execution'] = str(wf_ex.id)

        return ctx

    def run(self, action_parameters):
        # Read workflow definition from file.
        wf_def = self.get_workflow_definition(self.entry_point)

        try:
            # Request workflow execution.
            wf_ex_db = wf_svc.request(wf_def, self.execution)
        except wf_lib_exc.WorkflowInspectionError as e:
            status = ac_const.LIVEACTION_STATUS_FAILED
            result = {'errors': e.args[1]}
            return (status, result, self.context)
        except Exception as e:
            status = ac_const.LIVEACTION_STATUS_FAILED
            result = {'errors': str(e)}
            return (status, result, self.context)

        # Set return values.
        status = ac_const.LIVEACTION_STATUS_RUNNING
        partial_results = {'tasks': []}
        ctx = self._construct_context(wf_ex_db)

        return (status, partial_results, ctx)


def get_runner():
    return OrchestraRunner(str(uuid.uuid4()))


def get_metadata():
    return runners.get_metadata('orchestra_runner')

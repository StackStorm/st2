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
from orchestra.specs import loader as specs_loader
from orchestra.utils import plugin

from st2common.constants import action as action_constants
from st2common import log as logging
from st2common.models.db.workflow import WorkflowExecutionDB
from st2common.persistence.workflow import WorkflowExecution
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
        self.composer = plugin.get_module('orchestra.composers', 'native')
        self.spec_module = specs_loader.get_spec_module('native')

    @staticmethod
    def get_workflow_definition(entry_point):
        with open(entry_point, 'r') as def_file:
            return def_file.read()

    def _construct_context(self, wf_ex):
        ctx = copy.deepcopy(self.context)
        ctx['workflow_execution'] = str(wf_ex.id)

        return ctx

    def run(self, action_parameters):
        # Load workflow definition from file into spec model.
        wf_def = self.get_workflow_definition(self.entry_point)
        wf_spec = self.spec_module.instantiate(wf_def)

        # Inspect workflow definition.
        try:
            wf_spec.inspect(raise_exception=True)
        except wf_lib_exc.WorkflowInspectionError as e:
            status = action_constants.LIVEACTION_STATUS_FAILED
            result = {'errors': e.args[1]}
            return (status, result, self.context)

        # Composer workflow spec into workflow execution graph.
        wf_ex_graph = self.composer.compose(wf_spec)

        # Create a record for workflow execution.
        wf_ex_db = WorkflowExecutionDB(graph=wf_ex_graph.serialize(), liveaction=self.liveaction_id)
        wf_ex_db = WorkflowExecution.insert(wf_ex_db)

        # Set return values.
        status = action_constants.LIVEACTION_STATUS_RUNNING
        partial_results = {'tasks': []}
        ctx = self._construct_context(wf_ex_db)

        return (status, partial_results, ctx)


def get_runner():
    return OrchestraRunner(str(uuid.uuid4()))


def get_metadata():
    return runners.get_metadata('orchestra_runner')

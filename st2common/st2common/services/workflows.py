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

from orchestra import conducting
from orchestra.specs import loader as specs_loader
from orchestra import states

from st2common.exceptions import action as action_exc
from st2common import log as logging
from st2common.models.db import workflow as wf_db_models
from st2common.persistence import workflow as wf_db_access
from st2common.util import action_db as ac_db_util
from st2common.util import param as param_utils


LOG = logging.getLogger(__name__)


def request(wf_def, ac_ex_db):
    # Load workflow definition into workflow spec model.
    spec_module = specs_loader.get_spec_module('native')
    wf_spec = spec_module.instantiate(wf_def)

    # Inspect the workflow spec.
    wf_spec.inspect(raise_exception=True)

    # Identify the action to execute.
    action_db = ac_db_util.get_action_by_ref(ref=ac_ex_db.action['ref'])

    if not action_db:
        error = 'Unable to find action "%s".' % ac_ex_db.action['ref']
        raise action_exc.InvalidActionReferencedException(error)

    # Identify the runner for the action.
    runner_type_db = ac_db_util.get_runnertype_by_name(action_db.runner_type['name'])

    # Render action execution parameters.
    runner_params, action_params = param_utils.render_final_params(
        runner_type_db.runner_parameters,
        action_db.parameters,
        ac_ex_db.parameters,
        ac_ex_db.context
    )

    # Instantiate the workflow conductor.
    conductor = conducting.WorkflowConductor(wf_spec, **action_params)

    # Create a record for workflow execution.
    wf_ex_db = wf_db_models.WorkflowExecutionDB(
        action_execution=str(ac_ex_db.id),
        spec=conductor.spec.serialize(),
        graph=conductor.graph.serialize(),
        flow=conductor.flow.serialize(),
        inputs=conductor.inputs,
        context=conductor.context,
        status=states.REQUESTED
    )

    # Insert new record into the database and publish to the message bus.
    wf_ex_db = wf_db_access.WorkflowExecution.insert(wf_ex_db, publish=True)

    return wf_ex_db

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
from orchestra.expressions import base as expr
from orchestra.specs import loader as specs_loader
from orchestra import states

from st2common.exceptions import action as ac_exc
from st2common import log as logging
from st2common.models.db import liveaction as lv_db_models
from st2common.models.db import workflow as wf_db_models
from st2common.persistence import workflow as wf_db_access
from st2common.services import action as ac_svc
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
        raise ac_exc.InvalidActionReferencedException(error)

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


def request_task_execution(wf_ex_db, task_id, task_spec, task_ctx, st2_ctx):
    # Identify the action to execute.
    action_db = ac_db_util.get_action_by_ref(ref=task_spec.action)

    if not action_db:
        error = 'Unable to find action "%s".' % task_spec.action
        raise ac_exc.InvalidActionReferencedException(error)

    # Identify the runner for the action.
    runner_type_db = ac_db_util.get_runnertype_by_name(action_db.runner_type['name'])

    # Create a record for task execution.
    task_ex_db = wf_db_models.TaskExecutionDB(
        workflow_execution=str(wf_ex_db.id),
        task_name=task_spec.name or task_id,
        task_id=task_id,
        task_spec=task_spec.serialize(),
        incoming_context=task_ctx,
        status=states.REQUESTED
    )

    # Insert new record into the database.
    task_ex_db = wf_db_access.TaskExecution.insert(task_ex_db, publish=False)

    # Set context for the action execution.
    ac_ex_ctx = {
        'parent': st2_ctx,
        'orchestra': {
            'workflow_execution_id': str(wf_ex_db.id),
            'task_execution_id': str(task_ex_db.id),
            'task_name': task_spec.name,
            'task_id': task_id
        }
    }

    # Render action execution parameters and setup action execution object.
    task_params = expr.evaluate(task_spec.input, task_ctx)

    ac_ex_params = param_utils.render_live_params(
        runner_type_db.runner_parameters,
        action_db.parameters,
        task_params,
        ac_ex_ctx
    )

    lv_ac_db = lv_db_models.LiveActionDB(
        action=task_spec.action,
        workflow_execution=str(wf_ex_db.id),
        task_execution=str(task_ex_db.id),
        context=ac_ex_ctx,
        parameters=ac_ex_params
    )

    # Request action execution.
    ac_svc.request(lv_ac_db)

    return task_ex_db

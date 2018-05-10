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

import retrying

from orchestra import conducting
from orchestra.specs import loader as specs_loader
from orchestra import states

from st2common.constants import action as ac_const
from st2common.exceptions import action as ac_exc
from st2common.exceptions import workflow as wf_exc
from st2common import log as logging
from st2common.models.db import liveaction as lv_db_models
from st2common.models.db import workflow as wf_db_models
from st2common.persistence import execution as ex_db_access
from st2common.persistence import workflow as wf_db_access
from st2common.services import action as ac_svc
from st2common.services import executions as ex_svc
from st2common.util import action_db as ac_db_util
from st2common.util import date as date_utils
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
        status=states.REQUESTED
    )

    # Insert new record into the database and publish to the message bus.
    wf_ex_db = wf_db_access.WorkflowExecution.insert(wf_ex_db, publish=True)

    return wf_ex_db


@retrying.retry(retry_on_exception=wf_exc.retry_on_exceptions)
def request_cancellation(ac_ex_db):
    wf_ex_dbs = wf_db_access.WorkflowExecution.query(action_execution=str(ac_ex_db.id))

    if not wf_ex_dbs:
        raise wf_exc.WorkflowExecutionNotFoundException(str(ac_ex_db.id))

    if len(wf_ex_dbs) > 1:
        raise wf_exc.AmbiguousWorkflowExecutionException(str(ac_ex_db.id))

    wf_ex_db = wf_ex_dbs[0]

    if wf_ex_db.status in states.COMPLETED_STATES:
        raise wf_exc.WorkflowExecutionAlreadyCompletedException(str(wf_ex_db.id))

    conductor = deserialize_conductor(wf_ex_db)

    if conductor.get_workflow_state() in states.COMPLETED_STATES:
        raise wf_exc.WorkflowExecutionAlreadyCompletedException(str(wf_ex_db.id))

    conductor.set_workflow_state(states.CANCELED)

    # Write the updated workflow state and task flow to the database.
    wf_ex_db.status = conductor.get_workflow_state()
    wf_ex_db.flow = conductor.flow.serialize()
    wf_ex_db = wf_db_access.WorkflowExecution.update(wf_ex_db, publish=False)

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
        initial_context=task_ctx,
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
            'task_name': task_spec.name or task_id,
            'task_id': task_id
        }
    }

    # Render action execution parameters and setup action execution object.
    ac_ex_params = param_utils.render_live_params(
        runner_type_db.runner_parameters or {},
        action_db.parameters or {},
        getattr(task_spec, 'input', None) or {},
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

    # Sst the task execution to running.
    task_ex_db.status = states.RUNNING
    task_ex_db = wf_db_access.TaskExecution.update(task_ex_db, publish=False)

    return task_ex_db


def handle_action_execution_completion(ac_ex_db):
    # Check that the action execution is completed.
    if ac_ex_db.status not in ac_const.LIVEACTION_COMPLETED_STATES:
        raise Exception(
            'Unable to handle completion of action execution. The action execution '
            '"%s" is in "%s" state.' % (str(ac_ex_db.id), ac_ex_db.status)
        )

    # Get related record identifiers.
    wf_ex_id = ac_ex_db.context['orchestra']['workflow_execution_id']
    task_ex_id = ac_ex_db.context['orchestra']['task_execution_id']

    # Update task execution if completed.
    update_task_execution(task_ex_id, ac_ex_db.status, ac_ex_db.result)

    # Request the next set of tasks if workflow execution is not complete.
    request_next_tasks(task_ex_id)

    # Update workflow execution if completed.
    update_workflow_execution(wf_ex_id)


def deserialize_conductor(wf_ex_db):
    data = {
        'spec': wf_ex_db.spec,
        'graph': wf_ex_db.graph,
        'state': wf_ex_db.status,
        'flow': wf_ex_db.flow,
        'inputs': wf_ex_db.inputs
    }

    return conducting.WorkflowConductor.deserialize(data)


def refresh_conductor(wf_ex_id):
    wf_ex_db = wf_db_access.WorkflowExecution.get_by_id(wf_ex_id)
    conductor = deserialize_conductor(wf_ex_db)

    return conductor, wf_ex_db


@retrying.retry(retry_on_exception=wf_exc.retry_on_exceptions)
def update_task_execution(task_ex_id, ac_ex_status, ac_ex_result):
    # Return if action execution is not completed.
    if ac_ex_status not in states.COMPLETED_STATES:
        return

    # Update task execution if action execution is completed.
    task_ex_db = wf_db_access.TaskExecution.get_by_id(task_ex_id)
    task_ex_db.status = ac_ex_status
    task_ex_db.result = ac_ex_result
    task_ex_db.end_timestamp = date_utils.get_datetime_utc_now()
    wf_db_access.TaskExecution.update(task_ex_db, publish=False)


@retrying.retry(retry_on_exception=wf_exc.retry_on_exceptions)
def request_next_tasks(task_ex_id):
    task_ex_db = wf_db_access.TaskExecution.get_by_id(task_ex_id)

    # Return if task execution is not complete..
    if task_ex_db.status not in states.COMPLETED_STATES:
        return

    # Update task flow if task execution is completed.
    conductor, wf_ex_db = refresh_conductor(task_ex_db.workflow_execution)
    conductor.update_task_flow(task_ex_db.task_id, task_ex_db.status, result=task_ex_db.result)

    # Identify the list of next set of tasks.
    next_tasks = conductor.get_next_tasks(task_ex_db.task_id)

    # Mark the next tasks as running in the task flow.
    # The task should be marked before actual task execution.
    for task in next_tasks:
        conductor.update_task_flow(task['id'], states.RUNNING)

    # Write the updated workflow state and task flow to the database.
    wf_ex_db.status = conductor.get_workflow_state()
    wf_ex_db.flow = conductor.flow.serialize()
    wf_ex_db = wf_db_access.WorkflowExecution.update(wf_ex_db, publish=False)

    # Request task execution for the root tasks.
    for task in next_tasks:
        st2_ctx = {'execution_id': wf_ex_db.action_execution}
        request_task_execution(wf_ex_db, task['id'], task['spec'], task['ctx'], st2_ctx)


@retrying.retry(retry_on_exception=wf_exc.retry_on_exceptions)
def update_workflow_execution(wf_ex_id):
    conductor, wf_ex_db = refresh_conductor(wf_ex_id)

    # There is nothing to update if workflow execution is not complete.
    if conductor.get_workflow_state() not in states.COMPLETED_STATES:
        return

    # Write the updated workflow state and task flow to the database.
    wf_ex_db.end_timestamp = date_utils.get_datetime_utc_now()
    wf_ex_db.status = conductor.get_workflow_state()
    wf_ex_db.outputs = conductor.get_workflow_output()
    wf_ex_db.flow = conductor.flow.serialize()
    wf_ex_db = wf_db_access.WorkflowExecution.update(wf_ex_db, publish=False)

    # Update the corresponding liveaction and action execution for the workflow.
    wf_ac_ex_db = ex_db_access.ActionExecution.get_by_id(wf_ex_db.action_execution)
    wf_lv_ac_db = ac_db_util.get_liveaction_by_id(wf_ac_ex_db.liveaction['id'])

    wf_lv_ac_db = ac_db_util.update_liveaction_status(
        status=wf_ex_db.status,
        result=wf_ex_db.outputs,
        end_timestamp=wf_ex_db.end_timestamp,
        liveaction_db=wf_lv_ac_db)

    ex_svc.update_execution(wf_lv_ac_db)

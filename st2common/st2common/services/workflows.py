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
from st2common.persistence import liveaction as lv_db_access
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
    conductor.set_workflow_state(states.REQUESTED)

    # Serialize the conductor which initializes some internal values.
    data = conductor.serialize()

    # Create a record for workflow execution.
    wf_ex_db = wf_db_models.WorkflowExecutionDB(
        action_execution=str(ac_ex_db.id),
        spec=data['spec'],
        graph=data['graph'],
        flow=data['flow'],
        input=data['input'],
        output=data['output'],
        errors=data['errors'],
        status=data['state']
    )

    # Insert new record into the database and publish to the message bus.
    wf_ex_db = wf_db_access.WorkflowExecution.insert(wf_ex_db, publish=True)

    return wf_ex_db


@retrying.retry(retry_on_exception=wf_exc.retry_on_exceptions)
def request_pause(ac_ex_db):
    wf_ex_dbs = wf_db_access.WorkflowExecution.query(action_execution=str(ac_ex_db.id))

    if not wf_ex_dbs:
        raise wf_exc.WorkflowExecutionNotFoundException(str(ac_ex_db.id))

    if len(wf_ex_dbs) > 1:
        raise wf_exc.AmbiguousWorkflowExecutionException(str(ac_ex_db.id))

    wf_ex_db = wf_ex_dbs[0]

    if wf_ex_db.status in states.COMPLETED_STATES:
        raise wf_exc.WorkflowExecutionIsCompletedException(str(wf_ex_db.id))

    conductor = deserialize_conductor(wf_ex_db)

    if conductor.get_workflow_state() in states.COMPLETED_STATES:
        raise wf_exc.WorkflowExecutionIsCompletedException(str(wf_ex_db.id))

    conductor.set_workflow_state(states.PAUSED)

    # Write the updated workflow state and task flow to the database.
    wf_ex_db.status = conductor.get_workflow_state()
    wf_ex_db.flow = conductor.flow.serialize()
    wf_ex_db = wf_db_access.WorkflowExecution.update(wf_ex_db, publish=False)

    return wf_ex_db


@retrying.retry(retry_on_exception=wf_exc.retry_on_exceptions)
def request_resume(ac_ex_db):
    wf_ex_dbs = wf_db_access.WorkflowExecution.query(action_execution=str(ac_ex_db.id))

    if not wf_ex_dbs:
        raise wf_exc.WorkflowExecutionNotFoundException(str(ac_ex_db.id))

    if len(wf_ex_dbs) > 1:
        raise wf_exc.AmbiguousWorkflowExecutionException(str(ac_ex_db.id))

    wf_ex_db = wf_ex_dbs[0]

    if wf_ex_db.status in states.COMPLETED_STATES:
        raise wf_exc.WorkflowExecutionIsCompletedException(str(wf_ex_db.id))

    if wf_ex_db.status in states.RUNNING_STATES:
        raise wf_exc.WorkflowExecutionIsRunningException(str(wf_ex_db.id))

    conductor = deserialize_conductor(wf_ex_db)

    if conductor.get_workflow_state() in states.COMPLETED_STATES:
        raise wf_exc.WorkflowExecutionIsCompletedException(str(wf_ex_db.id))

    if conductor.get_workflow_state() in states.RUNNING_STATES:
        raise wf_exc.WorkflowExecutionIsRunningException(str(wf_ex_db.id))

    conductor.set_workflow_state(states.RESUMING)

    # Write the updated workflow state and task flow to the database.
    wf_ex_db.status = conductor.get_workflow_state()
    wf_ex_db.flow = conductor.flow.serialize()
    wf_ex_db = wf_db_access.WorkflowExecution.update(wf_ex_db, publish=False)

    # Publish state change.
    wf_db_access.WorkflowExecution.publish_status(wf_ex_db)

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
        raise wf_exc.WorkflowExecutionIsCompletedException(str(wf_ex_db.id))

    conductor = deserialize_conductor(wf_ex_db)

    if conductor.get_workflow_state() in states.COMPLETED_STATES:
        raise wf_exc.WorkflowExecutionIsCompletedException(str(wf_ex_db.id))

    conductor.set_workflow_state(states.CANCELED)

    # Write the updated workflow state and task flow to the database.
    wf_ex_db.status = conductor.get_workflow_state()
    wf_ex_db.flow = conductor.flow.serialize()
    wf_ex_db = wf_db_access.WorkflowExecution.update(wf_ex_db, publish=False)

    # Cascade the cancellation up to the root of the workflow.
    root_ac_ex_db = ac_svc.get_root_execution(ac_ex_db)

    if root_ac_ex_db != ac_ex_db and root_ac_ex_db.status not in ac_const.LIVEACTION_CANCEL_STATES:
        root_lv_ac_db = lv_db_access.LiveAction.get(id=root_ac_ex_db.liveaction['id'])
        ac_svc.request_cancellation(root_lv_ac_db, None)

    return wf_ex_db


def request_task_execution(wf_ex_db, task_id, task_spec, task_ctx, st2_ctx):
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

    try:
        # Return here if no action is specified in task spec.
        if task_spec.action is None:
            # Set the task execution to running.
            task_ex_db.status = states.RUNNING
            task_ex_db = wf_db_access.TaskExecution.update(task_ex_db, publish=False)

            # Fast forward task execution to completion.
            update_task_execution(str(task_ex_db.id), states.SUCCEEDED)
            update_task_flow(str(task_ex_db.id), publish=False)

            # Refresh and return the task execution
            return wf_db_access.TaskExecution.get_by_id(str(task_ex_db.id))

        # Identify the action to execute.
        action_db = ac_db_util.get_action_by_ref(ref=task_spec.action)

        if not action_db:
            error = 'Unable to find action "%s".' % task_spec.action
            raise ac_exc.InvalidActionReferencedException(error)

        # Identify the runner for the action.
        runner_type_db = ac_db_util.get_runnertype_by_name(action_db.runner_type['name'])

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

        # Set the task execution to running.
        task_ex_db.status = states.RUNNING
        task_ex_db = wf_db_access.TaskExecution.update(task_ex_db, publish=False)
    except Exception as e:
        result = {'errors': [{'message': str(e), 'task_id': task_ex_db.task_id}]}
        update_task_execution(str(task_ex_db.id), states.FAILED, result)
        raise e

    return task_ex_db


def handle_action_execution_pause(ac_ex_db):
    # Check that the action execution is paused.
    if ac_ex_db.status != ac_const.LIVEACTION_STATUS_PAUSED:
        raise Exception(
            'Unable to handle pause of action execution. The action execution '
            '"%s" is in "%s" state.' % (str(ac_ex_db.id), ac_ex_db.status)
        )

    # Get related record identifiers.
    task_ex_id = ac_ex_db.context['orchestra']['task_execution_id']

    # Updat task execution
    update_task_execution(task_ex_id, ac_ex_db.status)

    # Update task flow in the workflow execution.
    update_task_flow(task_ex_id, publish=False)


def handle_action_execution_resume(ac_ex_db):
    if 'orchestra' not in ac_ex_db.context:
        raise Exception(
            'Unable to handle resume of action execution. The action execution '
            '%s is not an orchestra workflow task.' % str(ac_ex_db.id)
        )

    wf_ex_id = ac_ex_db.context['orchestra']['workflow_execution_id']
    task_ex_id = ac_ex_db.context['orchestra']['task_execution_id']

    # Updat task execution to running.
    resume_task_execution(task_ex_id)

    # Update workflow execution to running.
    resume_workflow_execution(wf_ex_id, task_ex_id)

    # If action execution has a parent, cascade status change upstream and do not publish
    # the status change because we do not want to trigger resume of other peer subworkflows.
    if 'parent' in ac_ex_db.context:
        parent_ac_ex_id = ac_ex_db.context['parent']['execution_id']
        parent_ac_ex_db = ex_db_access.ActionExecution.get_by_id(parent_ac_ex_id)

        if parent_ac_ex_db.status == ac_const.LIVEACTION_STATUS_PAUSED:
            ac_db_util.update_liveaction_status(
                liveaction_id=parent_ac_ex_db.liveaction['id'],
                status=ac_const.LIVEACTION_STATUS_RUNNING,
                publish=False)

        # If there are grand parents, handle the resume of the parent action execution.
        if 'orchestra' in parent_ac_ex_db.context and 'parent' in parent_ac_ex_db.context:
            handle_action_execution_resume(parent_ac_ex_db)


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
        'input': wf_ex_db.input,
        'output': wf_ex_db.output,
        'errors': wf_ex_db.errors
    }

    return conducting.WorkflowConductor.deserialize(data)


def refresh_conductor(wf_ex_id):
    wf_ex_db = wf_db_access.WorkflowExecution.get_by_id(wf_ex_id)
    conductor = deserialize_conductor(wf_ex_db)

    return conductor, wf_ex_db


@retrying.retry(retry_on_exception=wf_exc.retry_on_exceptions)
def update_task_flow(task_ex_id, publish=True):
    task_ex_db = wf_db_access.TaskExecution.get_by_id(task_ex_id)

    # Return if task execution is not completed or paused.
    if task_ex_db.status not in states.COMPLETED_STATES + [states.PAUSED]:
        return

    # Update task flow if task execution is completed or paused.
    conductor, wf_ex_db = refresh_conductor(task_ex_db.workflow_execution)
    conductor.update_task_flow(task_ex_db.task_id, task_ex_db.status, result=task_ex_db.result)

    # Update workflow execution and related liveaction and action execution.
    update_execution_records(
        wf_ex_db,
        conductor,
        update_lv_ac_on_states=(states.COMPLETED_STATES + [states.PAUSED]),
        pub_lv_ac=publish,
        pub_ac_ex=publish
    )


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

    # If there is no new tasks, update execution records to handle possible completion.
    if not next_tasks:
        # Update workflow execution and related liveaction and action execution.
        update_execution_records(wf_ex_db, conductor)

    # Iterate while there are next tasks identified for processing. In the case for
    # task with no action execution defined, the task execution will complete
    # immediately with a new set of tasks available.
    while next_tasks:
        # Mark the tasks as running in the task flow before actual task execution.
        for task in next_tasks:
            conductor.update_task_flow(task['id'], states.RUNNING)

        # Update workflow execution and related liveaction and action execution.
        update_execution_records(wf_ex_db, conductor)

        # Request task execution for the tasks.
        for task in next_tasks:
            try:
                task_id, task_spec, task_ctx = task['id'], task['spec'], task['ctx']
                st2_ctx = {'execution_id': wf_ex_db.action_execution}
                request_task_execution(wf_ex_db, task_id, task_spec, task_ctx, st2_ctx)
            except Exception as e:
                fail_workflow_execution(str(wf_ex_db.id), e, task_id=task['id'])
                return

        # Identify the next set of tasks to execute.
        conductor, wf_ex_db = refresh_conductor(str(wf_ex_db.id))
        next_tasks = conductor.get_next_tasks()


@retrying.retry(retry_on_exception=wf_exc.retry_on_exceptions)
def update_task_execution(task_ex_id, ac_ex_status, ac_ex_result=None):
    if ac_ex_status not in states.COMPLETED_STATES + [states.PAUSED]:
        return

    task_ex_db = wf_db_access.TaskExecution.get_by_id(task_ex_id)
    task_ex_db.status = ac_ex_status
    task_ex_db.result = ac_ex_result if ac_ex_result else task_ex_db.result

    if ac_ex_status in states.COMPLETED_STATES:
        task_ex_db.end_timestamp = date_utils.get_datetime_utc_now()

    wf_db_access.TaskExecution.update(task_ex_db, publish=False)


@retrying.retry(retry_on_exception=wf_exc.retry_on_exceptions)
def resume_task_execution(task_ex_id):
    # Update task execution to running.
    task_ex_db = wf_db_access.TaskExecution.get_by_id(task_ex_id)
    task_ex_db.status = states.RUNNING

    # Write update to the database.
    wf_db_access.TaskExecution.update(task_ex_db, publish=False)


@retrying.retry(retry_on_exception=wf_exc.retry_on_exceptions)
def update_workflow_execution(wf_ex_id):
    conductor, wf_ex_db = refresh_conductor(wf_ex_id)

    # There is nothing to update if workflow execution is not completed or paused.
    if conductor.get_workflow_state() in states.COMPLETED_STATES + [states.PAUSED]:
        # Update workflow execution and related liveaction and action execution.
        update_execution_records(wf_ex_db, conductor)


@retrying.retry(retry_on_exception=wf_exc.retry_on_exceptions)
def resume_workflow_execution(wf_ex_id, task_ex_id):
    # Update workflow execution to running.
    conductor, wf_ex_db = refresh_conductor(wf_ex_id)
    conductor.set_workflow_state(states.RUNNING)

    # Update task execution in task flow to running.
    task_ex_db = wf_db_access.TaskExecution.get_by_id(task_ex_id)
    conductor.update_task_flow(task_ex_db.task_id, states.RUNNING)

    # Update workflow execution and related liveaction and action execution.
    update_execution_records(wf_ex_db, conductor)


@retrying.retry(retry_on_exception=wf_exc.retry_on_exceptions)
def fail_workflow_execution(wf_ex_id, exception, task_id=None):
    conductor, wf_ex_db = refresh_conductor(wf_ex_id)

    # Set workflow execution status to failed and record error.
    conductor.set_workflow_state(states.FAILED)
    conductor.log_error(str(exception), task_id=task_id)

    # Update workflow execution and related liveaction and action execution.
    update_execution_records(wf_ex_db, conductor)


def update_execution_records(wf_ex_db, conductor, update_lv_ac_on_states=None,
                             pub_wf_ex=False, pub_lv_ac=True, pub_ac_ex=True):

    # Update timestamp and output if workflow is completed.
    if conductor.get_workflow_state() in states.COMPLETED_STATES:
        wf_ex_db.end_timestamp = date_utils.get_datetime_utc_now()
        wf_ex_db.output = conductor.get_workflow_output()

    # Update workflow status and task flow and write changes to database.
    wf_ex_db.status = conductor.get_workflow_state()
    wf_ex_db.errors = copy.deepcopy(conductor.errors)
    wf_ex_db.flow = conductor.flow.serialize()
    wf_ex_db = wf_db_access.WorkflowExecution.update(wf_ex_db, publish=pub_wf_ex)

    # Return if workflow execution status is not specified in update_lv_ac_on_states.
    if isinstance(update_lv_ac_on_states, list) and wf_ex_db.status not in update_lv_ac_on_states:
        return

    # Update the corresponding liveaction and action execution for the workflow.
    wf_ac_ex_db = ex_db_access.ActionExecution.get_by_id(wf_ex_db.action_execution)
    wf_lv_ac_db = ac_db_util.get_liveaction_by_id(wf_ac_ex_db.liveaction['id'])

    # Gather result for liveaction and action execution.
    result = {'output': wf_ex_db.output or None}

    if wf_ex_db.status in states.ABENDED_STATES:
        result['errors'] = wf_ex_db.errors

    # Sync update with corresponding liveaction and action execution.
    wf_lv_ac_db = ac_db_util.update_liveaction_status(
        status=wf_ex_db.status,
        result=result,
        end_timestamp=wf_ex_db.end_timestamp,
        liveaction_db=wf_lv_ac_db,
        publish=pub_lv_ac)

    ex_svc.update_execution(wf_lv_ac_db, publish=pub_ac_ex)

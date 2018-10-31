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
import six

from orquesta import conducting
from orquesta import events
from orquesta import exceptions as orquesta_exc
from orquesta.expressions import base as expressions
from orquesta.specs import loader as specs_loader
from orquesta import states

from st2common.constants import action as ac_const
from st2common.exceptions import action as ac_exc
from st2common.exceptions import workflow as wf_exc
from st2common import log as logging
from st2common.models.api import notification as notify_api_models
from st2common.models.db import liveaction as lv_db_models
from st2common.models.db import workflow as wf_db_models
from st2common.models.system import common as sys_models
from st2common.models.utils import action_param_utils
from st2common.persistence import liveaction as lv_db_access
from st2common.persistence import execution as ex_db_access
from st2common.persistence import workflow as wf_db_access
from st2common.services import action as ac_svc
from st2common.services import executions as ex_svc
from st2common.util import action_db as action_utils
from st2common.util import date as date_utils
from st2common.util import param as param_utils


LOG = logging.getLogger(__name__)


def is_action_execution_under_workflow_context(ac_ex_db):
    # The action execution is executed under the context of a workflow
    # if it contains the orquesta key in its context dictionary.
    return ac_ex_db.context and 'orquesta' in ac_ex_db.context


def format_inspection_result(result):
    errors = []

    categories = {
        'contents': 'content',
        'context': 'context',
        'expressions': 'expression',
        'semantics': 'semantic',
        'syntax': 'syntax'
    }

    # For context and expression errors, rename the attribute from type to language.
    for category in ['context', 'expressions']:
        for entry in result.get(category, []):
            if 'language' not in entry:
                entry['language'] = entry['type']
                del entry['type']

    # For all categories, put the category value in the type attribute.
    for category, entries in six.iteritems(result):
        for entry in entries:
            entry['type'] = categories[category]
            errors.append(entry)

    return errors


def inspect(wf_spec, st2_ctx, raise_exception=True):
    # Inspect workflow definition.
    result = wf_spec.inspect(app_ctx=st2_ctx, raise_exception=False)
    errors = format_inspection_result(result)

    # Inspect st2 specific contents.
    errors += inspect_task_contents(wf_spec)

    # Sort the list of errors by type and path.
    errors = sorted(errors, key=lambda e: (e['type'], e['schema_path']))

    if errors and raise_exception:
        raise orquesta_exc.WorkflowInspectionError(errors)

    return errors


def inspect_task_contents(wf_spec):
    result = []
    spec_path = 'tasks'
    schema_path = 'properties.tasks.patternProperties.^\\w+$'
    action_schema_path = schema_path + '.properties.action'
    action_input_schema_path = schema_path + '.properties.input'

    def is_action_an_expression(action):
        if isinstance(action, six.string_types):
            for name, evaluator in six.iteritems(expressions.get_evaluators()):
                if evaluator.has_expressions(action):
                    return True

    for task_name, task_spec in six.iteritems(wf_spec.tasks):
        action_ref = getattr(task_spec, 'action', None)
        action_spec_path = spec_path + '.' + task_name + '.action'
        action_input_spec_path = spec_path + '.' + task_name + '.input'

        # Move on if action is empty or an expression.
        if not action_ref or is_action_an_expression(action_ref):
            continue

        # Check that the format of the action is a valid resource reference.
        if not sys_models.ResourceReference.is_resource_reference(action_ref):
            entry = {
                'type': 'content',
                'message': 'The action reference "%s" is not formatted correctly.' % action_ref,
                'spec_path': action_spec_path,
                'schema_path': action_schema_path
            }

            result.append(entry)
            continue

        # Check that the action is registered in the database.
        if not action_utils.get_action_by_ref(ref=action_ref):
            entry = {
                'type': 'content',
                'message': 'The action "%s" is not registered in the database.' % action_ref,
                'spec_path': action_spec_path,
                'schema_path': action_schema_path
            }

            result.append(entry)
            continue

        # Check the action parameters.
        params = getattr(task_spec, 'input', None) or {}

        if params and not isinstance(params, dict):
            continue

        requires, unexpected = action_param_utils.validate_action_parameters(action_ref, params)

        for param in requires:
            message = 'Action "%s" is missing required input "%s".' % (action_ref, param)

            entry = {
                'type': 'content',
                'message': message,
                'spec_path': action_input_spec_path,
                'schema_path': action_input_schema_path
            }

            result.append(entry)

        for param in unexpected:
            message = 'Action "%s" has unexpected input "%s".' % (action_ref, param)

            entry = {
                'type': 'content',
                'message': message,
                'spec_path': action_input_spec_path + '.' + param,
                'schema_path': action_input_schema_path + '.patternProperties.^\\w+$'
            }

            result.append(entry)

    return result


def request(wf_def, ac_ex_db, st2_ctx, notify_cfg=None):
    wf_ac_ex_id = str(ac_ex_db.id)
    LOG.info('[%s] Processing action execution request for workflow.', wf_ac_ex_id)

    # Load workflow definition into workflow spec model.
    spec_module = specs_loader.get_spec_module('native')
    wf_spec = spec_module.instantiate(wf_def)

    # Inspect the workflow spec.
    inspect(wf_spec, st2_ctx, raise_exception=True)

    # Identify the action to execute.
    action_db = action_utils.get_action_by_ref(ref=ac_ex_db.action['ref'])

    if not action_db:
        error = 'Unable to find action "%s".' % ac_ex_db.action['ref']
        raise ac_exc.InvalidActionReferencedException(error)

    # Identify the runner for the action.
    runner_type_db = action_utils.get_runnertype_by_name(action_db.runner_type['name'])

    # Render action execution parameters.
    runner_params, action_params = param_utils.render_final_params(
        runner_type_db.runner_parameters,
        action_db.parameters,
        ac_ex_db.parameters,
        ac_ex_db.context
    )

    # Instantiate the workflow conductor.
    conductor_params = {'inputs': action_params, 'context': st2_ctx}
    conductor = conducting.WorkflowConductor(wf_spec, **conductor_params)

    # Set the initial workflow state to requested.
    conductor.request_workflow_state(states.REQUESTED)

    # Serialize the conductor which initializes some internal values.
    data = conductor.serialize()

    # Create a record for workflow execution.
    wf_ex_db = wf_db_models.WorkflowExecutionDB(
        action_execution=str(ac_ex_db.id),
        spec=data['spec'],
        graph=data['graph'],
        flow=data['flow'],
        context=data['context'],
        input=data['input'],
        output=data['output'],
        errors=data['errors'],
        status=data['state']
    )

    # Inspect that the list of tasks in the notify parameter exist in the workflow spec.
    if runner_params.get('notify'):
        invalid_tasks = list(set(runner_params.get('notify')) - set(wf_spec.tasks.keys()))

        if invalid_tasks:
            raise wf_exc.WorkflowExecutionException(
                'The following tasks in the notify parameter do not exist '
                'in the workflow definition: %s.' % ', '.join(invalid_tasks)
            )

    # Write notify instruction to record.
    if notify_cfg:
        # Set up the notify instruction in the workflow execution record.
        wf_ex_db.notify = {
            'config': notify_cfg,
            'tasks': runner_params.get('notify')
        }

    # Insert new record into the database and do not publish to the message bus yet.
    wf_ex_db = wf_db_access.WorkflowExecution.insert(wf_ex_db, publish=False)
    LOG.info('[%s] Workflow execution "%s" is created.', wf_ac_ex_id, str(wf_ex_db.id))

    # Update the context with the workflow execution id created on database insert.
    # Publish the workflow execution requested state to the message bus.
    if wf_ex_db.status not in states.COMPLETED_STATES:
        wf_ex_db.context['st2']['workflow_execution_id'] = str(wf_ex_db.id)
        wf_ex_db.flow['contexts'][0]['value']['st2']['workflow_execution_id'] = str(wf_ex_db.id)
        wf_ex_db = wf_db_access.WorkflowExecution.update(wf_ex_db, publish=False)
        wf_db_access.WorkflowExecution.publish_status(wf_ex_db)
        msg = '[%s] Workflow execution "%s" is published.'
        LOG.info(msg, wf_ac_ex_id, str(wf_ex_db.id))
    else:
        msg = '[%s] Workflow execution is in completed state "%s".'
        LOG.info(msg, wf_ac_ex_id, wf_ex_db.status)

    return wf_ex_db


@retrying.retry(retry_on_exception=wf_exc.retry_on_exceptions)
def request_pause(ac_ex_db):
    wf_ac_ex_id = str(ac_ex_db.id)
    LOG.info('[%s] Processing pause request for workflow.', wf_ac_ex_id)

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

    conductor.request_workflow_state(states.PAUSED)

    # Write the updated workflow state and task flow to the database.
    wf_ex_db.status = conductor.get_workflow_state()
    wf_ex_db.flow = conductor.flow.serialize()
    wf_ex_db = wf_db_access.WorkflowExecution.update(wf_ex_db, publish=False)

    LOG.info('[%s] Completed processing pause request for workflow.', wf_ac_ex_id)

    return wf_ex_db


@retrying.retry(retry_on_exception=wf_exc.retry_on_exceptions)
def request_resume(ac_ex_db):
    wf_ac_ex_id = str(ac_ex_db.id)
    LOG.info('[%s] Processing resume request for workflow.', wf_ac_ex_id)

    wf_ex_dbs = wf_db_access.WorkflowExecution.query(action_execution=str(ac_ex_db.id))

    if not wf_ex_dbs:
        raise wf_exc.WorkflowExecutionNotFoundException(str(ac_ex_db.id))

    if len(wf_ex_dbs) > 1:
        raise wf_exc.AmbiguousWorkflowExecutionException(str(ac_ex_db.id))

    wf_ex_db = wf_ex_dbs[0]

    if wf_ex_db.status in states.COMPLETED_STATES:
        raise wf_exc.WorkflowExecutionIsCompletedException(str(wf_ex_db.id))

    if wf_ex_db.status in states.RUNNING_STATES:
        msg = '[%s] Workflow execution "%s" is not resumed because it is already active.'
        LOG.info(msg, wf_ac_ex_id, str(wf_ex_db.id))
        return

    conductor = deserialize_conductor(wf_ex_db)

    if conductor.get_workflow_state() in states.COMPLETED_STATES:
        raise wf_exc.WorkflowExecutionIsCompletedException(str(wf_ex_db.id))

    if conductor.get_workflow_state() in states.RUNNING_STATES:
        msg = '[%s] Workflow execution "%s" is not resumed because it is already active.'
        LOG.info(msg, wf_ac_ex_id, str(wf_ex_db.id))
        return

    conductor.request_workflow_state(states.RESUMING)

    # Write the updated workflow state and task flow to the database.
    wf_ex_db.status = conductor.get_workflow_state()
    wf_ex_db.flow = conductor.flow.serialize()
    wf_db_access.WorkflowExecution.update(wf_ex_db, publish=False)
    wf_ex_db = wf_db_access.WorkflowExecution.get_by_id(str(wf_ex_db.id))

    # Publish state change.
    wf_db_access.WorkflowExecution.publish_status(wf_ex_db)

    LOG.info('[%s] Completed processing resume request for workflow.', wf_ac_ex_id)

    return wf_ex_db


@retrying.retry(retry_on_exception=wf_exc.retry_on_exceptions)
def request_cancellation(ac_ex_db):
    wf_ac_ex_id = str(ac_ex_db.id)
    LOG.info('[%s] Processing cancelation request for workflow.', wf_ac_ex_id)

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

    conductor.request_workflow_state(states.CANCELED)

    # Write the updated workflow state and task flow to the database.
    wf_ex_db.status = conductor.get_workflow_state()
    wf_ex_db.flow = conductor.flow.serialize()
    wf_ex_db = wf_db_access.WorkflowExecution.update(wf_ex_db, publish=False)

    # Cascade the cancellation up to the root of the workflow.
    root_ac_ex_db = ac_svc.get_root_execution(ac_ex_db)

    if root_ac_ex_db != ac_ex_db and root_ac_ex_db.status not in ac_const.LIVEACTION_CANCEL_STATES:
        LOG.info('[%s] Cascading cancelation request to parent workflow.', wf_ac_ex_id)
        root_lv_ac_db = lv_db_access.LiveAction.get(id=root_ac_ex_db.liveaction['id'])
        ac_svc.request_cancellation(root_lv_ac_db, None)

    LOG.debug('[%s] %s', wf_ac_ex_id, conductor.serialize())
    LOG.info('[%s] Completed processing cancelation request for workflow.', wf_ac_ex_id)

    return wf_ex_db


def request_task_execution(wf_ex_db, st2_ctx, task_req):
    wf_ac_ex_id = wf_ex_db.action_execution
    task_id = task_req['id']
    task_spec = task_req['spec']
    task_ctx = task_req['ctx']
    task_actions = task_req['actions']

    LOG.info('[%s] Processing task execution request for "%s".', wf_ac_ex_id, task_id)

    # Use existing task execution when task is with items and still running.
    task_ex_dbs = wf_db_access.TaskExecution.query(
        workflow_execution=str(wf_ex_db.id),
        task_id=task_id,
        order_by=['-start_timestamp']
    )

    if (len(task_ex_dbs) > 0 and task_ex_dbs[0].itemized and
            task_ex_dbs[0].status == ac_const.LIVEACTION_STATUS_RUNNING):
        task_ex_db = task_ex_dbs[0]
        task_ex_id = str(task_ex_db.id)
        msg = '[%s] Task execution "%s" retrieved for task "%s".'
        LOG.info(msg, wf_ac_ex_id, task_ex_id, task_id)
    else:
        # Create a record for task execution.
        task_ex_db = wf_db_models.TaskExecutionDB(
            workflow_execution=str(wf_ex_db.id),
            task_name=task_spec.name or task_id,
            task_id=task_id,
            task_spec=task_spec.serialize(),
            itemized=task_spec.has_items(),
            context=task_ctx,
            status=states.REQUESTED
        )

        # Prepare the result format for itemized task execution.
        if task_ex_db.itemized:
            task_ex_db.result = {'items': [None] * task_req['items_count']}

        # Insert new record into the database.
        task_ex_db = wf_db_access.TaskExecution.insert(task_ex_db, publish=False)
        task_ex_id = str(task_ex_db.id)
        msg = '[%s] Task execution "%s" created for task "%s".'
        LOG.info(msg, wf_ac_ex_id, task_ex_id, task_id)

    try:
        # Return here if no action is specified in task spec.
        if task_spec.action is None:
            LOG.info('[%s] Task "%s" is action less and succeed by default.', wf_ac_ex_id, task_id)

            # Set the task execution to running.
            task_ex_db.status = states.RUNNING
            task_ex_db = wf_db_access.TaskExecution.update(task_ex_db, publish=False)

            # Fast forward task execution to completion.
            update_task_execution(str(task_ex_db.id), states.SUCCEEDED)
            update_task_flow(str(task_ex_db.id), states.SUCCEEDED, publish=False)

            # Refresh and return the task execution
            return wf_db_access.TaskExecution.get_by_id(str(task_ex_db.id))

        # Request action execution for each actions in the task request.
        for action in task_actions:
            request_action_execution(wf_ex_db, task_ex_db, st2_ctx, action)
            task_ex_db = wf_db_access.TaskExecution.get_by_id(str(task_ex_db.id))
    except Exception as e:
        msg = '[%s] Failed action execution(s) for task "%s". %s'
        LOG.exception(msg, wf_ac_ex_id, task_id, str(e))
        result = {'errors': [{'message': str(e), 'task_id': task_ex_db.task_id}]}
        update_task_execution(str(task_ex_db.id), states.FAILED, result)
        raise e

    return task_ex_db


@retrying.retry(retry_on_exception=wf_exc.retry_on_exceptions)
def request_action_execution(wf_ex_db, task_ex_db, st2_ctx, ac_ex_req):
    wf_ac_ex_id = wf_ex_db.action_execution
    action_ref = ac_ex_req['action']
    action_input = ac_ex_req['input']
    item_id = ac_ex_req.get('item_id')

    # If the task is with items and item_id is not provided, raise exception.
    if task_ex_db.itemized and item_id is None:
        msg = 'Unable to request action execution. Identifier for the item is not provided.'
        raise Exception(msg)

    # Identify the action to execute.
    action_db = action_utils.get_action_by_ref(ref=action_ref)

    if not action_db:
        error = 'Unable to find action "%s".' % action_ref
        raise ac_exc.InvalidActionReferencedException(error)

    # Identify the runner for the action.
    runner_type_db = action_utils.get_runnertype_by_name(action_db.runner_type['name'])

    # Set context for the action execution.
    ac_ex_ctx = {
        'parent': st2_ctx,
        'orquesta': {
            'workflow_execution_id': str(wf_ex_db.id),
            'task_execution_id': str(task_ex_db.id),
            'task_name': task_ex_db.task_name,
            'task_id': task_ex_db.task_id
        }
    }

    if item_id is not None:
        ac_ex_ctx['orquesta']['item_id'] = item_id

    # Render action execution parameters and setup action execution object.
    ac_ex_params = param_utils.render_live_params(
        runner_type_db.runner_parameters or {},
        action_db.parameters or {},
        action_input or {},
        ac_ex_ctx
    )

    lv_ac_db = lv_db_models.LiveActionDB(
        action=action_ref,
        workflow_execution=str(wf_ex_db.id),
        task_execution=str(task_ex_db.id),
        context=ac_ex_ctx,
        parameters=ac_ex_params
    )

    # Set notification if instructed.
    if (wf_ex_db.notify and wf_ex_db.notify.get('config') and
            wf_ex_db.notify.get('tasks') and task_ex_db.task_name in wf_ex_db.notify['tasks']):
        lv_ac_db.notify = notify_api_models.NotificationsHelper.to_model(wf_ex_db.notify['config'])

    # Set the task execution to running first otherwise a race can occur
    # where the action execution finishes first and the completion handler
    # conflicts with this status update.
    task_ex_db.status = states.RUNNING
    task_ex_db = wf_db_access.TaskExecution.update(task_ex_db, publish=False)

    # Request action execution.
    lv_ac_db, ac_ex_db = ac_svc.request(lv_ac_db)
    msg = '[%s] Action execution "%s" requested for task "%s".'
    LOG.info(msg, wf_ac_ex_id, str(ac_ex_db.id), task_ex_db.task_id)

    return ac_ex_db


def handle_action_execution_pending(ac_ex_db):
    # Check that the action execution is paused.
    if ac_ex_db.status != ac_const.LIVEACTION_STATUS_PENDING:
        raise Exception(
            'Unable to handle pending of action execution. The action execution '
            '"%s" is in "%s" state.' % (str(ac_ex_db.id), ac_ex_db.status)
        )

    # Get related record identifiers.
    wf_ex_id = ac_ex_db.context['orquesta']['workflow_execution_id']
    task_ex_id = ac_ex_db.context['orquesta']['task_execution_id']

    # Get execution records for logging purposes.
    wf_ex_db = wf_db_access.WorkflowExecution.get_by_id(wf_ex_id)
    task_ex_db = wf_db_access.TaskExecution.get_by_id(task_ex_id)

    msg = '[%s] Handling pending of action execution "%s" for task "%s".'
    LOG.info(msg, wf_ex_db.action_execution, str(ac_ex_db.id), task_ex_db.task_id)

    # Updat task execution
    update_task_execution(task_ex_id, ac_ex_db.status, ac_ex_ctx=ac_ex_db.context)

    # Update task flow in the workflow execution.
    ac_ex_ctx = ac_ex_db.context.get('orquesta')
    update_task_flow(task_ex_id, ac_ex_db.status, ac_ex_ctx=ac_ex_ctx, publish=True)


def handle_action_execution_pause(ac_ex_db):
    # Check that the action execution is paused.
    if ac_ex_db.status != ac_const.LIVEACTION_STATUS_PAUSED:
        raise Exception(
            'Unable to handle pause of action execution. The action execution '
            '"%s" is in "%s" state.' % (str(ac_ex_db.id), ac_ex_db.status)
        )

    # Get related record identifiers.
    wf_ex_id = ac_ex_db.context['orquesta']['workflow_execution_id']
    task_ex_id = ac_ex_db.context['orquesta']['task_execution_id']

    # Get execution records for logging purposes.
    wf_ex_db = wf_db_access.WorkflowExecution.get_by_id(wf_ex_id)
    task_ex_db = wf_db_access.TaskExecution.get_by_id(task_ex_id)

    # If task is already paused, then there is nothing to process.
    if task_ex_db.status == ac_ex_db.status:
        return

    msg = '[%s] Handling pause of action execution "%s" for task "%s".'
    LOG.info(msg, wf_ex_db.action_execution, str(ac_ex_db.id), task_ex_db.task_id)

    # Updat task execution
    update_task_execution(task_ex_id, ac_ex_db.status, ac_ex_ctx=ac_ex_db.context)

    # Update task flow in the workflow execution.
    ac_ex_ctx = ac_ex_db.context.get('orquesta')
    update_task_flow(task_ex_id, ac_ex_db.status, ac_ex_ctx=ac_ex_ctx, publish=True)


def handle_action_execution_resume(ac_ex_db):
    if 'orquesta' not in ac_ex_db.context:
        raise Exception(
            'Unable to handle resume of action execution. The action execution '
            '%s is not an orquesta workflow task.' % str(ac_ex_db.id)
        )

    # Get related record identifiers.
    wf_ex_id = ac_ex_db.context['orquesta']['workflow_execution_id']
    task_ex_id = ac_ex_db.context['orquesta']['task_execution_id']

    # Get execution records for logging purposes.
    wf_ex_db = wf_db_access.WorkflowExecution.get_by_id(wf_ex_id)
    task_ex_db = wf_db_access.TaskExecution.get_by_id(task_ex_id)

    msg = '[%s] Handling resume of action execution "%s" for task "%s".'
    LOG.info(msg, wf_ex_db.action_execution, str(ac_ex_db.id), task_ex_db.task_id)

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
            action_utils.update_liveaction_status(
                liveaction_id=parent_ac_ex_db.liveaction['id'],
                status=ac_const.LIVEACTION_STATUS_RUNNING,
                publish=False)

        # If there are grand parents, handle the resume of the parent action execution.
        if 'orquesta' in parent_ac_ex_db.context and 'parent' in parent_ac_ex_db.context:
            handle_action_execution_resume(parent_ac_ex_db)


def handle_action_execution_completion(ac_ex_db):
    # Check that the action execution is completed.
    if ac_ex_db.status not in ac_const.LIVEACTION_COMPLETED_STATES:
        raise Exception(
            'Unable to handle completion of action execution. The action execution '
            '"%s" is in "%s" state.' % (str(ac_ex_db.id), ac_ex_db.status)
        )

    # Get related record identifiers.
    wf_ex_id = ac_ex_db.context['orquesta']['workflow_execution_id']
    task_ex_id = ac_ex_db.context['orquesta']['task_execution_id']

    # Get execution records for logging purposes.
    wf_ex_db = wf_db_access.WorkflowExecution.get_by_id(wf_ex_id)
    task_ex_db = wf_db_access.TaskExecution.get_by_id(task_ex_id)

    msg = '[%s] Handling completion of action execution "%s" in state "%s" for task "%s".'
    LOG.info(msg, wf_ex_db.action_execution, str(ac_ex_db.id), ac_ex_db.status, task_ex_db.task_id)

    # If task is currently paused and the action execution is skipped to
    # completion, then transition task status to running first.
    if task_ex_db.status == ac_const.LIVEACTION_STATUS_PAUSED:
        resume_task_execution(task_ex_id)

    # Update task execution if completed.
    update_task_execution(task_ex_id, ac_ex_db.status, ac_ex_db.result, ac_ex_db.context)

    # Update task flow in the workflow execution.
    update_task_flow(
        task_ex_id,
        ac_ex_db.status,
        ac_ex_result=ac_ex_db.result,
        ac_ex_ctx=ac_ex_db.context.get('orquesta')
    )

    # Request the next set of tasks if workflow execution is not complete.
    request_next_tasks(wf_ex_db, task_ex_id=task_ex_id)

    # Update workflow execution if completed.
    update_workflow_execution(wf_ex_id)


def deserialize_conductor(wf_ex_db):
    data = {
        'spec': wf_ex_db.spec,
        'graph': wf_ex_db.graph,
        'state': wf_ex_db.status,
        'flow': wf_ex_db.flow,
        'context': wf_ex_db.context,
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
def update_task_flow(task_ex_id, ac_ex_status, ac_ex_result=None, ac_ex_ctx=None, publish=True):
    # Return if action execution status is not in the list of states to process.
    states_to_process = states.COMPLETED_STATES + [states.PAUSED, states.PENDING]

    if ac_ex_status not in states_to_process:
        return

    # Refresh records
    task_ex_db = wf_db_access.TaskExecution.get_by_id(task_ex_id)
    conductor, wf_ex_db = refresh_conductor(task_ex_db.workflow_execution)
    wf_ac_ex_id = wf_ex_db.action_execution

    # Update task flow if task execution is completed or paused.
    msg = '[%s] Publish task "%s" with status "%s" to conductor.'
    LOG.info(msg, wf_ac_ex_id, task_ex_db.task_id, task_ex_db.status)
    ac_ex_event = events.ActionExecutionEvent(ac_ex_status, result=ac_ex_result, context=ac_ex_ctx)
    LOG.debug('[%s] %s', wf_ac_ex_id, conductor.serialize())
    conductor.update_task_flow(task_ex_db.task_id, ac_ex_event)

    # Update workflow execution and related liveaction and action execution.
    update_execution_records(
        wf_ex_db,
        conductor,
        update_lv_ac_on_states=states_to_process,
        pub_lv_ac=publish,
        pub_ac_ex=publish
    )


@retrying.retry(retry_on_exception=wf_exc.retry_on_exceptions)
def request_next_tasks(wf_ex_db, task_ex_id=None):
    iteration = 0

    # Refresh records.
    conductor, wf_ex_db = refresh_conductor(str(wf_ex_db.id))
    wf_ac_ex_id = wf_ex_db.action_execution

    # If workflow is in requested state, set it to running.
    if conductor.get_workflow_state() in [states.REQUESTED, states.SCHEDULED]:
        LOG.info('[%s] Requesting conductor to start running workflow execution.', wf_ac_ex_id)
        conductor.request_workflow_state(states.RUNNING)

    # Identify the list of next set of tasks. Don't pass the task id to the conductor
    # so it can identify any next set of tasks to run from the workflow.
    if task_ex_id:
        task_ex_db = wf_db_access.TaskExecution.get_by_id(task_ex_id)
        msg = '[%s] Identifying next set (%s) of tasks after completion of task "%s".'
        LOG.info(msg, wf_ac_ex_id, str(iteration), task_ex_db.task_id)
        LOG.debug('[%s] %s', wf_ac_ex_id, conductor.serialize())
        next_tasks = conductor.get_next_tasks()
    else:
        msg = '[%s] Identifying next set (%s) of tasks for workflow execution in state "%s".'
        LOG.info(msg, wf_ac_ex_id, str(iteration), conductor.get_workflow_state())
        LOG.debug('[%s] %s', wf_ac_ex_id, conductor.serialize())
        next_tasks = conductor.get_next_tasks()

    # If there is no new tasks, update execution records to handle possible completion.
    if not next_tasks:
        # Update workflow execution and related liveaction and action execution.
        LOG.info('[%s] No tasks identified to execute next.', wf_ac_ex_id)
        update_execution_records(wf_ex_db, conductor)

    # If workflow execution is no longer active, then stop processing here.
    if wf_ex_db.status in states.COMPLETED_STATES:
        msg = '[%s] Workflow execution is in completed state "%s".'
        LOG.info(msg, wf_ac_ex_id, wf_ex_db.status)
        return

    # Iterate while there are next tasks identified for processing. In the case for
    # task with no action execution defined, the task execution will complete
    # immediately with a new set of tasks available.
    while next_tasks:
        msg = '[%s] Identified the following set of tasks to execute next: %s'
        LOG.info(msg, wf_ac_ex_id, ', '.join([task['id'] for task in next_tasks]))

        # Mark the tasks as running in the task flow before actual task execution.
        for task in next_tasks:
            msg = '[%s] Mark task "%s" in conductor as running.'
            LOG.info(msg, wf_ac_ex_id, task['id'])

            # If task contains multiple action execution (i.e. with items),
            # then mark each item individually.
            for action in task['actions']:
                ac_ex_ctx = None

                if 'item_id' in action and action['item_id'] is not None:
                    msg = '[%s] Mark task "%s" item "%s" in conductor as running.'
                    LOG.info(msg, wf_ac_ex_id, task['id'], action['item_id'])
                    ac_ex_ctx = {'item_id': action['item_id']} if 'item_id' in action else None

                ac_ex_event = events.ActionExecutionEvent(states.RUNNING, context=ac_ex_ctx)
                conductor.update_task_flow(task['id'], ac_ex_event)

        # Update workflow execution and related liveaction and action execution.
        LOG.debug('[%s] %s', wf_ac_ex_id, conductor.serialize())
        update_execution_records(wf_ex_db, conductor)

        # If workflow execution is no longer active, then stop processing here.
        if wf_ex_db.status in states.COMPLETED_STATES:
            msg = '[%s] Workflow execution is in completed state "%s".'
            LOG.info(msg, wf_ac_ex_id, wf_ex_db.status)
            break

        # Request task execution for the tasks.
        for task in next_tasks:
            try:
                LOG.info('[%s] Requesting execution for task "%s".', wf_ac_ex_id, task['id'])
                root_st2_ctx = wf_ex_db.context.get('st2', {})
                st2_ctx = {'execution_id': wf_ac_ex_id, 'user': root_st2_ctx.get('user')}
                request_task_execution(wf_ex_db, st2_ctx, task)
            except Exception as e:
                LOG.exception('[%s] Failed task execution for "%s".', wf_ac_ex_id, task['id'])
                fail_workflow_execution(str(wf_ex_db.id), e, task_id=task['id'])
                return

        # Identify the next set of tasks to execute.
        iteration += 1
        conductor, wf_ex_db = refresh_conductor(str(wf_ex_db.id))
        msg = '[%s] Identifying next set (%s) of tasks for workflow execution in state "%s".'
        LOG.info(msg, wf_ac_ex_id, str(iteration), conductor.get_workflow_state())
        LOG.debug('[%s] %s', wf_ac_ex_id, conductor.serialize())
        next_tasks = conductor.get_next_tasks()

        if not next_tasks:
            LOG.info('[%s] No tasks identified to execute next.', wf_ac_ex_id)


@retrying.retry(retry_on_exception=wf_exc.retry_on_exceptions)
def update_task_execution(task_ex_id, ac_ex_status, ac_ex_result=None, ac_ex_ctx=None):
    if ac_ex_status not in states.COMPLETED_STATES + [states.PAUSED, states.PENDING]:
        return

    task_ex_db = wf_db_access.TaskExecution.get_by_id(task_ex_id)
    wf_ex_db = wf_db_access.WorkflowExecution.get_by_id(task_ex_db.workflow_execution)

    if not task_ex_db.itemized:
        if ac_ex_status != task_ex_db.status:
            msg = '[%s] Updating task execution from state "%s" to "%s".'
            LOG.debug(msg, wf_ex_db.action_execution, task_ex_db.status, ac_ex_status)

        task_ex_db.status = ac_ex_status
        task_ex_db.result = ac_ex_result if ac_ex_result else task_ex_db.result
    elif task_ex_db.itemized and ac_ex_ctx:
        if 'orquesta' not in ac_ex_ctx or 'item_id' not in ac_ex_ctx['orquesta']:
            raise Exception('Context information for the item is not provided. %s' % str(ac_ex_ctx))

        item_id = ac_ex_ctx['orquesta']['item_id']

        msg = '[%s] Processing action execution for task "%s" item "%s".'
        LOG.debug(msg, wf_ex_db.action_execution, task_ex_db.task_id, item_id)

        task_ex_db.result['items'][item_id] = {'status': ac_ex_status, 'result': ac_ex_result}

        statuses = [
            item.get('status', states.UNSET) if item else states.UNSET
            for item in task_ex_db.result['items']
        ]

        task_completed = all([status in states.COMPLETED_STATES for status in statuses])

        if task_completed:
            new_task_status = (
                states.SUCCEEDED
                if all([status == states.SUCCEEDED for status in statuses])
                else states.FAILED
            )

            msg = '[%s] Updating task execution from state "%s" to "%s".'
            LOG.debug(msg, wf_ex_db.action_execution, task_ex_db.status, new_task_status)
            task_ex_db.status = new_task_status
        else:
            msg = '[%s] Task execution is not complete because not all items are complete: %s'
            LOG.debug(msg, wf_ex_db.action_execution, ', '.join(statuses))

    if task_ex_db.status in states.COMPLETED_STATES:
        task_ex_db.end_timestamp = date_utils.get_datetime_utc_now()

    wf_db_access.TaskExecution.update(task_ex_db, publish=False)


@retrying.retry(retry_on_exception=wf_exc.retry_on_exceptions)
def resume_task_execution(task_ex_id):
    # Update task execution to running.
    task_ex_db = wf_db_access.TaskExecution.get_by_id(task_ex_id)
    wf_ex_db = wf_db_access.WorkflowExecution.get_by_id(task_ex_db.workflow_execution)

    msg = '[%s] Updating task execution from state "%s" to "%s".'
    LOG.debug(msg, wf_ex_db.action_execution, task_ex_db.status, states.RUNNING)

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
    conductor.request_workflow_state(states.RUNNING)

    # Update task execution in task flow to running.
    task_ex_db = wf_db_access.TaskExecution.get_by_id(task_ex_id)
    ac_ex_event = events.ActionExecutionEvent(states.RUNNING)
    conductor.update_task_flow(task_ex_db.task_id, ac_ex_event)

    # Update workflow execution and related liveaction and action execution.
    update_execution_records(wf_ex_db, conductor)


@retrying.retry(retry_on_exception=wf_exc.retry_on_exceptions)
def fail_workflow_execution(wf_ex_id, exception, task_id=None):
    conductor, wf_ex_db = refresh_conductor(wf_ex_id)

    # Set workflow execution status to failed and record error.
    conductor.request_workflow_state(states.FAILED)
    conductor.log_error(str(exception), task_id=task_id)

    # Update workflow execution and related liveaction and action execution.
    update_execution_records(wf_ex_db, conductor)


def update_execution_records(wf_ex_db, conductor, update_lv_ac_on_states=None,
                             pub_wf_ex=False, pub_lv_ac=True, pub_ac_ex=True):

    wf_ac_ex_id = wf_ex_db.action_execution
    wf_old_status = wf_ex_db.status

    # Update workflow status.
    wf_ex_db.status = conductor.get_workflow_state()

    if wf_old_status != wf_ex_db.status:
        msg = '[%s] Updating workflow execution from state "%s" to "%s".'
        LOG.info(msg, wf_ac_ex_id, wf_old_status, wf_ex_db.status)

    # Update timestamp and output if workflow is completed.
    if wf_ex_db.status in states.COMPLETED_STATES:
        wf_ex_db.end_timestamp = date_utils.get_datetime_utc_now()
        wf_ex_db.output = conductor.get_workflow_output()

    # Update task flow and other attributes.
    wf_ex_db.errors = copy.deepcopy(conductor.errors)
    wf_ex_db.flow = conductor.flow.serialize()

    # Write changes to the database.
    wf_ex_db = wf_db_access.WorkflowExecution.update(wf_ex_db, publish=pub_wf_ex)

    # Return if workflow execution status is not specified in update_lv_ac_on_states.
    if isinstance(update_lv_ac_on_states, list) and wf_ex_db.status not in update_lv_ac_on_states:
        return

    # Update the corresponding liveaction and action execution for the workflow.
    wf_ac_ex_db = ex_db_access.ActionExecution.get_by_id(wf_ex_db.action_execution)
    wf_lv_ac_db = action_utils.get_liveaction_by_id(wf_ac_ex_db.liveaction['id'])

    # Gather result for liveaction and action execution.
    result = {'output': wf_ex_db.output or None}

    if wf_ex_db.status in states.ABENDED_STATES:
        result['errors'] = wf_ex_db.errors

        for wf_ex_error in wf_ex_db.errors:
            msg = '[%s] Workflow execution completed with errors.'
            LOG.error(msg, wf_ac_ex_id, extra=wf_ex_error)

    # Sync update with corresponding liveaction and action execution.
    if pub_lv_ac or pub_ac_ex:
        pub_lv_ac = (wf_lv_ac_db.status != wf_ex_db.status)
        pub_ac_ex = pub_lv_ac

    if wf_lv_ac_db.status != wf_ex_db.status:
        msg = '[%s] Updating workflow liveaction from state "%s" to "%s".'
        LOG.debug(msg, wf_ac_ex_id, wf_lv_ac_db.status, wf_ex_db.status)
        msg = '[%s] Workflow liveaction status change %s be published.'
        LOG.debug(msg, wf_ac_ex_id, 'will' if pub_lv_ac else 'will not')
        msg = '[%s] Workflow action execution status change %s be published.'
        LOG.debug(msg, wf_ac_ex_id, 'will' if pub_ac_ex else 'will not')

    wf_lv_ac_db = action_utils.update_liveaction_status(
        status=wf_ex_db.status,
        result=result,
        end_timestamp=wf_ex_db.end_timestamp,
        liveaction_db=wf_lv_ac_db,
        publish=pub_lv_ac)

    ex_svc.update_execution(wf_lv_ac_db, publish=pub_ac_ex)

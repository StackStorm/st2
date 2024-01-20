# Copyright 2020 The StackStorm Authors.
# Copyright 2019 Extreme Networks, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
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
import datetime
import retrying
import six

from orquesta import conducting
from orquesta import events
from orquesta import exceptions as orquesta_exc
from orquesta.expressions import base as expressions
from orquesta import requests as orquesta_reqs
from orquesta.specs import loader as specs_loader
from orquesta import statuses
from oslo_config import cfg

from st2common.constants import action as ac_const
from st2common.exceptions import action as ac_exc
from st2common.exceptions import db as db_exc
from st2common.exceptions import workflow as wf_exc
from st2common import log as logging
from st2common.models.api import notification as notify_api_models
from st2common.models.db import liveaction as lv_db_models
from st2common.models.db import workflow as wf_db_models
from st2common.models.system import common as sys_models
from st2common.models.utils import action_param_utils
from st2common.persistence import execution as ex_db_access
from st2common.persistence import liveaction as lv_db_access
from st2common.persistence import workflow as wf_db_access
from st2common.runners import utils as runners_utils
from st2common.services import action as ac_svc
from st2common.services import coordination as coord_svc
from st2common.services import executions as ex_svc
from st2common.util import action_db as action_utils
from st2common.util import date as date_utils
from st2common.util import param as param_utils


LOG = logging.getLogger(__name__)

LOG_FUNCTIONS = {
    "audit": LOG.audit,
    "debug": LOG.debug,
    "info": LOG.info,
    "warning": LOG.warning,
    "error": LOG.error,
    "critical": LOG.critical,
}


def update_progress(wf_ex_db, message, severity="info", log=True, stream=True):
    if not wf_ex_db:
        return

    if log and severity in LOG_FUNCTIONS:
        LOG_FUNCTIONS[severity](
            "[%s] %s", wf_ex_db.context["st2"]["action_execution_id"], message
        )

    if stream:
        ac_svc.store_execution_output_data_ex(
            wf_ex_db.context["st2"]["action_execution_id"],
            wf_ex_db.context["st2"]["action"],
            wf_ex_db.context["st2"]["runner"],
            "%s\n" % message,
        )


def is_action_execution_under_workflow_context(ac_ex_db):
    # The action execution is executed under the context of a workflow
    # if it contains the orquesta key in its context dictionary.
    return ac_ex_db.context and "orquesta" in ac_ex_db.context


def format_inspection_result(result):
    errors = []

    categories = {
        "contents": "content",
        "context": "context",
        "expressions": "expression",
        "semantics": "semantic",
        "syntax": "syntax",
    }

    # For context and expression errors, rename the attribute from type to language.
    for category in ["context", "expressions"]:
        for entry in result.get(category, []):
            if "language" not in entry:
                entry["language"] = entry["type"]
                del entry["type"]

    # For all categories, put the category value in the type attribute.
    for category, entries in six.iteritems(result):
        for entry in entries:
            entry["type"] = categories[category]
            errors.append(entry)

    return errors


def inspect(wf_spec, st2_ctx, raise_exception=True):
    # Inspect workflow definition.
    result = wf_spec.inspect(app_ctx=st2_ctx, raise_exception=False)
    errors = format_inspection_result(result)

    # Inspect st2 specific contents.
    errors += inspect_task_contents(wf_spec)

    # Sort the list of errors by type and path.
    errors = sorted(errors, key=lambda e: (e["type"], e["schema_path"]))

    if errors and raise_exception:
        raise orquesta_exc.WorkflowInspectionError(errors)

    return errors


def inspect_task_contents(wf_spec):
    result = []
    spec_path = "tasks"
    schema_path = "properties.tasks.patternProperties.^\\w+$"
    action_schema_path = schema_path + ".properties.action"
    action_input_schema_path = schema_path + ".properties.input"

    def is_action_an_expression(action):
        if isinstance(action, six.string_types):
            for name, evaluator in six.iteritems(expressions.get_evaluators()):
                if evaluator.has_expressions(action):
                    return True

    for task_name, task_spec in six.iteritems(wf_spec.tasks):
        action_ref = getattr(task_spec, "action", None)
        action_spec_path = spec_path + "." + task_name + ".action"
        action_input_spec_path = spec_path + "." + task_name + ".input"

        # Move on if action is empty or an expression.
        if not action_ref or is_action_an_expression(action_ref):
            continue

        # Check that the format of the action is a valid resource reference.
        if not sys_models.ResourceReference.is_resource_reference(action_ref):
            entry = {
                "type": "content",
                "message": 'The action reference "%s" is not formatted correctly.'
                % action_ref,
                "spec_path": action_spec_path,
                "schema_path": action_schema_path,
            }

            result.append(entry)
            continue

        # Check that the action is registered in the database.
        if not action_utils.get_action_by_ref(ref=action_ref):
            entry = {
                "type": "content",
                "message": 'The action "%s" is not registered in the database.'
                % action_ref,
                "spec_path": action_spec_path,
                "schema_path": action_schema_path,
            }

            result.append(entry)
            continue

        # Check the action parameters.
        params = getattr(task_spec, "input", None) or {}

        if params and not isinstance(params, dict):
            continue

        requires, unexpected = action_param_utils.validate_action_parameters(
            action_ref, params
        )

        for param in requires:
            message = 'Action "%s" is missing required input "%s".' % (
                action_ref,
                param,
            )

            entry = {
                "type": "content",
                "message": message,
                "spec_path": action_input_spec_path,
                "schema_path": action_input_schema_path,
            }

            result.append(entry)

        for param in unexpected:
            message = 'Action "%s" has unexpected input "%s".' % (action_ref, param)

            entry = {
                "type": "content",
                "message": message,
                "spec_path": action_input_spec_path + "." + param,
                "schema_path": action_input_schema_path + ".patternProperties.^\\w+$",
            }

            result.append(entry)

    return result


def request(wf_def, ac_ex_db, st2_ctx, notify_cfg=None):
    LOG.info("[%s] Processing action execution request for workflow.", str(ac_ex_db.id))

    # Load workflow definition into workflow spec model.
    spec_module = specs_loader.get_spec_module("native")
    wf_spec = spec_module.instantiate(wf_def)

    # Inspect the workflow spec.
    inspect(wf_spec, st2_ctx, raise_exception=True)

    # Identify the action to execute.
    action_db = action_utils.get_action_by_ref(ref=ac_ex_db.action["ref"])

    if not action_db:
        error = 'Unable to find action "%s".' % ac_ex_db.action["ref"]
        raise ac_exc.InvalidActionReferencedException(error)

    # Identify the runner for the action.
    runner_type_db = action_utils.get_runnertype_by_name(action_db.runner_type["name"])

    # Render action execution parameters.
    runner_params, action_params = param_utils.render_final_params(
        runner_type_db.runner_parameters,
        action_db.parameters,
        ac_ex_db.parameters,
        ac_ex_db.context,
    )

    # Instantiate the workflow conductor.
    conductor_params = {"inputs": action_params, "context": st2_ctx}
    conductor = conducting.WorkflowConductor(wf_spec, **conductor_params)

    # Serialize the conductor which initializes some internal values.
    data = conductor.serialize()

    # Create a record for workflow execution.
    wf_ex_db = wf_db_models.WorkflowExecutionDB(
        action_execution=str(ac_ex_db.id),
        spec=data["spec"],
        graph=data["graph"],
        input=data["input"],
        context=data["context"],
        state=data["state"],
        status=data["state"]["status"],
        output=data["output"],
        errors=data["errors"],
    )

    # Inspect that the list of tasks in the notify parameter exist in the workflow spec.
    if runner_params.get("notify"):
        invalid_tasks = list(
            set(runner_params.get("notify")) - set(wf_spec.tasks.keys())
        )

        if invalid_tasks:
            raise wf_exc.WorkflowExecutionException(
                "The following tasks in the notify parameter do not exist "
                "in the workflow definition: %s." % ", ".join(invalid_tasks)
            )

    # Write notify instruction to record.
    if notify_cfg:
        # Set up the notify instruction in the workflow execution record.
        wf_ex_db.notify = {"config": notify_cfg, "tasks": runner_params.get("notify")}

    # Insert new record into the database and do not publish to the message bus yet.
    wf_ex_db = wf_db_access.WorkflowExecution.insert(wf_ex_db, publish=False)
    update_progress(wf_ex_db, 'Workflow execution "%s" is created.' % str(wf_ex_db.id))

    # Update the context with the workflow execution id created on database insert.
    # Publish the workflow execution requested status to the message bus.
    if wf_ex_db.status not in statuses.COMPLETED_STATUSES:
        # Set the initial workflow status to requested.
        conductor.request_workflow_status(statuses.REQUESTED)
        data = conductor.serialize()
        wf_ex_db.state = data["state"]
        wf_ex_db.status = data["state"]["status"]

        # Put the ID of the workflow execution record in the context.
        wf_ex_db.context["st2"]["workflow_execution_id"] = str(wf_ex_db.id)
        wf_ex_db.state["contexts"][0]["st2"]["workflow_execution_id"] = str(wf_ex_db.id)

        # Update the workflow execution record.
        wf_ex_db = wf_db_access.WorkflowExecution.update(wf_ex_db, publish=False)
        wf_db_access.WorkflowExecution.publish_status(wf_ex_db)
        msg = 'Workflow execution "%s" is published.'
        update_progress(wf_ex_db, msg % str(wf_ex_db.id), stream=False)
    else:
        msg = 'Unable to request workflow execution. It is already in completed status "%s".'
        update_progress(wf_ex_db, msg % wf_ex_db.status)

    return wf_ex_db


@retrying.retry(
    retry_on_exception=wf_exc.retry_on_transient_db_errors,
    wait_fixed=cfg.CONF.workflow_engine.retry_wait_fixed_msec,
    wait_jitter_max=cfg.CONF.workflow_engine.retry_max_jitter_msec,
)
@retrying.retry(
    retry_on_exception=wf_exc.retry_on_connection_errors,
    stop_max_delay=cfg.CONF.workflow_engine.retry_stop_max_msec,
    wait_fixed=cfg.CONF.workflow_engine.retry_wait_fixed_msec,
    wait_jitter_max=cfg.CONF.workflow_engine.retry_max_jitter_msec,
)
def request_pause(ac_ex_db):
    wf_ac_ex_id = str(ac_ex_db.id)
    LOG.info("[%s] Processing pause request for workflow.", wf_ac_ex_id)

    wf_ex_dbs = wf_db_access.WorkflowExecution.query(action_execution=str(ac_ex_db.id))

    if not wf_ex_dbs:
        raise wf_exc.WorkflowExecutionNotFoundException(str(ac_ex_db.id))

    if len(wf_ex_dbs) > 1:
        raise wf_exc.AmbiguousWorkflowExecutionException(str(ac_ex_db.id))

    wf_ex_db = wf_ex_dbs[0]

    if wf_ex_db.status in statuses.COMPLETED_STATUSES:
        raise wf_exc.WorkflowExecutionIsCompletedException(str(wf_ex_db.id))

    conductor = deserialize_conductor(wf_ex_db)

    if conductor.get_workflow_status() in statuses.COMPLETED_STATUSES:
        raise wf_exc.WorkflowExecutionIsCompletedException(str(wf_ex_db.id))

    conductor.request_workflow_status(statuses.PAUSED)

    # Write the updated workflow status and task flow to the database.
    wf_ex_db.status = conductor.get_workflow_status()
    wf_ex_db.state = conductor.workflow_state.serialize()
    wf_ex_db = wf_db_access.WorkflowExecution.update(wf_ex_db, publish=False)

    LOG.info("[%s] Completed processing pause request for workflow.", wf_ac_ex_id)

    return wf_ex_db


@retrying.retry(
    retry_on_exception=wf_exc.retry_on_transient_db_errors,
    wait_fixed=cfg.CONF.workflow_engine.retry_wait_fixed_msec,
    wait_jitter_max=cfg.CONF.workflow_engine.retry_max_jitter_msec,
)
@retrying.retry(
    retry_on_exception=wf_exc.retry_on_connection_errors,
    stop_max_delay=cfg.CONF.workflow_engine.retry_stop_max_msec,
    wait_fixed=cfg.CONF.workflow_engine.retry_wait_fixed_msec,
    wait_jitter_max=cfg.CONF.workflow_engine.retry_max_jitter_msec,
)
def request_resume(ac_ex_db):
    wf_ac_ex_id = str(ac_ex_db.id)
    LOG.info("[%s] Processing resume request for workflow.", wf_ac_ex_id)

    wf_ex_dbs = wf_db_access.WorkflowExecution.query(action_execution=str(ac_ex_db.id))

    if not wf_ex_dbs:
        raise wf_exc.WorkflowExecutionNotFoundException(str(ac_ex_db.id))

    if len(wf_ex_dbs) > 1:
        raise wf_exc.AmbiguousWorkflowExecutionException(str(ac_ex_db.id))

    wf_ex_db = wf_ex_dbs[0]

    if wf_ex_db.status in statuses.COMPLETED_STATUSES:
        raise wf_exc.WorkflowExecutionIsCompletedException(str(wf_ex_db.id))

    if wf_ex_db.status in statuses.RUNNING_STATUSES:
        msg = (
            '[%s] Workflow execution "%s" is not resumed because it is already active.'
        )
        LOG.info(msg, wf_ac_ex_id, str(wf_ex_db.id))
        return

    conductor = deserialize_conductor(wf_ex_db)

    if conductor.get_workflow_status() in statuses.COMPLETED_STATUSES:
        raise wf_exc.WorkflowExecutionIsCompletedException(str(wf_ex_db.id))

    if conductor.get_workflow_status() in statuses.RUNNING_STATUSES:
        msg = (
            '[%s] Workflow execution "%s" is not resumed because it is already active.'
        )
        LOG.info(msg, wf_ac_ex_id, str(wf_ex_db.id))
        return

    conductor.request_workflow_status(statuses.RESUMING)

    # Write the updated workflow status and task flow to the database.
    wf_ex_db.status = conductor.get_workflow_status()
    wf_ex_db.state = conductor.workflow_state.serialize()
    wf_db_access.WorkflowExecution.update(wf_ex_db, publish=False)
    wf_ex_db = wf_db_access.WorkflowExecution.get_by_id(str(wf_ex_db.id))

    # Publish status change.
    wf_db_access.WorkflowExecution.publish_status(wf_ex_db)

    LOG.info("[%s] Completed processing resume request for workflow.", wf_ac_ex_id)

    return wf_ex_db


@retrying.retry(
    retry_on_exception=wf_exc.retry_on_transient_db_errors,
    wait_fixed=cfg.CONF.workflow_engine.retry_wait_fixed_msec,
    wait_jitter_max=cfg.CONF.workflow_engine.retry_max_jitter_msec,
)
@retrying.retry(
    retry_on_exception=wf_exc.retry_on_connection_errors,
    stop_max_delay=cfg.CONF.workflow_engine.retry_stop_max_msec,
    wait_fixed=cfg.CONF.workflow_engine.retry_wait_fixed_msec,
    wait_jitter_max=cfg.CONF.workflow_engine.retry_max_jitter_msec,
)
def request_cancellation(ac_ex_db):
    wf_ac_ex_id = str(ac_ex_db.id)
    LOG.info("[%s] Processing cancelation request for workflow.", wf_ac_ex_id)

    wf_ex_dbs = wf_db_access.WorkflowExecution.query(action_execution=str(ac_ex_db.id))

    if not wf_ex_dbs:
        raise wf_exc.WorkflowExecutionNotFoundException(str(ac_ex_db.id))

    if len(wf_ex_dbs) > 1:
        raise wf_exc.AmbiguousWorkflowExecutionException(str(ac_ex_db.id))

    wf_ex_db = wf_ex_dbs[0]

    if wf_ex_db.status in statuses.COMPLETED_STATUSES:
        raise wf_exc.WorkflowExecutionIsCompletedException(str(wf_ex_db.id))

    conductor = deserialize_conductor(wf_ex_db)

    if conductor.get_workflow_status() in statuses.COMPLETED_STATUSES:
        raise wf_exc.WorkflowExecutionIsCompletedException(str(wf_ex_db.id))

    conductor.request_workflow_status(statuses.CANCELED)

    # Write the updated workflow status and task flow to the database.
    wf_ex_db.status = conductor.get_workflow_status()
    wf_ex_db.state = conductor.workflow_state.serialize()
    wf_ex_db = wf_db_access.WorkflowExecution.update(wf_ex_db, publish=False)

    # Cascade the cancellation up to the root of the workflow.
    root_ac_ex_db = ac_svc.get_root_execution(ac_ex_db)

    if (
        root_ac_ex_db != ac_ex_db
        and root_ac_ex_db.status not in ac_const.LIVEACTION_CANCEL_STATES
    ):
        LOG.info("[%s] Cascading cancelation request to parent workflow.", wf_ac_ex_id)
        root_lv_ac_db = lv_db_access.LiveAction.get(id=root_ac_ex_db.liveaction["id"])
        ac_svc.request_cancellation(root_lv_ac_db, None)

    LOG.debug("[%s] %s", wf_ac_ex_id, conductor.serialize())
    LOG.info("[%s] Completed processing cancelation request for workflow.", wf_ac_ex_id)

    return wf_ex_db


@retrying.retry(
    retry_on_exception=wf_exc.retry_on_transient_db_errors,
    wait_fixed=cfg.CONF.workflow_engine.retry_wait_fixed_msec,
    wait_jitter_max=cfg.CONF.workflow_engine.retry_max_jitter_msec,
)
@retrying.retry(
    retry_on_exception=wf_exc.retry_on_connection_errors,
    stop_max_delay=cfg.CONF.workflow_engine.retry_stop_max_msec,
    wait_fixed=cfg.CONF.workflow_engine.retry_wait_fixed_msec,
    wait_jitter_max=cfg.CONF.workflow_engine.retry_max_jitter_msec,
)
def request_rerun(ac_ex_db, st2_ctx, options=None):
    wf_ac_ex_id = str(ac_ex_db.id)
    LOG.info("[%s] Processing rerun request for workflow.", wf_ac_ex_id)

    wf_ex_id = st2_ctx.get("workflow_execution_id")

    if not wf_ex_id:
        msg = "Unable to rerun workflow execution because workflow_execution_id is not provided."
        raise wf_exc.WorkflowExecutionRerunException(msg)

    try:
        wf_ex_db = wf_db_access.WorkflowExecution.get_by_id(wf_ex_id)
    except db_exc.StackStormDBObjectNotFoundError:
        msg = 'Unable to rerun workflow execution "%s" because it does not exist.'
        raise wf_exc.WorkflowExecutionRerunException(msg % wf_ex_id)

    if wf_ex_db.status not in statuses.COMPLETED_STATUSES:
        msg = 'Unable to rerun workflow execution "%s" because it is not in a completed state.'
        raise wf_exc.WorkflowExecutionRerunException(msg % wf_ex_id)

    wf_ex_db.action_execution = wf_ac_ex_id
    wf_ex_db.context["st2"] = st2_ctx["st2"]
    wf_ex_db.context["parent"] = st2_ctx["parent"]
    conductor = deserialize_conductor(wf_ex_db)

    try:
        task_requests = None
        problems = []

        if options:
            task_requests = []
            task_names = options.get("tasks", [])
            task_resets = options.get("reset", [])

            for task_name in task_names:
                reset_items = task_name in task_resets
                task_state_entries = conductor.workflow_state.get_tasks(
                    task_id=task_name
                )

                if not task_state_entries:
                    problems.append(task_name)
                    continue

                for _, task_state_entry in task_state_entries:
                    route = task_state_entry["route"]
                    req = orquesta_reqs.TaskRerunRequest.new(
                        task_name, route, reset_items=reset_items
                    )
                    task_requests.append(req)

            if problems:
                msg = "Unable to rerun workflow because one or more tasks is not found: %s"
                raise Exception(msg % ",".join(problems))

        conductor.request_workflow_rerun(task_requests=task_requests)
    except Exception as e:
        raise wf_exc.WorkflowExecutionRerunException(six.text_type(e))

    if conductor.get_workflow_status() not in statuses.RUNNING_STATUSES:
        msg = 'Unable to rerun workflow execution "%s" due to an unknown cause.'
        raise wf_exc.WorkflowExecutionRerunException(msg % wf_ex_id)

    data = conductor.serialize()
    wf_ex_db.status = data["state"]["status"]
    wf_ex_db.spec = data["spec"]
    wf_ex_db.graph = data["graph"]
    wf_ex_db.state = data["state"]

    wf_db_access.WorkflowExecution.update(wf_ex_db, publish=False)
    wf_ex_db = wf_db_access.WorkflowExecution.get_by_id(str(wf_ex_db.id))

    # Publish status change.
    wf_db_access.WorkflowExecution.publish_status(wf_ex_db)

    return wf_ex_db


def request_task_execution(wf_ex_db, st2_ctx, task_ex_req):
    task_id = task_ex_req["id"]
    task_route = task_ex_req["route"]
    task_spec = task_ex_req["spec"]
    task_ctx = task_ex_req["ctx"]
    task_actions = task_ex_req["actions"]
    task_delay = task_ex_req.get("delay")

    msg = 'Processing task execution request for task "%s", route "%s".'
    update_progress(wf_ex_db, msg % (task_id, str(task_route)), stream=False)

    # Use existing task execution when task is with items and still running.
    task_ex_dbs = wf_db_access.TaskExecution.query(
        workflow_execution=str(wf_ex_db.id),
        task_id=task_id,
        task_route=task_route,
        order_by=["-start_timestamp"],
    )

    if (
        len(task_ex_dbs) > 0
        and task_ex_dbs[0].itemized
        and task_ex_dbs[0].status == ac_const.LIVEACTION_STATUS_RUNNING
    ):
        task_ex_db = task_ex_dbs[0]
        task_ex_id = str(task_ex_db.id)
        msg = 'Task execution "%s" retrieved for task "%s", route "%s".'
        update_progress(wf_ex_db, msg % (task_ex_id, task_id, str(task_route)))
    else:
        # Create a record for task execution.
        task_ex_db = wf_db_models.TaskExecutionDB(
            workflow_execution=str(wf_ex_db.id),
            task_name=task_spec.name or task_id,
            task_id=task_id,
            task_route=task_route,
            task_spec=task_spec.serialize(),
            delay=task_delay,
            itemized=task_spec.has_items(),
            items_count=task_ex_req.get("items_count"),
            items_concurrency=task_ex_req.get("concurrency"),
            context=task_ctx,
            status=statuses.REQUESTED,
        )

        # Prepare the result format for itemized task execution.
        if task_ex_db.itemized:
            task_ex_db.result = {"items": [None] * task_ex_db.items_count}

        # Insert new record into the database.
        task_ex_db = wf_db_access.TaskExecution.insert(task_ex_db, publish=False)
        task_ex_id = str(task_ex_db.id)
        msg = 'Task execution "%s" created for task "%s", route "%s".'
        update_progress(wf_ex_db, msg % (task_ex_id, task_id, str(task_route)))

    try:
        # Return here if no action is specified in task spec.
        if task_spec.action is None:
            msg = 'Task "%s", route "%s", is action less and succeed by default.'
            update_progress(wf_ex_db, msg % (task_id, str(task_route)))

            # Set the task execution to running.
            task_ex_db.status = statuses.RUNNING
            task_ex_db = wf_db_access.TaskExecution.update(task_ex_db, publish=False)

            # Fast forward task execution to completion.
            update_task_execution(str(task_ex_db.id), statuses.SUCCEEDED)
            update_task_state(str(task_ex_db.id), statuses.SUCCEEDED, publish=False)

            # Refresh and return the task execution
            return wf_db_access.TaskExecution.get_by_id(str(task_ex_db.id))

        # Return here for task with items but the items list is empty.
        if task_ex_db.itemized and task_ex_db.items_count == 0:
            msg = 'Task "%s", route "%s", has no items and succeed by default.'
            update_progress(wf_ex_db, msg % (task_id, str(task_route)))

            # Set the task execution to running.
            task_ex_db.status = statuses.RUNNING
            task_ex_db = wf_db_access.TaskExecution.update(task_ex_db, publish=False)

            # Fast forward task execution to completion.
            update_task_execution(str(task_ex_db.id), statuses.SUCCEEDED)
            update_task_state(str(task_ex_db.id), statuses.SUCCEEDED)

            # Refresh and return the task execution
            return wf_db_access.TaskExecution.get_by_id(str(task_ex_db.id))

        # Request action execution for each actions in the task request.
        for ac_ex_req in task_actions:
            ac_ex_delay = eval_action_execution_delay(
                task_ex_req, ac_ex_req, task_ex_db.itemized
            )
            request_action_execution(
                wf_ex_db, task_ex_db, st2_ctx, ac_ex_req, delay=ac_ex_delay
            )
            task_ex_db = wf_db_access.TaskExecution.get_by_id(str(task_ex_db.id))
    except Exception as e:
        msg = 'Failed action execution(s) for task "%s", route "%s".'
        msg = msg % (task_id, str(task_route))
        LOG.exception(msg)
        msg = "%s %s: %s" % (msg, type(e).__name__, six.text_type(e))
        update_progress(wf_ex_db, msg, severity="error", log=False)
        msg = "%s: %s" % (type(e).__name__, six.text_type(e))
        error = {
            "type": "error",
            "message": msg,
            "task_id": task_id,
            "route": task_route,
        }
        update_task_execution(str(task_ex_db.id), statuses.FAILED, {"errors": [error]})
        raise e

    return task_ex_db


def eval_action_execution_delay(task_ex_req, ac_ex_req, itemized=False):
    task_ex_delay = task_ex_req.get("delay")
    items_concurrency = task_ex_req.get("concurrency")

    # If there is a task delay and not with items, return the delay value.
    if task_ex_delay and not itemized:
        return task_ex_delay

    # If there is a task delay and task has items but no concurrency, return the delay value.
    if task_ex_delay and itemized and not items_concurrency:
        return task_ex_delay

    # If there is a task delay and task has items with concurrency,
    # return the delay value up if item id is less than the concurrency value.
    if task_ex_delay and itemized and ac_ex_req["item_id"] < items_concurrency:
        return task_ex_delay

    return None


@retrying.retry(
    retry_on_exception=wf_exc.retry_on_transient_db_errors,
    wait_fixed=cfg.CONF.workflow_engine.retry_wait_fixed_msec,
    wait_jitter_max=cfg.CONF.workflow_engine.retry_max_jitter_msec,
)
@retrying.retry(
    retry_on_exception=wf_exc.retry_on_connection_errors,
    stop_max_delay=cfg.CONF.workflow_engine.retry_stop_max_msec,
    wait_fixed=cfg.CONF.workflow_engine.retry_wait_fixed_msec,
    wait_jitter_max=cfg.CONF.workflow_engine.retry_max_jitter_msec,
)
def request_action_execution(wf_ex_db, task_ex_db, st2_ctx, ac_ex_req, delay=None):
    action_ref = ac_ex_req["action"]
    action_input = ac_ex_req["input"]
    item_id = ac_ex_req.get("item_id")

    # If the task is with items and item_id is not provided, raise exception.
    if task_ex_db.itemized and item_id is None:
        msg = "Unable to request action execution. Identifier for the item is not provided."
        raise Exception(msg)

    # Identify the action to execute.
    action_db = action_utils.get_action_by_ref(ref=action_ref)

    if not action_db:
        error = 'Unable to find action "%s".' % action_ref
        raise ac_exc.InvalidActionReferencedException(error)

    # Identify the runner for the action.
    runner_type_db = action_utils.get_runnertype_by_name(action_db.runner_type["name"])

    # Identify action pack name
    pack_name = action_ref.split(".")[0] if action_ref else st2_ctx.get("pack")

    # Set context for the action execution.
    ac_ex_ctx = {
        "pack": pack_name,
        "user": st2_ctx.get("user"),
        "parent": st2_ctx,
        "orquesta": {
            "workflow_execution_id": str(wf_ex_db.id),
            "task_execution_id": str(task_ex_db.id),
            "task_name": task_ex_db.task_name,
            "task_id": task_ex_db.task_id,
            "task_route": task_ex_db.task_route,
        },
    }

    if st2_ctx.get("api_user"):
        ac_ex_ctx["api_user"] = st2_ctx.get("api_user")

    if st2_ctx.get("source_channel"):
        ac_ex_ctx["source_channel"] = st2_ctx.get("source_channel")

    if item_id is not None:
        ac_ex_ctx["orquesta"]["item_id"] = item_id

    # Render action execution parameters and setup action execution object.
    ac_ex_params = param_utils.render_live_params(
        runner_type_db.runner_parameters or {},
        action_db.parameters or {},
        action_input or {},
        ac_ex_ctx,
    )

    # The delay spec is in seconds and scheduler expects milliseconds.
    if delay is not None and delay > 0:
        delay = delay * 1000

    # Instantiate the live action record.
    lv_ac_db = lv_db_models.LiveActionDB(
        action=action_ref,
        workflow_execution=str(wf_ex_db.id),
        task_execution=str(task_ex_db.id),
        delay=delay,
        context=ac_ex_ctx,
        parameters=ac_ex_params,
    )

    # Set notification if instructed.
    if (
        wf_ex_db.notify
        and wf_ex_db.notify.get("config")
        and wf_ex_db.notify.get("tasks")
        and task_ex_db.task_name in wf_ex_db.notify["tasks"]
    ):
        lv_ac_db.notify = notify_api_models.NotificationsHelper.to_model(
            wf_ex_db.notify["config"]
        )

    # Set the task execution to running first otherwise a race can occur
    # where the action execution finishes first and the completion handler
    # conflicts with this status update.
    task_ex_db.status = statuses.RUNNING
    task_ex_db = wf_db_access.TaskExecution.update(task_ex_db, publish=False)

    # Request action execution.
    lv_ac_db, ac_ex_db = ac_svc.request(lv_ac_db)
    msg = 'Action execution "%s" requested for task "%s", route "%s".'
    msg = msg % (str(ac_ex_db.id), task_ex_db.task_id, str(task_ex_db.task_route))
    update_progress(wf_ex_db, msg)

    return ac_ex_db


def handle_action_execution_pending(ac_ex_db):
    # Check that the action execution is paused.
    if ac_ex_db.status != ac_const.LIVEACTION_STATUS_PENDING:
        raise Exception(
            "Unable to handle pending of action execution. The action execution "
            '"%s" is in "%s" status.' % (str(ac_ex_db.id), ac_ex_db.status)
        )

    # Get related record identifiers.
    wf_ex_id = ac_ex_db.context["orquesta"]["workflow_execution_id"]
    task_ex_id = ac_ex_db.context["orquesta"]["task_execution_id"]

    # Get execution records for logging purposes.
    wf_ex_db = wf_db_access.WorkflowExecution.get_by_id(wf_ex_id)
    task_ex_db = wf_db_access.TaskExecution.get_by_id(task_ex_id)

    msg = 'Handling pending of action execution "%s" for task "%s", route "%s".'
    update_progress(
        wf_ex_db,
        msg % (str(ac_ex_db.id), task_ex_db.task_id, str(task_ex_db.task_route)),
    )

    # Updat task execution
    update_task_execution(task_ex_id, ac_ex_db.status, ac_ex_ctx=ac_ex_db.context)

    # Update task flow in the workflow execution.
    ac_ex_ctx = ac_ex_db.context.get("orquesta")
    update_task_state(task_ex_id, ac_ex_db.status, ac_ex_ctx=ac_ex_ctx, publish=True)


def handle_action_execution_pause(ac_ex_db):
    # Check that the action execution is paused.
    if ac_ex_db.status != ac_const.LIVEACTION_STATUS_PAUSED:
        raise Exception(
            "Unable to handle pause of action execution. The action execution "
            '"%s" is in "%s" status.' % (str(ac_ex_db.id), ac_ex_db.status)
        )

    # Get related record identifiers.
    wf_ex_id = ac_ex_db.context["orquesta"]["workflow_execution_id"]
    task_ex_id = ac_ex_db.context["orquesta"]["task_execution_id"]

    # Get execution records for logging purposes.
    wf_ex_db = wf_db_access.WorkflowExecution.get_by_id(wf_ex_id)
    task_ex_db = wf_db_access.TaskExecution.get_by_id(task_ex_id)

    # If task is already paused, then there is nothing to process.
    if task_ex_db.status == ac_ex_db.status:
        return

    msg = 'Handling pause of action execution "%s" for task "%s", route "%s".'
    update_progress(
        wf_ex_db,
        msg % (str(ac_ex_db.id), task_ex_db.task_id, str(task_ex_db.task_route)),
    )

    # Updat task execution
    update_task_execution(task_ex_id, ac_ex_db.status, ac_ex_ctx=ac_ex_db.context)

    # Update task flow in the workflow execution.
    ac_ex_ctx = ac_ex_db.context.get("orquesta")
    update_task_state(task_ex_id, ac_ex_db.status, ac_ex_ctx=ac_ex_ctx, publish=True)


def handle_action_execution_resume(ac_ex_db):
    if "orquesta" not in ac_ex_db.context:
        raise Exception(
            "Unable to handle resume of action execution. The action execution "
            "%s is not an orquesta workflow task." % str(ac_ex_db.id)
        )

    # Get related record identifiers.
    wf_ex_id = ac_ex_db.context["orquesta"]["workflow_execution_id"]
    task_ex_id = ac_ex_db.context["orquesta"]["task_execution_id"]

    # Get execution records for logging purposes.
    wf_ex_db = wf_db_access.WorkflowExecution.get_by_id(wf_ex_id)
    task_ex_db = wf_db_access.TaskExecution.get_by_id(task_ex_id)

    msg = 'Handling resume of action execution "%s" for task "%s", route "%s".'
    update_progress(
        wf_ex_db,
        msg % (str(ac_ex_db.id), task_ex_db.task_id, str(task_ex_db.task_route)),
    )

    # Updat task execution to running.
    resume_task_execution(task_ex_id)

    # Update workflow execution to running.
    resume_workflow_execution(wf_ex_id, task_ex_id)

    # If action execution has a parent, cascade status change upstream and do not publish
    # the status change because we do not want to trigger resume of other peer subworkflows.
    if "parent" in ac_ex_db.context:
        parent_ac_ex_id = ac_ex_db.context["parent"]["execution_id"]
        parent_ac_ex_db = ex_db_access.ActionExecution.get_by_id(parent_ac_ex_id)

        if parent_ac_ex_db.status == ac_const.LIVEACTION_STATUS_PAUSED:
            action_utils.update_liveaction_status(
                liveaction_id=parent_ac_ex_db.liveaction["id"],
                status=ac_const.LIVEACTION_STATUS_RUNNING,
                publish=False,
            )

        # If there are grand parents, handle the resume of the parent action execution.
        if (
            "orquesta" in parent_ac_ex_db.context
            and "parent" in parent_ac_ex_db.context
        ):
            handle_action_execution_resume(parent_ac_ex_db)


@retrying.retry(
    retry_on_exception=wf_exc.retry_on_connection_errors,
    stop_max_delay=cfg.CONF.workflow_engine.retry_stop_max_msec,
    wait_fixed=cfg.CONF.workflow_engine.retry_wait_fixed_msec,
    wait_jitter_max=cfg.CONF.workflow_engine.retry_max_jitter_msec,
)
def handle_action_execution_completion(ac_ex_db):
    # Check that the action execution is completed.
    if ac_ex_db.status not in ac_const.LIVEACTION_COMPLETED_STATES:
        raise Exception(
            "Unable to handle completion of action execution. The action execution "
            '"%s" is in "%s" status.' % (str(ac_ex_db.id), ac_ex_db.status)
        )

    # Get related record identifiers.
    wf_ex_id = ac_ex_db.context["orquesta"]["workflow_execution_id"]
    task_ex_id = ac_ex_db.context["orquesta"]["task_execution_id"]

    # Acquire lock before write operations.
    with coord_svc.get_coordinator(start_heart=True).get_lock(str(wf_ex_id).encode()):
        # Get execution records for logging purposes.
        wf_ex_db = wf_db_access.WorkflowExecution.get_by_id(wf_ex_id)
        task_ex_db = wf_db_access.TaskExecution.get_by_id(task_ex_id)

        msg = (
            'Handling completion of action execution "%s" '
            'in status "%s" for task "%s", route "%s".'
            % (
                str(ac_ex_db.id),
                ac_ex_db.status,
                task_ex_db.task_id,
                str(task_ex_db.task_route),
            )
        )
        update_progress(wf_ex_db, msg)

        # If task is currently paused and the action execution is skipped to
        # completion, then transition task status to running first.
        if task_ex_db.status == ac_const.LIVEACTION_STATUS_PAUSED:
            resume_task_execution(task_ex_id)

        # Update task execution if completed.
        update_task_execution(
            task_ex_id, ac_ex_db.status, ac_ex_db.result, ac_ex_db.context
        )

        # Update task flow in the workflow execution.
        update_task_state(
            task_ex_id,
            ac_ex_db.status,
            ac_ex_result=ac_ex_db.result,
            ac_ex_ctx=ac_ex_db.context.get("orquesta"),
        )

        # Request the next set of tasks if workflow execution is not complete.
        request_next_tasks(wf_ex_db, task_ex_id=task_ex_id)

        # Update workflow execution if completed.
        update_workflow_execution(wf_ex_id)


def deserialize_conductor(wf_ex_db):
    data = {
        "spec": wf_ex_db.spec,
        "graph": wf_ex_db.graph,
        "input": wf_ex_db.input,
        "context": wf_ex_db.context,
        "state": wf_ex_db.state,
        "output": wf_ex_db.output,
        "errors": wf_ex_db.errors,
    }

    return conducting.WorkflowConductor.deserialize(data)


def refresh_conductor(wf_ex_id):
    wf_ex_db = wf_db_access.WorkflowExecution.get_by_id(wf_ex_id)
    conductor = deserialize_conductor(wf_ex_db)

    return conductor, wf_ex_db


@retrying.retry(
    retry_on_exception=wf_exc.retry_on_transient_db_errors,
    wait_fixed=cfg.CONF.workflow_engine.retry_wait_fixed_msec,
    wait_jitter_max=cfg.CONF.workflow_engine.retry_max_jitter_msec,
)
@retrying.retry(
    retry_on_exception=wf_exc.retry_on_connection_errors,
    stop_max_delay=cfg.CONF.workflow_engine.retry_stop_max_msec,
    wait_fixed=cfg.CONF.workflow_engine.retry_wait_fixed_msec,
    wait_jitter_max=cfg.CONF.workflow_engine.retry_max_jitter_msec,
)
def update_task_state(
    task_ex_id, ac_ex_status, ac_ex_result=None, ac_ex_ctx=None, publish=True
):
    # Return if action execution status is not in the list of statuses to process.
    statuses_to_process = copy.copy(ac_const.LIVEACTION_COMPLETED_STATES) + [
        ac_const.LIVEACTION_STATUS_PAUSED,
        ac_const.LIVEACTION_STATUS_PENDING,
    ]

    if ac_ex_status not in statuses_to_process:
        return

    # Refresh records
    task_ex_db = wf_db_access.TaskExecution.get_by_id(task_ex_id)
    conductor, wf_ex_db = refresh_conductor(task_ex_db.workflow_execution)

    # Update task flow if task execution is completed or paused.
    msg = 'Publish task "%s", route "%s", with status "%s" to conductor.'
    msg = msg % (task_ex_db.task_id, str(task_ex_db.task_route), task_ex_db.status)
    update_progress(wf_ex_db, msg, stream=False)

    if not ac_ex_ctx or "item_id" not in ac_ex_ctx or ac_ex_ctx["item_id"] < 0:
        ac_ex_event = events.ActionExecutionEvent(ac_ex_status, result=ac_ex_result)
    else:
        accumulated_result = [
            item.get("result") if item else None for item in task_ex_db.result["items"]
        ]

        ac_ex_event = events.TaskItemActionExecutionEvent(
            ac_ex_ctx["item_id"],
            ac_ex_status,
            result=ac_ex_result,
            accumulated_result=accumulated_result,
        )

    update_progress(wf_ex_db, conductor.serialize(), severity="debug", stream=False)
    conductor.update_task_state(task_ex_db.task_id, task_ex_db.task_route, ac_ex_event)

    # Update workflow execution and related liveaction and action execution.
    update_execution_records(
        wf_ex_db,
        conductor,
        update_lv_ac_on_statuses=statuses_to_process,
        pub_lv_ac=publish,
        pub_ac_ex=publish,
    )


@retrying.retry(
    retry_on_exception=wf_exc.retry_on_transient_db_errors,
    wait_fixed=cfg.CONF.workflow_engine.retry_wait_fixed_msec,
    wait_jitter_max=cfg.CONF.workflow_engine.retry_max_jitter_msec,
)
@retrying.retry(
    retry_on_exception=wf_exc.retry_on_connection_errors,
    stop_max_delay=cfg.CONF.workflow_engine.retry_stop_max_msec,
    wait_fixed=cfg.CONF.workflow_engine.retry_wait_fixed_msec,
    wait_jitter_max=cfg.CONF.workflow_engine.retry_max_jitter_msec,
)
def request_next_tasks(wf_ex_db, task_ex_id=None):
    iteration = 0

    # Refresh records.
    conductor, wf_ex_db = refresh_conductor(str(wf_ex_db.id))

    # If workflow is in requested status, set it to running.
    if conductor.get_workflow_status() in [statuses.REQUESTED, statuses.SCHEDULED]:
        update_progress(
            wf_ex_db, "Requesting conductor to start running workflow execution."
        )
        conductor.request_workflow_status(statuses.RUNNING)

    # Identify the list of next set of tasks. Don't pass the task id to the conductor
    # so it can identify any next set of tasks to run from the workflow.
    if task_ex_id:
        task_ex_db = wf_db_access.TaskExecution.get_by_id(task_ex_id)
        msg = 'Identifying next set (iter %s) of tasks after completion of task "%s", route "%s".'
        msg = msg % (str(iteration), task_ex_db.task_id, str(task_ex_db.task_route))
        update_progress(wf_ex_db, msg)
        update_progress(wf_ex_db, conductor.serialize(), severity="debug", stream=False)
        next_tasks = conductor.get_next_tasks()
    else:
        msg = 'Identifying next set (iter %s) of tasks for workflow execution in status "%s".'
        msg = msg % (str(iteration), conductor.get_workflow_status())
        update_progress(wf_ex_db, msg)
        update_progress(wf_ex_db, conductor.serialize(), severity="debug", stream=False)
        next_tasks = conductor.get_next_tasks()

    # If there is no new tasks, update execution records to handle possible completion.
    if not next_tasks:
        # Update workflow execution and related liveaction and action execution.
        update_progress(wf_ex_db, "No tasks identified to execute next.")
        update_progress(wf_ex_db, "\n", log=False)
        update_execution_records(wf_ex_db, conductor)

        if conductor.get_workflow_status() in statuses.COMPLETED_STATUSES:
            msg = 'The workflow execution is completed with status "%s".'
            update_progress(wf_ex_db, msg % conductor.get_workflow_status())
            update_progress(wf_ex_db, "\n", log=False)

    # Iterate while there are next tasks identified for processing. In the case for
    # task with no action execution defined, the task execution will complete
    # immediately with a new set of tasks available.
    while next_tasks:
        msg = "Identified the following set of tasks to execute next: %s"
        tasks_list = ", ".join(
            ["%s (route %s)" % (t["id"], str(t["route"])) for t in next_tasks]
        )
        update_progress(wf_ex_db, msg % tasks_list)

        # Mark the tasks as running in the task flow before actual task execution.
        for task in next_tasks:
            msg = 'Mark task "%s", route "%s", in conductor as running.'
            update_progress(
                wf_ex_db, msg % (task["id"], str(task["route"])), stream=False
            )

            # If task has items and items list is empty, then actions under the next task is empty
            # and will not be processed in the for loop below. Handle this use case separately and
            # mark it as running in the conductor. The task will be completed automatically when
            # it is requested for task execution.
            if (
                task["spec"].has_items()
                and "items_count" in task
                and task["items_count"] == 0
            ):
                ac_ex_event = events.ActionExecutionEvent(statuses.RUNNING)
                conductor.update_task_state(task["id"], task["route"], ac_ex_event)

            # If task contains multiple action execution (i.e. with items),
            # then mark each item individually.
            for action in task["actions"]:
                if "item_id" not in action or action["item_id"] is None:
                    ac_ex_event = events.ActionExecutionEvent(statuses.RUNNING)
                else:
                    msg = (
                        'Mark task "%s", route "%s", item "%s" in conductor as running.'
                    )
                    msg = msg % (task["id"], str(task["route"]), action["item_id"])
                    update_progress(wf_ex_db, msg)
                    ac_ex_event = events.TaskItemActionExecutionEvent(
                        action["item_id"], statuses.RUNNING
                    )

                conductor.update_task_state(task["id"], task["route"], ac_ex_event)

        # Update workflow execution and related liveaction and action execution.
        update_progress(wf_ex_db, conductor.serialize(), severity="debug", stream=False)
        update_execution_records(wf_ex_db, conductor)

        # Request task execution for the tasks.
        for task in next_tasks:
            try:
                msg = 'Requesting execution for task "%s", route "%s".'
                update_progress(wf_ex_db, msg % (task["id"], str(task["route"])))

                # Pass down appropriate st2 context to the task and action execution(s).
                root_st2_ctx = wf_ex_db.context.get("st2", {})
                st2_ctx = {
                    "execution_id": wf_ex_db.action_execution,
                    "user": root_st2_ctx.get("user"),
                    "pack": root_st2_ctx.get("pack"),
                }
                if root_st2_ctx.get("api_user"):
                    st2_ctx["api_user"] = root_st2_ctx.get("api_user")

                if root_st2_ctx.get("source_channel"):
                    st2_ctx["source_channel"] = root_st2_ctx.get("source_channel")

                # Request the task execution.
                request_task_execution(wf_ex_db, st2_ctx, task)
            except Exception as e:
                msg = 'Failed task execution for task "%s", route "%s".'
                msg = msg % (task["id"], str(task["route"]))
                update_progress(
                    wf_ex_db, "%s %s" % (msg, str(e)), severity="error", log=False
                )
                LOG.exception(msg)
                fail_workflow_execution(str(wf_ex_db.id), e, task=task)
                return

        # Identify the next set of tasks to execute.
        iteration += 1
        conductor, wf_ex_db = refresh_conductor(str(wf_ex_db.id))
        msg = 'Identifying next set (iter %s) of tasks for workflow execution in status "%s".'
        msg = msg % (str(iteration), conductor.get_workflow_status())
        update_progress(wf_ex_db, msg)
        update_progress(wf_ex_db, conductor.serialize(), severity="debug", stream=False)
        next_tasks = conductor.get_next_tasks()

        if not next_tasks:
            update_progress(wf_ex_db, "No tasks identified to execute next.")
            update_progress(wf_ex_db, "\n", log=False)


@retrying.retry(
    retry_on_exception=wf_exc.retry_on_transient_db_errors,
    wait_fixed=cfg.CONF.workflow_engine.retry_wait_fixed_msec,
    wait_jitter_max=cfg.CONF.workflow_engine.retry_max_jitter_msec,
)
@retrying.retry(
    retry_on_exception=wf_exc.retry_on_connection_errors,
    stop_max_delay=cfg.CONF.workflow_engine.retry_stop_max_msec,
    wait_fixed=cfg.CONF.workflow_engine.retry_wait_fixed_msec,
    wait_jitter_max=cfg.CONF.workflow_engine.retry_max_jitter_msec,
)
def update_task_execution(task_ex_id, ac_ex_status, ac_ex_result=None, ac_ex_ctx=None):
    if ac_ex_status not in statuses.COMPLETED_STATUSES + [
        statuses.PAUSED,
        statuses.PENDING,
    ]:
        return

    task_ex_db = wf_db_access.TaskExecution.get_by_id(task_ex_id)
    wf_ex_db = wf_db_access.WorkflowExecution.get_by_id(task_ex_db.workflow_execution)

    # Treat the update of task with items but items list is empty like a normal task execution.
    if not task_ex_db.itemized or (task_ex_db.itemized and task_ex_db.items_count == 0):
        if ac_ex_status != task_ex_db.status:
            msg = 'Updating task execution "%s" for task "%s" from status "%s" to "%s".'
            msg = msg % (
                task_ex_id,
                task_ex_db.task_id,
                task_ex_db.status,
                ac_ex_status,
            )
            update_progress(wf_ex_db, msg)

        task_ex_db.status = ac_ex_status
        task_ex_db.result = ac_ex_result if ac_ex_result else task_ex_db.result
    elif task_ex_db.itemized and ac_ex_ctx:
        if "orquesta" not in ac_ex_ctx or "item_id" not in ac_ex_ctx["orquesta"]:
            msg = "Context information for the item is not provided. %s" % str(
                ac_ex_ctx
            )
            update_progress(wf_ex_db, msg, severity="error", log=False)
            raise Exception(msg)

        item_id = ac_ex_ctx["orquesta"]["item_id"]

        msg = 'Processing action execution for task "%s", route "%s", item "%s".'
        msg = msg % (task_ex_db.task_id, str(task_ex_db.task_route), item_id)
        update_progress(wf_ex_db, msg, severity="debug")

        task_ex_db.result["items"][item_id] = {
            "status": ac_ex_status,
            "result": ac_ex_result,
        }

        item_statuses = [
            item.get("status", statuses.UNSET) if item else statuses.UNSET
            for item in task_ex_db.result["items"]
        ]

        task_completed = all(
            [status in statuses.COMPLETED_STATUSES for status in item_statuses]
        )

        if task_completed:
            new_task_status = (
                statuses.SUCCEEDED
                if all([status == statuses.SUCCEEDED for status in item_statuses])
                else statuses.FAILED
            )

            msg = 'Updating task execution from status "%s" to "%s".'
            update_progress(
                wf_ex_db, msg % (task_ex_db.status, new_task_status), severity="debug"
            )
            task_ex_db.status = new_task_status
        else:
            msg = (
                "Task execution is not complete because not all items are complete: %s"
            )
            update_progress(wf_ex_db, msg % ", ".join(item_statuses), severity="debug")

    if task_ex_db.status in statuses.COMPLETED_STATUSES:
        task_ex_db.end_timestamp = date_utils.get_datetime_utc_now()

    wf_db_access.TaskExecution.update(task_ex_db, publish=False)


@retrying.retry(
    retry_on_exception=wf_exc.retry_on_transient_db_errors,
    wait_fixed=cfg.CONF.workflow_engine.retry_wait_fixed_msec,
    wait_jitter_max=cfg.CONF.workflow_engine.retry_max_jitter_msec,
)
@retrying.retry(
    retry_on_exception=wf_exc.retry_on_connection_errors,
    stop_max_delay=cfg.CONF.workflow_engine.retry_stop_max_msec,
    wait_fixed=cfg.CONF.workflow_engine.retry_wait_fixed_msec,
    wait_jitter_max=cfg.CONF.workflow_engine.retry_max_jitter_msec,
)
def resume_task_execution(task_ex_id):
    # Update task execution to running.
    task_ex_db = wf_db_access.TaskExecution.get_by_id(task_ex_id)
    wf_ex_db = wf_db_access.WorkflowExecution.get_by_id(task_ex_db.workflow_execution)

    msg = 'Updating task execution from status "%s" to "%s".'
    update_progress(
        wf_ex_db, msg % (task_ex_db.status, statuses.RUNNING), severity="debug"
    )
    task_ex_db.status = statuses.RUNNING

    # Write update to the database.
    wf_db_access.TaskExecution.update(task_ex_db, publish=False)


@retrying.retry(
    retry_on_exception=wf_exc.retry_on_transient_db_errors,
    wait_fixed=cfg.CONF.workflow_engine.retry_wait_fixed_msec,
    wait_jitter_max=cfg.CONF.workflow_engine.retry_max_jitter_msec,
)
@retrying.retry(
    retry_on_exception=wf_exc.retry_on_connection_errors,
    stop_max_delay=cfg.CONF.workflow_engine.retry_stop_max_msec,
    wait_fixed=cfg.CONF.workflow_engine.retry_wait_fixed_msec,
    wait_jitter_max=cfg.CONF.workflow_engine.retry_max_jitter_msec,
)
def update_workflow_execution(wf_ex_id):
    conductor, wf_ex_db = refresh_conductor(wf_ex_id)

    # There is nothing to update if workflow execution is not completed or paused.
    if conductor.get_workflow_status() in statuses.COMPLETED_STATUSES + [
        statuses.PAUSED
    ]:
        # Update workflow execution and related liveaction and action execution.
        update_execution_records(wf_ex_db, conductor)


@retrying.retry(
    retry_on_exception=wf_exc.retry_on_transient_db_errors,
    wait_fixed=cfg.CONF.workflow_engine.retry_wait_fixed_msec,
    wait_jitter_max=cfg.CONF.workflow_engine.retry_max_jitter_msec,
)
@retrying.retry(
    retry_on_exception=wf_exc.retry_on_connection_errors,
    stop_max_delay=cfg.CONF.workflow_engine.retry_stop_max_msec,
    wait_fixed=cfg.CONF.workflow_engine.retry_wait_fixed_msec,
    wait_jitter_max=cfg.CONF.workflow_engine.retry_max_jitter_msec,
)
def resume_workflow_execution(wf_ex_id, task_ex_id):
    # Update workflow execution to running.
    conductor, wf_ex_db = refresh_conductor(wf_ex_id)
    conductor.request_workflow_status(statuses.RUNNING)

    # Update task execution in task flow to running.
    task_ex_db = wf_db_access.TaskExecution.get_by_id(task_ex_id)
    ac_ex_event = events.ActionExecutionEvent(statuses.RUNNING)
    conductor.update_task_state(task_ex_db.task_id, task_ex_db.task_route, ac_ex_event)

    # Update workflow execution and related liveaction and action execution.
    update_execution_records(wf_ex_db, conductor)


@retrying.retry(
    retry_on_exception=wf_exc.retry_on_transient_db_errors,
    wait_fixed=cfg.CONF.workflow_engine.retry_wait_fixed_msec,
    wait_jitter_max=cfg.CONF.workflow_engine.retry_max_jitter_msec,
)
@retrying.retry(
    retry_on_exception=wf_exc.retry_on_connection_errors,
    stop_max_delay=cfg.CONF.workflow_engine.retry_stop_max_msec,
    wait_fixed=cfg.CONF.workflow_engine.retry_wait_fixed_msec,
    wait_jitter_max=cfg.CONF.workflow_engine.retry_max_jitter_msec,
)
def fail_workflow_execution(wf_ex_id, exception, task=None):
    conductor, wf_ex_db = refresh_conductor(wf_ex_id)

    # Set workflow execution status to failed and record error.
    conductor.request_workflow_status(statuses.FAILED)

    if task is not None and isinstance(task, dict):
        conductor.log_error(exception, task_id=task.get("id"), route=task.get("route"))
    else:
        conductor.log_error(exception)

    # Update workflow execution and related liveaction and action execution.
    update_execution_records(wf_ex_db, conductor)


def update_execution_records(
    wf_ex_db,
    conductor,
    update_lv_ac_on_statuses=None,
    pub_wf_ex=False,
    pub_lv_ac=True,
    pub_ac_ex=True,
):
    # If the workflow execution is completed, then render the workflow output.
    if conductor.get_workflow_status() in statuses.COMPLETED_STATUSES:
        conductor.render_workflow_output()

    # Determine if workflow status has changed.
    wf_old_status = wf_ex_db.status
    wf_ex_db.status = conductor.get_workflow_status()
    status_changed = wf_old_status != wf_ex_db.status

    if status_changed:
        msg = 'Updating workflow execution from status "%s" to "%s".'
        update_progress(wf_ex_db, msg % (wf_old_status, wf_ex_db.status))

    # Update timestamp and output if workflow is completed.
    if wf_ex_db.status in statuses.COMPLETED_STATUSES:
        wf_ex_db.end_timestamp = date_utils.get_datetime_utc_now()
        wf_ex_db.output = conductor.get_workflow_output()

    # Update task flow and other attributes.
    wf_ex_db.errors = copy.deepcopy(conductor.errors)
    wf_ex_db.state = conductor.workflow_state.serialize()

    # Write changes to the database.
    wf_ex_db = wf_db_access.WorkflowExecution.update(wf_ex_db, publish=pub_wf_ex)

    # Return if workflow execution status is not specified in update_lv_ac_on_statuses.
    if (
        isinstance(update_lv_ac_on_statuses, list)
        and wf_ex_db.status not in update_lv_ac_on_statuses
    ):
        return

    # Update the corresponding liveaction and action execution for the workflow.
    wf_ac_ex_db = ex_db_access.ActionExecution.get_by_id(wf_ex_db.action_execution)
    wf_lv_ac_db = action_utils.get_liveaction_by_id(wf_ac_ex_db.liveaction["id"])

    # Gather result for liveaction and action execution.
    result = {"output": wf_ex_db.output or None}

    if wf_ex_db.status in statuses.ABENDED_STATUSES:
        result["errors"] = wf_ex_db.errors

        if wf_ex_db.errors:
            msg = "Workflow execution completed with errors."
            update_progress(wf_ex_db, msg, severity="error")

            for wf_ex_error in wf_ex_db.errors:
                update_progress(wf_ex_db, wf_ex_error, severity="error")

    # Sync update with corresponding liveaction and action execution.
    if pub_lv_ac or pub_ac_ex:
        pub_lv_ac = wf_lv_ac_db.status != wf_ex_db.status
        pub_ac_ex = pub_lv_ac

    if wf_lv_ac_db.status != wf_ex_db.status:
        kwargs = {"severity": "debug", "stream": False}
        msg = 'Updating workflow liveaction from status "%s" to "%s".'
        update_progress(wf_ex_db, msg % (wf_lv_ac_db.status, wf_ex_db.status), **kwargs)
        msg = "Workflow liveaction status change %s be published."
        update_progress(wf_ex_db, msg % "will" if pub_lv_ac else "will not", **kwargs)
        msg = "Workflow action execution status change %s be published."
        update_progress(wf_ex_db, msg % "will" if pub_ac_ex else "will not", **kwargs)

    wf_lv_ac_db = action_utils.update_liveaction_status(
        status=wf_ex_db.status,
        result=result,
        end_timestamp=wf_ex_db.end_timestamp,
        liveaction_db=wf_lv_ac_db,
        publish=pub_lv_ac,
    )

    ex_svc.update_execution(wf_lv_ac_db, publish=pub_ac_ex, set_result_size=True)

    # Invoke post run on the liveaction for the workflow execution.
    if status_changed and wf_lv_ac_db.status in ac_const.LIVEACTION_COMPLETED_STATES:
        update_progress(
            wf_ex_db, "Workflow action execution is completed and invoking post run."
        )
        runners_utils.invoke_post_run(wf_lv_ac_db)


def identify_orphaned_workflows():
    orphaned = []

    # Identify expiry datetime.
    gc_max_idle = cfg.CONF.workflow_engine.gc_max_idle_sec
    utc_now_dt = date_utils.get_datetime_utc_now()
    expiry_dt = utc_now_dt - datetime.timedelta(seconds=gc_max_idle)

    # Identify action executions that are still running. The action execution start timestamp
    # does not necessary means it is the max idle time. The use of workflow_executions_idled_ttl
    # to filter is to reduce the number of action executions that need to be evaluated.
    query_filters = {
        "runner__name": "orquesta",
        "status": ac_const.LIVEACTION_STATUS_RUNNING,
        "start_timestamp__lte": expiry_dt,
    }
    ac_ex_dbs = ex_db_access.ActionExecution.query(**query_filters)

    for ac_ex_db in ac_ex_dbs:
        # Figure out the runtime for the action execution.
        status_change_logs = sorted(
            [
                log
                for log in ac_ex_db.log
                if log["status"] == ac_const.LIVEACTION_STATUS_RUNNING
            ],
            key=lambda x: x["timestamp"],
            reverse=True,
        )

        if len(status_change_logs) <= 0:
            continue

        runtime = (utc_now_dt - status_change_logs[0]["timestamp"]).total_seconds()

        # Fetch the task executions for the workflow execution.
        # Ensure that the root action execution is not being selected.
        wf_ex_id = ac_ex_db.context["workflow_execution"]
        wf_ex_db = wf_db_access.WorkflowExecution.get_by_id(wf_ex_id)
        query_filters = {"workflow_execution": wf_ex_id, "id__ne": ac_ex_db.id}
        tk_ac_ex_dbs = ex_db_access.ActionExecution.query(**query_filters)

        # The workflow execution is orphaned if there are
        # no task executions and runtime passed expiry.
        if len(tk_ac_ex_dbs) <= 0 and runtime > gc_max_idle:
            msg = "The action execution is orphaned and will be canceled by the garbage collector."
            update_progress(wf_ex_db, msg)
            orphaned.append(ac_ex_db)
            continue

        # The workflow execution is orphaned if there are no active task execution and
        # the end_timestamp of the most recent task execution passed expiry.
        has_active_tasks = len([t for t in tk_ac_ex_dbs if t.end_timestamp is None]) > 0

        completed_tasks = [
            t
            for t in tk_ac_ex_dbs
            if t.end_timestamp is not None and t.end_timestamp <= expiry_dt
        ]

        completed_tasks = sorted(completed_tasks, key=lambda x: x.end_timestamp)

        most_recent_completed_task_expired = (
            completed_tasks[-1].end_timestamp <= expiry_dt
            if len(completed_tasks) > 0
            else False
        )

        if (
            len(tk_ac_ex_dbs) > 0
            and not has_active_tasks
            and most_recent_completed_task_expired
        ):
            msg = "The action execution is orphaned and will be canceled by the garbage collector."
            update_progress(wf_ex_db, msg)
            orphaned.append(ac_ex_db)
            continue

    return orphaned

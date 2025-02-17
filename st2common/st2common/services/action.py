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
import six

from st2common import log as logging
from st2common.constants import action as action_constants
from st2common.exceptions import actionrunner as runner_exc
from st2common.exceptions import db as db_exc
from st2common.exceptions import trace as trace_exc
from st2common.persistence.liveaction import LiveAction
from st2common.persistence.execution import ActionExecution
from st2common.persistence.execution import ActionExecutionOutput
from st2common.persistence.workflow import TaskExecution
from st2common.persistence.workflow import WorkflowExecution
from st2common.models.db.execution import ActionExecutionOutputDB
from st2common.models.db.auth import UserDB
from st2common.runners import utils as runners_utils
from st2common.services import executions
from st2common.services import trace as trace_service
from st2common.services import workflows as workflow_service
from st2common.util import date as date_utils
from st2common.util import action_db as action_utils
from st2common.util import schema as util_schema


__all__ = [
    "request",
    "create_request",
    "publish_request",
    "is_action_canceled_or_canceling",
    "request_pause",
    "request_resume",
    "store_execution_output_data",
]

LOG = logging.getLogger(__name__)


def _get_immutable_params(parameters):
    if not parameters:
        return []
    return [k for k, v in six.iteritems(parameters) if v.get("immutable", False)]


def create_request(
    liveaction, action_db=None, runnertype_db=None, validate_params=True
):
    """
    Create an action execution.

    :param action_db: Action model to operate one. If not provided, one is retrieved from the
                      database using values from "liveaction".
    :type action_db: :class:`ActionDB`

    :param runnertype_db: Runner model to operate one. If not provided, one is retrieved from the
                          database using values from "liveaction".
    :type runnertype_db: :class:`RunnerTypeDB`
    :param validate_params: Whether to validate parameters against schema. Default to True, but
                          set to False when raising a request to report an error.
    :type validate_params: ``bool``

    :return: (liveaction, execution)
    :rtype: tuple
    """
    # We import this here to avoid conflicts w/ runners that might import this
    # file since the runners don't have the config context by default.
    from st2common.metrics.base import get_driver

    # Use the user context from the parent action execution. Subtasks in a workflow
    # action can be invoked by a system user and so we want to use the user context
    # from the original workflow action.
    parent_context = executions.get_parent_context(liveaction) or {}
    parent_user = parent_context.get("user", None)

    if parent_user:
        liveaction.context["user"] = parent_user

    # Validate action
    if not action_db:
        action_db = action_utils.get_action_by_ref(liveaction.action)

    if not action_db:
        raise ValueError('Action "%s" cannot be found.' % liveaction.action)
    if not action_db.enabled:
        raise ValueError(
            'Unable to execute. Action "%s" is disabled.' % liveaction.action
        )

    if not runnertype_db:
        runnertype_db = action_utils.get_runnertype_by_name(
            action_db.runner_type["name"]
        )

    if not hasattr(liveaction, "parameters"):
        liveaction.parameters = dict()

    # For consistency add pack to the context here in addition to RunnerContainer.dispatch() method
    liveaction.context["pack"] = action_db.pack

    # Validate action parameters.
    schema = util_schema.get_schema_for_action_parameters(action_db, runnertype_db)
    validator = util_schema.get_validator()
    if validate_params:
        util_schema.validate(
            liveaction.parameters,
            schema,
            validator,
            use_default=True,
            allow_default_none=True,
        )

    # validate that no immutable params are being overriden. Although possible to
    # ignore the override it is safer to inform the user to avoid surprises.
    immutables = _get_immutable_params(action_db.parameters)
    immutables.extend(_get_immutable_params(runnertype_db.runner_parameters))
    overridden_immutables = [
        p for p in six.iterkeys(liveaction.parameters) if p in immutables
    ]
    if len(overridden_immutables) > 0:
        raise ValueError(
            "Override of immutable parameter(s) %s is unsupported."
            % str(overridden_immutables)
        )

    # Set notification settings for action.
    # XXX: There are cases when we don't want notifications to be sent for a particular
    # execution. So we should look at liveaction.parameters['notify']
    # and not set liveaction.notify.
    if not _is_notify_skipped(liveaction) and not _is_notify_empty(action_db.notify):
        liveaction.notify = action_db.notify

    # Write to database and send to message queue.
    liveaction.status = action_constants.LIVEACTION_STATUS_REQUESTED
    liveaction.start_timestamp = date_utils.get_datetime_utc_now()

    # Set the "action_is_workflow" attribute
    liveaction.action_is_workflow = action_db.is_workflow()

    # Publish creation after both liveaction and actionexecution are created.
    liveaction = LiveAction.add_or_update(liveaction, publish=False)
    # Get trace_db if it exists. This could throw. If it throws, we have to cleanup
    # liveaction object so we don't see things in requested mode.
    trace_db = None
    try:
        _, trace_db = trace_service.get_trace_db_by_live_action(liveaction)
    except db_exc.StackStormDBObjectNotFoundError as e:
        _cleanup_liveaction(liveaction)
        raise trace_exc.TraceNotFoundException(six.text_type(e))

    execution = executions.create_execution_object(
        liveaction=liveaction,
        action_db=action_db,
        runnertype_db=runnertype_db,
        publish=False,
    )

    if trace_db:
        trace_service.add_or_update_given_trace_db(
            trace_db=trace_db,
            action_executions=[
                trace_service.get_trace_component_for_action_execution(
                    execution, liveaction
                )
            ],
        )

    get_driver().inc_counter("action.executions.%s" % (liveaction.status))

    return liveaction, execution


def publish_request(liveaction, execution):
    """
    Publish an action execution.

    :return: (liveaction, execution)
    :rtype: tuple
    """
    # Assume that this is a creation.
    LiveAction.publish_create(liveaction)
    LiveAction.publish_status(liveaction)
    ActionExecution.publish_create(execution)

    # TODO: This results in two queries, optimize it
    #  extra = {'liveaction_db': liveaction, 'execution_db': execution}
    extra = {}
    LOG.audit(
        "Action execution requested. LiveAction.id=%s, ActionExecution.id=%s"
        % (liveaction.id, execution.id),
        extra=extra,
    )

    return liveaction, execution


def request(liveaction):
    liveaction, execution = create_request(liveaction)
    liveaction, execution = publish_request(liveaction, execution)

    return liveaction, execution


def update_status(
    liveaction,
    new_status,
    result=None,
    publish=True,
    set_result_size=False,
    context=None,
):
    if liveaction.status == new_status:
        return liveaction

    old_status = liveaction.status

    updates = {
        "liveaction_id": liveaction.id,
        "status": new_status,
        "result": result,
        "publish": False,
        "context": context,
    }

    if new_status in action_constants.LIVEACTION_COMPLETED_STATES:
        updates["end_timestamp"] = date_utils.get_datetime_utc_now()

    liveaction = action_utils.update_liveaction_status(**updates)
    action_execution = executions.update_execution(
        liveaction, set_result_size=set_result_size
    )

    msg = (
        "The status of action execution is changed from %s to %s. "
        "<LiveAction.id=%s, ActionExecution.id=%s>"
        % (old_status, new_status, liveaction.id, action_execution.id)
    )

    extra = {"action_execution_db": action_execution, "liveaction_db": liveaction}

    LOG.audit(msg, extra=extra)
    LOG.info(msg)

    # Invoke post run if liveaction status is completed or paused.
    if (
        new_status in action_constants.LIVEACTION_COMPLETED_STATES
        or new_status == action_constants.LIVEACTION_STATUS_PAUSED
    ):
        runners_utils.invoke_post_run(liveaction)

    if publish:
        LiveAction.publish_status(liveaction)

    return liveaction


def is_action_canceled_or_canceling(liveaction_id):
    liveaction_db = action_utils.get_liveaction_by_id(liveaction_id)
    return liveaction_db.status in [
        action_constants.LIVEACTION_STATUS_CANCELED,
        action_constants.LIVEACTION_STATUS_CANCELING,
    ]


def is_action_paused_or_pausing(liveaction_id):
    liveaction_db = action_utils.get_liveaction_by_id(liveaction_id)
    return liveaction_db.status in [
        action_constants.LIVEACTION_STATUS_PAUSED,
        action_constants.LIVEACTION_STATUS_PAUSING,
    ]


def request_cancellation(liveaction, requester):
    """
    Request cancellation of an action execution.

    :return: (liveaction, execution)
    :rtype: tuple
    """
    if liveaction.status == action_constants.LIVEACTION_STATUS_CANCELING:
        return liveaction

    if liveaction.status not in action_constants.LIVEACTION_CANCELABLE_STATES:
        raise Exception(
            'Unable to cancel liveaction "%s" because it is already in a '
            "completed state." % liveaction.id
        )

    result = {"message": "Action canceled by user.", "user": requester}

    # Run cancelation sequence for liveaction that is in running state or
    # if the liveaction is operating under a workflow.
    if (
        "parent" in liveaction.context
        or liveaction.status in action_constants.LIVEACTION_STATUS_RUNNING
    ):
        status = action_constants.LIVEACTION_STATUS_CANCELING
    else:
        status = action_constants.LIVEACTION_STATUS_CANCELED

    liveaction.context["cancelled_by"] = get_requester(requester)
    liveaction = update_status(
        liveaction, status, result=result, context=liveaction.context
    )

    execution = ActionExecution.get(liveaction__id=str(liveaction.id))

    return (liveaction, execution)


def request_pause(liveaction, requester):
    """
    Request pause for a running action execution.

    :return: (liveaction, execution)
    :rtype: tuple
    """
    # Validate that the runner type of the action supports pause.
    action_db = action_utils.get_action_by_ref(liveaction.action)

    if not action_db:
        raise ValueError(
            'Unable to pause liveaction "%s" because the action "%s" '
            "is not found." % (liveaction.id, liveaction.action)
        )

    if action_db.runner_type["name"] not in action_constants.WORKFLOW_RUNNER_TYPES:
        raise runner_exc.InvalidActionRunnerOperationError(
            'Unable to pause liveaction "%s" because it is not supported by the '
            '"%s" runner.' % (liveaction.id, action_db.runner_type["name"])
        )

    if (
        liveaction.status == action_constants.LIVEACTION_STATUS_PAUSING
        or liveaction.status == action_constants.LIVEACTION_STATUS_PAUSED
    ):
        execution = ActionExecution.get(liveaction__id=str(liveaction.id))
        return (liveaction, execution)

    if liveaction.status != action_constants.LIVEACTION_STATUS_RUNNING:
        raise runner_exc.UnexpectedActionExecutionStatusError(
            'Unable to pause liveaction "%s" because it is not in a running state.'
            % liveaction.id
        )

    liveaction.context["paused_by"] = get_requester(requester)
    liveaction = update_status(
        liveaction,
        action_constants.LIVEACTION_STATUS_PAUSING,
        context=liveaction.context,
    )

    execution = ActionExecution.get(liveaction__id=str(liveaction.id))

    return (liveaction, execution)


def request_resume(liveaction, requester):
    """
    Request resume for a paused action execution.

    :return: (liveaction, execution)
    :rtype: tuple
    """
    # Validate that the runner type of the action supports pause.
    action_db = action_utils.get_action_by_ref(liveaction.action)

    if not action_db:
        raise ValueError(
            'Unable to resume liveaction "%s" because the action "%s" '
            "is not found." % (liveaction.id, liveaction.action)
        )

    if action_db.runner_type["name"] not in action_constants.WORKFLOW_RUNNER_TYPES:
        raise runner_exc.InvalidActionRunnerOperationError(
            'Unable to resume liveaction "%s" because it is not supported by the '
            '"%s" runner.' % (liveaction.id, action_db.runner_type["name"])
        )

    running_states = [
        action_constants.LIVEACTION_STATUS_RUNNING,
        action_constants.LIVEACTION_STATUS_RESUMING,
    ]

    if liveaction.status in running_states:
        execution = ActionExecution.get(liveaction__id=str(liveaction.id))
        return (liveaction, execution)

    if liveaction.status != action_constants.LIVEACTION_STATUS_PAUSED:
        raise runner_exc.UnexpectedActionExecutionStatusError(
            'Unable to resume liveaction "%s" because it is in "%s" state and '
            'not in "paused" state.' % (liveaction.id, liveaction.status)
        )

    liveaction.context["resumed_by"] = get_requester(requester)
    liveaction = update_status(
        liveaction,
        action_constants.LIVEACTION_STATUS_RESUMING,
        context=liveaction.context,
    )

    execution = ActionExecution.get(liveaction__id=str(liveaction.id))

    return (liveaction, execution)


def get_parent_liveaction(liveaction_db):
    """Get the liveaction for the parent workflow

    Useful for finding the parent workflow. Pass in any LiveActionDB instance,
    and this function will return the liveaction of the parent workflow.

    :param liveaction_db: The LiveActionDB instance for which to find the parent.
    :rtype: LiveActionDB
    """

    parent = liveaction_db.context.get("parent")

    if not parent:
        return None

    parent_execution_db = ActionExecution.get(id=parent["execution_id"])
    parent_liveaction_db = LiveAction.get(id=parent_execution_db.liveaction["id"])

    return parent_liveaction_db


def get_parent_execution(execution_db):
    """Get the action execution for the parent workflow

    Useful for finding the parent workflow. Pass in any ActionExecutionDB instance,
    and this function will return the action execution of the parent workflow.

    :param execution_db: The ActionExecutionDB instance for which to find the parent.
    :rtype: ActionExecutionDB
    """

    if not execution_db.parent:
        return None

    parent_execution_db = ActionExecution.get(id=execution_db.parent)

    return parent_execution_db


def get_root_liveaction(liveaction_db):
    """Recursively ascends until the root liveaction is found

    Useful for finding an original parent workflow. Pass in any LiveActionDB instance,
    and this function will eventually return the top-most liveaction, even if the two
    are one and the same.

    :param liveaction_db: The LiveActionDB instance for which to find the root parent.
    :rtype: LiveActionDB
    """

    parent_liveaction_db = get_parent_liveaction(liveaction_db)

    return (
        get_root_liveaction(parent_liveaction_db)
        if parent_liveaction_db
        else liveaction_db
    )


def get_root_execution(execution_db):
    """Recursively ascends until the root action execution is found

    Useful for finding an original parent workflow. Pass in any ActionExecutionDB instance,
    and this function will eventually return the top-most action execution, even if the two
    are one and the same.

    :param execution_db: The ActionExecutionDB instance for which to find the root parent.
    :rtype: ActionExecutionDB
    """

    parent_execution_db = get_parent_execution(execution_db)

    return (
        get_root_execution(parent_execution_db) if parent_execution_db else execution_db
    )


def store_execution_output_data(
    execution_db, action_db, data, output_type="output", timestamp=None
):
    """
    Store output from an execution as a new document in the collection.
    """
    execution_id = str(execution_db.id)

    if action_db is None:
        action_ref = execution_db.action.get("ref", "unknown")
        runner_ref = execution_db.action.get("runner_type", "unknown")
    else:
        action_ref = action_db.ref
        runner_ref = getattr(action_db, "runner_type", {}).get("name", "unknown")

    return store_execution_output_data_ex(
        execution_id,
        action_ref,
        runner_ref,
        data,
        output_type=output_type,
        timestamp=timestamp,
    )


def store_execution_output_data_ex(
    execution_id, action_ref, runner_ref, data, output_type="output", timestamp=None
):
    timestamp = timestamp or date_utils.get_datetime_utc_now()

    output_db = ActionExecutionOutputDB(
        execution_id=execution_id,
        action_ref=action_ref,
        runner_ref=runner_ref,
        timestamp=timestamp,
        output_type=output_type,
        data=data,
    )

    output_db = ActionExecutionOutput.add_or_update(
        output_db, publish=True, dispatch_trigger=False
    )

    return output_db


def is_children_active(liveaction_id):
    execution_db = ActionExecution.get(liveaction__id=str(liveaction_id))

    if execution_db.runner["name"] not in action_constants.WORKFLOW_RUNNER_TYPES:
        return False

    children_execution_dbs = ActionExecution.query(parent=str(execution_db.id))

    inactive_statuses = action_constants.LIVEACTION_COMPLETED_STATES + [
        action_constants.LIVEACTION_STATUS_PAUSED,
        action_constants.LIVEACTION_STATUS_PENDING,
    ]

    completed = [
        child_exec_db.status in inactive_statuses
        for child_exec_db in children_execution_dbs
    ]

    return not all(completed)


def _cleanup_liveaction(liveaction):
    try:
        LiveAction.delete(liveaction)
    except:
        LOG.exception("Failed cleaning up LiveAction: %s.", liveaction)
        pass


def _is_notify_empty(notify_db):
    """
    notify_db is considered to be empty if notify_db is None and neither
    of on_complete, on_success and on_failure have values.
    """
    if not notify_db:
        return True
    return not (notify_db.on_complete or notify_db.on_success or notify_db.on_failure)


def _is_notify_skipped(liveaction):
    """
    notification is skipped if action execution is under workflow context and
    task is not specified under wf_ex_db.notify["tasks"].
    """
    is_under_workflow_context = (
        workflow_service.is_action_execution_under_workflow_context(liveaction)
    )
    is_under_action_chain_context = is_action_execution_under_action_chain_context(
        liveaction
    )
    if is_under_workflow_context:
        wf_ex_db = WorkflowExecution.get(
            id=liveaction.workflow_execution, only_fields=["notify"]
        )
        task_ex_db = TaskExecution.get(
            id=liveaction.task_execution, only_fields=["task_name"]
        )
        return not wf_ex_db.notify or task_ex_db.task_name not in wf_ex_db.notify.get(
            "tasks", {}
        )
    if is_under_action_chain_context:
        task_name = liveaction.context["chain"]["name"]
        parent = liveaction.context.get("parent")
        if parent:
            parent_execution_db = ActionExecution.get(
                id=parent["execution_id"],
                only_fields=["action.parameters", "parameters"],
            )
            skip_notify_tasks = parent_execution_db["parameters"].get("skip_notify", [])
            default_skip_notify_tasks = parent_execution_db["action"]["parameters"].get(
                "skip_notify", {}
            )
            if skip_notify_tasks:
                if task_name in skip_notify_tasks:
                    return True
                # If skip_notify parameter is specified, but task is not skipped.
                return False
            # If skip_notify parameter is not specified, check the task in default list.
            return task_name in default_skip_notify_tasks.get("default", [])
    return False


def is_action_execution_under_action_chain_context(liveaction):
    """
    The action execution is executed under action-chain context
    if it contains the chain key in its context dictionary.
    """
    return liveaction.context and "chain" in liveaction.context


def get_requester(requester):
    if isinstance(requester, UserDB):
        return requester["name"]
    return requester

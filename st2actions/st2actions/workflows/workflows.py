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
from oslo_config import cfg

from orquesta import statuses
from tooz.coordination import GroupNotCreated
from st2common.services import coordination
from eventlet.semaphore import Semaphore
from eventlet import spawn_after
from st2common.constants import action as ac_const
from st2common import log as logging
from st2common.metrics import base as metrics
from st2common.models.db import execution as ex_db_models
from st2common.models.db import workflow as wf_db_models
from st2common.persistence import liveaction as lv_db_access
from st2common.persistence import workflow as wf_db_access
from st2common.persistence import execution as ex_db_access
from st2common.services import policies as pc_svc
from st2common.services import workflows as wf_svc
from st2common.transport import consumers
from st2common.transport import queues
from st2common.transport import utils as txpt_utils
from st2common.util import concurrency
from st2common.util import action_db as action_utils

LOG = logging.getLogger(__name__)


WORKFLOW_EXECUTION_QUEUES = [
    queues.WORKFLOW_EXECUTION_WORK_QUEUE,
    queues.WORKFLOW_EXECUTION_RESUME_QUEUE,
    queues.WORKFLOW_ACTION_EXECUTION_UPDATE_QUEUE,
]

WORKFLOW_ENGINE = "workflow_engine"
WORKFLOW_ENGINE_START_STOP_SEQ = "workflow_engine_start_stop_seq"


class WorkflowExecutionHandler(consumers.VariableMessageHandler):
    def __init__(self, connection, queues):
        super(WorkflowExecutionHandler, self).__init__(connection, queues)
        self._active_messages = 0
        self._semaphore = Semaphore()
        # This is required to ensure workflows stuck in pausing state after shutdown transition to paused state after engine startup.
        self._delay = 30

        def handle_workflow_execution_with_instrumentation(wf_ex_db):
            with metrics.CounterWithTimer(key="orquesta.workflow.executions"):
                return self.handle_workflow_execution(wf_ex_db=wf_ex_db)

        def handle_action_execution_with_instrumentation(ac_ex_db):
            # Ignore non orquesta workflow executions
            if not wf_svc.is_action_execution_under_workflow_context(ac_ex_db):
                return

            with metrics.CounterWithTimer(key="orquesta.action.executions"):
                return self.handle_action_execution(ac_ex_db=ac_ex_db)

        self.message_types = {
            wf_db_models.WorkflowExecutionDB: handle_workflow_execution_with_instrumentation,
            ex_db_models.ActionExecutionDB: handle_action_execution_with_instrumentation,
        }

    def _pause_running_workflows_on_connection_loss(self):
        """
        Pause all running workflows when this is the last workflow engine.

        This method checks if there are other workflow engines running (when coordination is enabled).
        If this is the last engine, it pauses all running workflows.
        """
        coordinator = coordination.get_coordinator()

        # Only pause workflows if coordination service is enabled
        if not cfg.CONF.coordination.service_registry:
            LOG.warning(
                "Coordination service not enabled. Cannot safely determine if other engines exist. "
                "Pausing all running workflows as a safety measure."
            )
            self._pause_all_running_workflows()
            return

        try:
            with coordinator.get_lock(WORKFLOW_ENGINE_START_STOP_SEQ):
                group_id = coordination.get_group_id(WORKFLOW_ENGINE)
                try:
                    member_ids = list(coordinator.get_members(group_id).get())
                except GroupNotCreated:
                    member_ids = []

                # Check if there are other workflow engines still running
                # Note: member_ids includes this engine, so we check for <= 1
                if not member_ids or len(member_ids) <= 1:
                    LOG.info(
                        "This appears to be the last workflow engine. Pausing running workflows."
                    )
                    self._pause_all_running_workflows()
                else:
                    LOG.info(
                        "Other workflow engines detected (%d members). "
                        "Skipping workflow pause on this instance.",
                        len(member_ids),
                    )
        except Exception as e:
            LOG.error(
                "Error checking for other workflow engines: %s. "
                "Pausing workflows as a safety measure.",
                e,
                exc_info=True,
            )
            self._pause_all_running_workflows()

    def _pause_all_running_workflows(self):
        """
        Pause all running workflows by setting them to PAUSED state.
        """
        ac_ex_dbs = self._get_running_workflows()
        paused_count = 0

        for ac_ex_db in ac_ex_dbs:
            try:
                lv_ac = action_utils.get_liveaction_by_id(ac_ex_db.liveaction_id)
                # Directly set to "paused" instead of "pausing" since RabbitMQ is down
                # and action runners won't be able to complete the transition
                lv_ac.context["paused_by"] = WORKFLOW_ENGINE_START_STOP_SEQ
                action_utils.update_liveaction_status(
                    liveaction_id=str(lv_ac.id),
                    status=ac_const.LIVEACTION_STATUS_PAUSED,
                    context=lv_ac.context,
                    publish=False,  # Don't publish since RabbitMQ is down
                )

                # Also update the ActionExecution directly since we're not publishing
                # This ensures the execution status is consistent with the liveaction
                ac_ex_db.status = ac_const.LIVEACTION_STATUS_PAUSED
                # is this now using rabbitmq?
                # yes. this needs to do a direct update not a publish.
                ex_db_access.ActionExecution.add_or_update(ac_ex_db, publish=False)

                # Update the WorkflowExecution status and conductor state to paused
                # This ensures that auto-resume logic can correctly identify paused workflows
                wf_ex_id = ac_ex_db.context.get("workflow_execution")
                if wf_ex_id:
                    wf_ex_db = wf_db_access.WorkflowExecution.get_by_id(wf_ex_id)
                    if wf_ex_db.status != ac_const.LIVEACTION_STATUS_PAUSED:
                        # Deserialize the conductor to update its internal state
                        conductor = wf_svc.deserialize_conductor(wf_ex_db)
                        # Request the conductor to transition to PAUSED status
                        conductor.request_workflow_status(statuses.PAUSED)
                        # Update both DB status and workflow state from conductor
                        wf_ex_db.status = conductor.get_workflow_status()
                        wf_ex_db.state = conductor.workflow_state.serialize()
                        wf_db_access.WorkflowExecution.update(wf_ex_db, publish=False)
                        LOG.debug(
                            'Updated WorkflowExecution "%s" status and state to paused.',
                            wf_ex_id,
                        )

                paused_count += 1
                LOG.info(
                    'Paused workflow execution "%s" due to engine shutdown.',
                    str(ac_ex_db.id),
                )
            except Exception as e:
                LOG.error(
                    "Failed to pause workflow %s: %s",
                    str(ac_ex_db.id),
                    str(e),
                    exc_info=True,
                )

        LOG.info(
            "Paused %d running workflow(s) due to engine shutdown.",
            paused_count,
        )

    def process(self, message):
        handler_function = self.message_types.get(type(message), None)

        if not handler_function:
            msg = 'Handler function for message type "%s" is not defined.' % type(
                message
            )
            raise ValueError(msg)

        try:
            with self._semaphore:
                self._active_messages += 1
            handler_function(message)
        except Exception as e:
            # If the exception is caused by DB connection error, then the following
            # error handling routine will fail as well because it will try to update
            # the database and fail the workflow execution gracefully. In this case,
            # the garbage collector will find and cancel these workflow executions.
            LOG.error(e, exc_info=True)
            self.fail_workflow_execution(message, e)
        finally:
            with self._semaphore:
                self._active_messages -= 1

    def start(self, wait):
        spawn_after(self._delay, self._resume_workflows_paused_during_shutdown)
        super(WorkflowExecutionHandler, self).start(wait=wait)

    def shutdown(self):
        super(WorkflowExecutionHandler, self).shutdown()
        exit_timeout = cfg.CONF.workflow_engine.exit_still_active_check
        sleep_delay = cfg.CONF.workflow_engine.still_active_check_interval
        timeout = 0

        while timeout < exit_timeout and self._active_messages > 0:
            concurrency.sleep(sleep_delay)
            timeout += sleep_delay

        # Pause workflows if this is the last engine
        self._pause_running_workflows_on_connection_loss()

    def _get_running_workflows(self):
        query_filters = {
            "runner__name": "orquesta",
            "status": ac_const.LIVEACTION_STATUS_RUNNING,
        }
        return ex_db_access.ActionExecution.query(**query_filters)

    def _get_workflows_paused_during_shutdown(self):
        query_filters = {
            "status": ac_const.LIVEACTION_STATUS_PAUSED,
            "context__paused_by": WORKFLOW_ENGINE_START_STOP_SEQ,
        }
        return lv_db_access.LiveAction.query(**query_filters)

    def _sync_completed_tasks_to_conductor(self, wf_ex_id):
        """
        Synchronize task executions from database to conductor state.

        This handles two scenarios:
        1. Completed tasks: Sync their completion to conductor state
        2. Running tasks: Re-stage them so get_next_tasks() can find them

        This is needed when tasks complete or are running during shutdown but the
        conductor state wasn't updated. Without this, the conductor may think tasks
        are still running when they're done, or may not identify running tasks as
        next tasks to execute.
        """
        from orquesta import events, statuses

        LOG.debug("Starting task synchronization for workflow execution %s", wf_ex_id)

        wf_ex_db = wf_db_access.WorkflowExecution.get_by_id(wf_ex_id)
        conductor = wf_svc.deserialize_conductor(wf_ex_db)

        # Query all task executions for this workflow
        task_ex_dbs = wf_db_access.TaskExecution.query(workflow_execution=wf_ex_id)

        LOG.debug(
            "Found %d task execution(s) for workflow %s", len(task_ex_dbs), wf_ex_id
        )

        updated = False
        restaged_count = 0

        for task_ex_db in task_ex_dbs:
            # Handle completed tasks
            if task_ex_db.status in statuses.COMPLETED_STATUSES:
                # Check if conductor has this task in non-completed state
                task_state = conductor.get_task_state_entry(
                    task_ex_db.task_id, task_ex_db.task_route
                )
                if (
                    task_state
                    and task_state.get("status") not in statuses.COMPLETED_STATUSES
                ):
                    # Update conductor with the completion
                    ac_ex_event = events.ActionExecutionEvent(
                        task_ex_db.status, result=task_ex_db.result
                    )
                    conductor.update_task_state(
                        task_ex_db.task_id, task_ex_db.task_route, ac_ex_event
                    )
                    updated = True
                    LOG.debug(
                        'Synchronized completed task "%s" (status: %s) to conductor state',
                        task_ex_db.task_id,
                        task_ex_db.status,
                    )

            # Handle running tasks - need to re-stage them
            elif task_ex_db.status == statuses.RUNNING:
                # Check if task is already staged
                staged_task = conductor.workflow_state.get_staged_task(
                    task_ex_db.task_id, task_ex_db.task_route
                )

                if not staged_task:
                    # Task is running but not staged - re-stage it
                    task_state = conductor.get_task_state_entry(
                        task_ex_db.task_id, task_ex_db.task_route
                    )

                    if task_state:
                        # Re-stage using context from task state
                        # ctxs should be a list of context indices, extract from task_state
                        ctxs_in = task_state.get("ctxs", {}).get("in", [0])
                        conductor.workflow_state.add_staged_task(
                            task_ex_db.task_id,
                            task_ex_db.task_route,
                            ctxs=ctxs_in,
                            prev=task_state.get("prev", {}),
                            ready=True,
                        )
                        updated = True
                        restaged_count += 1
                        LOG.debug(
                            'Re-staged running task "%s" (route: %s) to conductor',
                            task_ex_db.task_id,
                            task_ex_db.task_route,
                        )
                    else:
                        LOG.warning(
                            'Cannot re-stage task "%s" - no task state entry found',
                            task_ex_db.task_id,
                        )

        # If we updated the conductor, save it back to the database
        if updated:
            wf_ex_db.state = conductor.workflow_state.serialize()
            wf_db_access.WorkflowExecution.update(wf_ex_db, publish=False)

            completed_count = len(
                [t for t in task_ex_dbs if t.status in statuses.COMPLETED_STATUSES]
            )
            if completed_count > 0:
                LOG.info(
                    'Synchronized %d completed task(s) to conductor for workflow "%s"',
                    completed_count,
                    wf_ex_id,
                )
            if restaged_count > 0:
                LOG.info(
                    'Re-staged %d running task(s) to conductor for workflow "%s"',
                    restaged_count,
                    wf_ex_id,
                )
        else:
            LOG.debug(
                "No tasks needed synchronization for workflow %s (all tasks already in sync)",
                wf_ex_id,
            )

    def _resume_workflows_paused_during_shutdown(self):
        """
        Resume workflows that were paused during engine shutdown.

        This method includes health checks to ensure the system is stable before
        automatically resuming workflows. This prevents resume loops when critical
        services are unavailable.

        Auto-resume behavior matrix:
        | Scenario         | RabbitMQ | Database | Auto-Resume? |
        |------------------|----------|----------|--------------|
        | Normal restart   | ✅ Up    | ✅ Up    | ✅ Yes       |
        | RabbitMQ down    | ❌ Down  | ✅ Up    | ❌ No        |
        | Database down    | ✅ Up    | ❌ Down  | ❌ No        |
        | Both down        | ❌ Down  | ❌ Down  | ❌ No        |

        Workflows that fail auto-resume remain paused and can be manually resumed
        using: st2 execution resume <execution-id>
        """
        coordinator = coordination.get_coordinator()

        # Only resume workflows if coordination service is enabled
        if not cfg.CONF.coordination.service_registry:
            LOG.warning(
                "Coordination service not enabled. Cannot safely determine if this is the first engine. "
                "Skipping automatic workflow resume. Workflows can be manually resumed if needed."
            )
            return

        # Check system health before attempting to resume workflows
        if not self._check_system_health():
            LOG.warning(
                "System health check failed. Skipping automatic workflow resume. "
                "Workflows remain paused and can be manually resumed once system is healthy."
            )
            return

        with coordinator.get_lock(WORKFLOW_ENGINE_START_STOP_SEQ):
            group_id = coordination.get_group_id(WORKFLOW_ENGINE)
            try:
                member_ids = list(coordinator.get_members(group_id).get())
            except GroupNotCreated:
                member_ids = []

            # Sort member IDs for deterministic ordering
            member_ids_sorted = sorted(member_ids)

            # Get our own member_id
            our_member_id = coordination.get_member_id()

            # Only resume if we're the first member in the sorted list
            # This prevents race conditions when multiple engines start simultaneously
            if not member_ids_sorted or member_ids_sorted[0] != our_member_id:
                LOG.info(
                    "Not the first workflow engine. Skipping workflow resume. "
                    "(First member: %s, Our member: %s, Total members: %d)",
                    member_ids_sorted[0] if member_ids_sorted else "none",
                    our_member_id,
                    len(member_ids_sorted),
                )
                return

            LOG.info(
                "This is the first workflow engine (member_id: %s). Checking for workflows to resume.",
                our_member_id,
            )
        lv_ac_dbs = self._get_workflows_paused_during_shutdown()
        if lv_ac_dbs:
            LOG.info(
                "System health check passed. Auto-resuming %d paused workflow(s).",
                len(lv_ac_dbs),
            )
        for lv_ac_db in lv_ac_dbs:
            try:
                LOG.debug(
                    "[%s] DEBUG: Starting resume - LiveAction status: %s",
                    str(lv_ac_db.id),
                    lv_ac_db.status,
                )

                # Clear the paused_by marker before resuming
                if "paused_by" in lv_ac_db.context:
                    LOG.debug(
                        "[%s] DEBUG: Clearing paused_by marker from context",
                        str(lv_ac_db.id),
                    )
                    del lv_ac_db.context["paused_by"]
                    lv_ac_db = lv_db_access.LiveAction.add_or_update(
                        lv_ac_db, publish=False
                    )
                    LOG.debug(
                        "[%s] DEBUG: After clearing paused_by - LiveAction status: %s",
                        str(lv_ac_db.id),
                        lv_ac_db.status,
                    )

                # Refresh the ActionExecution to get updated liveaction reference
                ac_ex_db = ex_db_access.ActionExecution.get(
                    liveaction_id=str(lv_ac_db.id)
                )
                LOG.debug(
                    "[%s] DEBUG: ActionExecution before resume: %s",
                    str(ac_ex_db.id),
                    ac_ex_db,
                )

                # Get the WorkflowExecution to sync completed tasks before resuming
                wf_ex_id = ac_ex_db.context.get("workflow_execution")
                LOG.debug(
                    "[%s] DEBUG: Workflow execution ID from context: %s",
                    str(ac_ex_db.id),
                    wf_ex_id or "None",
                )

                if wf_ex_id:
                    # Synchronize any completed tasks to the conductor state
                    # This fixes the issue where tasks completed during shutdown
                    # but the conductor still thinks they are running
                    LOG.debug(
                        "[%s] DEBUG: Calling _sync_completed_tasks_to_conductor for workflow %s",
                        str(ac_ex_db.id),
                        wf_ex_id,
                    )
                    self._sync_completed_tasks_to_conductor(wf_ex_id)
                    LOG.debug(
                        "[%s] DEBUG: Completed _sync_completed_tasks_to_conductor for workflow %s",
                        str(ac_ex_db.id),
                        wf_ex_id,
                    )
                else:
                    LOG.warning(
                        "[%s] No workflow_execution ID found in context. Skipping task synchronization.",
                        str(ac_ex_db.id),
                    )

                # Call workflow-specific resume - this handles everything:
                # - Checks if workflow is in PAUSED status
                # - Identifies next tasks to execute
                # - Updates status to RUNNING (calls ac_svc.request_resume internally)
                # - Publishes workflow for processing
                LOG.debug(
                    "[%s] DEBUG: Calling wf_svc.request_resume()",
                    str(ac_ex_db.id),
                )
                wf_svc.request_resume(ac_ex_db)

                LOG.info(
                    'Successfully resumed workflow execution "%s" after shutdown.',
                    str(ac_ex_db.id),
                )
            except Exception as e:
                LOG.error(
                    "Failed to resume workflow %s: %s",
                    str(lv_ac_db.id),
                    str(e),
                    exc_info=True,
                )

    def _check_system_health(self):
        """
        Check if RabbitMQ and database connections are healthy.

        Returns:
            bool: True if both RabbitMQ and database are healthy, False otherwise.
        """
        # Check RabbitMQ connectivity
        if not self._check_rabbitmq_health():
            return False

        # Check database connectivity
        if not self._check_database_health():
            return False

        return True

    def _check_rabbitmq_health(self):
        """
        Check if RabbitMQ connection is working by creating a test connection.

        Returns:
            bool: True if RabbitMQ is accessible, False otherwise.
        """
        try:
            # Create a fresh connection to test RabbitMQ availability
            # This avoids issues with the stale connection object from the context manager
            with txpt_utils.get_connection() as conn:
                # Try to ensure the connection is established
                conn.ensure_connection(max_retries=1, interval_start=0, interval_step=0)
                LOG.debug("RabbitMQ health check: HEALTHY (test connection successful)")
                return True
        except Exception as e:
            LOG.error("RabbitMQ health check failed: %s", e)
            return False

    def _check_database_health(self):
        """
        Check if database connection is working.

        Returns:
            bool: True if database is accessible, False otherwise.
        """
        try:
            # Simple query to verify DB connectivity
            ex_db_access.ActionExecution.query(limit=1)
            LOG.debug("Database health check: HEALTHY")
            return True
        except Exception as e:
            LOG.error("Database health check failed: %s", e)
            return False

    def fail_workflow_execution(self, message, exception):
        # Prepare attributes based on message type.
        if isinstance(message, wf_db_models.WorkflowExecutionDB):
            msg_type = "workflow"
            wf_ex_db = message
            wf_ex_id = str(wf_ex_db.id)
            task = None
        else:
            msg_type = "task"
            ac_ex_db = message
            wf_ex_id = ac_ex_db.context["orquesta"]["workflow_execution_id"]
            task_ex_id = ac_ex_db.context["orquesta"]["task_execution_id"]
            wf_ex_db = wf_db_access.WorkflowExecution.get_by_id(wf_ex_id)
            task_ex_db = wf_db_access.TaskExecution.get_by_id(task_ex_id)
            task = {"id": task_ex_db.task_id, "route": task_ex_db.task_route}

        # Log the error.
        msg = "Unknown error while processing %s execution. %s: %s"
        wf_svc.update_progress(
            wf_ex_db,
            msg % (msg_type, exception.__class__.__name__, str(exception)),
            severity="error",
        )

        # Fail the task execution so it's marked correctly in the
        # conductor state to allow for task rerun if needed.
        if isinstance(message, ex_db_models.ActionExecutionDB):
            msg = 'Unknown error while processing %s execution. Failing task execution "%s".'
            wf_svc.update_progress(
                wf_ex_db, msg % (msg_type, task_ex_id), severity="error"
            )
            wf_svc.update_task_execution(task_ex_id, ac_const.LIVEACTION_STATUS_FAILED)
            wf_svc.update_task_state(task_ex_id, ac_const.LIVEACTION_STATUS_FAILED)

        # Fail the workflow execution.
        msg = 'Unknown error while processing %s execution. Failing workflow execution "%s".'
        wf_svc.update_progress(wf_ex_db, msg % (msg_type, wf_ex_id), severity="error")
        wf_svc.fail_workflow_execution(wf_ex_id, exception, task=task)

    def handle_workflow_execution(self, wf_ex_db):
        # Request the next set of tasks to execute.
        wf_svc.update_progress(wf_ex_db, "Processing request for workflow execution.")
        wf_svc.request_next_tasks(wf_ex_db)

    def handle_action_execution(self, ac_ex_db):
        # Exit if action execution is not executed under an orquesta workflow.
        if not wf_svc.is_action_execution_under_workflow_context(ac_ex_db):
            return

        # Get related record identifiers.
        wf_ex_id = ac_ex_db.context["orquesta"]["workflow_execution_id"]
        task_ex_id = ac_ex_db.context["orquesta"]["task_execution_id"]

        # Get execution records for logging purposes.
        wf_ex_db = wf_db_access.WorkflowExecution.get_by_id(wf_ex_id)
        task_ex_db = wf_db_access.TaskExecution.get_by_id(task_ex_id)

        msg = 'Action execution "%s" for task "%s" is updated and in "%s" state.' % (
            str(ac_ex_db.id),
            task_ex_db.task_id,
            ac_ex_db.status,
        )
        wf_svc.update_progress(wf_ex_db, msg)

        # Skip if task execution is already in completed state.
        if task_ex_db.status in statuses.COMPLETED_STATUSES:
            msg = (
                'Action execution "%s" for task "%s", route "%s", is not processed '
                'because task execution "%s" is already in completed state "%s".'
                % (
                    str(ac_ex_db.id),
                    task_ex_db.task_id,
                    str(task_ex_db.task_route),
                    str(task_ex_db.id),
                    task_ex_db.status,
                )
            )
            wf_svc.update_progress(wf_ex_db, msg)
            return

        # Process pending request on the action execution.
        if ac_ex_db.status == ac_const.LIVEACTION_STATUS_PENDING:
            wf_svc.handle_action_execution_pending(ac_ex_db)
            return

        # Process pause request on the action execution.
        if ac_ex_db.status == ac_const.LIVEACTION_STATUS_PAUSED:
            wf_svc.handle_action_execution_pause(ac_ex_db)
            return

        # Exit if action execution has not completed yet.
        if ac_ex_db.status not in ac_const.LIVEACTION_COMPLETED_STATES:
            return

        # Check if workflow was paused during shutdown.
        # If so, don't process completion to avoid resuming the workflow.
        wf_ac_ex_db = ex_db_access.ActionExecution.get_by_id(wf_ex_db.action_execution)
        wf_lv_ac_db = lv_db_access.LiveAction.get_by_id(wf_ac_ex_db.liveaction_id)
        if (
            wf_lv_ac_db.status == ac_const.LIVEACTION_STATUS_PAUSED
            and wf_lv_ac_db.context.get("paused_by") == WORKFLOW_ENGINE_START_STOP_SEQ
        ):
            msg = (
                "Workflow execution is paused during shutdown. "
                'Skipping action execution completion processing for task "%s".'
                % task_ex_db.task_id
            )
            wf_svc.update_progress(wf_ex_db, msg)
            return

        # Get the task's liveaction for post-run policies
        lv_ac_db = lv_db_access.LiveAction.get_by_id(ac_ex_db.liveaction_id)

        # Apply post run policies.
        pc_svc.apply_post_run_policies(lv_ac_db)

        # Process completion of the action execution.
        wf_svc.handle_action_execution_completion(ac_ex_db)


def get_engine():
    with txpt_utils.get_connection() as conn:
        return WorkflowExecutionHandler(conn, WORKFLOW_EXECUTION_QUEUES)

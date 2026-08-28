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
import datetime

from oslo_config import cfg

from orquesta import statuses
from tooz.coordination import GroupNotCreated
from tooz.coordination import ToozError
from st2common.services import coordination
from eventlet.semaphore import Semaphore
from eventlet import spawn
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
from st2common.services.workflows import WORKFLOW_ENGINE_START_STOP_SEQ
from st2common.transport import consumers
from st2common.transport import queues
from st2common.transport import utils as txpt_utils
from st2common.util import concurrency
from st2common.util import action_db as action_utils
from st2common.util import date as date_utils

LOG = logging.getLogger(__name__)


WORKFLOW_EXECUTION_QUEUES = [
    queues.WORKFLOW_EXECUTION_WORK_QUEUE,
    queues.WORKFLOW_EXECUTION_RESUME_QUEUE,
    queues.WORKFLOW_ACTION_EXECUTION_UPDATE_QUEUE,
]

WORKFLOW_ENGINE = "workflow_engine"


class WorkflowExecutionHandler(consumers.VariableMessageHandler):
    def __init__(self, connection, queues):
        super(WorkflowExecutionHandler, self).__init__(connection, queues)
        self._active_messages = 0
        self._semaphore = Semaphore()
        self._shutdown = False
        self._bootstrap_thread = None

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

                # Determine whether any *other* workflow engine is still running.
                # We must not rely on the raw member count: during a graceful
                # shutdown the engine deregisters from the coordination group
                # before this check runs (see st2actions.cmd.workflow_engine), so
                # our own member id may already be gone. Excluding our own id makes
                # the decision correct regardless of that ordering -- we only pause
                # when there is genuinely no other engine left to take over.
                our_member_id = coordination.get_member_id()
                other_member_ids = [
                    member_id for member_id in member_ids if member_id != our_member_id
                ]

                if not other_member_ids:
                    LOG.info(
                        "This appears to be the last workflow engine. Pausing running workflows."
                    )
                    self._pause_all_running_workflows()
                else:
                    LOG.info(
                        "Other workflow engines detected (%d other members). "
                        "Skipping workflow pause on this instance.",
                        len(other_member_ids),
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
        if cfg.CONF.workflow_engine.bootstrap_enabled:
            self._bootstrap_thread = spawn(self._run_bootstrap_loop)
        super(WorkflowExecutionHandler, self).start(wait=wait)

    def shutdown(self):
        # Stop the bootstrap loop before the shutdown pause path so a bootstrap
        # pass cannot fire between the drain and
        # _pause_running_workflows_on_connection_loss().
        self._shutdown = True
        if self._bootstrap_thread is not None:
            self._bootstrap_thread.kill()
            self._bootstrap_thread = None
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
        lookback_days = cfg.CONF.workflow_engine.bootstrap_lookback_days
        start_timestamp_gte = date_utils.get_datetime_utc_now() - datetime.timedelta(
            days=lookback_days
        )
        query_filters = {
            "status": ac_const.LIVEACTION_STATUS_PAUSED,
            "context__paused_by": WORKFLOW_ENGINE_START_STOP_SEQ,
            "start_timestamp__gte": start_timestamp_gte,
        }
        return lv_db_access.LiveAction.query(**query_filters)

    def _resume_workflows_paused_during_shutdown(self):
        """
        Resume workflows that were paused during engine shutdown.

        Runs pre-flight checks — coordination enabled, system healthy, this
        instance is the first-elected engine — and then delegates the
        per-execution work to wf_svc.bootstrap_resume_execution.

        Auto-resume behavior matrix:
        | Scenario         | RabbitMQ | Database | Auto-Resume? |
        |------------------|----------|----------|--------------|
        | Normal restart   | up       | up       | yes          |
        | RabbitMQ down    | down     | up       | no           |
        | Database down    | up       | down     | no           |
        | Both down        | down     | down     | no           |
        """
        coordinator = coordination.get_coordinator()

        if not cfg.CONF.coordination.service_registry:
            LOG.warning(
                "Coordination service not enabled. Cannot safely determine if this is the first engine. "
                "Skipping automatic workflow resume. Workflows can be manually resumed if needed."
            )
            return

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

            member_ids_sorted = sorted(member_ids)
            our_member_id = coordination.get_member_id()

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
                wf_svc.bootstrap_resume_execution(lv_ac_db)
            except Exception as e:
                LOG.error(
                    "Failed to bootstrap-resume workflow %s: %s",
                    str(lv_ac_db.id),
                    str(e),
                    exc_info=True,
                )

    def _run_bootstrap_loop(self):
        """Bootstrap loop: run every bootstrap_interval seconds for up to
        bootstrap_duration seconds, then exit. Survives transient DB and
        coordination errors; any other exception kills the greenthread so
        real bugs surface."""
        import pymongo

        interval = cfg.CONF.workflow_engine.bootstrap_interval
        duration = cfg.CONF.workflow_engine.bootstrap_duration
        deadline = date_utils.get_datetime_utc_now() + datetime.timedelta(
            seconds=duration
        )
        LOG.info(
            "Workflow bootstrap loop started; interval=%ds, duration=%ds",
            interval,
            duration,
        )
        while not self._shutdown and date_utils.get_datetime_utc_now() < deadline:
            concurrency.sleep(interval)
            if self._shutdown or date_utils.get_datetime_utc_now() >= deadline:
                break
            try:
                self._resume_workflows_paused_during_shutdown()
            except (pymongo.errors.PyMongoError, ToozError):
                LOG.exception("Bootstrap pass failed; will retry next interval.")
        LOG.info("Workflow bootstrap loop exiting.")

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

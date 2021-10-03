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

from orquesta import statuses

from st2common.constants import action as ac_const
from st2common import log as logging
from st2common.metrics import base as metrics
from st2common.models.db import execution as ex_db_models
from st2common.models.db import workflow as wf_db_models
from st2common.persistence import liveaction as lv_db_access
from st2common.persistence import workflow as wf_db_access
from st2common.services import policies as pc_svc
from st2common.services import workflows as wf_svc
from st2common.transport import consumers
from st2common.transport import queues
from st2common.transport import utils as txpt_utils


LOG = logging.getLogger(__name__)


WORKFLOW_EXECUTION_QUEUES = [
    queues.WORKFLOW_EXECUTION_WORK_QUEUE,
    queues.WORKFLOW_EXECUTION_RESUME_QUEUE,
    queues.WORKFLOW_ACTION_EXECUTION_UPDATE_QUEUE,
]


class WorkflowExecutionHandler(consumers.VariableMessageHandler):
    def __init__(self, connection, queues):
        super(WorkflowExecutionHandler, self).__init__(connection, queues)

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

    def get_queue_consumer(self, connection, queues):
        # We want to use a special ActionsQueueConsumer which uses 2 dispatcher pools
        return consumers.VariableMessageQueueConsumer(
            connection=connection, queues=queues, handler=self
        )

    def process(self, message):
        handler_function = self.message_types.get(type(message), None)

        if not handler_function:
            msg = 'Handler function for message type "%s" is not defined.' % type(
                message
            )
            raise ValueError(msg)

        try:
            handler_function(message)
        except Exception as e:
            # If the exception is caused by DB connection error, then the following
            # error handling routine will fail as well because it will try to update
            # the database and fail the workflow execution gracefully. In this case,
            # the garbage collector will find and cancel these workflow executions.
            self.fail_workflow_execution(message, e)

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

        # Apply post run policies.
        lv_ac_db = lv_db_access.LiveAction.get_by_id(ac_ex_db.liveaction["id"])
        pc_svc.apply_post_run_policies(lv_ac_db)

        # Process completion of the action execution.
        wf_svc.handle_action_execution_completion(ac_ex_db)


def get_engine():
    with txpt_utils.get_connection() as conn:
        return WorkflowExecutionHandler(conn, WORKFLOW_EXECUTION_QUEUES)

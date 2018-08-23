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

import kombu

from orquesta import events
from orquesta import states

from st2common.constants import action as ac_const
from st2common import log as logging
from st2common.models.db import execution as ex_db_models
from st2common.models.db import workflow as wf_db_models
from st2common.persistence import liveaction as lv_db_access
from st2common.persistence import workflow as wf_db_access
from st2common.services import policies as pc_svc
from st2common.services import workflows as wf_svc
from st2common.transport import consumers
from st2common.transport import queues
from st2common.transport import utils as txpt_utils
from st2common.metrics.base import CounterWithTimer


LOG = logging.getLogger(__name__)


WORKFLOW_EXECUTION_QUEUES = [
    queues.WORKFLOW_EXECUTION_WORK_QUEUE,
    queues.WORKFLOW_EXECUTION_RESUME_QUEUE,
    queues.WORKFLOW_ACTION_EXECUTION_UPDATE_QUEUE
]


class WorkflowExecutionHandler(consumers.VariableMessageHandler):

    def __init__(self, connection, queues):
        super(WorkflowExecutionHandler, self).__init__(connection, queues)

        def handle_workflow_execution_with_instrumentation(self, wf_ex_db):
            with CounterWithTimer(key='orquesta.workflow.executions'):
                return self.handle_workflow_execution(wf_ex_db=wf_ex_db)

        def handle_action_execution_with_instrumentation(self, ac_ex_db):
            with CounterWithTimer(key='orquesta.action.executions'):
                return self.handle_action_execution(ac_ex_db=ac_ex_db)

        self.message_types = {
            wf_db_models.WorkflowExecutionDB: handle_workflow_execution_with_instrumentation,
            ex_db_models.ActionExecutionDB: handle_action_execution_with_instrumentation
        }

    def get_queue_consumer(self, connection, queues):
        # We want to use a special ActionsQueueConsumer which uses 2 dispatcher pools
        return consumers.VariableMessageQueueConsumer(
            connection=connection,
            queues=queues,
            handler=self
        )

    def process(self, message):
        handler_function = self.message_types.get(type(message))
        handler_function(message)

    def handle_workflow_execution(self, wf_ex_db):
        iteration = 0
        wf_ac_ex_id = wf_ex_db.action_execution
        LOG.info('[%s] Processing request for workflow execution.', wf_ac_ex_id)

        # Refresh record from the database in case the request is in the queue for too long.
        conductor, wf_ex_db = wf_svc.refresh_conductor(str(wf_ex_db.id))

        # Continue if workflow is still active and set workflow to running state.
        if conductor.get_workflow_state() not in states.COMPLETED_STATES:
            LOG.info('[%s] Requesting conductor to start running workflow execution.', wf_ac_ex_id)
            conductor.request_workflow_state(states.RUNNING)

        # Identify the next set of tasks to execute.
        msg = '[%s] Identifying next set (%s) of tasks for workflow execution in state "%s".'
        LOG.info(msg, wf_ac_ex_id, str(iteration), conductor.get_workflow_state())
        LOG.debug('[%s] %s', wf_ac_ex_id, conductor.serialize())
        next_tasks = conductor.get_next_tasks()

        # If there is no new tasks, update execution records to handle possible completion.
        if not next_tasks:
            # Update workflow execution and related liveaction and action execution.
            LOG.info('[%s] No tasks identified to execute next.', wf_ac_ex_id)
            wf_svc.update_execution_records(wf_ex_db, conductor)

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
                ac_ex_event = events.ActionExecutionEvent(states.RUNNING)
                conductor.update_task_flow(task['id'], ac_ex_event)

            # Update workflow execution and related liveaction and action execution.
            wf_svc.update_execution_records(wf_ex_db, conductor)

            # If workflow execution is no longer active, then stop processing here.
            if wf_ex_db.status in states.COMPLETED_STATES:
                msg = '[%s] Workflow execution is in completed state "%s".'
                LOG.info(msg, wf_ac_ex_id, wf_ex_db.status)
                break

            # Request task execution for the tasks.
            for task in next_tasks:
                try:
                    LOG.info('[%s] Requesting execution for task "%s".', wf_ac_ex_id, task['id'])
                    task_id, task_spec, task_ctx = task['id'], task['spec'], task['ctx']
                    st2_ctx = {'execution_id': wf_ex_db.action_execution}
                    wf_svc.request_task_execution(wf_ex_db, task_id, task_spec, task_ctx, st2_ctx)
                except Exception as e:
                    LOG.exception('[%s] Failed task execution for "%s".', wf_ac_ex_id, task['id'])
                    wf_svc.fail_workflow_execution(str(wf_ex_db.id), e, task_id=task['id'])
                    return

            # Identify the next set of tasks to execute.
            iteration += 1
            conductor, wf_ex_db = wf_svc.refresh_conductor(str(wf_ex_db.id))
            msg = '[%s] Identifying next set (%s) of tasks for workflow execution in state "%s".'
            LOG.info(msg, wf_ac_ex_id, str(iteration), conductor.get_workflow_state())
            LOG.debug('[%s] %s', wf_ac_ex_id, conductor.serialize())
            next_tasks = conductor.get_next_tasks()

            if not next_tasks:
                LOG.info('[%s] No tasks identified to execute next.', wf_ac_ex_id)

    def handle_action_execution(self, ac_ex_db):
        # Exit if action execution is not  executed under an orquesta workflow.
        if 'orquesta' not in ac_ex_db.context:
            return

        # Get related record identifiers.
        wf_ex_id = ac_ex_db.context['orquesta']['workflow_execution_id']
        task_ex_id = ac_ex_db.context['orquesta']['task_execution_id']

        # Get execution records for logging purposes.
        wf_ex_db = wf_db_access.WorkflowExecution.get_by_id(wf_ex_id)
        task_ex_db = wf_db_access.TaskExecution.get_by_id(task_ex_id)

        wf_ac_ex_id = wf_ex_db.action_execution
        msg = '[%s] Action execution "%s" for task "%s" is updated and in "%s" state.'
        LOG.info(msg, wf_ac_ex_id, str(ac_ex_db.id), task_ex_db.task_id, ac_ex_db.status)

        # Skip if task execution is already in completed state.
        if task_ex_db.status in states.COMPLETED_STATES:
            LOG.info(
                '[%s] Action execution "%s" for task "%s" is not processed because '
                'task execution "%s" is already in completed state "%s".',
                wf_ac_ex_id,
                str(ac_ex_db.id),
                task_ex_db.task_id,
                str(task_ex_db.id),
                task_ex_db.status
            )

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
        lv_ac_db = lv_db_access.LiveAction.get_by_id(ac_ex_db.liveaction['id'])
        pc_svc.apply_post_run_policies(lv_ac_db)

        # Process completion of the action execution.
        wf_svc.handle_action_execution_completion(ac_ex_db)


def get_engine():
    with kombu.Connection(txpt_utils.get_messaging_urls()) as conn:
        return WorkflowExecutionHandler(conn, WORKFLOW_EXECUTION_QUEUES)

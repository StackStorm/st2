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
import kombu

from orchestra import states

from st2common import log as logging
from st2common.models.db import workflow as wf_db_models
from st2common.persistence import execution as ex_db_access
from st2common.persistence import workflow as wf_db_access
from st2common.services import executions as ex_svc
from st2common.services import workflows as wf_svc
from st2common.transport import consumers
from st2common.transport import queues
from st2common.transport import utils as txpt_utils
from st2common.util import action_db as ac_db_util
from st2common.util import date as date_utils


LOG = logging.getLogger(__name__)


WORKFLOW_EXECUTION_QUEUES = [
    queues.WORKFLOW_EXECUTION_WORK_QUEUE,
    queues.WORKFLOW_EXECUTION_RESUME_QUEUE
]


class WorkflowDispatcher(consumers.MessageHandler):
    message_type = wf_db_models.WorkflowExecutionDB

    def __init__(self, connection, queues):
        super(WorkflowDispatcher, self).__init__(connection, queues)

    def get_queue_consumer(self, connection, queues):
        # We want to use a special ActionsQueueConsumer which uses 2 dispatcher pools
        return consumers.ActionsQueueConsumer(connection=connection, queues=queues, handler=self)

    def process(self, wf_ex_db):
        # Refresh record from the database in case the request is in the queue for too long.
        conductor, wf_ex_db = wf_svc.refresh_conductor(str(wf_ex_db.id))

        # Continue if workflow is still active.
        if conductor.get_workflow_state() not in states.COMPLETED_STATES:
            # Set workflow to running state.
            conductor.set_workflow_state(states.RUNNING)

            # Identify the next set of tasks to execute.
            next_tasks = conductor.get_next_tasks()

            # Mark the tasks as running in the task flow before actual task execution.
            for task in next_tasks:
                conductor.update_task_flow(task['id'], states.RUNNING)

        # Update timestamp and output if workflow is no longer running.
        if conductor.get_workflow_state() in states.COMPLETED_STATES:
            wf_ex_db.end_timestamp = date_utils.get_datetime_utc_now()
            wf_ex_db.output = conductor.get_workflow_output()

        # Write the updated workflow state and task flow to the database.
        wf_ex_db.status = conductor.get_workflow_state()
        wf_ex_db.errors = copy.deepcopy(conductor.errors)
        wf_ex_db.flow = conductor.flow.serialize()
        wf_ex_db = wf_db_access.WorkflowExecution.update(wf_ex_db, publish=False)

        # If workflow execution is no longer active, then update database and stop.
        if wf_ex_db.status in states.COMPLETED_STATES:
            # Update the corresponding liveaction and action execution for the workflow.
            wf_ac_ex_db = ex_db_access.ActionExecution.get_by_id(wf_ex_db.action_execution)
            wf_lv_ac_db = ac_db_util.get_liveaction_by_id(wf_ac_ex_db.liveaction['id'])

            result = {'output': wf_ex_db.output or None}

            if wf_ex_db.status in states.ABENDED_STATES:
                result['errors'] = wf_ex_db.errors

            wf_lv_ac_db = ac_db_util.update_liveaction_status(
                status=wf_ex_db.status,
                result=result,
                end_timestamp=wf_ex_db.end_timestamp,
                liveaction_db=wf_lv_ac_db)

            ex_svc.update_execution(wf_lv_ac_db)

            # stop processing
            return

        # Request task execution for the tasks.
        for task in next_tasks:
            st2_ctx = {'execution_id': wf_ex_db.action_execution}
            wf_svc.request_task_execution(wf_ex_db, task['id'], task['spec'], task['ctx'], st2_ctx)


def get_engine():
    with kombu.Connection(txpt_utils.get_messaging_urls()) as conn:
        return WorkflowDispatcher(conn, WORKFLOW_EXECUTION_QUEUES)

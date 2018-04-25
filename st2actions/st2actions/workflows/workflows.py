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

from orchestra import conducting
from orchestra import states

from st2common import log as logging
from st2common.models.db import workflow as wf_db_models
from st2common.persistence import workflow as wf_db_access
from st2common.services import workflows as wf_svc
from st2common.transport import consumers
from st2common.transport import queues
from st2common.transport import utils as txpt_utils


LOG = logging.getLogger(__name__)


WORKFLOW_EXECUTION_QUEUES = [
    queues.WORKFLOW_EXECUTION_WORK_QUEUE
]


class WorkflowDispatcher(consumers.MessageHandler):
    message_type = wf_db_models.WorkflowExecutionDB

    def __init__(self, connection, queues):
        super(WorkflowDispatcher, self).__init__(connection, queues)

    def get_queue_consumer(self, connection, queues):
        # We want to use a special ActionsQueueConsumer which uses 2 dispatcher pools
        return consumers.ActionsQueueConsumer(connection=connection, queues=queues, handler=self)

    def process(self, wf_ex_db):
        # Instantiate the workflow conductor.
        data = {
            'spec': wf_ex_db.spec,
            'graph': wf_ex_db.graph,
            'state': wf_ex_db.status,
            'flow': wf_ex_db.flow,
            'inputs': wf_ex_db.inputs
        }

        conductor = conducting.WorkflowConductor.deserialize(data)
        conductor.set_workflow_state(states.RUNNING)

        # Identify the list of starting tasks.
        root_tasks = conductor.get_start_tasks()

        # Mark the starting tasks as running in the task flow.
        # The task should be marked before actual task execution.
        for task in root_tasks:
            conductor.update_task_flow_entry(task['id'], states.RUNNING)

        # Write the updated workflow state and task flow to the database.
        wf_ex_db.status = conductor.get_workflow_state()
        wf_ex_db.flow = conductor.flow.serialize()
        wf_ex_db = wf_db_access.WorkflowExecution.update(wf_ex_db, publish=False)

        # Request task execution for the root tasks.
        for task in root_tasks:
            st2_ctx = {'execution_id': wf_ex_db.action_execution}
            wf_svc.request_task_execution(wf_ex_db, task['id'], task['spec'], task['ctx'], st2_ctx)


def get_engine():
    with kombu.Connection(txpt_utils.get_messaging_urls()) as conn:
        return WorkflowDispatcher(conn, WORKFLOW_EXECUTION_QUEUES)

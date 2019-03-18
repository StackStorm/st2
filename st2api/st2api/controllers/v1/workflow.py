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

from six.moves import http_client

from st2common import log as logging
from st2common.models.api.workflow import TaskExecutionAPI
from st2common.persistence.workflow import TaskExecution
from st2common.router import Response

LOG = logging.getLogger(__name__)


class WorkflowExecutionController(object):
    """
    Workflow execution controller.
    """

    model = TaskExecutionAPI
    access = TaskExecution

    def get_all(self, task_id):
        task_ex_dbs = self.access.query(workflow_execution=str(task_id))

        db_iter = [self.model.from_model(task) for task in task_ex_dbs]
        res = Response(json=db_iter, status=http_client.OK)
        return res


workflow_execution_controller = WorkflowExecutionController()

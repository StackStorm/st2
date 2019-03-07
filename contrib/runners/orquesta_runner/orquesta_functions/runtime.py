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

import logging

from orquesta import constants
from orquesta import exceptions as exc
from orquesta.expressions.functions import workflow as workflow_functions

from st2common.persistence import workflow as wf_db_access


LOG = logging.getLogger(__name__)


def format_task_result(instances):
    # Sort the instances by ascending start_timestamp and get the latest instance.
    instances = sorted(instances, key=lambda x: x.start_timestamp)
    instance = instances[-1]

    return {
        'task_execution_id': str(instance.id),
        'workflow_execution_id': instance.workflow_execution,
        'task_name': instance.task_id,
        'task_id': instance.task_id,
        'route': instance.task_route,
        'result': instance.result,
        'status': instance.status,
        'start_timestamp': str(instance.start_timestamp),
        'end_timestamp': str(instance.end_timestamp)
    }


def task(context, task_id=None, route=None):
    instances = None

    try:
        current_task = workflow_functions._get_current_task(context)
    except:
        current_task = {}

    if task_id is None:
        task_id = current_task['id']

    if route is None:
        route = current_task.get('route', 0)

    try:
        task_flow = context['__flow'] or {}
    except KeyError:
        task_flow = {}

    task_flow_pointers = task_flow.get('tasks') or {}
    task_flow_task_uid = constants.TASK_FLOW_ROUTE_FORMAT % (task_id, str(route))
    task_flow_item_idx = task_flow_pointers.get(task_flow_task_uid)

    # If unable to identify the task flow entry and if there are other routes, then
    # use an earlier route before the split to find the specific task.
    if task_flow_item_idx is None:
        if route > 0:
            current_route_details = task_flow['routes'][route]
            # Reverse the list because we want to start with the next longest route.
            for idx, prev_route_details in enumerate(reversed(task_flow['routes'][:route])):
                if len(set(prev_route_details) - set(current_route_details)) == 0:
                    # The index is from a reversed list so need to calculate
                    # the index of the item in the list before the reverse.
                    prev_route = route - idx - 1
                    return task(context, task_id=task_id, route=prev_route)
    else:
        # Otherwise, get the task flow entry and use the
        # task id and route to query the database.
        task_flow_seqs = task_flow.get('sequence') or []
        task_flow_item = task_flow_seqs[task_flow_item_idx]
        route = task_flow_item['route']
        st2_ctx = context['__vars']['st2']
        workflow_execution_id = st2_ctx['workflow_execution_id']

        # Query the database by the workflow execution ID, task ID, and task route.
        instances = wf_db_access.TaskExecution.query(
            workflow_execution=workflow_execution_id,
            task_id=task_id,
            task_route=route
        )

    if not instances:
        message = 'Unable to find task execution for "%s".' % task_id
        raise exc.ExpressionEvaluationException(message)

    return format_task_result(instances)

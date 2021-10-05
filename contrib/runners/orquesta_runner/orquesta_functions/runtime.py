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
        "task_execution_id": str(instance.id),
        "workflow_execution_id": instance.workflow_execution,
        "task_name": instance.task_id,
        "task_id": instance.task_id,
        "route": instance.task_route,
        "result": instance.result,
        "status": instance.status,
        "start_timestamp": str(instance.start_timestamp),
        "end_timestamp": str(instance.end_timestamp),
    }


def task(context, task_id=None, route=None):
    instances = None

    try:
        current_task = workflow_functions._get_current_task(context)
    except:
        current_task = {}

    if task_id is None:
        task_id = current_task["id"]

    if route is None:
        route = current_task.get("route", 0)

    try:
        workflow_state = context["__state"] or {}
    except KeyError:
        workflow_state = {}

    task_state_pointers = workflow_state.get("tasks") or {}
    task_state_entry_uid = constants.TASK_STATE_ROUTE_FORMAT % (task_id, str(route))
    task_state_entry_idx = task_state_pointers.get(task_state_entry_uid)

    # If unable to identify the task flow entry and if there are other routes, then
    # use an earlier route before the split to find the specific task.
    if task_state_entry_idx is None:
        if route > 0:
            current_route_details = workflow_state["routes"][route]
            # Reverse the list because we want to start with the next longest route.
            for idx, prev_route_details in enumerate(
                reversed(workflow_state["routes"][:route])
            ):
                if len(set(prev_route_details) - set(current_route_details)) == 0:
                    # The index is from a reversed list so need to calculate
                    # the index of the item in the list before the reverse.
                    prev_route = route - idx - 1
                    return task(context, task_id=task_id, route=prev_route)
    else:
        # Otherwise, get the task flow entry and use the
        # task id and route to query the database.
        task_state_seqs = workflow_state.get("sequence") or []
        task_state_entry = task_state_seqs[task_state_entry_idx]
        route = task_state_entry["route"]
        st2_ctx = context["__vars"]["st2"]
        workflow_execution_id = st2_ctx["workflow_execution_id"]

        # Query the database by the workflow execution ID, task ID, and task route.
        instances = wf_db_access.TaskExecution.query(
            workflow_execution=workflow_execution_id, task_id=task_id, task_route=route
        )

    if not instances:
        message = 'Unable to find task execution for "%s".' % task_id
        raise exc.ExpressionEvaluationException(message)

    return format_task_result(instances)

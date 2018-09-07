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
        'task_name': instance.task_name,
        'task_id': instance.task_id,
        'result': instance.result,
        'status': instance.status,
        'start_timestamp': str(instance.start_timestamp),
        'end_timestamp': str(instance.end_timestamp)
    }


def task(context, task_name=None, task_id=None):
    instances = None
    st2_ctx = context['__vars']['st2']
    workflow_execution_id = st2_ctx['workflow_execution_id']

    try:
        current_task = workflow_functions._get_current_task(context)
    except:
        current_task = None

    def parse_path_id(task_name, task_id):
        return task_id[len(task_name):] if task_id.startswith(task_name) else ''

    # First try using task name as task id.
    if task_name:
        query_filters = {'workflow_execution': workflow_execution_id, 'task_id': task_name}
        instances = wf_db_access.TaskExecution.query(**query_filters)

    # Default to current task if task name is not provided.
    if not instances and current_task and not task_name:
        task_id = current_task['id']
        query_filters = {'workflow_execution': workflow_execution_id, 'task_id': task_id}
        instances = wf_db_access.TaskExecution.query(**query_filters)

    # Try to query next with task name and path id.
    if not instances and current_task:
        current_task_path = parse_path_id(current_task['name'], current_task['id'])
        task_id = task_name + current_task_path
        query_filters = {'workflow_execution': workflow_execution_id, 'task_id': task_id}
        instances = wf_db_access.TaskExecution.query(**query_filters)

    # If there is no match, try with just task name.
    if not instances and task_name:
        query_filters = {'workflow_execution': workflow_execution_id, 'task_name': task_name}
        instances = wf_db_access.TaskExecution.query(**query_filters)

    if not instances:
        message = 'Unable to find task execution for "%s".' % task_name
        raise exc.ExpressionEvaluationException(message)

    # Sort the instances by ascending start_timestamp and get the latest instance.
    instances = sorted(instances, key=lambda x: x.start_timestamp)
    instance = instances[-1]

    return {
        'task_execution_id': str(instance.id),
        'workflow_execution_id': instance.workflow_execution,
        'task_name': instance.task_name,
        'task_id': instance.task_id,
        'result': instance.result,
        'status': instance.status,
        'start_timestamp': str(instance.start_timestamp),
        'end_timestamp': str(instance.end_timestamp)
    }

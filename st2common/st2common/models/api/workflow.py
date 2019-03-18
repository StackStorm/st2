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

import six

from orquesta import statuses

from st2common.models.api.base import BaseAPI
from st2common.models.db.workflow import TaskExecutionDB
from st2common.util import isotime

__all__ = [
    'TaskExecutionAPI'
]


class TaskExecutionAPI(BaseAPI):
    """The system entity that represents the task execution in the system.
    """

    model = TaskExecutionDB
    schema = {
        "title": "taskexecution",
        "description": "A task execution of an action.",
        "type": "object",
        "properties": {
            "id": {
                "type": "string",
                "required": True
            },
            "workflow_execution": {
                "description": "The unique identifier for the workflow execution.",
                "type": "string"
            },
            "task_name": {
                "description": "The current task name of the task execution.",
                "type": "string"
            },
            "task_id": {
                "description": "The current task id of the task execution.",
                "type": "string"
            },
            "task_route": {
                "description": "The current task routing value.",
                "type": "integer"
            },
            'task_spec': {
                "description": "The current task specification.",
                'type': 'object',
                'default': {}
            },
            "delay": {
                "description": ("How long (in milliseconds) to delay the execution before"
                                "scheduling."),
                "type": "integer"
            },
            "itemized": {
                "type": "boolean",
                "default": False
            },
            "items_count": {
                "description": "The current task items count value.",
                "type": "integer"
            },
            "items_concurrency": {
                "description": "The current task items concurrency.",
                "type": "integer"
            },
            "context": {
                "description": "The current task context.",
                "type": "object",
                "default": False
            },
            "status": {
                "description": "The current status of the task execution.",
                "type": "string"
            },
            "result": {
                "description": "The current task execution result.",
                'type': 'object',
                'default': {}
            },
            "start_timestamp": {
                "description": "The start time when the task is executed.",
                "type": "string",
                "pattern": isotime.ISO8601_UTC_REGEX
            },
            "end_timestamp": {
                "description": "The timestamp when the task has finished.",
                "type": "string",
                "pattern": isotime.ISO8601_UTC_REGEX
            },
            "log": {
                "description": "Contains information about execution state transitions.",
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "timestamp": {
                            "type": "string",
                            "pattern": isotime.ISO8601_UTC_REGEX},
                        "status": {
                            "type": "string",
                            "enum": statuses
                        }
                    }
                }
            },
            "additionalProperties": False
        }
    }

    @classmethod
    def from_model(cls, model, mask_secrets=True):
        doc = cls._from_model(model, mask_secrets=mask_secrets)
        if model.start_timestamp:
            doc['start_timestamp'] = isotime.format(model.start_timestamp, offset=False)
        if model.end_timestamp:
            doc['end_timestamp'] = isotime.format(model.end_timestamp, offset=False)

        for entry in doc.get('log', []):
            entry['timestamp'] = isotime.format(entry['timestamp'], offset=False)

        attrs = {attr: value for attr, value in six.iteritems(doc) if value is not None}
        return cls(**attrs)

    @classmethod
    def to_model(cls, task_execution):
        if getattr(task_execution, 'start_timestamp', None):
            start_timestamp = isotime.parse(task_execution.start_timestamp)
        else:
            start_timestamp = None

        if getattr(task_execution, 'end_timestamp', None):
            end_timestamp = isotime.parse(task_execution.end_timestamp)
        else:
            end_timestamp = None

        workflow_execution = getattr(task_execution, 'workflow_execution', None)
        task_name = getattr(task_execution, 'task_name', None)
        task_id = getattr(task_execution, 'task_id', None)
        status = getattr(task_execution, 'status', None)
        result = getattr(task_execution, 'result', None)
        log = getattr(task_execution, 'log', [])

        model = cls.model(workflow_execution=workflow_execution, task_name=task_name,
                          task_id=task_id, status=status, result=result,
                          start_timestamp=start_timestamp, end_timestamp=end_timestamp, log=log)

        return model

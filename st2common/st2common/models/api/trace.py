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

from st2common.util import isotime
from st2common.models.api.base import BaseAPI
from st2common.models.db.trace import TraceDB, TraceComponentDB


TraceComponentAPISchema = {
    'type': 'object',
    'properties': {
        'object_id': {
            'type': 'string',
            'description': 'Message to use for notification',
            'required': True
        },
        'updated_at': {
            'description': 'The start time when the action is executed.',
            'type': 'string',
            'pattern': isotime.ISO8601_UTC_REGEX
        }
    },
    'additionalProperties': False
}


class TraceAPI(BaseAPI):
    model = TraceDB
    schema = {
        'title': 'Trace',
        'desciption': 'Trace is a collection of all TriggerInstances, Rules and ActionExecutions \
                       that represent an activity which begins with the introduction of a \
                       TriggerInstance or request of an ActionExecution and ends with the \
                       completion of an ActionExecution.',
        'type': 'object',
        'properties': {
            'id': {
                'description': 'The unique identifier for a Trace.',
                'type': 'string',
                'default': None
            },
            'trace_id': {
                'description': 'User assigned identifier for each Trace.',
                'type': 'string',
                'required': True
            },
            'action_executions': {
                'description': 'All ActionExecutions belonging to a Trace.',
                'type': 'array',
                'items': TraceComponentAPISchema
            },
            'rules': {
                'description': 'All rules that applied as part of a Trace.',
                'type': 'array',
                'items': TraceComponentAPISchema
            },
            'trigger_instances': {
                'description': 'All TriggerInstances fired during a Trace.',
                'type': 'array',
                'items': TraceComponentAPISchema
            },
            'start_timestamp': {
                'description': 'Timestamp when the Trace is started.',
                'type': 'string',
                'pattern': isotime.ISO8601_UTC_REGEX
            },
        },
        'additionalProperties': False
    }

    @classmethod
    def to_component_model(cls, component):
        values = {
            'object_id': component.object_id
        }
        updated_at = getattr(component, 'updated_at', None)
        if updated_at:
            values['updated_at'] = updated_at
        return TraceComponentDB(**values)

    @classmethod
    def to_model(cls, instance):
        values = {
            'trace_id': instance.trace_id
        }
        action_executions = getattr(instance, 'action_executions', [])
        action_executions = [TraceAPI.to_component_model(component=action_execution)
                             for action_execution in action_executions]
        values['action_executions'] = action_executions

        rules = getattr(instance, 'rules', [])
        rules = [TraceAPI.to_component_model(component=rule) for rule in rules]
        values['rules'] = rules

        trigger_instances = getattr(instance, 'trigger_instances', [])
        trigger_instances = [TraceAPI.to_component_model(component=trigger_instance)
                             for trigger_instance in trigger_instances]
        values['trigger_instances'] = trigger_instances

        start_timestamp = getattr(instance, 'start_timestamp', None)
        if start_timestamp:
            values['start_timestamp'] = isotime.parse(start_timestamp)

        return model(**values)

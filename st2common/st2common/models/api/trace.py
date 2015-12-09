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
            'description': 'Id of the component',
            'required': True
        },
        'ref':  {
            'type': 'string',
            'description': 'ref of the component',
            'required': False
        },
        'updated_at': {
            'description': 'The start time when the action is executed.',
            'type': 'string',
            'pattern': isotime.ISO8601_UTC_REGEX
        },
        'caused_by': {
            'type': 'object',
            'description': 'Component that is the cause or the predecesor.',
            'properties': {
                'id': {
                    'description': 'Id of the causal component.',
                    'type': 'string'
                },
                'type': {
                    'description': 'Type of the causal component.',
                    'type': 'string'
                }
            }
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
            'trace_tag': {
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
            'object_id': component['object_id'],
            'ref': component['ref'],
            'caused_by': component.get('caused_by', {})
        }
        updated_at = component.get('updated_at', None)
        if updated_at:
            values['updated_at'] = isotime.parse(updated_at)
        return TraceComponentDB(**values)

    @classmethod
    def to_model(cls, instance):
        values = {
            'trace_tag': instance.trace_tag
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
        return cls.model(**values)

    @classmethod
    def from_component_model(cls, component_model):
        return {'object_id': component_model.object_id,
                'ref': component_model.ref,
                'updated_at': isotime.format(component_model.updated_at, offset=False),
                'caused_by': component_model.caused_by}

    @classmethod
    def from_model(cls, model, mask_secrets=False):
        instance = cls._from_model(model, mask_secrets=mask_secrets)
        instance['start_timestamp'] = isotime.format(model.start_timestamp, offset=False)
        if model.action_executions:
            instance['action_executions'] = [cls.from_component_model(action_execution)
                                             for action_execution in model.action_executions]
        if model.rules:
            instance['rules'] = [cls.from_component_model(rule) for rule in model.rules]
        if model.trigger_instances:
            instance['trigger_instances'] = [cls.from_component_model(trigger_instance)
                                             for trigger_instance in model.trigger_instances]
        return cls(**instance)


class TraceContext(object):
    """
    Context object that either represents an existing Trace in the system or
    provides sufficient information to start a new Trace. Note that one of id
    or trace must be provided.

    :param id_: Id of an existing Trace. This is unique and must exist in the system
                Optional property.
    :type id_: ``str``

    :param trace_tag: User assigned value which may or may not be unique.
                     Optional property.
    :type trace_tag: ``str``
    """
    def __init__(self, id_=None, trace_tag=None):
        self.id_ = id_
        self.trace_tag = trace_tag

    def __str__(self):
        return '{id_: %s, trace_tag: %s}' % (self.id_, self.trace_tag)

    def __json__(self):
        return vars(self)

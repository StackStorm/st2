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

import jsonschema

from st2common.util import isotime
from st2common.util import schema as util_schema
from st2common import log as logging
from st2common.models.api.base import BaseAPI
from st2common.models.api.tag import TagsHelper
from st2common.models.db.action import (RunnerTypeDB, ActionDB, ActionExecutionDB)
from st2common.models.db.action import ActionExecutionStateDB
from st2common.constants.action import ACTIONEXEC_STATUSES


__all__ = ['ActionAPI',
           'ActionExecutionAPI',
           'RunnerTypeAPI']


LOG = logging.getLogger(__name__)


class RunnerTypeAPI(BaseAPI):
    """
    The representation of an RunnerType in the system. An RunnerType
    has a one-to-one mapping to a particular ActionRunner implementation.
    """
    model = RunnerTypeDB
    schema = {
        "title": "Runner",
        "description": "A handler for a specific type of actions.",
        "type": "object",
        "properties": {
            "id": {
                "description": "The unique identifier for the action runner.",
                "type": "string",
                "default": None
            },
            "name": {
                "description": "The name of the action runner.",
                "type": "string",
                "required": True
            },
            "description": {
                "description": "The description of the action runner.",
                "type": "string"
            },
            "enabled": {
                "description": "Enable or disable the action runner.",
                "type": "boolean",
                "default": True
            },
            "runner_module": {
                "description": "The python module that implements the "
                               "action runner for this type.",
                "type": "string",
                "required": True
            },
            "query_module": {
                "description": "The python module that implements the "
                               "results tracker (querier) for the runner.",
                "type": "string",
                "required": False
            },
            "runner_parameters": {
                "description": "Input parameters for the action runner.",
                "type": "object",
                "patternProperties": {
                    "^\w+$": util_schema.get_draft_schema()
                }
            }
        },
        "additionalProperties": False
    }

    def __init__(self, **kw):
        # Ideally, you should not do that. You should not redefine __init__ to validate and then set
        # default values, instead you should define defaults in schema and use BaseAPI __init__
        # validator to unwrap them. The problem here is that draft schema also contains default
        # values and we don't want them to be unwrapped at the same time. I've tried to remove the
        # default values from draft schema, but, either because of a bug or some weird intention, it
        # has continued to resolve $ref'erenced properties against the initial draft schema, not the
        # modified one
        jsonschema.validate(kw, self.schema, util_schema.get_validator())
        for key, value in kw.items():
            setattr(self, key, value)
        if not hasattr(self, 'runner_parameters'):
            setattr(self, 'runner_parameters', dict())

    @classmethod
    def to_model(cls, runnertype):
        model = super(cls, cls).to_model(runnertype)
        model.enabled = bool(runnertype.enabled)
        model.runner_module = str(runnertype.runner_module)
        if getattr(runnertype, 'query_module', None):
            model.query_module = str(runnertype.query_module)
        model.runner_parameters = getattr(runnertype, 'runner_parameters', dict())
        return model


class ActionAPI(BaseAPI):
    """The system entity that represents a Stack Action/Automation in the system."""

    model = ActionDB
    schema = {
        "title": "Action",
        "description": "An activity that happens as a response to the external event.",
        "type": "object",
        "properties": {
            "id": {
                "description": "The unique identifier for the action.",
                "type": "string"
            },
            "name": {
                "description": "The name of the action.",
                "type": "string",
                "required": True
            },
            "description": {
                "description": "The description of the action.",
                "type": "string"
            },
            "enabled": {
                "description": "Enable or disable the action from invocation.",
                "type": "boolean",
                "default": True
            },
            "runner_type": {
                "description": "The type of runner that executes the action.",
                "type": "string",
                "required": True
            },
            "entry_point": {
                "description": "The entry point for the action.",
                "type": "string",
                "default": ""
            },
            "pack": {
                "description": "The content pack this action belongs to.",
                "type": "string"
            },
            "parameters": {
                "description": "Input parameters for the action.",
                "type": "object",
                "patternProperties": {
                    "^\w+$": util_schema.get_draft_schema()
                },
                "default": {}
            },
            "tags": {
                "description": "User associated metadata assigned to this object.",
                "type": "array",
                "items": {"type": "object"}
            }
        },
        "additionalProperties": False
    }

    def __init__(self, **kw):
        jsonschema.validate(kw, self.schema, util_schema.get_validator())
        for key, value in kw.items():
            setattr(self, key, value)
        if not hasattr(self, 'parameters'):
            setattr(self, 'parameters', dict())
        if not hasattr(self, 'entry_point'):
            setattr(self, 'entry_point', '')

    @classmethod
    def from_model(cls, model):
        action = cls._from_model(model)
        action['runner_type'] = action['runner_type']['name']
        action['tags'] = TagsHelper.from_model(model.tags)
        return cls(**action)

    @classmethod
    def to_model(cls, action):
        model = super(cls, cls).to_model(action)
        model.enabled = bool(action.enabled)
        model.entry_point = str(action.entry_point)
        model.pack = str(action.pack)
        model.runner_type = {'name': str(action.runner_type)}
        model.parameters = getattr(action, 'parameters', dict())
        model.tags = TagsHelper.to_model(getattr(action, 'tags', []))
        return model


class ActionExecutionAPI(BaseAPI):
    """The system entity that represents the execution of a Stack Action/Automation
    in the system.
    """

    model = ActionExecutionDB
    schema = {
        "title": "ActionExecution",
        "description": "An execution of an action.",
        "type": "object",
        "properties": {
            "id": {
                "description": "The unique identifier for the action execution.",
                "type": "string"
            },
            "status": {
                "description": "The current status of the action execution.",
                "enum": ACTIONEXEC_STATUSES
            },
            "start_timestamp": {
                "description": "The start time when the action is executed.",
                "type": "string",
                "pattern": isotime.ISO8601_UTC_REGEX
            },
            "end_timestamp": {
                "description": "The timestamp when the action has finished.",
                "type": "string",
                "pattern": isotime.ISO8601_UTC_REGEX
            },
            "action": {
                "description": "Reference to the action to be executed.",
                "type": "string",
                "required": True
            },
            "parameters": {
                "description": "Input parameters for the action.",
                "type": "object",
                "patternProperties": {
                    "^\w+$": {
                        "anyOf": [
                            {"type": "array"},
                            {"type": "boolean"},
                            {"type": "integer"},
                            {"type": "number"},
                            {"type": "object"},
                            {"type": "string"}
                        ]
                    }
                }
            },
            "result": {
                "anyOf": [{"type": "array"},
                          {"type": "boolean"},
                          {"type": "integer"},
                          {"type": "number"},
                          {"type": "object"},
                          {"type": "string"}]
            },
            "context": {
                "type": "object"
            },
            "callback": {
                "type": "object"
            }
        },
        "additionalProperties": False
    }

    @classmethod
    def from_model(cls, model):
        doc = super(cls, cls)._from_model(model)
        if model.start_timestamp:
            doc['start_timestamp'] = isotime.format(model.start_timestamp, offset=False)
        if model.end_timestamp:
            doc['end_timestamp'] = isotime.format(model.end_timestamp, offset=False)
        return cls(**doc)

    @classmethod
    def to_model(cls, execution):
        model = super(cls, cls).to_model(execution)
        model.action = execution.action

        if getattr(execution, 'start_timestamp', None):
            model.start_timestamp = isotime.parse(execution.start_timestamp)

        if getattr(execution, 'end_timestamp', None):
            model.end_timestamp = isotime.parse(execution.end_timestamp)

        model.status = getattr(execution, 'status', None)
        model.parameters = getattr(execution, 'parameters', dict())
        model.context = getattr(execution, 'context', dict())
        model.callback = getattr(execution, 'callback', dict())
        model.result = getattr(execution, 'result', None)
        return model


class ActionExecutionStateAPI(BaseAPI):
    """
    System entity that represents state of an action in the system.
    This is used only in tests for now.
    """
    model = ActionExecutionStateDB
    schema = {
        "title": "ActionExecutionState",
        "description": "Execution state of an action.",
        "type": "object",
        "properties": {
            "id": {
                "description": "The unique identifier for the action execution state.",
                "type": "string"
            },
            "execution_id": {
                "type": "string",
                "description": "ID of the action execution.",
                "required": True
            },
            "query_context": {
                "type": "object",
                "description": "query context to be used by querier.",
                "required": True
            },
            "query_module": {
                "type": "string",
                "description": "Name of the query module.",
                "required": True
            }
        },
        "additionalProperties": False
    }

    @classmethod
    def to_model(cls, state):
        model = super(cls, cls).to_model(state)
        model.query_module = state.query_module
        model.execution_id = state.execution_id
        model.query_context = state.query_context
        return model

import datetime

import jsonschema

from st2common import util
from st2common import log as logging
from st2common.models.base import BaseAPI
from st2common.models.api.stormbase import (StormFoundationAPI, StormBaseAPI)
from st2common.models.db.action import (RunnerTypeDB, ActionDB, ActionExecutionDB)

__all__ = ['ActionAPI',
           'ActionExecutionAPI',
           'RunnerTypeAPI']


LOG = logging.getLogger(__name__)


class RunnerTypeAPI(BaseAPI):
    """
    The representation of an RunnerType in the system. An RunnerType
    has a one-to-one mapping to a particular ActionRunner implementation.
    """

    schema = {
        "$schema": "http://json-schema.org/draft-04/schema#",
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
                "type": "string"
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
            },
            "runner_parameters": {
                "description": "Input parameters for the action runner.",
                "type": "object",
                "patternProperties": {
                    "^\w+$": util.schema.get_draft_schema()
                }
            },
            "required_parameters": {
                "description": "List of required parameters.",
                "type": "array",
                "items": {
                    "type": "string"
                }
            }
        },
        "required": ["name", "runner_module"],
        "additionalProperties": False
    }

    def __init__(self, **kw):
        jsonschema.validate(kw, self.schema)
        for key, value in kw.items():
            setattr(self, key, value)
        if not hasattr(self, 'runner_parameters'):
            setattr(self, 'runner_parameters', dict())
        if not hasattr(self, 'required_parameters'):
            setattr(self, 'required_parameters', list())

    @classmethod
    def from_model(cls, model):
        runnertype = model.to_mongo()
        runnertype['id'] = str(runnertype['_id'])
        del runnertype['_id']
        return cls(**runnertype)

    @classmethod
    def to_model(cls, runnertype):
        model = StormBaseAPI.to_model(RunnerTypeDB, runnertype)
        model.enabled = bool(runnertype.enabled)
        model.runner_module = str(runnertype.runner_module)
        model.runner_parameters = getattr(runnertype, 'runner_parameters', dict())
        model.required_parameters = getattr(runnertype, 'required_parameters', list())
        return model


class ActionAPI(BaseAPI):
    """The system entity that represents a Stack Action/Automation in the system."""

    schema = {
        "$schema": "http://json-schema.org/draft-04/schema#",
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
                "type": "string"
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
            },
            "entry_point": {
                "description": "The entry point for the action.",
                "type": "string"
            },
            "parameters": {
                "description": "Input parameters for the action.",
                "type": "object",
                "patternProperties": {
                    "^\w+$": util.schema.get_draft_schema()
                }
            },
            "required_parameters": {
                "description": "List of required parameters.",
                "type": "array",
                "items": {
                    "type": "string"
                }
            }
        },
        "required": ["name", "runner_type"],
        "additionalProperties": False
    }

    def __init__(self, **kw):
        jsonschema.validate(kw, self.schema)
        for key, value in kw.items():
            setattr(self, key, value)
        if not hasattr(self, 'parameters'):
            setattr(self, 'parameters', dict())
        if not hasattr(self, 'required_parameters'):
            setattr(self, 'required_parameters', list())

    @classmethod
    def from_model(cls, model):
        action = model.to_mongo()
        action['id'] = str(action['_id'])
        action['runner_type'] = action['runner_type']['name']
        del action['_id']
        return cls(**action)

    @classmethod
    def to_model(cls, action):
        model = StormBaseAPI.to_model(ActionDB, action)
        model.enabled = bool(action.enabled)
        model.entry_point = str(action.entry_point)
        model.runner_type = {'name': str(action.runner_type)}
        model.parameters = getattr(action, 'parameters', dict())
        model.required_parameters = getattr(action, 'required_parameters', list())
        return model


ACTIONEXEC_STATUS_INIT = 'initializing'
ACTIONEXEC_STATUS_SCHEDULED = 'scheduled'
ACTIONEXEC_STATUS_RUNNING = 'running'
ACTIONEXEC_STATUS_COMPLETE = 'complete'
ACTIONEXEC_STATUS_ERROR = 'error'

ACTIONEXEC_STATUSES = [ACTIONEXEC_STATUS_INIT, ACTIONEXEC_STATUS_SCHEDULED,
                       ACTIONEXEC_STATUS_RUNNING, ACTIONEXEC_STATUS_COMPLETE,
                       ACTIONEXEC_STATUS_ERROR]

ACTION_NAME = 'name'
ACTION_ID = 'id'


class ActionExecutionAPI(BaseAPI):
    """The system entity that represents the execution of a Stack Action/Automation
    in the system.
    """

    schema = {
        "$schema": "http://json-schema.org/draft-04/schema#",
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
                "pattern": "^\d{4}-\d{2}-\d{2}[ ]\d{2}:\d{2}:\d{2}.\d{6}$"
            },
            "action": {
                "description": "The action to be executed.",
                "type": "object",
                "properties": {
                    "id": {
                        "description": "The unique identifier for the action.",
                        "type": "string"
                    },
                    "name": {
                        "description": "The name of the action.",
                        "type": "string"
                    }
                }
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
                "type": ["boolean", "integer", "null", "number", "object", "string"]
            },
            "context": {
                "type": "object"
            },
            "callback": {
                "type": "object"
            }
        },
        "required": ["action"],
        "additionalProperties": False
    }

    def __init__(self, **kw):
        start_timestamp = kw.pop('start_timestamp') if 'start_timestamp' in kw else None
        super(ActionExecutionAPI, self).__init__(**kw)
        if start_timestamp and not isinstance(start_timestamp, datetime.datetime):
            start_timestamp = datetime.datetime.strptime(start_timestamp,
                                                         '%Y-%m-%d %H:%M:%S.%f')
        if start_timestamp:
            self.start_timestamp = start_timestamp

    @classmethod
    def from_model(cls, model):
        execution = model.to_mongo()
        execution['id'] = str(execution['_id'])
        del execution['_id']
        result = cls(**execution)
        return result

    @classmethod
    def to_model(cls, execution):
        model = StormFoundationAPI.to_model(ActionExecutionDB, execution)
        model.status = str(execution.status)
        model.start_timestamp = getattr(execution, 'start_timestamp')
        model.action = execution.action
        model.parameters = getattr(execution, 'parameters', dict())
        model.context = getattr(execution, 'context', dict())
        model.callback = getattr(execution, 'callback', dict())
        model.result = getattr(execution, 'result', None)
        return model

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
from st2common.util import schema as util_schema
from st2common import log as logging
from st2common.models.api.base import BaseAPI
from st2common.models.api.tag import TagsHelper
from st2common.models.api.notification import (NotificationSubSchemaAPI, NotificationsHelper)
from st2common.models.db.action import ActionDB
from st2common.models.db.actionalias import ActionAliasDB
from st2common.models.db.executionstate import ActionExecutionStateDB
from st2common.models.db.liveaction import LiveActionDB
from st2common.models.db.runner import RunnerTypeDB
from st2common.constants.action import LIVEACTION_STATUSES
from st2common.models.system.common import ResourceReference


__all__ = ['ActionAPI',
           'LiveActionAPI',
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
            "ref": {
                "description": "System computed user friendly reference for the action. \
                                Provided value will be overridden by computed value.",
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
            },
            "notify": {
                "description": "Notification settings for action.",
                "type": "object",
                "properties": {
                    "on-complete": NotificationSubSchemaAPI,
                    "on-failure": NotificationSubSchemaAPI,
                    "on-success": NotificationSubSchemaAPI
                },
                "additionalProperties": False
            }
        },
        "additionalProperties": False
    }

    def __init__(self, **kw):
        for key, value in kw.items():
            setattr(self, key, value)
        if not hasattr(self, 'parameters'):
            setattr(self, 'parameters', dict())
        if not hasattr(self, 'entry_point'):
            setattr(self, 'entry_point', '')

    @classmethod
    def from_model(cls, model, mask_secrets=False):
        action = cls._from_model(model)
        action['runner_type'] = action['runner_type']['name']
        action['tags'] = TagsHelper.from_model(model.tags)

        if getattr(model, 'notify', None):
            action['notify'] = NotificationsHelper.from_model(model.notify)

        return cls(**action)

    @classmethod
    def to_model(cls, action):
        model = super(cls, cls).to_model(action)
        model.enabled = bool(getattr(action, 'enabled', True))
        model.entry_point = str(action.entry_point)
        model.pack = str(action.pack)
        model.runner_type = {'name': str(action.runner_type)}
        model.parameters = getattr(action, 'parameters', dict())
        model.tags = TagsHelper.to_model(getattr(action, 'tags', []))
        model.ref = ResourceReference.to_string_reference(pack=model.pack, name=model.name)
        if getattr(action, 'notify', None):
            model.notify = NotificationsHelper.to_model(action.notify)

        return model


class LiveActionAPI(BaseAPI):
    """The system entity that represents the execution of a Stack Action/Automation
    in the system.
    """

    model = LiveActionDB
    schema = {
        "title": "liveaction",
        "description": "An execution of an action.",
        "type": "object",
        "properties": {
            "id": {
                "description": "The unique identifier for the action execution.",
                "type": "string"
            },
            "status": {
                "description": "The current status of the action execution.",
                "enum": LIVEACTION_STATUSES
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
            },
            "runner_info": {
                "type": "object"
            },
            "notify": {
                "description": "Notification settings for liveaction.",
                "type": "object",
                "properties": {
                    "on-complete": NotificationSubSchemaAPI,
                    "on-failure": NotificationSubSchemaAPI,
                    "on-success": NotificationSubSchemaAPI
                },
                "additionalProperties": False
            }
        },
        "additionalProperties": False
    }

    @classmethod
    def from_model(cls, model, mask_secrets=False):
        doc = super(cls, cls)._from_model(model, mask_secrets=mask_secrets)
        if model.start_timestamp:
            doc['start_timestamp'] = isotime.format(model.start_timestamp, offset=False)
        if model.end_timestamp:
            doc['end_timestamp'] = isotime.format(model.end_timestamp, offset=False)

        if getattr(model, 'notify', None):
            doc['notify'] = NotificationsHelper.from_model(model.notify)

        return cls(**doc)

    @classmethod
    def to_model(cls, liveaction):
        model = super(cls, cls).to_model(liveaction)
        model.action = liveaction.action

        if getattr(liveaction, 'start_timestamp', None):
            model.start_timestamp = isotime.parse(liveaction.start_timestamp)

        if getattr(liveaction, 'end_timestamp', None):
            model.end_timestamp = isotime.parse(liveaction.end_timestamp)

        model.status = getattr(liveaction, 'status', None)
        model.parameters = getattr(liveaction, 'parameters', dict())
        model.context = getattr(liveaction, 'context', dict())
        model.callback = getattr(liveaction, 'callback', dict())
        model.result = getattr(liveaction, 'result', None)

        if getattr(liveaction, 'notify', None):
            model.notify = NotificationsHelper.to_model(liveaction.notify)

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


class ActionAliasAPI(BaseAPI):
    """
    Alias for an action in the system.
    """
    model = ActionAliasDB
    schema = {
        "title": "ActionAlias",
        "description": "Alias for an action.",
        "type": "object",
        "properties": {
            "id": {
                "description": "The unique identifier for the action alias.",
                "type": "string"
            },
            "ref": {
                "description": "System computed user friendly reference for the alias. \
                                Provided value will be overridden by computed value.",
                "type": "string"
            },
            "name": {
                "type": "string",
                "description": "Name of the action alias.",
                "required": True
            },
            "pack": {
                "description": "The content pack this actionalias belongs to.",
                "type": "string",
                "required": True
            },
            "description": {
                "type": "string",
                "description": "Description of the action alias."
            },
            "enabled": {
                "description": "Flag indicating of action alias is enabled.",
                "type": "boolean",
                "default": True
            },
            "action_ref": {
                "type": "string",
                "description": "Reference to the aliased action.",
                "required": True
            },
            "formats": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Possible parameter format."
            }
        },
        "additionalProperties": False
    }

    @classmethod
    def to_model(cls, alias):
        model = super(cls, cls).to_model(alias)
        model.name = alias.name
        model.pack = alias.pack
        model.enabled = getattr(alias, 'enabled', True)
        model.ref = ResourceReference.to_string_reference(pack=model.pack, name=model.name)
        model.action_ref = alias.action_ref
        model.formats = alias.formats
        return model


class AliasExecutionAPI(BaseAPI):
    """
    Alias for an action in the system.
    """
    model = None
    schema = {
        "title": "AliasExecution",
        "description": "Execution of an ActionAlias.",
        "type": "object",
        "properties": {
            "name": {
                "type": "string",
                "description": "Name of the action alias which matched.",
                "required": True
            },
            "format": {
                "type": "string",
                "description": "Format string which matched.",
                "required": True
            },
            "command": {
                "type": "string",
                "description": "Command used in chat.",
                "required": True
            },
            "user": {
                "type": "string",
                "description": "User that requested the execution.",
                "default": "channel"
            },
            "source_channel": {
                "type": "string",
                "description": "Channel from which the execution was requested. This is not the channel \
                                as defined by the notification system."
            },
            "notification_channel": {
                "type": "string",
                "description": "StackStorm notification channel to use to respond.",
                "required": True
            }
        },
        "additionalProperties": False
    }

    @classmethod
    def to_model(cls, aliasexecution):
        # probably should be unsupported
        raise NotImplementedError()

    @classmethod
    def from_model(cls, aliasexecution):
        raise NotImplementedError()

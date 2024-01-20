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
import copy

from st2common.util import isotime
from st2common.util import schema as util_schema
from st2common import log as logging
from st2common.constants.pack import DEFAULT_PACK_NAME
from st2common.models.api.base import BaseAPI
from st2common.models.api.base import APIUIDMixin
from st2common.models.api.tag import TagsHelper
from st2common.models.api.notification import (
    NotificationSubSchemaAPI,
    NotificationsHelper,
)
from st2common.models.db.action import ActionDB
from st2common.models.db.actionalias import ActionAliasDB
from st2common.models.db.executionstate import ActionExecutionStateDB
from st2common.models.db.liveaction import LiveActionDB
from st2common.models.db.runner import RunnerTypeDB
from st2common.constants.action import LIVEACTION_STATUSES
from st2common.models.system.common import ResourceReference


__all__ = [
    "ActionAPI",
    "ActionCreateAPI",
    "LiveActionAPI",
    "LiveActionCreateAPI",
    "RunnerTypeAPI",
    "AliasExecutionAPI",
    "AliasMatchAndExecuteInputAPI",
    "ActionAliasAPI",
    "ActionAliasMatchAPI",
    "ActionAliasHelpAPI",
]


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
                "default": None,
            },
            "uid": {"type": "string"},
            "name": {
                "description": "The name of the action runner.",
                "type": "string",
                "required": True,
            },
            "description": {
                "description": "The description of the action runner.",
                "type": "string",
            },
            "enabled": {
                "description": "Enable or disable the action runner.",
                "type": "boolean",
                "default": True,
            },
            "runner_package": {
                "description": "The python package that implements the "
                "action runner for this type.",
                "type": "string",
                "required": False,
            },
            "runner_module": {
                "description": "The python module that implements the "
                "action runner for this type.",
                "type": "string",
                "required": True,
            },
            "query_module": {
                "description": "The python module that implements the "
                "results tracker (querier) for the runner.",
                "type": "string",
                "required": False,
            },
            "runner_parameters": {
                "description": "Input parameters for the action runner.",
                "type": "object",
                "patternProperties": {
                    r"^\w+$": util_schema.get_action_parameters_schema()
                },
                "additionalProperties": False,
            },
            "output_key": {
                "description": "Default key to expect results to be published to.",
                "type": "string",
                "required": False,
            },
            "output_schema": util_schema.get_action_output_schema(
                description="Runner Output Schema"
            ),
        },
        "additionalProperties": False,
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
        if not hasattr(self, "runner_parameters"):
            setattr(self, "runner_parameters", dict())

    @classmethod
    def to_model(cls, runner_type):
        name = runner_type.name
        description = runner_type.description
        enabled = getattr(runner_type, "enabled", True)
        runner_package = getattr(
            runner_type, "runner_package", runner_type.runner_module
        )
        runner_module = str(runner_type.runner_module)
        runner_parameters = getattr(runner_type, "runner_parameters", dict())
        output_key = getattr(runner_type, "output_key", None)
        output_schema = getattr(runner_type, "output_schema", dict())
        query_module = getattr(runner_type, "query_module", None)

        model = cls.model(
            name=name,
            description=description,
            enabled=enabled,
            runner_package=runner_package,
            runner_module=runner_module,
            runner_parameters=runner_parameters,
            output_schema=output_schema,
            query_module=query_module,
            output_key=output_key,
        )

        return model


# NOTE: Update pylint_plugins/fixtures/api_models.py if this changes significantly
class ActionAPI(BaseAPI, APIUIDMixin):
    """
    The system entity that represents a Stack Action/Automation in the system.
    """

    model = ActionDB
    schema = {
        "title": "Action",
        "description": "An activity that happens as a response to the external event.",
        "type": "object",
        "properties": {
            "id": {
                "description": "The unique identifier for the action.",
                "type": "string",
            },
            "ref": {
                "description": "System computed user friendly reference for the action. \
                                Provided value will be overridden by computed value.",
                "type": "string",
            },
            "uid": {"type": "string"},
            "name": {
                "description": "The name of the action.",
                "type": "string",
                "required": True,
            },
            "description": {
                "description": "The description of the action.",
                "type": "string",
            },
            "enabled": {
                "description": "Enable or disable the action from invocation.",
                "type": "boolean",
                "default": True,
            },
            "runner_type": {
                "description": "The type of runner that executes the action.",
                "type": "string",
                "required": True,
            },
            "entry_point": {
                "description": "The entry point for the action.",
                "type": "string",
                "default": "",
            },
            "pack": {
                "description": "The content pack this action belongs to.",
                "type": "string",
                "default": DEFAULT_PACK_NAME,
            },
            "parameters": {
                "description": "Input parameters for the action.",
                "type": "object",
                "patternProperties": {
                    r"^\w+$": util_schema.get_action_parameters_schema()
                },
                "additionalProperties": False,
                "default": {},
            },
            "output_schema": util_schema.get_action_output_schema(
                description="Action Output Schema"
            ),
            "tags": {
                "description": "User associated metadata assigned to this object.",
                "type": "array",
                "items": {"type": "object"},
            },
            "notify": {
                "description": "Notification settings for action.",
                "type": "object",
                "properties": {
                    "on-complete": NotificationSubSchemaAPI,
                    "on-failure": NotificationSubSchemaAPI,
                    "on-success": NotificationSubSchemaAPI,
                },
                "additionalProperties": False,
            },
            "metadata_file": {
                "description": "Path to the metadata file relative to the pack directory.",
                "type": "string",
                "default": "",
            },
        },
        "additionalProperties": False,
    }

    def __init__(self, **kw):
        for key, value in kw.items():
            setattr(self, key, value)
        if not hasattr(self, "parameters"):
            setattr(self, "parameters", dict())
        if not hasattr(self, "entry_point"):
            setattr(self, "entry_point", "")

    @classmethod
    def from_model(cls, model, mask_secrets=False):
        action = cls._from_model(model)
        action["runner_type"] = action.get("runner_type", {}).get("name", None)
        action["tags"] = TagsHelper.from_model(model.tags)

        if getattr(model, "notify", None):
            action["notify"] = NotificationsHelper.from_model(model.notify)

        return cls(**action)

    @classmethod
    def to_model(cls, action):
        name = getattr(action, "name", None)
        description = getattr(action, "description", None)
        enabled = bool(getattr(action, "enabled", True))
        entry_point = str(action.entry_point)
        pack = str(action.pack)
        runner_type = {"name": str(action.runner_type)}
        parameters = getattr(action, "parameters", dict())
        output_schema = getattr(action, "output_schema", dict())
        tags = TagsHelper.to_model(getattr(action, "tags", []))
        ref = ResourceReference.to_string_reference(pack=pack, name=name)

        if getattr(action, "notify", None):
            notify = NotificationsHelper.to_model(action.notify)
        else:
            # We use embedded document model for ``notify`` in action model. If notify is
            # set notify to None, Mongoengine interprets ``None`` as unmodified
            # field therefore doesn't delete the embedded document. Therefore, we need
            # to use an empty document.
            notify = NotificationsHelper.to_model({})

        metadata_file = getattr(action, "metadata_file", None)

        model = cls.model(
            name=name,
            description=description,
            enabled=enabled,
            entry_point=entry_point,
            pack=pack,
            runner_type=runner_type,
            tags=tags,
            parameters=parameters,
            output_schema=output_schema,
            notify=notify,
            ref=ref,
            metadata_file=metadata_file,
        )

        return model


class ActionCreateAPI(ActionAPI, APIUIDMixin):
    """
    API model for create action operation.
    """

    schema = copy.deepcopy(ActionAPI.schema)
    schema["properties"]["data_files"] = {
        "description": "Optional action script and data files which are written to the filesystem.",
        "type": "array",
        "items": {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": (
                        "Path to the file relative to the pack actions directory "
                        "(e.g. my_action.py)"
                    ),
                    "required": True,
                },
                "content": {
                    "type": "string",
                    "description": "Raw file content.",
                    "required": True,
                },
            },
            "additionalProperties": False,
        },
        "default": [],
    }


class ActionUpdateAPI(ActionAPI, APIUIDMixin):
    """
    API model for update action operation.
    """

    schema = copy.deepcopy(ActionCreateAPI.schema)
    del schema["properties"]["pack"]["default"]


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
                "type": "string",
            },
            "status": {
                "description": "The current status of the action execution.",
                "type": "string",
                "enum": LIVEACTION_STATUSES,
            },
            "start_timestamp": {
                "description": "The start time when the action is executed.",
                "type": "string",
                "pattern": isotime.ISO8601_UTC_REGEX,
            },
            "end_timestamp": {
                "description": "The timestamp when the action has finished.",
                "type": "string",
                "pattern": isotime.ISO8601_UTC_REGEX,
            },
            "action": {
                "description": "Reference to the action to be executed.",
                "type": "string",
                "required": True,
            },
            "parameters": {
                "description": "Input parameters for the action.",
                "type": "object",
                "patternProperties": {
                    r"^\w+$": {
                        "anyOf": [
                            {"type": "array"},
                            {"type": "boolean"},
                            {"type": "integer"},
                            {"type": "number"},
                            {"type": "object"},
                            {"type": "string"},
                            {"type": "null"},
                        ]
                    }
                },
                "additionalProperties": False,
            },
            "result": {
                "anyOf": [
                    {"type": "array"},
                    {"type": "boolean"},
                    {"type": "integer"},
                    {"type": "number"},
                    {"type": "object"},
                    {"type": "string"},
                ]
            },
            "context": {"type": "object"},
            "callback": {"type": "object"},
            "runner_info": {"type": "object"},
            "notify": {
                "description": "Notification settings for liveaction.",
                "type": "object",
                "properties": {
                    "on-complete": NotificationSubSchemaAPI,
                    "on-failure": NotificationSubSchemaAPI,
                    "on-success": NotificationSubSchemaAPI,
                },
                "additionalProperties": False,
            },
            "delay": {
                "description": (
                    "How long (in milliseconds) to delay the execution before"
                    "scheduling."
                ),
                "type": "integer",
            },
        },
        "additionalProperties": False,
    }
    skip_unescape_field_names = [
        "result",
    ]

    @classmethod
    def from_model(cls, model, mask_secrets=False):
        doc = super(cls, cls)._from_model(model, mask_secrets=mask_secrets)
        if model.start_timestamp:
            doc["start_timestamp"] = isotime.format(model.start_timestamp, offset=False)
        if model.end_timestamp:
            doc["end_timestamp"] = isotime.format(model.end_timestamp, offset=False)

        if getattr(model, "notify", None):
            doc["notify"] = NotificationsHelper.from_model(model.notify)

        return cls(**doc)

    @classmethod
    def to_model(cls, live_action):
        action = live_action.action

        if getattr(live_action, "start_timestamp", None):
            start_timestamp = isotime.parse(live_action.start_timestamp)
        else:
            start_timestamp = None

        if getattr(live_action, "end_timestamp", None):
            end_timestamp = isotime.parse(live_action.end_timestamp)
        else:
            end_timestamp = None

        status = getattr(live_action, "status", None)
        parameters = getattr(live_action, "parameters", dict())
        context = getattr(live_action, "context", dict())
        callback = getattr(live_action, "callback", dict())
        result = getattr(live_action, "result", None)
        delay = getattr(live_action, "delay", None)

        if getattr(live_action, "notify", None):
            notify = NotificationsHelper.to_model(live_action.notify)
        else:
            notify = None

        model = cls.model(
            action=action,
            start_timestamp=start_timestamp,
            end_timestamp=end_timestamp,
            status=status,
            parameters=parameters,
            context=context,
            callback=callback,
            result=result,
            notify=notify,
            delay=delay,
        )

        return model


class LiveActionCreateAPI(LiveActionAPI):
    """
    API model for action execution create (run action) operations.
    """

    schema = copy.deepcopy(LiveActionAPI.schema)
    schema["properties"]["user"] = {
        "description": "User context under which action should run (admins only)",
        "type": "string",
        "default": None,
    }


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
                "type": "string",
            },
            "execution_id": {
                "type": "string",
                "description": "ID of the action execution.",
                "required": True,
            },
            "query_context": {
                "type": "object",
                "description": "query context to be used by querier.",
                "required": True,
            },
            "query_module": {
                "type": "string",
                "description": "Name of the query module.",
                "required": True,
            },
        },
        "additionalProperties": False,
    }

    @classmethod
    def to_model(cls, state):
        execution_id = state.execution_id
        query_module = state.query_module
        query_context = state.query_context

        model = cls.model(
            execution_id=execution_id,
            query_module=query_module,
            query_context=query_context,
        )
        return model


class ActionAliasAPI(BaseAPI, APIUIDMixin):
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
                "type": "string",
            },
            "ref": {
                "description": (
                    "System computed user friendly reference for the alias. "
                    "Provided value will be overridden by computed value."
                ),
                "type": "string",
            },
            "uid": {"type": "string"},
            "name": {
                "type": "string",
                "description": "Name of the action alias.",
                "required": True,
            },
            "pack": {
                "description": "The content pack this actionalias belongs to.",
                "type": "string",
                "required": True,
            },
            "description": {
                "type": "string",
                "description": "Description of the action alias.",
                "default": None,
            },
            "enabled": {
                "description": "Flag indicating of action alias is enabled.",
                "type": "boolean",
                "default": True,
            },
            "action_ref": {
                "type": "string",
                "description": "Reference to the aliased action.",
                "required": True,
            },
            "formats": {
                "type": "array",
                "items": {
                    "anyOf": [
                        {"type": "string"},
                        {
                            "type": "object",
                            "properties": {
                                "display": {"type": "string"},
                                "representation": {
                                    "type": "array",
                                    "items": {"type": "string"},
                                },
                            },
                        },
                    ]
                },
                "description": "Possible parameter format.",
            },
            "ack": {
                "type": "object",
                "properties": {
                    "enabled": {"type": "boolean"},
                    "format": {"type": "string"},
                    "extra": {"type": "object"},
                    "append_url": {"type": "boolean"},
                },
                "description": "Acknowledgement message format.",
            },
            "result": {
                "type": "object",
                "properties": {
                    "enabled": {"type": "boolean"},
                    "format": {"type": "string"},
                    "extra": {"type": "object"},
                },
                "description": "Execution message format.",
            },
            "extra": {
                "type": "object",
                "description": "Extra parameters, usually adapter-specific.",
            },
            "immutable_parameters": {
                "type": "object",
                "description": "Parameters to be passed to the action on every execution.",
            },
            "metadata_file": {
                "description": "Path to the metadata file relative to the pack directory.",
                "type": "string",
                "default": "",
            },
        },
        "additionalProperties": False,
    }

    @classmethod
    def to_model(cls, alias):
        name = alias.name
        description = getattr(alias, "description", None)
        pack = alias.pack
        ref = ResourceReference.to_string_reference(pack=pack, name=name)
        enabled = getattr(alias, "enabled", True)
        action_ref = alias.action_ref
        formats = alias.formats
        ack = getattr(alias, "ack", None)
        result = getattr(alias, "result", None)
        extra = getattr(alias, "extra", None)
        immutable_parameters = getattr(alias, "immutable_parameters", None)
        metadata_file = getattr(alias, "metadata_file", None)

        model = cls.model(
            name=name,
            description=description,
            pack=pack,
            ref=ref,
            enabled=enabled,
            action_ref=action_ref,
            formats=formats,
            ack=ack,
            result=result,
            extra=extra,
            immutable_parameters=immutable_parameters,
            metadata_file=metadata_file,
        )
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
                "required": True,
            },
            "format": {
                "type": "string",
                "description": "Format string which matched.",
                "required": True,
            },
            "command": {
                "type": "string",
                "description": "Command used in chat.",
                "required": True,
            },
            "user": {
                "type": "string",
                "description": "User that requested the execution.",
                "default": "channel",  # TODO: This value doesnt get set
            },
            "source_channel": {
                "type": "string",
                "description": "Channel from which the execution was requested. This is not the "
                "channel as defined by the notification system.",
                "required": True,
            },
            "source_context": {
                "type": "object",
                "description": "ALL data included with the message (also called the message "
                "envelope). This is currently only used by the Microsoft Teams "
                "adapter.",
                "required": False,
            },
            "notification_channel": {
                "type": "string",
                "description": "StackStorm notification channel to use to respond.",
                "required": False,
            },
            "notification_route": {
                "type": "string",
                "description": "StackStorm notification route to use to respond.",
                "required": False,
            },
        },
        "additionalProperties": False,
    }

    @classmethod
    def to_model(cls, aliasexecution):
        # probably should be unsupported
        raise NotImplementedError()

    @classmethod
    def from_model(cls, aliasexecution):
        raise NotImplementedError()


class AliasMatchAndExecuteInputAPI(BaseAPI):
    """
    API object used for alias execution "match and execute" API endpoint request payload.
    """

    model = None
    schema = {
        "title": "ActionAliasMatchAndExecuteInputAPI",
        "description": "Input for alias execution match and execute API.",
        "type": "object",
        "properties": {
            "command": {
                "type": "string",
                "description": "Command used in chat.",
                "required": True,
            },
            "user": {
                "type": "string",
                "description": "User that requested the execution.",
            },
            "source_channel": {
                "type": "string",
                "description": "Channel from which the execution was requested. This is not the \
                                channel as defined by the notification system.",
                "required": True,
            },
            "notification_channel": {
                "type": "string",
                "description": "StackStorm notification channel to use to respond.",
                "required": False,
                "default": None,
            },
            "notification_route": {
                "type": "string",
                "description": "StackStorm notification route to use to respond.",
                "required": False,
                "default": None,
            },
        },
        "additionalProperties": False,
    }


class ActionAliasMatchAPI(BaseAPI):
    """
    API model used for alias match API endpoint.
    """

    model = None

    schema = {
        "title": "ActionAliasMatchAPI",
        "description": "ActionAliasMatchAPI.",
        "type": "object",
        "properties": {
            "command": {
                "type": "string",
                "description": "Command string to try to match the aliases against.",
                "required": True,
            }
        },
        "additionalProperties": False,
    }

    @classmethod
    def to_model(cls, aliasexecution):
        raise NotImplementedError()

    @classmethod
    def from_model(cls, aliasexecution):
        raise NotImplementedError()


class ActionAliasHelpAPI(BaseAPI):
    """
    API model used to display action-alias help API endpoint.
    """

    model = None

    schema = {
        "title": "ActionAliasHelpAPI",
        "description": "ActionAliasHelpAPI.",
        "type": "object",
        "properties": {
            "filter": {
                "type": "string",
                "description": "Find help strings containing keyword.",
                "required": False,
                "default": "",
            },
            "pack": {
                "type": "string",
                "description": "List help strings for a specific pack.",
                "required": False,
                "default": "",
            },
            "offset": {
                "type": "integer",
                "description": "List help strings from the offset position.",
                "required": False,
                "default": 0,
            },
            "limit": {
                "type": "integer",
                "description": "Limit the number of help strings returned.",
                "required": False,
                "default": 0,
            },
        },
        "additionalProperties": False,
    }

    @classmethod
    def to_model(cls, aliasexecution):
        raise NotImplementedError()

    @classmethod
    def from_model(cls, aliasexecution):
        raise NotImplementedError()

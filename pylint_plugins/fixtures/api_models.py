# Copyright 2022 The StackStorm Authors.
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


import abc

DEFAULT_PACK_NAME = "default"


# copied from st2common.models.api.notification
NotificationSubSchemaAPI = {
    "type": "object",
    "properties": {
        "message": {"type": "string", "description": "Message to use for notification"},
        "data": {
            "type": "object",
            "description": "Data to be sent as part of notification",
        },
        "routes": {
            "type": "array",
            "description": "Channels to post notifications to.",
        },
        "channels": {  # Deprecated. Only here for backward compatibility.
            "type": "array",
            "description": "Channels to post notifications to.",
        },
    },
    "additionalProperties": False,
}


def get_schema(**kwargs):
    return {}


# copied (in part) from st2common.models.api.base
class BaseAPI(abc.ABC):
    schema = abc.abstractproperty
    name = None


# copied (in part) from st2common.models.api.action
class ActionAPI(BaseAPI):
    """
    The system entity that represents a Stack Action/Automation in the system.
    """

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
            "name": {  # used in test
                "description": "The name of the action.",
                "type": "string",
                "required": True,
            },
            "description": {  # used in test
                "description": "The description of the action.",
                "type": "string",
            },
            "enabled": {
                "description": "Enable or disable the action from invocation.",
                "type": "boolean",
                "default": True,
            },
            "runner_type": {  # used in test
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
                "patternProperties": {r"^\w+$": get_schema()},
                "additionalProperties": False,
                "default": {},
            },
            "output_schema": get_schema(description="Action Output Schema"),
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


# copied (in part) from st2common.models.api.trigger
class TriggerTypeAPI(BaseAPI):
    schema = {
        "type": "object",
        "properties": {
            "id": {"type": "string", "default": None},
            "ref": {"type": "string"},
            "uid": {"type": "string"},
            "name": {"type": "string", "required": True},
            "pack": {"type": "string"},
            "description": {"type": "string"},
            "payload_schema": {"type": "object", "default": {}},
            "parameters_schema": {"type": "object", "default": {}},
            "tags": {
                "description": "User associated metadata assigned to this object.",
                "type": "array",
                "items": {"type": "object"},
            },
            "metadata_file": {
                "description": "Path to the metadata file relative to the pack directory.",
                "type": "string",
                "default": "",
            },
        },
        "additionalProperties": False,
    }

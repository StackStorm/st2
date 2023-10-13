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
import uuid

from st2common.constants.triggers import TRIGGER_INSTANCE_STATUSES
from st2common.util import isotime
from st2common.models.api.base import BaseAPI
from st2common.models.api.tag import TagsHelper
from st2common.models.db.trigger import TriggerTypeDB, TriggerDB, TriggerInstanceDB
from st2common.models.system.common import ResourceReference

DATE_FORMAT = "%Y-%m-%d %H:%M:%S.%f"


# NOTE: Update pylint_plugins/fixtures/api_models.py if this changes significantly
class TriggerTypeAPI(BaseAPI):
    model = TriggerTypeDB
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

    @classmethod
    def to_model(cls, trigger_type):
        name = getattr(trigger_type, "name", None)
        description = getattr(trigger_type, "description", None)
        pack = getattr(trigger_type, "pack", None)
        payload_schema = getattr(trigger_type, "payload_schema", {})
        parameters_schema = getattr(trigger_type, "parameters_schema", {})
        tags = TagsHelper.to_model(getattr(trigger_type, "tags", []))
        metadata_file = getattr(trigger_type, "metadata_file", None)

        model = cls.model(
            name=name,
            description=description,
            pack=pack,
            payload_schema=payload_schema,
            parameters_schema=parameters_schema,
            tags=tags,
            metadata_file=metadata_file,
        )
        return model

    @classmethod
    def from_model(cls, model, mask_secrets=False):
        triggertype = cls._from_model(model, mask_secrets=mask_secrets)
        triggertype["tags"] = TagsHelper.from_model(model.tags)
        return cls(**triggertype)


class TriggerAPI(BaseAPI):
    model = TriggerDB
    schema = {
        "type": "object",
        "properties": {
            "id": {"type": "string", "default": None},
            "ref": {"type": "string"},
            "uid": {"type": "string"},
            "name": {"type": "string"},
            "pack": {"type": "string"},
            "type": {"type": "string", "required": True},
            "parameters": {"type": "object"},
            "description": {"type": "string"},
        },
        "additionalProperties": False,
    }

    @classmethod
    def from_model(cls, model, mask_secrets=False):
        trigger = cls._from_model(model, mask_secrets=mask_secrets)
        # Hide ref count from API.
        trigger.pop("ref_count", None)
        return cls(**trigger)

    @classmethod
    def to_model(cls, trigger):
        name = getattr(trigger, "name", None)
        description = getattr(trigger, "description", None)
        pack = getattr(trigger, "pack", None)
        _type = getattr(trigger, "type", None)
        parameters = getattr(trigger, "parameters", {})

        if _type and not parameters:
            trigger_type_ref = ResourceReference.from_string_reference(_type)
            name = trigger_type_ref.name

        if hasattr(trigger, "name") and trigger.name:
            name = trigger.name
        else:
            # assign a name if none is provided.
            name = str(uuid.uuid4())

        model = cls.model(
            name=name,
            description=description,
            pack=pack,
            type=_type,
            parameters=parameters,
        )
        return model

    def to_dict(self):
        # Return dictionary version of the trigger
        return vars(self)


class TriggerInstanceAPI(BaseAPI):
    model = TriggerInstanceDB
    schema = {
        "type": "object",
        "properties": {
            "id": {"type": "string"},
            "occurrence_time": {"type": "string", "pattern": isotime.ISO8601_UTC_REGEX},
            "payload": {"type": "object"},
            "trigger": {"type": "string", "default": None, "required": True},
            "status": {
                "type": "string",
                "default": None,
                "enum": TRIGGER_INSTANCE_STATUSES,
            },
        },
        "additionalProperties": False,
    }
    skip_unescape_field_names = [
        "payload",
    ]

    @classmethod
    def from_model(cls, model, mask_secrets=False):
        instance = cls._from_model(model, mask_secrets=mask_secrets)

        if "payload" in instance:
            instance["payload"] = TriggerInstanceDB.payload.parse_field_value(
                instance["payload"]
            )

        if instance.get("occurrence_time", None):
            instance["occurrence_time"] = isotime.format(
                instance["occurrence_time"], offset=False
            )

        return cls(**instance)

    @classmethod
    def to_model(cls, instance):
        trigger = instance.trigger
        payload = instance.payload
        occurrence_time = isotime.parse(instance.occurrence_time)
        status = instance.status

        model = cls.model(
            trigger=trigger,
            payload=payload,
            occurrence_time=occurrence_time,
            status=status,
        )
        return model

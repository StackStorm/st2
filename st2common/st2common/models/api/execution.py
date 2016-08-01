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

import copy

import six

from st2common.constants.action import LIVEACTION_STATUSES
from st2common.util import isotime
from st2common.models.api.base import BaseAPI
from st2common.models.db.execution import ActionExecutionDB
from st2common.models.api.trigger import TriggerTypeAPI, TriggerAPI, TriggerInstanceAPI
from st2common.models.api.rule import RuleAPI
from st2common.models.api.action import RunnerTypeAPI, ActionAPI, LiveActionAPI
from st2common import log as logging


LOG = logging.getLogger(__name__)

REQUIRED_ATTR_SCHEMAS = {
    "action": copy.deepcopy(ActionAPI.schema),
    "runner": copy.deepcopy(RunnerTypeAPI.schema),
    "liveaction": copy.deepcopy(LiveActionAPI.schema),
}

for k, v in six.iteritems(REQUIRED_ATTR_SCHEMAS):
    v.update({"required": True})


class ActionExecutionAPI(BaseAPI):
    model = ActionExecutionDB
    SKIP = ['start_timestamp', 'end_timestamp']
    schema = {
        "title": "ActionExecution",
        "description": "Record of the execution of an action.",
        "type": "object",
        "properties": {
            "id": {
                "type": "string",
                "required": True
            },
            "trigger": TriggerAPI.schema,
            "trigger_type": TriggerTypeAPI.schema,
            "trigger_instance": TriggerInstanceAPI.schema,
            "rule": RuleAPI.schema,
            "action": REQUIRED_ATTR_SCHEMAS['action'],
            "runner": REQUIRED_ATTR_SCHEMAS['runner'],
            "liveaction": REQUIRED_ATTR_SCHEMAS['liveaction'],
            "status": {
                "description": "The current status of the action execution.",
                "type": "string",
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
            "elapsed_seconds": {
                "description": "Time duration in seconds taken for completion of this execution.",
                "type": "number",
                "required": False
            },
            "web_url": {
                "description": "History URL for this execution if you want to view in UI.",
                "type": "string",
                "required": False
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
            "context": {
                "type": "object"
            },
            "result": {
                "anyOf": [{"type": "array"},
                          {"type": "boolean"},
                          {"type": "integer"},
                          {"type": "number"},
                          {"type": "object"},
                          {"type": "string"}]
            },
            "parent": {"type": "string"},
            "children": {
                "type": "array",
                "items": {"type": "string"},
                "uniqueItems": True
            },
            "log": {
                "description": "Contains information about execution state transitions.",
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "timestamp": {
                            "type": "string",
                            "pattern": isotime.ISO8601_UTC_REGEX
                        },
                        "status": {
                            "type": "string",
                            "enum": LIVEACTION_STATUSES
                        }
                    }
                }
            }
        },
        "additionalProperties": False
    }

    @classmethod
    def from_model(cls, model, mask_secrets=False):
        doc = cls._from_model(model, mask_secrets=mask_secrets)
        start_timestamp = model.start_timestamp
        start_timestamp_iso = isotime.format(start_timestamp, offset=False)
        doc['start_timestamp'] = start_timestamp_iso

        end_timestamp = model.end_timestamp
        if end_timestamp:
            end_timestamp_iso = isotime.format(end_timestamp, offset=False)
            doc['end_timestamp'] = end_timestamp_iso
            doc['elapsed_seconds'] = (end_timestamp - start_timestamp).total_seconds()

        for entry in doc.get('log', []):
            entry['timestamp'] = isotime.format(entry['timestamp'], offset=False)

        attrs = {attr: value for attr, value in six.iteritems(doc) if value}
        return cls(**attrs)

    @classmethod
    def to_model(cls, instance):
        values = {}
        for attr, meta in six.iteritems(cls.schema.get('properties', dict())):
            if not getattr(instance, attr, None):
                continue

            default = copy.deepcopy(meta.get('default', None))
            value = getattr(instance, attr, default)

            # pylint: disable=no-member
            # TODO: Add plugin which lets pylint know each MongoEngine document has _fields
            # attribute
            attr_schema = cls.model._fields.get(attr, None)
            if not value and (attr_schema and not attr_schema.required):
                continue
            if attr not in ActionExecutionAPI.SKIP:
                values[attr] = value

        values['start_timestamp'] = isotime.parse(instance.start_timestamp)
        values['end_timestamp'] = isotime.parse(instance.end_timestamp)

        model = cls.model(**values)
        return model

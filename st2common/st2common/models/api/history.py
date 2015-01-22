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

from st2common.util import isotime
from st2common.models.api.base import BaseAPI
from st2common.models.db.history import ActionExecutionHistoryDB
from st2common.models.api.reactor import TriggerTypeAPI, TriggerAPI, TriggerInstanceAPI
from st2common.models.api.rule import RuleAPI
from st2common.models.api.action import RunnerTypeAPI, ActionAPI, LiveActionAPI
from st2common import log as logging


LOG = logging.getLogger(__name__)

REQUIRED_ATTR_SCHEMAS = {
    "action": copy.deepcopy(ActionAPI.schema),
    "runner": copy.deepcopy(RunnerTypeAPI.schema),
    "execution": copy.deepcopy(LiveActionAPI.schema),
}

for k, v in six.iteritems(REQUIRED_ATTR_SCHEMAS):
    v.update({"required": True})


class ActionExecutionHistoryAPI(BaseAPI):
    model = ActionExecutionHistoryDB
    schema = {
        "title": "ActionExecutionHistory",
        "description": "History record for action execution.",
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
            "execution": REQUIRED_ATTR_SCHEMAS['execution'],
            "parent": {"type": "string"},
            "children": {
                "type": "array",
                "items": {"type": "string"},
                "uniqueItems": True
            }
        },
        "additionalProperties": False
    }

    @classmethod
    def from_model(cls, model):
        doc = cls._from_model(model)
        start_timestamp = isotime.format(doc['execution']['start_timestamp'], offset=False)

        end_timestamp = doc['execution'].get('end_timestamp', None)
        if end_timestamp is not None:
            end_timestamp = isotime.format(end_timestamp, offset=False)
            doc['execution']['end_timestamp'] = end_timestamp

        doc['execution']['start_timestamp'] = start_timestamp

        attrs = {attr: value for attr, value in six.iteritems(doc) if value}
        return cls(**attrs)

    @classmethod
    def to_model(cls, instance):
        model = cls.model()
        for attr, meta in six.iteritems(cls.schema.get('properties', dict())):
            default = copy.deepcopy(meta.get('default', None))
            value = getattr(instance, attr, default)
            if not value and not cls.model._fields[attr].required:
                continue
            setattr(model, attr, value)

        model.execution['start_timestamp'] = isotime.parse(model.execution['start_timestamp'])
        model.execution['end_timestamp'] = isotime.parse(model.execution['end_timestamp'])
        return model

import copy

import six

from st2common.util import isotime
from st2common.models.base import BaseAPI
from st2common.models.db.history import ActionExecutionHistoryDB
from st2common.models.api.reactor import TriggerTypeAPI, TriggerAPI, TriggerInstanceAPI
from st2common.models.api.rule import RuleAPI
from st2common.models.api.action import RunnerTypeAPI, ActionAPI, ActionExecutionAPI
from st2common import log as logging


LOG = logging.getLogger(__name__)


class ActionExecutionHistoryAPI(BaseAPI):
    model = ActionExecutionHistoryDB
    schema = {
        "$schema": "http://json-schema.org/draft-04/schema#",
        "title": "ActionExecutionHistory",
        "description": "History record for action execution.",
        "type": "object",
        "properties": {
            "id": {"type": "string"},
            "trigger": TriggerAPI.schema,
            "trigger_type": TriggerTypeAPI.schema,
            "trigger_instance": TriggerInstanceAPI.schema,
            "rule": RuleAPI.schema,
            "action": ActionAPI.schema,
            "runner": RunnerTypeAPI.schema,
            "execution": ActionExecutionAPI.schema,
            "parent": {"type": "string"},
            "children": {
                "type": "array",
                "items": {"type": "string"},
                "uniqueItems": True
            }
        },
        "required": ["id",
                     "action",
                     "runner",
                     "execution"],
        "additionalProperties": False
    }

    @classmethod
    def from_model(cls, model):
        doc = cls._from_model(model)
        timestamp = isotime.format(doc['execution']['start_timestamp'], offset=False)
        doc['execution']['start_timestamp'] = timestamp
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
        return model

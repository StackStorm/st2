import copy

from st2common.models.base import BaseAPI
from st2common.models.db.history import ActionExecutionHistoryDB
from st2common.models.api.reactor import TriggerTypeAPI, TriggerAPI, TriggerInstanceAPI, RuleAPI
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
            "executions": {
                "type": "array",
                "items": ActionExecutionAPI.schema,
                "uniqueItems": True
            }
        },
        "required": ["id",
                     "action",
                     "runner",
                     "executions"],
        "additionalProperties": False
    }

    @classmethod
    def to_model(cls, instance):
        model = cls.model()
        for attr, meta in cls.schema.get('properties', dict()).iteritems():
            default = copy.deepcopy(meta.get('default', None))
            value = getattr(instance, attr, default)
            if not value and not cls.model._fields[attr].required:
                continue
            setattr(model, attr, value)
        return model

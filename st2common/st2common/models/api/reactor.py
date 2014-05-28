import datetime
from wsme import types as wstypes

from st2common.models.api.stormbase import BaseAPI
from st2common.models.db.reactor import RuleDB
from st2common.persistence.reactor import Trigger
from st2common.persistence.action import Action


def get_id(identifiable):
    if identifiable is None:
        return ''
    return str(identifiable.id)


class TriggerAPI(BaseAPI):
    payload_info = wstypes.ArrayType(wstypes.DictType(str, str))

    @classmethod
    def from_model(cls, model):
        trigger = BaseAPI.from_model(cls, model)
        trigger.payload_info = model.payload_info
        return trigger


class TriggerInstanceAPI(BaseAPI):
    trigger = wstypes.text
    payload = wstypes.DictType(str, str)
    occurrence_time = datetime.datetime

    @classmethod
    def from_model(cls, model):
        trigger_instance = BaseAPI.from_model(cls, model)
        trigger_instance.trigger = get_id(model.trigger)
        trigger_instance.payload = dict(model.payload)
        trigger_instance.occurrence_time = model.occurrence_time
        return trigger_instance


class RuleAPI(BaseAPI):
    trigger = wstypes.text
    action = wstypes.text
    data_mapping = wstypes.DictType(str, str)
    status = wstypes.Enum(str, 'enabled', 'disabled')

    @classmethod
    def from_model(cls, model):
        rule = BaseAPI.from_model(cls, model)
        rule.trigger = get_id(model.trigger)
        rule.action = get_id(model.action)
        rule.data_mapping = dict(model.data_mapping)
        rule.status = model.status
        return rule

    @classmethod
    def to_model(cls, rule):
        model = BaseAPI.to_model(RuleDB, rule)
        model.trigger = Trigger.get_by_id(rule.trigger)
        model.action = Action.get_by_id(rule.action)
        model.data_mapping = rule.data_mapping
        model.status = rule.status
        return model


class RuleEnforcementAPI(BaseAPI):
    rule = wstypes.text
    trigger_instance = wstypes.text
    action_execution = wstypes.text

    @classmethod
    def from_model(cls, model):
        rule_enforcement = BaseAPI.from_model(cls, model)
        rule_enforcement.rule = get_id(model.rule)
        rule_enforcement.trigger_instance = get_id(model.trigger_instance)
        rule_enforcement.action_execution = get_id(model.action_execution)
        return rule_enforcement

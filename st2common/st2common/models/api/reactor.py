from wsme import types as wstypes

from st2common.models.api.stormbase import BaseAPI


class TriggerAPI(BaseAPI):
    payload_info = wstypes.ArrayType(wstypes.DictType)

    @classmethod
    def from_model(cls, model):
        trigger = BaseAPI.from_model(cls, model)
        trigger.payload_info = model.payload_info
        return trigger


class TriggerInstanceAPI(BaseAPI):
    trigger = wstypes.text
    payload = wstypes.DictType
    occurrence_time = wstypes.dt_types

    @classmethod
    def from_model(cls, model):
        trigger_instance = BaseAPI.from_model(cls, model)
        trigger_instance.trigger = model.trigger
        trigger_instance.payload = model.payload
        trigger_instance.occurrence_time = model.occurence_time
        return trigger_instance


class RuleAPI(BaseAPI):
    trigger = wstypes.text
    action = wstypes.text
    data_mapping = wstypes.DictType
    status = wstypes.Enum(str, 'enabled', 'disabled')

    @classmethod
    def from_model(cls, model):
        rule = BaseAPI.from_model(cls, model)
        rule.trigger = model.trigger
        rule.action = model.action
        rule.data_mapping = model.data_mapping
        rule.status = model.status
        return rule


class RuleEnforcementAPI(BaseAPI):
    rule = wstypes.text
    trigger_instance = wstypes.text
    action_execution = wstypes.text

    @classmethod
    def from_model(cls, model):
        rule_enforcement = BaseAPI.from_model(cls, model)
        rule_enforcement.rule = model.rule
        rule_enforcement.trigger_instance = model.trigger_instance
        rule_enforcement.action_execution = model.action_execution
        return rule_enforcement
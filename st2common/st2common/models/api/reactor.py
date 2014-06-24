import datetime
from wsme import types as wstypes

from st2common.models.api.stormbase import StormBaseAPI, StormFoundationAPI
from st2common.models.db.reactor import RuleDB, ActionExecutionSpecDB
from st2common.persistence.reactor import Trigger
from st2common.persistence.action import Action


def get_id(identifiable):
    if identifiable is None:
        return ''
    return str(identifiable.id)


def get_ref(identifiable):
    if identifiable is None:
        return {}
    return {'id': str(identifiable.id), 'name': identifiable.name}


def get_model_from_ref(db_api, ref):
    if ref is None:
        return None
    model_id = ref['id'] if 'id' in ref else None
    if model_id is not None:
        return db_api.get_by_id(model_id)
    model_name = ref['name'] if 'name' in ref else None
    for model in db_api.query(name=model_name):
        return model
    return None


class TriggerAPI(StormBaseAPI):
    payload_info = wstypes.ArrayType(str)

    @classmethod
    def from_model(kls, model):
        trigger = StormBaseAPI.from_model(kls, model)
        trigger.payload_info = model.payload_info
        return trigger


class TriggerInstanceAPI(StormFoundationAPI):
    trigger = wstypes.text
    payload = wstypes.DictType(str, str)
    occurrence_time = datetime.datetime

    @classmethod
    def from_model(kls, model):
        trigger_instance = StormFoundationAPI.from_model(kls, model)
        trigger_instance.trigger = get_id(model.trigger)
        trigger_instance.payload = dict(model.payload)
        trigger_instance.occurrence_time = model.occurrence_time
        return trigger_instance


class RuleAPI(StormBaseAPI):
    """
    Attribute:
        trigger_type: Trigger that trips this rule. Of the form {'id':'1234', 'name':'trigger-1'}.
        Only 1 of the id or name is required and if both are specified name is ignored.
        criteria: Criteria used to further restrict the trigger that applies to this rule.
        e.g.
        { "trigger.from" :
            { "pattern": "{{ rule_data.mailserver }}$"
            , "type": "matchregex" }
        , "trigger.subject" :
            { "pattern": "RE:"
            , "operator": "contain" }
        }
        rule_data:
        action: Specification of the action to execute and the mappings to apply.
        expected arguments are type, mapping.
        e.g.
        "action":
        { "type": {"id": "2345678901"}
        , "mapping":
            { "command": "{{ rule_data.foo }}"
            , "args": "--email {{ trigger.from }} --subject \'{{ user[stanley].ALERT_SUBJECT }}\'"}
        }
        status: enabled or disabled. If disabled occurrence of the trigger
        does not lead to execution of a action and vice-versa.
    """
    trigger_type = wstypes.DictType(str, str)
    criteria = wstypes.DictType(str, wstypes.DictType(str, str))
    rule_data = wstypes.DictType(str, str)
    action = wstypes.DictType(str, wstypes.DictType(str, str))
    enabled = wstypes.wsattr(bool, default=True)

    @classmethod
    def from_model(kls, model):
        rule = StormBaseAPI.from_model(kls, model)
        rule.trigger_type = get_ref(model.trigger_type)
        rule.criteria = dict(model.criteria)
        rule.action = {'type': get_ref(model.action.action),
                       'mapping': dict(model.action.data_mapping)}
        rule.rule_data = dict(model.rule_data)
        rule.enabled = model.enabled
        return rule

    @classmethod
    def to_model(kls, rule):
        model = StormBaseAPI.to_model(RuleDB, rule)
        model.trigger_type = get_model_from_ref(Trigger, rule.trigger_type)
        model.criteria = dict(rule.criteria)
        model.action = ActionExecutionSpecDB()
        if 'type' in rule.action:
            model.action.action = get_model_from_ref(Action, rule.action['type'])
        if 'mapping' in rule.action:
            model.action.data_mapping = rule.action['mapping']
        model.rule_data = rule.rule_data
        model.enabled = rule.enabled
        return model


class RuleEnforcementAPI(StormFoundationAPI):
    rule = wstypes.text
    trigger_instance = wstypes.text
    action_execution = wstypes.text

    @classmethod
    def from_model(kls, model):
        rule_enforcement = StormFoundationAPI.from_model(kls, model)
        rule_enforcement.rule = get_id(model.rule)
        rule_enforcement.trigger_instance = get_id(model.trigger_instance)
        rule_enforcement.action_execution = get_id(model.action_execution)
        return rule_enforcement

import datetime
from wsme import types as wstypes

from st2common.models.base import BaseAPI
from st2common.models.api.stormbase import StormBaseAPI, StormFoundationAPI
from st2common.models.db.reactor import RuleDB, ActionExecutionSpecDB, TriggerDB, AHTriggerDB
import st2common.validators.api.reactor as validator


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


class TriggerAPI(BaseAPI):
    schema = {
        "type": "object"
    }

    @classmethod
    def from_model(cls, model):
        trigger = model.to_mongo()
        trigger['name'] = str(trigger.pop('_id'))
        return cls(**trigger)

    @classmethod
    def to_model(cls, trigger):
        model = StormBaseAPI.to_model(TriggerDB, trigger)
        model.payload_info = trigger.payload_info
        return model


class AHTriggerAPI(BaseAPI):
    schema = {
        "type": "object"
    }

    @classmethod
    def from_model(cls, model):
        trigger = model.to_mongo()
        del trigger['_id']
        return cls(**trigger)

    @classmethod
    def to_model(cls, trigger):
        model = StormFoundationAPI.to_model(AHTriggerDB, trigger)
        # We probably need to manually assign an ID based on the hash of trigger name and parameters
        model.name = trigger.name
        model.parameters = getattr(trigger, 'parameters', {})
        return model


class TriggerInstanceAPI(StormFoundationAPI):
    trigger = wstypes.text
    payload = wstypes.DictType(str, str)
    occurrence_time = datetime.datetime

    @classmethod
    def from_model(kls, model):
        trigger_instance = StormFoundationAPI.from_model(kls, model)
        trigger_instance.trigger = model.trigger
        trigger_instance.payload = dict(model.payload)
        trigger_instance.occurrence_time = model.occurrence_time
        return trigger_instance


class ActionSpec(BaseAPI):
    # name = wstypes.text
    # parameters = wstypes.DictType(str, *)
    schema = {
        'type': 'object',
        'properties': {
            'name': {
                'type': 'string'
            },
            'parameters': {
                'type': 'object'
            }
        },
        'required': ['name'],
        'additionalProperties': False
    }


class RuleAPI(BaseAPI):
    """
    Attribute:
        trigger_type: Trigger that trips this rule. Of the form {'id':'1234', 'name':'trigger-1'}.
        Only 1 of the id or name is required and if both are specified name is ignored.
        criteria: Criteria used to further restrict the trigger that applies to this rule.
        e.g.
        { "trigger.from" :
            { "pattern": "{{ system.mailserver }}$"
            , "type": "matchregex" }
        , "trigger.subject" :
            { "pattern": "RE:"
            , "operator": "contain" }
        }
        action: Specification of the action to execute and the mappings to apply.
        expected arguments are name, parameters.
        e.g.
        "action":
        { "name": "st2.action.foo"
        , "parameters":
            { "command": "{{ system.foo }}"
            , "args": "--email {{ trigger.from }} --subject \'{{ user[stanley].ALERT_SUBJECT }}\'"}
        }
        status: enabled or disabled. If disabled occurrence of the trigger
        does not lead to execution of a action and vice-versa.
    """
    # trigger = wstypes.DictType(str, *)
    # criteria = wstypes.DictType(str, wstypes.DictType(str, str))
    # action = ActionSpec
    # enabled = wstypes.wsattr(bool, default=True)
    schema = {
        'type': 'object',
        'properties': {
            'id': {
                'type': 'string',
                'default': None
            },
            'name': {
                'type': 'string'
            },
            'description': {
                'type': 'string'
            },
            'trigger': {
                'type': 'object'
            },
            'criteria': {
                'type': 'object'
            },
            'action': ActionSpec.schema,
            'enabled': {
                'type': 'boolean',
                'default': True
            }
        },
        'required': ['name', 'trigger', 'criteria', 'action'],
        'additionalProperties': False
    }

    @classmethod
    def from_model(cls, model):
        rule = model.to_mongo()
        rule['id'] = str(rule['_id'])
        del rule['_id']
        rule['trigger'] = vars(AHTriggerAPI.from_model(model.trigger))
        return cls(**rule)

    @classmethod
    def to_model(cls, rule):
        model = StormBaseAPI.to_model(RuleDB, rule)
        model.trigger = AHTriggerAPI(**rule.trigger)
        model.criteria = dict(rule.criteria)
        validator.validate_criteria(model.criteria)
        model.action = ActionExecutionSpecDB()
        model.action.name = rule.action['name']
        model.action.parameters = rule.action['parameters']
        model.enabled = rule.enabled
        return model


class RuleEnforcementAPI(StormFoundationAPI):
    rule = wstypes.text
    trigger_instance = wstypes.text
    action_execution = wstypes.text

    @classmethod
    def from_model(kls, model):
        rule_enforcement = StormFoundationAPI.from_model(kls, model)
        rule_enforcement.rule = model.rule
        rule_enforcement.trigger_instance = model.trigger_instance
        rule_enforcement.action_execution = model.action_execution
        return rule_enforcement

import datetime
import uuid
from wsme import types as wstypes

from st2common.models.base import BaseAPI
from st2common.models.api.stormbase import StormBaseAPI, StormFoundationAPI
from st2common.models.db.reactor import RuleDB, ActionExecutionSpecDB, TriggerTypeDB, TriggerDB
from st2common.persistence.reactor import Trigger
from st2common.util import reference
import st2common.validators.api.reactor as validator


class TriggerTypeAPI(BaseAPI):
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
                'type': 'string',
                'default': None
            },
            'payload_schema': {
                'type': 'object',
                'default': {}
            },
            'parameters_schema': {
                'type': 'object',
                'default': {}
            }
        },
        'required': ['name'],
        'additionalProperties': False
    }

    @classmethod
    def from_model(cls, model):
        trigger = model.to_mongo()
        trigger['id'] = str(trigger.pop('_id'))
        return cls(**trigger)

    @classmethod
    def to_model(cls, triggertype):
        model = StormBaseAPI.to_model(TriggerTypeDB, triggertype)
        model.payload_schema = triggertype.payload_schema
        model.parameters_schema = triggertype.parameters_schema
        return model


class TriggerAPI(BaseAPI):
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
            'type': {
                'type': 'string'
            },
            'parameters': {
                'type': 'object'
            }
        },
        'required': ['type'],
        'additionalProperties': False
    }

    @classmethod
    def from_model(cls, model):
        trigger = model.to_mongo()
        trigger['id'] = str(trigger['_id'])
        del trigger['_id']
        if 'type' in trigger:
            trigger['type'] = str(trigger['type'].get('name', ''))
        return cls(**trigger)

    @classmethod
    def to_model(cls, trigger):
        model = StormFoundationAPI.to_model(TriggerDB, trigger)
        # assign a name if none is provided.
        model.name = trigger.name if hasattr(trigger, 'name') and trigger.name else \
            str(uuid.uuid4())
        model.type = {'name': getattr(trigger, 'type', None)}
        model.parameters = getattr(trigger, 'parameters', None)
        return model


class TriggerInstanceAPI(StormFoundationAPI):
    trigger = wstypes.text
    payload = wstypes.DictType(str, str)
    occurrence_time = datetime.datetime

    @classmethod
    def from_model(kls, model):
        trigger_instance = StormFoundationAPI.from_model(kls, model)
        trigger_instance.trigger = model.trigger.get('name', '')
        trigger_instance.payload = dict(model.payload)
        trigger_instance.occurrence_time = model.occurrence_time
        return trigger_instance


class ActionSpec(BaseAPI):
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
            { "pattern": "@gmail.com$"
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
                'type': 'object',
                'properties': {
                    'type': {
                        'type': 'string'
                    },
                    'parameters': {
                        'type': 'object',
                        'default': {}
                    }
                },
                'required': ['type'],
                'additionalProperties': False
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
        rule['trigger'] = vars(TriggerAPI.from_model(reference.get_model_from_ref(Trigger,
                                                                                  model.trigger)))
        del rule['trigger']['id']
        del rule['trigger']['name']
        for oldkey, value in rule['criteria'].iteritems():
            newkey = oldkey.replace(u'\u2024', '.')
            if oldkey != newkey:
                rule['criteria'][newkey] = value
                del rule['criteria'][oldkey]
        return cls(**rule)

    @classmethod
    def to_model(cls, rule):
        model = StormBaseAPI.to_model(RuleDB, rule)
        model.trigger = TriggerAPI(**rule.trigger)
        model.criteria = dict(rule.criteria)
        for oldkey, value in model.criteria.iteritems():
            newkey = oldkey.replace('.', u'\u2024')
            if oldkey != newkey:
                model.criteria[newkey] = value
                del model.criteria[oldkey]
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

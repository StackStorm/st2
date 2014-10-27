import six

from st2common.models.base import BaseAPI
from st2common.models.api.reactor import TriggerAPI
from st2common.models.db.reactor import RuleDB, ActionExecutionSpecDB
from st2common.persistence.reactor import Trigger
import st2common.services.triggers as TriggerService
from st2common.util import reference
import st2common.validators.api.reactor as validator


class ActionSpec(BaseAPI):
    schema = {
        'type': 'object',
        'properties': {
            'ref': {
                'type': 'string'
            },
            'parameters': {
                'type': 'object'
            }
        },
        'required': ['ref'],
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
    model = RuleDB
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
                'additionalProperties': True
            },
            'criteria': {
                'type': 'object',
                'default': {}
            },
            'action': ActionSpec.schema,
            'enabled': {
                'type': 'boolean',
                'default': True
            }
        },
        'required': ['name', 'trigger', 'action'],
        'additionalProperties': False
    }

    @classmethod
    def from_model(cls, model):
        rule = cls._from_model(model)
        trigger_db = reference.get_model_by_resource_ref(Trigger, model.trigger)
        rule['trigger'] = vars(TriggerAPI.from_model(trigger_db))
        del rule['trigger']['id']
        del rule['trigger']['name']
        for oldkey, value in six.iteritems(rule['criteria']):
            newkey = oldkey.replace(u'\u2024', '.')
            if oldkey != newkey:
                rule['criteria'][newkey] = value
                del rule['criteria'][oldkey]
        return cls(**rule)

    @classmethod
    def to_model(cls, rule):
        model = super(cls, cls).to_model(rule)
        trigger_db = TriggerService.create_trigger_db_from_rule(rule)
        model.trigger = reference.get_str_resource_ref_from_model(trigger_db)
        model.criteria = dict(getattr(rule, 'criteria', {}))
        for oldkey, value in six.iteritems(model.criteria):
            newkey = oldkey.replace('.', u'\u2024')
            if oldkey != newkey:
                model.criteria[newkey] = value
                del model.criteria[oldkey]
        validator.validate_criteria(model.criteria)
        model.action = ActionExecutionSpecDB()
        model.action.ref = rule.action['ref']
        model.action.parameters = rule.action['parameters']
        model.enabled = rule.enabled
        return model

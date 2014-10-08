import uuid
import datetime

from st2common.models.base import BaseAPI
from st2common.models.db.reactor import RuleDB, ActionExecutionSpecDB
from st2common.models.db.reactor import TriggerTypeDB, TriggerDB, TriggerInstanceDB
from st2common.persistence.reactor import Trigger
from st2common.util import reference
import st2common.validators.api.reactor as validator
import six


DATE_FORMAT = '%Y-%m-%d %H:%M:%S.%f'


class TriggerTypeAPI(BaseAPI):
    model = TriggerTypeDB
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
    def to_model(cls, triggertype):
        model = super(cls, cls).to_model(triggertype)
        model.payload_schema = getattr(triggertype, 'payload_schema', {})
        model.parameters_schema = getattr(triggertype, 'parameters_schema', {})
        return model


class TriggerAPI(BaseAPI):
    model = TriggerDB
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
            },
            'description': {
                'type': 'string'
            }
        },
        'required': ['type'],
        'additionalProperties': False
    }

    @classmethod
    def from_model(cls, model):
        trigger = cls._from_model(model)
        if 'type' in trigger:
            trigger['type'] = str(trigger['type'].get('name', ''))
        return cls(**trigger)

    @classmethod
    def to_model(cls, trigger):
        model = super(cls, cls).to_model(trigger)
        # assign a name if none is provided.
        model.name = trigger.name if hasattr(trigger, 'name') and trigger.name else \
            str(uuid.uuid4())
        model.type = {'name': getattr(trigger, 'type', None)}
        model.parameters = getattr(trigger, 'parameters', None)
        return model


class TriggerInstanceAPI(BaseAPI):
    model = TriggerInstanceDB
    schema = {
        'type': 'object',
        'properties': {
            'id': {
                'type': 'string'
            },
            'occurrence_time': {
                'type': 'string',
                'format': 'date-time'
            },
            'payload': {
                'type': 'object'
            },
            'trigger': {
                'type': 'string',
                'default': None
            }
        },
        'required': ['trigger'],
        'additionalProperties': False
    }

    @classmethod
    def from_model(cls, model):
        instance = cls._from_model(model)
        instance['occurrence_time'] = instance['occurrence_time'].isoformat()
        if 'trigger' in instance:
            instance['trigger'] = str(instance['trigger'].get('name', ''))
        return cls(**instance)

    @classmethod
    def to_model(cls, instance):
        model = super(cls, cls).to_model(instance)
        trigger = Trigger.get_by_name(instance.trigger)
        model.trigger = {'id': str(trigger.id), 'name': trigger.name}
        model.payload = instance.payload
        model.occurrence_time = datetime.datetime.strptime(instance.occurrence_time, DATE_FORMAT)
        return model


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
        rule = cls._from_model(model)
        rule['trigger'] = vars(TriggerAPI.from_model(reference.get_model_from_ref(Trigger,
                                                                                  model.trigger)))
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
        model.trigger = TriggerAPI(**rule.trigger)
        model.criteria = dict(rule.criteria)
        for oldkey, value in six.iteritems(model.criteria):
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


class RuleEnforcementAPI(BaseAPI):
    schema = {
        'type': 'object',
        'properties': {
            'id': {
                'type': 'string'
            },
            'rule': {
                'type': 'object'
            },
            'trigger_instance': {
                'type': 'object'
            },
            'action_execution': {
                'type': 'object'
            }
        },
        'required': ['rule', 'trigger_instance', 'action_execution'],
        'additionalProperties': False
    }

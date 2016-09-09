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

from st2common.constants.pack import DEFAULT_PACK_NAME
from st2common.models.api.base import BaseAPI
from st2common.models.api.base import APIUIDMixin
from st2common.models.api.tag import TagsHelper
from st2common.models.db.rule import RuleDB, RuleTypeDB, RuleTypeSpecDB, ActionExecutionSpecDB
from st2common.models.system.common import ResourceReference
from st2common.persistence.trigger import Trigger
import st2common.services.triggers as TriggerService
from st2common.util import reference
import st2common.validators.api.reactor as validator


class RuleTypeSpec(BaseAPI):
    schema = {
        'type': 'object',
        'properties': {
            'ref': {
                'type': 'string',
                'required': True
            },
            'parameters': {
                'type': 'object'
            }
        },
        'additionalProperties': False
    }


class ActionSpec(BaseAPI):
    schema = {
        'type': 'object',
        'properties': {
            'ref': {
                'type': 'string',
                'required': True
            },
            'parameters': {
                'type': 'object'
            }
        },
        'additionalProperties': False
    }


REQUIRED_ATTR_SCHEMAS = {
    'action': copy.deepcopy(ActionSpec.schema)
}

for k, v in six.iteritems(REQUIRED_ATTR_SCHEMAS):
    v.update({'required': True})


class RuleTypeAPI(BaseAPI):
    model = RuleTypeDB
    schema = {
        'title': 'RuleType',
        'description': 'A specific type of rule.',
        'type': 'object',
        'properties': {
            'id': {
                'description': 'The unique identifier for the action runner.',
                'type': 'string',
                'default': None
            },
            'name': {
                'description': 'The name of the action runner.',
                'type': 'string',
                'required': True
            },
            'description': {
                'description': 'The description of the action runner.',
                'type': 'string'
            },
            'enabled': {
                'type': 'boolean',
                'default': True
            },
            'parameters': {
                'type': 'object'
            }
        },
        'additionalProperties': False
    }

    @classmethod
    def to_model(cls, rule_type):
        name = getattr(rule_type, 'name', None)
        description = getattr(rule_type, 'description', None)
        enabled = getattr(rule_type, 'enabled', False)
        parameters = getattr(rule_type, 'parameters', {})

        return cls.model(name=name, description=description, enabled=enabled,
                         parameters=parameters)


class RuleAPI(BaseAPI, APIUIDMixin):
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
            "ref": {
                "description": "System computed user friendly reference for the action. \
                                Provided value will be overridden by computed value.",
                "type": "string"
            },
            'uid': {
                'type': 'string'
            },
            'name': {
                'type': 'string',
                'required': True
            },
            'pack': {
                'type': 'string'
            },
            'description': {
                'type': 'string'
            },
            'type': RuleTypeSpec.schema,
            'trigger': {
                'type': 'object',
                'required': True,
                'properties': {
                    'type': {
                        'type': 'string',
                        'required': True
                    },
                    'parameters': {
                        'type': 'object',
                        'default': {}
                    },
                    'ref': {
                        'type': 'string',
                        'required': False
                    }
                },
                'additionalProperties': True
            },
            'criteria': {
                'type': 'object',
                'default': {}
            },
            'action': REQUIRED_ATTR_SCHEMAS['action'],
            'enabled': {
                'type': 'boolean',
                'default': False
            },
            "tags": {
                "description": "User associated metadata assigned to this object.",
                "type": "array",
                "items": {"type": "object"}
            }
        },
        'additionalProperties': False
    }

    @classmethod
    def from_model(cls, model, mask_secrets=False, ignore_missing_trigger=False):
        rule = cls._from_model(model, mask_secrets=mask_secrets)
        trigger_db = reference.get_model_by_resource_ref(Trigger, model.trigger)

        if not ignore_missing_trigger and not trigger_db:
            raise ValueError('Missing TriggerDB object for rule %s' % (rule['id']))

        if trigger_db:
            rule['trigger'] = {
                'type': trigger_db.type,
                'parameters': trigger_db.parameters,
                'ref': model.trigger
            }

        rule['tags'] = TagsHelper.from_model(model.tags)
        return cls(**rule)

    @classmethod
    def to_model(cls, rule):
        kwargs = {}
        kwargs['name'] = getattr(rule, 'name', None)
        kwargs['description'] = getattr(rule, 'description', None)

        # Validate trigger parameters
        # Note: This must happen before we create a trigger, otherwise create trigger could fail
        # with a cryptic error
        trigger = getattr(rule, 'trigger', {})
        trigger_type_ref = trigger.get('type', None)
        parameters = trigger.get('parameters', {})

        validator.validate_trigger_parameters(trigger_type_ref=trigger_type_ref,
                                              parameters=parameters)

        # Create a trigger for the provided rule
        trigger_db = TriggerService.create_trigger_db_from_rule(rule)
        kwargs['trigger'] = reference.get_str_resource_ref_from_model(trigger_db)

        kwargs['pack'] = getattr(rule, 'pack', DEFAULT_PACK_NAME)
        kwargs['ref'] = ResourceReference.to_string_reference(pack=kwargs['pack'],
                                                              name=kwargs['name'])

        # Validate criteria
        kwargs['criteria'] = dict(getattr(rule, 'criteria', {}))
        validator.validate_criteria(kwargs['criteria'])

        kwargs['action'] = ActionExecutionSpecDB(ref=rule.action['ref'],
                                                 parameters=rule.action.get('parameters', {}))

        rule_type = dict(getattr(rule, 'type', {}))
        if rule_type:
            kwargs['type'] = RuleTypeSpecDB(ref=rule_type['ref'],
                                            parameters=rule_type.get('parameters', {}))

        kwargs['enabled'] = getattr(rule, 'enabled', False)
        kwargs['tags'] = TagsHelper.to_model(getattr(rule, 'tags', []))

        model = cls.model(**kwargs)
        return model


class RuleViewAPI(RuleAPI):

    # Always deep-copy to avoid breaking the original.
    schema = copy.deepcopy(RuleAPI.schema)
    # Update the schema to include the description properties
    schema['properties']['action'].update({
        'description': {
            'type': 'string'
        }
    })
    schema['properties']['trigger'].update({
        'description': {
            'type': 'string'
        }
    })

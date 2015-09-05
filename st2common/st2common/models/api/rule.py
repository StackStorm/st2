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
from st2common.models.api.tag import TagsHelper
from st2common.models.db.rule import RuleDB, ActionExecutionSpecDB
from st2common.models.system.common import ResourceReference
from st2common.persistence.trigger import Trigger
import st2common.services.triggers as TriggerService
from st2common.util import reference
import st2common.validators.api.reactor as validator


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
    def from_model(cls, model, mask_secrets=False):
        rule = cls._from_model(model, mask_secrets=mask_secrets)
        trigger_db = reference.get_model_by_resource_ref(Trigger, model.trigger)

        if not trigger_db:
            raise ValueError('Missing TriggerDB object for rule %s' % (rule['id']))
        rule['trigger'] = {
            'type': trigger_db.type,
            'parameters': trigger_db.parameters,
            'ref': model.trigger
        }
        rule['tags'] = TagsHelper.from_model(model.tags)
        return cls(**rule)

    @classmethod
    def to_model(cls, rule):
        name = getattr(rule, 'name', None)
        description = getattr(rule, 'description', None)

        # Create a trigger for the provided rule
        trigger_db = TriggerService.create_trigger_db_from_rule(rule)

        trigger = reference.get_str_resource_ref_from_model(trigger_db)
        criteria = dict(getattr(rule, 'criteria', {}))
        pack = getattr(rule, 'pack', DEFAULT_PACK_NAME)
        ref = ResourceReference.to_string_reference(pack=pack, name=name)

        # Validate criteria
        validator.validate_criteria(criteria)

        # Validate trigger parameters
        validator.validate_trigger_parameters(trigger_db=trigger_db)

        action = ActionExecutionSpecDB(ref=rule.action['ref'],
                                       parameters=rule.action.get('parameters', {}))

        enabled = getattr(rule, 'enabled', False)
        tags = TagsHelper.to_model(getattr(rule, 'tags', []))

        model = cls.model(name=name, description=description, pack=pack, ref=ref, trigger=trigger,
                          criteria=criteria, action=action, enabled=enabled, tags=tags)
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

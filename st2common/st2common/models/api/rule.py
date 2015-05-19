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

from st2common.models.api.base import BaseAPI
from st2common.models.api.reactor import TriggerAPI
from st2common.models.api.tag import TagsHelper
from st2common.models.db.reactor import RuleDB, ActionExecutionSpecDB
from st2common.models.system.common import ResourceReference
from st2common.persistence.reactor import Trigger
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
            'name': {
                'type': 'string',
                'required': True
            },
            'pack': {
                'type': 'string'
            },
            "ref": {
                "description": "System computed user friendly reference for the action. \
                                Provided value will be overridden by computed value.",
                "type": "string"
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
                'default': True
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
    def from_model(cls, model):
        rule = cls._from_model(model)
        trigger_db = reference.get_model_by_resource_ref(Trigger, model.trigger)

        if not trigger_db:
            raise ValueError('Missing TriggerDB object for rule %s' % (rule['id']))

        rule['trigger'] = vars(TriggerAPI.from_model(trigger_db))
        del rule['trigger']['id']
        del rule['trigger']['name']
        rule['tags'] = TagsHelper.from_model(model.tags)
        return cls(**rule)

    @classmethod
    def to_model(cls, rule):
        model = super(cls, cls).to_model(rule)
        trigger_db = TriggerService.create_trigger_db_from_rule(rule)
        model.trigger = reference.get_str_resource_ref_from_model(trigger_db)
        model.criteria = dict(getattr(rule, 'criteria', {}))
        model.pack = str(rule.pack)
        model.ref = ResourceReference.to_string_reference(pack=model.pack, name=model.name)
        validator.validate_criteria(model.criteria)
        model.action = ActionExecutionSpecDB()
        model.action.ref = rule.action['ref']
        model.action.parameters = rule.action['parameters']
        model.enabled = rule.enabled
        model.tags = TagsHelper.to_model(getattr(rule, 'tags', []))
        return model

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

import six

from st2common.models.api.base import BaseAPI
from st2common.models.db.rule_enforcement import RuleEnforcementDB, RuleReferenceSpecDB
from st2common.util import isotime


class RuleReferenceSpec(BaseAPI):
    schema = {
        'type': 'object',
        'properties': {
            'ref': {
                'type': 'string',
                'required': True,
            },
            'uid': {
                'type': 'string',
                'required': True,
            },
            'id': {
                'type': 'string',
                'required': False,
            },
        },
        'additionalProperties': False
    }


class RuleEnforcementAPI(BaseAPI):
    model = RuleEnforcementDB
    schema = {
        'title': 'RuleEnforcement',
        'description': 'A specific instance of rule enforcement.',
        'type': 'object',
        'properties': {
            'trigger_instance_id': {
                'description': 'The unique identifier for the trigger instance ' +
                               'that flipped the rule.',
                'type': 'string',
                'required': True
            },
            'execution_id': {
                'description': 'ID of the action execution that was invoked as a response.',
                'type': 'string',
                'required': True
            },
            'rule': RuleReferenceSpec.schema,
            'enforced_at': {
                'description': 'Timestamp when rule enforcement happened.',
                'type': 'string',
                'required': True
            }
        },
        'additionalProperties': False
    }

    @classmethod
    def to_model(cls, rule_enforcement):
        trigger_instance_id = getattr(rule_enforcement, 'trigger_instance_id', None)
        execution_id = getattr(rule_enforcement, 'execution_id', None)
        enforced_at = getattr(rule_enforcement, 'enforced_at', None)

        rule_ref_model = dict(getattr(rule_enforcement, 'rule', {}))
        rule = RuleReferenceSpecDB(ref=rule_ref_model['ref'], id=rule_ref_model['id'],
                                   uid=rule_ref_model['uid'])

        if enforced_at:
            enforced_at = isotime.parse(enforced_at)

        return cls.model(trigger_instance_id=trigger_instance_id, execution_id=execution_id,
                         enforced_at=enforced_at, rule=rule)

    @classmethod
    def from_model(cls, model, mask_secrets=False):
        doc = cls._from_model(model, mask_secrets=mask_secrets)
        enforced_at = isotime.format(model.enforced_at, offset=False)
        doc['enforced_at'] = enforced_at
        attrs = {attr: value for attr, value in six.iteritems(doc) if value}
        return cls(**attrs)

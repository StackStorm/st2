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

from st2common import log as logging
from st2api.controllers import resource
from st2common.models.api.rule import RuleViewAPI
from st2common.models.api.base import jsexpose
from st2common.persistence.action import Action
from st2common.persistence.rule import Rule
from st2common.persistence.trigger import TriggerType, Trigger
from st2common.rbac.types import PermissionType
from st2common.rbac.decorators import request_user_has_permission
from st2common.rbac.decorators import request_user_has_resource_permission

http_client = six.moves.http_client

LOG = logging.getLogger(__name__)


__all__ = ['RuleViewController']


class RuleViewController(resource.ContentPackResourceController):

    model = RuleViewAPI
    access = Rule
    supported_filters = {
        'name': 'name',
        'pack': 'pack'
    }

    query_options = {
        'sort': ['pack', 'name']
    }

    include_reference = True

    @request_user_has_permission(permission_type=PermissionType.RULE_VIEW)
    @jsexpose()
    def get_all(self, **kwargs):
        rules = self._get_all(**kwargs)
        return self._append_view_properties(rules)

    @request_user_has_resource_permission(permission_type=PermissionType.RULE_VIEW)
    @jsexpose(arg_types=[str])
    def get_one(self, ref_or_id):
        rule = self._get_one(ref_or_id)
        return self._append_view_properties([rule])[0]

    def _append_view_properties(self, rules):
        action_by_refs, trigger_by_refs, trigger_type_by_refs = self._get_referenced_models(rules)

        for rule in rules:
            action_db = action_by_refs[rule.action['ref']]
            rule.action['description'] = action_db.description if action_db else ''

            trigger_db = trigger_by_refs[rule.trigger['ref']]
            rule.trigger['description'] = trigger_db.description if trigger_db else ''

            # If description is not found in trigger get description from triggertype
            if not rule.trigger['description']:
                trigger_type_db = trigger_type_by_refs[rule.trigger['type']]
                rule.trigger['description'] = trigger_type_db.description if trigger_type_db else ''

        return rules

    def _get_referenced_models(self, rules):
        """
        Reduces the number of queries to be made to the DB by creating sets of Actions, Triggers
        and TriggerTypes.
        """
        action_refs = set()
        trigger_refs = set()
        trigger_type_refs = set()

        for rule in rules:
            action_refs.add(rule.action['ref'])
            trigger_refs.add(rule.trigger['ref'])
            trigger_type_refs.add(rule.trigger['type'])

        action_by_refs = {}
        trigger_by_refs = {}
        trigger_type_by_refs = {}

        for ref in action_refs:
            action_by_refs[ref] = Action.get_by_ref(ref)

        for ref in trigger_refs:
            trigger_by_refs[ref] = Trigger.get_by_ref(ref)

        for ref in trigger_type_refs:
            trigger_type_by_refs[ref] = TriggerType.get_by_ref(ref)

        return (action_by_refs, trigger_by_refs, trigger_type_by_refs)

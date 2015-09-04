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

from mongoengine.queryset import Q

from st2common import log as logging
from st2api.controllers import resource
from st2common.models.api.rule import RuleViewAPI
from st2common.models.api.base import jsexpose
from st2common.models.system.common import ResourceReference
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
    """
    Add some extras to a Rule object to make it easier for UI to render a rule. The additions
    do not necessarily belong in the Rule itself but are still valuable augmentations.

    :Example:
        {
            "action": {
                "description": "Action that executes an arbitrary Linux command on the localhost.",
                "parameters": {
                    "cmd": "echo \"{{trigger.executed_at}}\""
                },
                "ref": "core.local"
            },
            "criteria": {},
            "description": "Sample rule using an Interval Timer.",
            "enabled": false,
            "id": "55ea221832ed35759cf3b312",
            "name": "sample.with_timer",
            "pack": "examples",
            "ref": "examples.sample.with_timer",
            "tags": [],
            "trigger": {
                "description": "Triggers on specified intervals. e.g. every 30s, 1week etc.",
                "parameters": {
                    "delta": 5,
                    "unit": "seconds"
                },
                "ref": "core.4ad65602-6fb4-4c89-b0f2-b990d7b68bad",
                "type": "core.st2.IntervalTimer"
            },
            "uid": "rule:examples:sample.with_timer"
        }

    The `description` fields in action and trigger are augmented properties.
    """

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
            action_db = action_by_refs.get(rule.action['ref'], None)
            rule.action['description'] = action_db.description if action_db else ''

            trigger_db = trigger_by_refs.get(rule.trigger['ref'], None)
            rule.trigger['description'] = trigger_db.description if trigger_db else ''

            # If description is not found in trigger get description from triggertype
            if not rule.trigger['description']:
                trigger_type_db = trigger_type_by_refs.get(rule.trigger['type'], None)
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

        # The functions that will return args that can used to query.
        ref_query_args = lambda resource_ref: {'ref': resource_ref.ref}
        name_pack_query_args = lambda resource_ref: {'name': resource_ref.name,
                                                     'pack': resource_ref.pack}
        action_dbs = self._get_entities(model_persistence=Action,
                                        refs=action_refs,
                                        query_args=ref_query_args)
        for action_db in action_dbs:
            action_by_refs[action_db.ref] = action_db

        trigger_dbs = self._get_entities(model_persistence=Trigger,
                                         refs=trigger_refs,
                                         query_args=name_pack_query_args)
        for trigger_db in trigger_dbs:
            trigger_by_refs[trigger_db.get_reference().ref] = trigger_db

        trigger_type_dbs = self._get_entities(model_persistence=TriggerType,
                                              refs=trigger_type_refs,
                                              query_args=name_pack_query_args)
        for trigger_type_db in trigger_type_dbs:
            trigger_type_by_refs[trigger_type_db.get_reference().ref] = trigger_type_db

        return (action_by_refs, trigger_by_refs, trigger_type_by_refs)

    def _get_entities(self, model_persistence, refs, query_args):
        """
        Returns all the entities for the supplied refs. model_persistence is the persistence
        object that will be used to get to the correct query method and the query_args function
        to return the ref specific query argument.

        This is such a weirdly specific method that it is likely better only in this context.
        """
        q = None
        for ref in refs:
            resource_ref = ResourceReference.from_string_reference(ref=ref)
            if not q:
                q = Q(**query_args(resource_ref))
            else:
                q |= Q(**query_args(resource_ref))
        if q:
            return model_persistence._get_impl().model.objects(q)
        return []

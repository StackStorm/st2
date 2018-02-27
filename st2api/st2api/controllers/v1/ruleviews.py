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

from mongoengine.queryset import Q
from oslo_config import cfg

from st2common import log as logging
from st2api.controllers import resource
from st2common.models.api.rule import RuleViewAPI
from st2common.models.db.auth import UserDB
from st2common.models.system.common import ResourceReference
from st2common.persistence.action import Action
from st2common.persistence.rule import Rule
from st2common.persistence.trigger import TriggerType, Trigger
from st2common.rbac.types import PermissionType
from st2common.router import Response

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
        'pack': 'pack',
        'user': 'context.user'
    }

    query_options = {
        'sort': ['pack', 'name']
    }

    include_reference = True

    def get_all(self, sort=None, offset=0, limit=None, requester_user=None, **raw_filters):
        if not requester_user:
            requester_user = UserDB(cfg.CONF.system_user.user)

        rules = self._get_all(sort=sort,
                              offset=offset,
                              limit=limit,
                              raw_filters=raw_filters,
                              requester_user=requester_user)
        result = self._append_view_properties(rules.json)
        rules.json = result
        return rules

    def _get_all(self, exclude_fields=None, sort=None, offset=0, limit=None, query_options=None,
                 from_model_kwargs=None, raw_filters=None, requester_user=None):
        """
        :param exclude_fields: A list of object fields to exclude.
        :type exclude_fields: ``list``
        """
        raw_filters = copy.deepcopy(raw_filters) or {}

        exclude_fields = exclude_fields or []
        query_options = query_options if query_options else self.query_options

        # TODO: Why do we use comma delimited string, user can just specify
        # multiple values using ?sort=foo&sort=bar and we get a list back
        sort = sort.split(',') if sort else []

        db_sort_values = []
        for sort_key in sort:
            if sort_key.startswith('-'):
                direction = '-'
                sort_key = sort_key[1:]
            elif sort_key.startswith('+'):
                direction = '+'
                sort_key = sort_key[1:]
            else:
                direction = ''

            if sort_key not in self.supported_filters:
                # Skip unsupported sort key
                continue

            sort_value = direction + self.supported_filters[sort_key]
            db_sort_values.append(sort_value)

        default_sort_values = copy.copy(query_options.get('sort'))
        raw_filters['sort'] = db_sort_values if db_sort_values else default_sort_values

        # TODO: To protect us from DoS, we need to make max_limit mandatory
        offset = int(offset)
        if offset >= 2**31:
            raise ValueError('Offset "%s" specified is more than 32-bit int' % (offset))

        limit = resource.validate_limit_query_param(limit=limit, requester_user=requester_user)
        eop = offset + int(limit) if limit else None

        filters = {}
        for k, v in six.iteritems(self.supported_filters):
            filter_value = raw_filters.get(k, None)

            if not filter_value:
                continue

            value_transform_function = self.filter_transform_functions.get(k, None)
            value_transform_function = value_transform_function or (lambda value: value)
            filter_value = value_transform_function(value=filter_value)

            if k == 'id' and isinstance(filter_value, list):
                filters[k + '__in'] = filter_value
            else:
                filters['__'.join(v.split('.'))] = filter_value

        instances = self.access.query(exclude_fields=exclude_fields, **filters)
        if limit == 1:
            # Perform the filtering on the DB side
            instances = instances.limit(limit)

        from_model_kwargs = from_model_kwargs or {}
        from_model_kwargs.update(self.from_model_kwargs)

        result = []
        for instance in instances[offset:eop]:
            item = self.model.from_model(instance, **from_model_kwargs)
            if cfg.CONF.rbac.enable and not cfg.CONF.rbac.permission_isolation:
                result.append(item)
            elif requester_user.name == cfg.CONF.system_user.user:
                result.append(item)
            else:
                user = item.context.get('user', None)
                if user and user == requester_user.name:
                    result.append(item)

        resp = Response(json=result)
        resp.headers['X-Total-Count'] = str(instances.count())

        if limit:
            resp.headers['X-Limit'] = str(limit)

        return resp

    def get_one(self, ref_or_id, requester_user):
        rule = self._get_one(ref_or_id, permission_type=PermissionType.RULE_VIEW,
                             requester_user=requester_user)
        result = self._append_view_properties([rule.json])[0]
        rule.json = result
        return rule

    def _append_view_properties(self, rules):
        action_by_refs, trigger_by_refs, trigger_type_by_refs = self._get_referenced_models(rules)

        for rule in rules:
            action_db = action_by_refs.get(rule['action']['ref'], None)
            rule['action']['description'] = action_db.description if action_db else ''

            rule['trigger']['description'] = ''

            trigger_db = trigger_by_refs.get(rule['trigger']['ref'], None)
            if trigger_db:
                rule['trigger']['description'] = trigger_db.description

            # If description is not found in trigger get description from triggertype
            if not rule['trigger']['description']:
                trigger_type_db = trigger_type_by_refs.get(rule['trigger']['type'], None)
                if trigger_type_db:
                    rule['trigger']['description'] = trigger_type_db.description

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
            action_refs.add(rule['action']['ref'])
            trigger_refs.add(rule['trigger']['ref'])
            trigger_type_refs.add(rule['trigger']['type'])

        action_by_refs = {}
        trigger_by_refs = {}
        trigger_type_by_refs = {}

        # The functions that will return args that can used to query.
        def ref_query_args(ref):
            return {'ref': ref}

        def name_pack_query_args(ref):
            resource_ref = ResourceReference.from_string_reference(ref=ref)
            return {'name': resource_ref.name, 'pack': resource_ref.pack}

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
            if not q:
                q = Q(**query_args(ref))
            else:
                q |= Q(**query_args(ref))
        if q:
            return model_persistence._get_impl().model.objects(q)
        return []


rule_view_controller = RuleViewController()

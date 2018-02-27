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
import jsonschema

from mongoengine import ValidationError
from oslo_config import cfg

from st2common import log as logging
from st2common.exceptions.apivalidation import ValueValidationException
from st2common.exceptions.triggers import TriggerDoesNotExistException
from st2api.controllers import resource
from st2api.controllers.controller_transforms import transform_to_bool
from st2api.controllers.v1.ruleviews import RuleViewController
from st2common.models.api.rule import RuleAPI
from st2common.models.db.auth import UserDB
from st2common.persistence.rule import Rule
from st2common.rbac.types import PermissionType
from st2common.rbac import utils as rbac_utils
from st2common.rbac.utils import assert_user_has_rule_trigger_and_action_permission
from st2common.rbac.utils import assert_user_is_admin_if_user_query_param_is_provided
from st2common.router import exc
from st2common.router import abort
from st2common.router import Response
from st2common.services.triggers import cleanup_trigger_db_for_rule, increment_trigger_ref_count

http_client = six.moves.http_client

LOG = logging.getLogger(__name__)


class RuleController(resource.ContentPackResourceController):
    """
        Implements the RESTful web endpoint that handles
        the lifecycle of Rules in the system.
    """
    views = RuleViewController()

    model = RuleAPI
    access = Rule
    supported_filters = {
        'name': 'name',
        'pack': 'pack',
        'action': 'action.ref',
        'trigger': 'trigger',
        'enabled': 'enabled',
        'user': 'context.user'
    }

    filter_transform_functions = {
        'enabled': transform_to_bool
    }

    query_options = {
        'sort': ['pack', 'name']
    }

    include_reference = True

    def get_all(self, sort=None, offset=0, limit=None, requester_user=None, **raw_filters):
        if not requester_user:
                        requester_user = UserDB(cfg.CONF.system_user.user)

        from_model_kwargs = {'ignore_missing_trigger': True}
        return self._get_all(from_model_kwargs=from_model_kwargs,
                             sort=sort,
                             offset=offset,
                             limit=limit,
                             raw_filters=raw_filters,
                             requester_user=requester_user)

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
            if not cfg.CONF.rbac.permission_isolation:
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
        from_model_kwargs = {'ignore_missing_trigger': True}
        return super(RuleController, self)._get_one(ref_or_id, from_model_kwargs=from_model_kwargs,
                                                    requester_user=requester_user,
                                                    permission_type=PermissionType.RULE_VIEW)

    def post(self, rule, requester_user):
        """
            Create a new rule.

            Handles requests:
                POST /rules/
        """

        permission_type = PermissionType.RULE_CREATE
        rbac_utils.assert_user_has_resource_api_permission(user_db=requester_user,
                                                           resource_api=rule,
                                                           permission_type=permission_type)

        if not requester_user:
            requester_user = UserDB(cfg.CONF.system_user.user)

        # Validate that the authenticated user is admin if user query param is provided
        user = requester_user.name
        assert_user_is_admin_if_user_query_param_is_provided(user_db=requester_user,
                                                             user=user)

        if not hasattr(rule, 'context'):
            rule.context = dict()

        rule.context['user'] = user

        try:
            rule_db = RuleAPI.to_model(rule)
            LOG.debug('/rules/ POST verified RuleAPI and formulated RuleDB=%s', rule_db)

            # Check referenced trigger and action permissions
            # Note: This needs to happen after "to_model" call since to_model performs some
            # validation (trigger exists, etc.)
            assert_user_has_rule_trigger_and_action_permission(user_db=requester_user,
                                                               rule_api=rule)

            rule_db = Rule.add_or_update(rule_db)
            # After the rule has been added modify the ref_count. This way a failure to add
            # the rule due to violated constraints will have no impact on ref_count.
            increment_trigger_ref_count(rule_api=rule)
        except (ValidationError, ValueError) as e:
            LOG.exception('Validation failed for rule data=%s.', rule)
            abort(http_client.BAD_REQUEST, str(e))
            return
        except (ValueValidationException, jsonschema.ValidationError) as e:
            LOG.exception('Validation failed for rule data=%s.', rule)
            abort(http_client.BAD_REQUEST, str(e))
            return
        except TriggerDoesNotExistException as e:
            msg = ('Trigger "%s" defined in the rule does not exist in system or it\'s missing '
                   'required "parameters" attribute' % (rule.trigger['type']))
            LOG.exception(msg)
            abort(http_client.BAD_REQUEST, msg)
            return

        extra = {'rule_db': rule_db}
        LOG.audit('Rule created. Rule.id=%s' % (rule_db.id), extra=extra)
        rule_api = RuleAPI.from_model(rule_db)

        return Response(json=rule_api, status=exc.HTTPCreated.code)

    def put(self, rule, rule_ref_or_id, requester_user):
        rule_db = self._get_by_ref_or_id(rule_ref_or_id)

        permission_type = PermissionType.RULE_MODIFY
        rbac_utils.assert_user_has_resource_db_permission(user_db=requester_user,
                                                          resource_db=rule,
                                                          permission_type=permission_type)

        LOG.debug('PUT /rules/ lookup with id=%s found object: %s', rule_ref_or_id, rule_db)

        if not requester_user:
            requester_user = UserDB(cfg.CONF.system_user.user)
        # Validate that the authenticated user is admin if user query param is provided
        user = requester_user.name
        assert_user_is_admin_if_user_query_param_is_provided(user_db=requester_user,
                                                             user=user)

        if not hasattr(rule, 'context'):
            rule.context = dict()
        rule.context['user'] = user

        try:
            if rule.id is not None and rule.id is not '' and rule.id != rule_ref_or_id:
                LOG.warning('Discarding mismatched id=%s found in payload and using uri_id=%s.',
                            rule.id, rule_ref_or_id)
            old_rule_db = rule_db

            try:
                rule_db = RuleAPI.to_model(rule)
            except TriggerDoesNotExistException as e:
                abort(http_client.BAD_REQUEST, str(e))
                return

            # Check referenced trigger and action permissions
            # Note: This needs to happen after "to_model" call since to_model performs some
            # validation (trigger exists, etc.)
            assert_user_has_rule_trigger_and_action_permission(user_db=requester_user,
                                                               rule_api=rule)

            rule_db.id = rule_ref_or_id
            rule_db = Rule.add_or_update(rule_db)
            # After the rule has been added modify the ref_count. This way a failure to add
            # the rule due to violated constraints will have no impact on ref_count.
            increment_trigger_ref_count(rule_api=rule)
        except (ValueValidationException, jsonschema.ValidationError, ValueError) as e:
            LOG.exception('Validation failed for rule data=%s', rule)
            abort(http_client.BAD_REQUEST, str(e))
            return

        # use old_rule_db for cleanup.
        cleanup_trigger_db_for_rule(old_rule_db)

        extra = {'old_rule_db': old_rule_db, 'new_rule_db': rule_db}
        LOG.audit('Rule updated. Rule.id=%s.' % (rule_db.id), extra=extra)
        rule_api = RuleAPI.from_model(rule_db)

        return rule_api

    def delete(self, rule_ref_or_id, requester_user):
        """
            Delete a rule.

            Handles requests:
                DELETE /rules/1
        """
        rule_db = self._get_by_ref_or_id(ref_or_id=rule_ref_or_id)

        permission_type = PermissionType.RULE_DELETE
        rbac_utils.assert_user_has_resource_db_permission(user_db=requester_user,
                                                          resource_db=rule_db,
                                                          permission_type=permission_type)

        LOG.debug('DELETE /rules/ lookup with id=%s found object: %s', rule_ref_or_id, rule_db)
        try:
            Rule.delete(rule_db)
        except Exception as e:
            LOG.exception('Database delete encountered exception during delete of id="%s".',
                          rule_ref_or_id)
            abort(http_client.INTERNAL_SERVER_ERROR, str(e))
            return

        # use old_rule_db for cleanup.
        cleanup_trigger_db_for_rule(rule_db)

        extra = {'rule_db': rule_db}
        LOG.audit('Rule deleted. Rule.id=%s.' % (rule_db.id), extra=extra)

        return Response(status=http_client.NO_CONTENT)


rule_controller = RuleController()

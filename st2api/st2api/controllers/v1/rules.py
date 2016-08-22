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
import jsonschema
import pecan
from pecan import abort
from mongoengine import ValidationError

from st2common import log as logging
from st2common.exceptions.apivalidation import ValueValidationException
from st2common.exceptions.triggers import TriggerDoesNotExistException
from st2api.controllers import resource
from st2api.controllers.controller_transforms import transform_to_bool
from st2api.controllers.v1.ruleviews import RuleViewController
from st2common.models.api.rule import RuleAPI
from st2common.models.api.base import jsexpose
from st2common.persistence.rule import Rule
from st2common.rbac.types import PermissionType
from st2common.rbac.decorators import request_user_has_permission
from st2common.rbac.decorators import request_user_has_resource_api_permission
from st2common.rbac.decorators import request_user_has_resource_db_permission
from st2common.rbac.utils import assert_request_user_has_rule_trigger_and_action_permission
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
        'enabled': 'enabled'
    }

    filter_transform_functions = {
        'enabled': transform_to_bool
    }

    query_options = {
        'sort': ['pack', 'name']
    }

    include_reference = True

    @request_user_has_permission(permission_type=PermissionType.RULE_LIST)
    @jsexpose()
    def get_all(self, **kwargs):
        from_model_kwargs = {'ignore_missing_trigger': True}
        return super(RuleController, self)._get_all(from_model_kwargs=from_model_kwargs, **kwargs)

    @request_user_has_resource_db_permission(permission_type=PermissionType.RULE_VIEW)
    @jsexpose(arg_types=[str])
    def get_one(self, ref_or_id):
        from_model_kwargs = {'ignore_missing_trigger': True}
        return super(RuleController, self)._get_one(ref_or_id, from_model_kwargs=from_model_kwargs)

    @jsexpose(body_cls=RuleAPI, status_code=http_client.CREATED)
    @request_user_has_resource_api_permission(permission_type=PermissionType.RULE_CREATE)
    def post(self, rule):
        """
            Create a new rule.

            Handles requests:
                POST /rules/
        """
        try:
            rule_db = RuleAPI.to_model(rule)
            LOG.debug('/rules/ POST verified RuleAPI and formulated RuleDB=%s', rule_db)

            # Check referenced trigger and action permissions
            # Note: This needs to happen after "to_model" call since to_model performs some
            # validation (trigger exists, etc.)
            assert_request_user_has_rule_trigger_and_action_permission(request=pecan.request,
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

        return rule_api

    @request_user_has_resource_db_permission(permission_type=PermissionType.RULE_MODIFY)
    @jsexpose(arg_types=[str], body_cls=RuleAPI)
    def put(self, rule, rule_ref_or_id):
        rule_db = self._get_by_ref_or_id(rule_ref_or_id)
        LOG.debug('PUT /rules/ lookup with id=%s found object: %s', rule_ref_or_id, rule_db)

        try:
            if rule.id is not None and rule.id is not '' and rule.id != rule_ref_or_id:
                LOG.warning('Discarding mismatched id=%s found in payload and using uri_id=%s.',
                            rule.id, rule_ref_or_id)
            old_rule_db = rule_db
            rule_db = RuleAPI.to_model(rule)

            # Check referenced trigger and action permissions
            # Note: This needs to happen after "to_model" call since to_model performs some
            # validation (trigger exists, etc.)
            assert_request_user_has_rule_trigger_and_action_permission(request=pecan.request,
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

    @request_user_has_resource_db_permission(permission_type=PermissionType.RULE_DELETE)
    @jsexpose(arg_types=[str], status_code=http_client.NO_CONTENT)
    def delete(self, rule_ref_or_id):
        """
            Delete a rule.

            Handles requests:
                DELETE /rules/1
        """
        rule_db = self._get_by_ref_or_id(ref_or_id=rule_ref_or_id)
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

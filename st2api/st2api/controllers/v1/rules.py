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
from pecan import abort
from mongoengine import ValidationError

from st2common import log as logging
from st2common.constants.pack import DEFAULT_PACK_NAME
from st2common.exceptions.apivalidation import ValueValidationException
from st2common.exceptions.db import StackStormDBObjectConflictError
from st2common.exceptions.triggers import TriggerDoesNotExistException
from st2api.controllers import resource
from st2common.models.api.rule import RuleAPI
from st2common.models.api.base import jsexpose
from st2common.persistence.rule import Rule

http_client = six.moves.http_client

LOG = logging.getLogger(__name__)


class RuleController(resource.ContentPackResourceController):
    """
        Implements the RESTful web endpoint that handles
        the lifecycle of Rules in the system.
    """

    model = RuleAPI
    access = Rule
    supported_filters = {
        'name': 'name',
        'pack': 'pack'
    }

    query_options = {
        'sort': ['pack', 'name']
    }

    include_reference = True

    @jsexpose(body_cls=RuleAPI, status_code=http_client.CREATED)
    def post(self, rule):
        """
            Create a new rule.

            Handles requests:
                POST /rules/
        """
        try:
            if not hasattr(rule, 'pack'):
                setattr(rule, 'pack', DEFAULT_PACK_NAME)
            rule_db = RuleAPI.to_model(rule)
            LOG.debug('/rules/ POST verified RuleAPI and formulated RuleDB=%s', rule_db)
            rule_db = Rule.add_or_update(rule_db)
        except (ValidationError, ValueError) as e:
            LOG.exception('Validation failed for rule data=%s.', rule)
            abort(http_client.BAD_REQUEST, str(e))
            return
        except ValueValidationException as e:
            LOG.exception('Validation failed for rule data=%s.', rule)
            abort(http_client.BAD_REQUEST, str(e))
            return
        except TriggerDoesNotExistException as e:
            msg = 'Trigger %s in rule does not exist in system' % rule.trigger['type']
            LOG.exception(msg)
            abort(http_client.BAD_REQUEST, msg)
            return
        except StackStormDBObjectConflictError as e:
            LOG.warn('Rule creation of %s failed with uniqueness conflict. Exception %s',
                     rule, str(e))
            abort(http_client.CONFLICT, str(e), body={'conflict-id': e.conflict_id})
            return

        extra = {'rule_db': rule_db}
        LOG.audit('Rule created. Rule.id=%s' % (rule_db.id), extra=extra)
        rule_api = RuleAPI.from_model(rule_db)

        return rule_api

    @jsexpose(arg_types=[str], body_cls=RuleAPI)
    def put(self, rule_ref_or_id, rule):
        try:
            rule_db = self._get_by_ref_or_id(rule_ref_or_id)
        except Exception as e:
            LOG.exception(e.message)
            abort(http_client.NOT_FOUND, e.message)
            return

        LOG.debug('PUT /rules/ lookup with id=%s found object: %s', rule_ref_or_id, rule_db)

        try:
            if rule.id is not None and rule.id is not '' and rule.id != rule_ref_or_id:
                LOG.warning('Discarding mismatched id=%s found in payload and using uri_id=%s.',
                            rule.id, rule_ref_or_id)
            old_rule_db = rule_db
            rule_db = RuleAPI.to_model(rule)
            rule_db.id = rule_ref_or_id
            rule_db = Rule.add_or_update(rule_db)
        except (ValidationError, ValueError) as e:
            LOG.exception('Validation failed for rule data=%s', rule)
            abort(http_client.BAD_REQUEST, str(e))
            return

        extra = {'old_rule_db': old_rule_db, 'new_rule_db': rule_db}
        LOG.audit('Rule updated. Rule.id=%s.' % (rule_db.id), extra=extra)
        rule_api = RuleAPI.from_model(rule_db)

        return rule_api

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

        extra = {'rule_db': rule_db}
        LOG.audit('Rule deleted. Rule.id=%s.' % (rule_db.id), extra=extra)

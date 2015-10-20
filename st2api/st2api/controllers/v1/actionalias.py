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

import pecan
import six

from mongoengine import ValidationError
from st2api.controllers import resource
from st2common import log as logging
from st2common.exceptions.apivalidation import ValueValidationException
from st2common.models.api.action import ActionAliasAPI
from st2common.persistence.actionalias import ActionAlias
from st2common.models.api.base import jsexpose
from st2common.rbac.types import PermissionType
from st2common.rbac.decorators import request_user_has_permission
from st2common.rbac.decorators import request_user_has_resource_api_permission
from st2common.rbac.decorators import request_user_has_resource_db_permission

http_client = six.moves.http_client

LOG = logging.getLogger(__name__)


class ActionAliasController(resource.ContentPackResourceController):
    """
        Implements the RESTful interface for ActionAliases.
    """
    model = ActionAliasAPI
    access = ActionAlias
    supported_filters = {
        'name': 'name',
        'pack': 'pack'
    }

    query_options = {
        'sort': ['pack', 'name']
    }

    @request_user_has_permission(permission_type=PermissionType.ACTION_ALIAS_LIST)
    @jsexpose()
    def get_all(self, **kwargs):
        return super(ActionAliasController, self)._get_all(**kwargs)

    @request_user_has_resource_db_permission(permission_type=PermissionType.ACTION_ALIAS_VIEW)
    @jsexpose(arg_types=[str])
    def get_one(self, ref_or_id):
        return super(ActionAliasController, self)._get_one(ref_or_id)

    @jsexpose(body_cls=ActionAliasAPI, status_code=http_client.CREATED)
    @request_user_has_resource_api_permission(permission_type=PermissionType.ACTION_ALIAS_CREATE)
    def post(self, action_alias):
        """
            Create a new ActionAlias.

            Handles requests:
                POST /actionalias/
        """
        try:
            action_alias_db = ActionAliasAPI.to_model(action_alias)
            LOG.debug('/actionalias/ POST verified ActionAliasAPI and formulated ActionAliasDB=%s',
                      action_alias_db)
            action_alias_db = ActionAlias.add_or_update(action_alias_db)
        except (ValidationError, ValueError, ValueValidationException) as e:
            LOG.exception('Validation failed for action alias data=%s.', action_alias)
            pecan.abort(http_client.BAD_REQUEST, str(e))
            return

        extra = {'action_alias_db': action_alias_db}
        LOG.audit('Action alias created. ActionAlias.id=%s' % (action_alias_db.id), extra=extra)
        action_alias_api = ActionAliasAPI.from_model(action_alias_db)

        return action_alias_api

    @request_user_has_resource_db_permission(permission_type=PermissionType.ACTION_MODIFY)
    @jsexpose(arg_types=[str], body_cls=ActionAliasAPI)
    def put(self, action_alias_ref_or_id, action_alias):
        action_alias_db = self._get_by_ref_or_id(ref_or_id=action_alias_ref_or_id)
        LOG.debug('PUT /actionalias/ lookup with id=%s found object: %s', action_alias_ref_or_id,
                  action_alias_db)

        try:
            if action_alias.id is not None and action_alias.id is not '' and \
               action_alias.id != action_alias_ref_or_id:
                LOG.warning('Discarding mismatched id=%s found in payload and using uri_id=%s.',
                            action_alias.id, action_alias_ref_or_id)
            old_action_alias_db = action_alias_db
            action_alias_db = ActionAliasAPI.to_model(action_alias)
            action_alias_db.id = action_alias_ref_or_id
            action_alias_db = ActionAlias.add_or_update(action_alias_db)
        except (ValidationError, ValueError) as e:
            LOG.exception('Validation failed for action alias data=%s', action_alias)
            pecan.abort(http_client.BAD_REQUEST, str(e))
            return

        extra = {'old_action_alias_db': old_action_alias_db, 'new_action_alias_db': action_alias_db}
        LOG.audit('Action alias updated. ActionAlias.id=%s.' % (action_alias_db.id), extra=extra)
        action_alias_api = ActionAliasAPI.from_model(action_alias_db)

        return action_alias_api

    @request_user_has_resource_db_permission(permission_type=PermissionType.ACTION_ALIAS_DELETE)
    @jsexpose(arg_types=[str], status_code=http_client.NO_CONTENT)
    def delete(self, action_alias_ref_or_id):
        """
            Delete an action alias.

            Handles requests:
                DELETE /actionalias/1
        """
        action_alias_db = self._get_by_ref_or_id(ref_or_id=action_alias_ref_or_id)
        LOG.debug('DELETE /actionalias/ lookup with id=%s found object: %s', action_alias_ref_or_id,
                  action_alias_db)
        try:
            ActionAlias.delete(action_alias_db)
        except Exception as e:
            LOG.exception('Database delete encountered exception during delete of id="%s".',
                          action_alias_ref_or_id)
            pecan.abort(http_client.INTERNAL_SERVER_ERROR, str(e))
            return

        extra = {'action_alias_db': action_alias_db}
        LOG.audit('Action alias deleted. ActionAlias.id=%s.' % (action_alias_db.id), extra=extra)

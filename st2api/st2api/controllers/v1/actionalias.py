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

from mongoengine import ValidationError
from st2api.controllers import resource
from st2common import log as logging
from st2common.exceptions.actionalias import ActionAliasAmbiguityException
from st2common.exceptions.apivalidation import ValueValidationException
from st2common.models.api.action import ActionAliasAPI
from st2common.persistence.actionalias import ActionAlias
from st2common.rbac.types import PermissionType
from st2common.rbac import utils as rbac_utils

from st2common.router import abort
from st2common.router import Response
from st2common.util.actionalias_matching import match_command_to_alias
from st2common.util.actionalias_helpstring import generate_helpstring_result


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

    _custom_actions = {
        'match': ['POST'],
        'help': ['POST']
    }

    def _match_tuple_to_dict(self, match):
        return {
            'actionalias': match[0],
            'display': match[1],
            'representation': match[2]
        }

    def get_all(self, sort=None, offset=0, limit=None, **raw_filters):
        return super(ActionAliasController, self)._get_all(sort=sort,
                                                           offset=offset,
                                                           limit=limit,
                                                           raw_filters=raw_filters)

    def get_one(self, ref_or_id, requester_user):
        permission_type = PermissionType.ACTION_ALIAS_VIEW
        return super(ActionAliasController, self)._get_one(ref_or_id,
                                                           requester_user=requester_user,
                                                           permission_type=permission_type)

    def match(self, action_alias_match_api):
        """
            Run a chatops command

            Handles requests:
                POST /actionalias/match
        """
        command = action_alias_match_api.command
        try:
            # 1. Get aliases
            aliases_resp = super(ActionAliasController, self)._get_all()
            aliases = [ActionAliasAPI(**alias) for alias in aliases_resp.json]
            # 2. Match alias(es) to command
            matches = match_command_to_alias(command, aliases)
            if len(matches) > 1:
                raise ActionAliasAmbiguityException("Command '%s' matched more than 1 pattern" %
                                                    command,
                                                    matches=matches,
                                                    command=command)
            elif len(matches) == 0:
                raise ActionAliasAmbiguityException("Command '%s' matched no patterns" %
                                                    command,
                                                    matches=[],
                                                    command=command)
            return [self._match_tuple_to_dict(match) for match in matches]
        except ActionAliasAmbiguityException as e:
            LOG.exception('Command "%s" matched (%s) patterns.', e.command, len(e.matches))
            return abort(http_client.BAD_REQUEST, str(e))

    def help(self, filter, pack, limit, offset, **kwargs):
        """
            Get available help strings for action aliases.

            Handles requests:
                GET /actionalias/help
        """
        try:
            aliases_resp = super(ActionAliasController, self)._get_all(**kwargs)
            aliases = [ActionAliasAPI(**alias) for alias in aliases_resp.json]
            return generate_helpstring_result(aliases, filter, pack, int(limit), int(offset))
        except (TypeError) as e:
            LOG.exception('Helpstring request contains an invalid data type: %s.', str(e))
            return abort(http_client.BAD_REQUEST, str(e))

    def post(self, action_alias, requester_user):
        """
            Create a new ActionAlias.

            Handles requests:
                POST /actionalias/
        """

        permission_type = PermissionType.ACTION_ALIAS_CREATE
        rbac_utils.assert_user_has_resource_api_permission(user_db=requester_user,
                                                           resource_api=action_alias,
                                                           permission_type=permission_type)

        try:
            action_alias_db = ActionAliasAPI.to_model(action_alias)
            LOG.debug('/actionalias/ POST verified ActionAliasAPI and formulated ActionAliasDB=%s',
                      action_alias_db)
            action_alias_db = ActionAlias.add_or_update(action_alias_db)
        except (ValidationError, ValueError, ValueValidationException) as e:
            LOG.exception('Validation failed for action alias data=%s.', action_alias)
            abort(http_client.BAD_REQUEST, str(e))
            return

        extra = {'action_alias_db': action_alias_db}
        LOG.audit('Action alias created. ActionAlias.id=%s' % (action_alias_db.id), extra=extra)
        action_alias_api = ActionAliasAPI.from_model(action_alias_db)

        return Response(json=action_alias_api, status=http_client.CREATED)

    def put(self, action_alias, ref_or_id, requester_user):
        """
            Update an action alias.

            Handles requests:
                PUT /actionalias/1
        """
        action_alias_db = self._get_by_ref_or_id(ref_or_id=ref_or_id)
        LOG.debug('PUT /actionalias/ lookup with id=%s found object: %s', ref_or_id,
                  action_alias_db)

        permission_type = PermissionType.ACTION_ALIAS_MODIFY
        rbac_utils.assert_user_has_resource_db_permission(user_db=requester_user,
                                                          resource_db=action_alias_db,
                                                          permission_type=permission_type)

        if not hasattr(action_alias, 'id'):
            action_alias.id = None

        try:
            if action_alias.id is not None and action_alias.id is not '' and \
               action_alias.id != ref_or_id:
                LOG.warning('Discarding mismatched id=%s found in payload and using uri_id=%s.',
                            action_alias.id, ref_or_id)
            old_action_alias_db = action_alias_db
            action_alias_db = ActionAliasAPI.to_model(action_alias)
            action_alias_db.id = ref_or_id
            action_alias_db = ActionAlias.add_or_update(action_alias_db)
        except (ValidationError, ValueError) as e:
            LOG.exception('Validation failed for action alias data=%s', action_alias)
            abort(http_client.BAD_REQUEST, str(e))
            return

        extra = {'old_action_alias_db': old_action_alias_db, 'new_action_alias_db': action_alias_db}
        LOG.audit('Action alias updated. ActionAlias.id=%s.' % (action_alias_db.id), extra=extra)
        action_alias_api = ActionAliasAPI.from_model(action_alias_db)

        return action_alias_api

    def delete(self, ref_or_id, requester_user):
        """
            Delete an action alias.

            Handles requests:
                DELETE /actionalias/1
        """
        action_alias_db = self._get_by_ref_or_id(ref_or_id=ref_or_id)
        LOG.debug('DELETE /actionalias/ lookup with id=%s found object: %s', ref_or_id,
                  action_alias_db)

        permission_type = PermissionType.ACTION_ALIAS_DELETE
        rbac_utils.assert_user_has_resource_db_permission(user_db=requester_user,
                                                          resource_db=action_alias_db,
                                                          permission_type=permission_type)

        try:
            ActionAlias.delete(action_alias_db)
        except Exception as e:
            LOG.exception('Database delete encountered exception during delete of id="%s".',
                          ref_or_id)
            abort(http_client.INTERNAL_SERVER_ERROR, str(e))
            return

        extra = {'action_alias_db': action_alias_db}
        LOG.audit('Action alias deleted. ActionAlias.id=%s.' % (action_alias_db.id), extra=extra)

        return Response(status=http_client.NO_CONTENT)


action_alias_controller = ActionAliasController()

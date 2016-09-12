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
from st2common.util.alias_matching import (list_format_strings_from_aliases,
                                           match_command_to_alias)


http_client = six.moves.http_client

LOG = logging.getLogger(__name__)


class ChatopsController(resource.ContentPackResourceController):
    """
        Implements the RESTful interface for Chatops.
        A super-set of ActionAliasController
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
        return list_format_strings_from_aliases(
            super(ChatopsController, self)._get_all(**kwargs))

    @request_user_has_resource_db_permission(permission_type=PermissionType.ACTION_ALIAS_VIEW)
    @jsexpose(arg_types=[str])
    def get_one(self, ref_or_id):
        return list_format_strings_from_aliases(
            super(ChatopsController, self)._get_one(ref_or_id))[0]

    @jsexpose(arg_types=[str], status_code=http_client.CREATED)
    @request_user_has_resource_api_permission(permission_type=PermissionType.ACTION_ALIAS_CREATE)
    def post(self, command):
        """
            Run a chatops command

            Handles requests:
                POST /chatops/
        """
        try:
            # 1. Get aliases
            aliases = self.get_all()
            # 2. Match alias(es) to command
            match = match_command_to_alias(command, aliases)
            if len(match) > 1:
                raise AmbiguityError("Too much choice, not enough action (alias).")
            # 3. Check user's ability to execute action?
            # 4. Run action.
            # action_execution = whatever_the_api_is()
        except (ValidationError, ValueError, ValueValidationException) as e:
            # TODO : error on unmatched alias
            LOG.exception('Validation failed for action alias data=%s.', action_alias)
            pecan.abort(http_client.BAD_REQUEST, str(e))
            return

        # extra = {'action_alias_db': action_alias_db}
        # LOG.audit('Action alias created. ActionAlias.id=%s' % (action_alias_db.id), extra=extra)

        return action_execution

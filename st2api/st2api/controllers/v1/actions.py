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

from mongoengine import ValidationError

from pecan import abort
import six

# TODO: Encapsulate mongoengine errors in our persistence layer. Exceptions
#       that bubble up to this layer should be core Python exceptions or
#       StackStorm defined exceptions.

from st2api.controllers import resource
from st2api.controllers.v1.actionviews import ActionViewsController
from st2common import log as logging
from st2common.constants.pack import DEFAULT_PACK_NAME
from st2common.exceptions.apivalidation import ValueValidationException
from st2common.models.api.base import jsexpose
from st2common.persistence.action import Action
from st2common.models.api.action import ActionAPI
from st2common.validators.api.misc import validate_not_part_of_system_pack
from st2common.rbac.types import PermissionType
from st2common.rbac.decorators import request_user_has_permission
from st2common.rbac.decorators import request_user_has_resource_permission
import st2common.validators.api.action as action_validator

http_client = six.moves.http_client

LOG = logging.getLogger(__name__)


class ActionsController(resource.ContentPackResourceController):
    """
        Implements the RESTful web endpoint that handles
        the lifecycle of Actions in the system.
    """
    views = ActionViewsController()

    model = ActionAPI
    access = Action
    supported_filters = {
        'name': 'name',
        'pack': 'pack'
    }

    query_options = {
        'sort': ['pack', 'name']
    }

    include_reference = True

    @staticmethod
    def _validate_action_parameters(action, runnertype_db):
        # check if action parameters conflict with those from the supplied runner_type.
        conflicts = [p for p in action.parameters.keys() if p in runnertype_db.runner_parameters]
        if len(conflicts) > 0:
            msg = 'Parameters %s conflict with those inherited from runner_type : %s' % \
                  (str(conflicts), action.runner_type)
            LOG.error(msg)
            abort(http_client.CONFLICT, msg)

    @jsexpose(body_cls=ActionAPI, status_code=http_client.CREATED)
    @request_user_has_permission(permission_type=PermissionType.ACTION_CREATE)
    def post(self, action):
        """
            Create a new action.

            Handles requests:
                POST /actions/
        """
        if not hasattr(action, 'pack'):
            setattr(action, 'pack', DEFAULT_PACK_NAME)

        try:
            action_validator.validate_action(action)
        except ValueValidationException as e:
            abort(http_client.BAD_REQUEST, str(e))
            return

        # ActionsController._validate_action_parameters(action, runnertype_db)
        action_model = ActionAPI.to_model(action)

        LOG.debug('/actions/ POST verified ActionAPI object=%s', action)
        action_db = Action.add_or_update(action_model)
        LOG.debug('/actions/ POST saved ActionDB object=%s', action_db)

        extra = {'action_db': action_db}
        LOG.audit('Action created. Action.id=%s' % (action_db.id), extra=extra)
        action_api = ActionAPI.from_model(action_db)

        return action_api

    @jsexpose(arg_types=[str], body_cls=ActionAPI)
    @request_user_has_resource_permission(permission_type=PermissionType.ACTION_MODIFY)
    def put(self, action_ref_or_id, action):
        action_db = self._get_by_ref_or_id(ref_or_id=action_ref_or_id)

        # Assert permissions
        action_id = action_db.id

        try:
            validate_not_part_of_system_pack(action_db)
        except ValueValidationException as e:
            abort(http_client.BAD_REQUEST, str(e))

        if not getattr(action, 'pack', None):
            action.pack = action_db.pack

        try:
            action_validator.validate_action(action)
        except ValueValidationException as e:
            abort(http_client.BAD_REQUEST, str(e))
            return

        try:
            action_db = ActionAPI.to_model(action)
            action_db.id = action_id
            action_db = Action.add_or_update(action_db)
        except (ValidationError, ValueError) as e:
            LOG.exception('Unable to update action data=%s', action)
            abort(http_client.BAD_REQUEST, str(e))
            return

        action_api = ActionAPI.from_model(action_db)
        LOG.debug('PUT /actions/ client_result=%s', action_api)

        return action_api

    @jsexpose(arg_types=[str], status_code=http_client.NO_CONTENT)
    @request_user_has_resource_permission(permission_type=PermissionType.ACTION_DELETE)
    def delete(self, action_ref_or_id):
        """
            Delete an action.

            Handles requests:
                POST /actions/1?_method=delete
                DELETE /actions/1
                DELETE /actions/mypack.myaction
        """
        action_db = self._get_by_ref_or_id(ref_or_id=action_ref_or_id)
        action_id = action_db.id

        try:
            validate_not_part_of_system_pack(action_db)
        except ValueValidationException as e:
            abort(http_client.BAD_REQUEST, str(e))

        LOG.debug('DELETE /actions/ lookup with ref_or_id=%s found object: %s',
                  action_ref_or_id, action_db)

        try:
            Action.delete(action_db)
        except Exception as e:
            LOG.error('Database delete encountered exception during delete of id="%s". '
                      'Exception was %s', action_id, e)
            abort(http_client.INTERNAL_SERVER_ERROR, str(e))
            return

        extra = {'action_db': action_db}
        LOG.audit('Action deleted. Action.id=%s' % (action_db.id), extra=extra)
        return None

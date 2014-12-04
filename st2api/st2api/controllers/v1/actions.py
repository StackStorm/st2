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

from mongoengine import ValidationError, NotUniqueError

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
from st2common.models.base import jsexpose
from st2common.persistence.action import Action
from st2common.models.api.action import ActionAPI
from st2common.validators.api.misc import validate_not_part_of_system_pack
import st2common.validators.api.action as action_validator

http_client = six.moves.http_client

LOG = logging.getLogger(__name__)


class ActionsController(resource.ContentPackResourceControler):
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

    @jsexpose(body=ActionAPI, status_code=http_client.CREATED)
    def post(self, action):
        """
            Create a new action.

            Handles requests:
                POST /actions/
        """

        LOG.info('POST /actions/ with action data=%s', action)

        if not hasattr(action, 'enabled'):
            LOG.debug('POST /actions/ incoming action data has enabled field unset. '
                      'Defaulting enabled to True.')
            setattr(action, 'enabled', True)
        else:
            action.enabled = bool(action.enabled)

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
        try:
            action_db = Action.add_or_update(action_model)
        except NotUniqueError as e:
            # If an existing DB object conflicts with new object then raise error.
            LOG.warn('/actions/ POST unable to save ActionDB object "%s" due to uniqueness '
                     'conflict. %s', action_model, str(e))
            abort(http_client.CONFLICT, str(e))
            return
        except Exception as e:
            LOG.exception('/actions/ POST unable to save ActionDB object "%s". %s',
                          action_model, e)
            abort(http_client.INTERNAL_SERVER_ERROR, str(e))
            return

        LOG.debug('/actions/ POST saved ActionDB object=%s', action_db)

        LOG.audit('Action created. Action=%s', action_db)
        action_api = ActionAPI.from_model(action_db)

        LOG.debug('POST /actions/ client_result=%s', action_api)
        return action_api

    @jsexpose(str, body=ActionAPI)
    def put(self, action_ref_or_id, action):
        try:
            action_db = self._get_by_ref_or_id(ref_or_id=action_ref_or_id)
        except Exception as e:
            LOG.exception(e.message)
            abort(http_client.NOT_FOUND, e.message)
            return

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

    @jsexpose(str, status_code=http_client.NO_CONTENT)
    def delete(self, action_ref_or_id):
        """
            Delete an action.

            Handles requests:
                POST /actions/1?_method=delete
                DELETE /actions/1
                DELETE /actions/mypack.myaction
        """

        LOG.info('DELETE /actions/ with ref_or_id="%s"', action_ref_or_id)

        try:
            action_db = self._get_by_ref_or_id(ref_or_id=action_ref_or_id)
        except Exception as e:
            LOG.exception(e.message)
            abort(http_client.NOT_FOUND, e.message)
            return

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

        LOG.audit('Action deleted. Action=%s', action_db)
        LOG.info('DELETE /actions/ with ref_or_id="%s" completed',
                 action_ref_or_id)
        return None

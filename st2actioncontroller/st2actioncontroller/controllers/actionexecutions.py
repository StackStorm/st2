import httplib
from pecan import abort
from pecan.rest import RestController

# TODO: Encapsulate mongoengine errors in our persistence layer. Exceptions
#       that bubble up to this layer should be core Python exceptions or
#       StackStorm defined exceptions.
from mongoengine import ValidationError

from wsme import types as wstypes
import wsmeext.pecan as wsme_pecan

from st2common import log as logging
from st2common.exceptions.db import StackStormDBObjectNotFoundError
from st2common.persistence.action import (Action, ActionExecution)
from st2common.models.api.action import (ActionExecutionAPI, ACTIONEXEC_STATUS_INIT,
                                         ACTION_ID, ACTION_NAME
                                         )


LOG = logging.getLogger(__name__)


class ActionExecutionsController(RestController):
    """
        Implements the RESTful web endpoint that handles
        the lifecycle of ActionExecutions in the system.
    """

    def _get_actionexec_by_id(self, id):
        """
            Get ActionExecution by id and abort http operation on errors.
        """
        try:
            actionexec = ActionExecution.get_by_id(id)
        except (ValidationError, ValueError) as e:
            LOG.error('Database lookup for id="%s" resulted in exception: %s', id, e)
            abort(httplib.NOT_FOUND)

        return actionexec

    @wsme_pecan.wsexpose(ActionExecutionAPI, wstypes.text)
    def get_one(self, id):
        """
            List actionexecution by id.

            Handle:
                GET /actionexecutions/1
        """

        LOG.info('GET /actionexecutions/ with id="%s"', id)

        actionexec_db = self._get_actionexec_by_id(id)
        actionexec_api = ActionExecutionAPI.from_model(actionexec_db)

        LOG.debug('GET /actionexecutions/ with id=%s, client_result=%s', id, actionexec_api)
        return actionexec_api

    # TODO: Support kwargs
    @wsme_pecan.wsexpose([ActionExecutionAPI])
    def get_all(self):
        """
            List all actionexecutions.

            Handles requests:
                GET /actionexecutions/
        """

        LOG.info('GET all /actionexecutions/')
        actionexec_apis = [ActionExecutionAPI.from_model(actionexec_db)
                           for actionexec_db in ActionExecution.get_all()]

        # TODO: unpack list in log message
        LOG.debug('GET all /actionexecutions/ client_result=%s', actionexec_apis)
        return actionexec_apis

    def _get_action_by_id(self, action_id):
        """
            Get Action by id.
            
            On error, raise StackStormDBObjectNotFoundError
        """
        action = None

        try:
            action = Action.get_by_id(action_id)
        except (ValueError, ValidationError) as e:
            LOG.warning('Database lookup for action with id="%s" resulted in '
                        'exception: %s', action_id, e)
            raise StackStormDBObjectNotFoundError('Unable to find action with '
                                                  'id="%s"' % action_id)

        return action

    def _get_action_by_name(self, action_name):
        """
            Get Action by name.
            
            On error, raise StackStormDBObjectNotFoundError
        """
        action = None

        try:
            action = Action.get_by_name(action_name)
        except (ValueError, ValidationError) as e:
            LOG.warning('Database lookup for action with name="%s" resulted in '
                        'exception: %s', action_name, e)
            raise StackStormDBObjectNotFoundError('Unable to find action with '
                                                  'name="%s"' % action_name)

        return action

    def _get_action_for_dict(self, action_dict):
        action = None

        if ACTION_ID in action_dict:
            action_id = action_dict[ACTION_ID]
            try:
                action = self._get_action_by_id(action_id)
            except StackStormDBObjectNotFoundError:
                LOG.info('Action not found by id, falling back to lookup by name and '
                         'removing action id from Action Execution.')
                del action_dict[ACTION_ID]
            else:
                return (action, action_dict)

        if ACTION_NAME in action_dict:
            action_name = action_dict[ACTION_NAME]
            try:
                action = self._get_action_by_name(action_name)
            except StackStormDBObjectNotFoundError:
                LOG.info('Action not found by name.')
            else:
                return (action, action_dict)
            
        # No action found by identifiers in action_dict.
        return (None,{})

    @wsme_pecan.wsexpose(ActionExecutionAPI, body=ActionExecutionAPI,
                         status_code=httplib.CREATED)
    def post(self, actionexecution):
        """
            Create a new actionexecution.

            Handles requests:
                POST /actionexecutions/
        """

        LOG.info('POST /actionexecutions/ with actionexec data=%s', actionexecution)

        if ACTION_ID not in actionexecution.action:
            LOG.error('Action can only be accessed by ID in the current implementation.'
                      'Aborting POST.')
            abort(httplib.NOT_IMPLEMENTED)

        (action_db,action_dict) = self._get_action_for_dict(actionexecution.action)
        if not action_db:
            LOG.error('POST /actionexecutions/ Action for "%s" cannot be found.', actionexecution.action)
            abort(httplib.INTERNAL_SERVER_ERROR)
        else:
            if action_dict != dict(actionexecution.action):
                LOG.info('POST /actionexecutions/ Action identity dict updated to remove '
                         'lookup failure.')
                actionexecution.action = action_dict

        LOG.debug('Setting actionexecution status to "%s"', ACTIONEXEC_STATUS_INIT)
        actionexecution.status = str(ACTIONEXEC_STATUS_INIT)
        LOG.info('POST /actionexecutions/ with actionexec data=%s', actionexecution)

        actionexec_api = ActionExecutionAPI.to_model(actionexecution)
        LOG.debug('/actionexecutions/ POST verified ActionExecutionAPI object=%s',
                  actionexec_api)

        # TODO: POST operations should only add to DB.
        #       If an existing object conflicts then raise an error.

        actionexec_db = ActionExecution.add_or_update(actionexec_api)
        LOG.debug('/actionexecutions/ POST saved ActionExecutionDB object=%s', actionexec_db)
        actionexec_api = ActionExecutionAPI.from_model(actionexec_db)

        LOG.debug('POST /actionexecutions/ client_result=%s', actionexec_api)
        return actionexec_api

    @wsme_pecan.wsexpose(ActionExecutionAPI, body=ActionExecutionAPI,
                         status_code=httplib.FORBIDDEN)
    def put(self, data):
        """
            Update an actionexecution does not make any sense.

            Handles requests:
                POST /actionexecutions/1?_method=put
                PUT /actionexecutions/1
        """
        return None

    @wsme_pecan.wsexpose(None, wstypes.text, status_code=httplib.NO_CONTENT)
    def delete(self, id):
        """
            Delete an actionexecution.

            Handles requests:
                POST /actionexecutions/1?_method=delete
                DELETE /actionexecutions/1
        """

        # TODO: Support delete by name
        LOG.info('DELETE /actionexecutions/ with id=%s', id)

        actionexec_db = self._get_actionexec_by_id(id)
        LOG.debug('DELETE /actionexecutions/ lookup with id=%s found object: %s',
                  id, actionexec_db)

        # TODO: Delete should migrate the execution data to a history collection.

        try:
            ActionExecution.delete(actionexec_db)
        except Exception, e:
            LOG.error('Database delete encountered exception during delete of id="%s". '
                      'Exception was %s', id, e)

        LOG.info('DELETE /actionexecutions/ with id="%s" completed', id)
        return None

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
                                         ACTION_ID)
from st2common.util.action_db import (get_action_for_dict, get_actionexec_by_id)


LOG = logging.getLogger(__name__)


class ActionExecutionsController(RestController):
    """
        Implements the RESTful web endpoint that handles
        the lifecycle of ActionExecutions in the system.
    """

    @wsme_pecan.wsexpose(ActionExecutionAPI, wstypes.text)
    def get_one(self, id):
        """
            List actionexecution by id.

            Handle:
                GET /actionexecutions/1
        """

        LOG.info('GET /actionexecutions/ with id="%s"', id)

        try:
            actionexec_db = get_actionexec_by_id(id)
        except StackStormDBObjectNotFoundError, e:
            LOG.error('GET /actionexecutions/ with id="%s": %s', id, e.message)
            abort(httplib.NOT_FOUND)

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

        (action_db,action_dict) = get_action_for_dict(actionexecution.action)
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

        try:
            actionexec_db = get_actionexec_by_id(id)
        except StackStormDBObjectNotFoundError, e:
            LOG.error('GET /actionexecutions/ with id="%s": %s', id, e.message)
            abort(httplib.NOT_FOUND)

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

import httplib
from pecan import abort
from pecan.rest import RestController

from wsme import types as wstypes
import wsmeext.pecan as wsme_pecan

from st2common import log as logging
from st2common.exceptions.db import StackStormDBObjectNotFoundError
from st2common.models.api.action import ActionTypeAPI
from st2common.persistence.action import ActionType
from st2common.util.action_db import (get_actiontype_by_id, get_actiontype_by_name)


LOG = logging.getLogger(__name__)


class ActionTypesController(RestController):
    """
        Implements the RESTful web endpoint that handles
        the lifecycle of an ActionType in the system.
    """
    @wsme_pecan.wsexpose(ActionTypeAPI, wstypes.text)
    def get_one(self, id):
        """
            List ActionType objects by id.

            Handle:
                GET /actiontypes/1
        """

        LOG.info('GET /actiontypes/ with id=%s', id)

        try:
            actiontype_db = get_actiontype_by_id(id)
        except StackStormDBObjectNotFoundError as e:
            LOG.error('GET /actiontypes/ with id="%s": %s', id, e.message)
            abort(httplib.NOT_FOUND)
        actiontype_api = ActionTypeAPI.from_model(actiontype_db)

        LOG.debug('GET /actiontypes/ with id=%s, client_result=%s', id, actiontype_api)
        return actiontype_api

    @wsme_pecan.wsexpose([ActionTypeAPI])
    def get_all(self):
        """
            List all ActionType objects.

            Handles requests:
                GET /actiontypes/
        """

        LOG.info('GET all /actiontypes/')

        actiontype_apis = [ActionTypeAPI.from_model(actiontype_db)
                           for actiontype_db in ActionType.get_all()]

        # TODO: Unpack list in log message
        LOG.debug('GET all /actiontypes/ client_result=%s', actiontype_apis)
        return actiontype_apis

    @wsme_pecan.wsexpose(ActionTypeAPI, body=ActionTypeAPI)
    def post(self, actiontype):
        """
            Update not supported for ActionType.

            Create a new ActionType object.

            Handles requests:
                POST /actiontypes/
        """

        abort(httplib.NOT_IMPLEMENTED)

    @wsme_pecan.wsexpose(ActionTypeAPI, body=ActionTypeAPI,
                         status_code=httplib.NOT_IMPLEMENTED)
    def put(self, action):
        """
            Update not supported for ActionType.

            Handles requests:
                POST /actiontypes/1?_method=put
                PUT /actiontypes/1
        """

        abort(httplib.METHOD_NOT_ALLOWED)

    @wsme_pecan.wsexpose(None, status_code=httplib.NOT_IMPLEMENTED)
    def delete(self):
        """
            Delete an ActionType.

            Handles requests:
                POST /actiontypes/1?_method=delete
                DELETE /actiontypes/1
        """

        # TODO: Support delete by name
        abort(httplib.NOT_IMPLEMENTED)

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
from st2common.persistence.action import Action
from st2common.models.api.action import ActionAPI
from st2common.util.action_db import get_action_by_id


LOG = logging.getLogger(__name__)


class ActionsController(RestController):
    """
        Implements the RESTful web endpoint that handles
        the lifecycle of Actions in the system.
    """

    # TODO: Investigate mako rendering
    @wsme_pecan.wsexpose(ActionAPI, wstypes.text)
    def get_one(self, id):
        """
            List action by id.

            Handle:
                GET /actions/1
        """

        LOG.info('GET /actions/ with id=%s', id)

        try:
            action_db = get_action_by_id(id)
        except StackStormDBObjectNotFoundError, e:
            LOG.error('GET /actions/ with id="%s": %s', id, e.message)
            abort(httplib.NOT_FOUND)

        action_api = ActionAPI.from_model(action_db)

        LOG.debug('GET /actions/ with id=%s, client_result=%s', id, action_api)
        return action_api

    @wsme_pecan.wsexpose([ActionAPI], wstypes.text)
    def get_all(self, name=None):
        """
            List all actions.

            Handles requests:
                GET /actions/
        """

        LOG.info('GET all /actions/ and name=%s', name)
        action_dbs = Action.get_all() if name is None else ActionsController.__get_by_name(name)
        action_apis = [ActionAPI.from_model(action_db) for action_db in action_dbs]

        # TODO: unpack list in log message
        LOG.debug('GET all /actions/ client_result=%s', action_apis)
        return action_apis

    @wsme_pecan.wsexpose(ActionAPI, body=ActionAPI, status_code=httplib.CREATED)
    def post(self, action):
        """
            Create a new action.

            Handles requests:
                POST /actions/
        """

        LOG.info('POST /actions/ with action data=%s', action)

        if action.enabled is wstypes.Unset:
            # Default enabled flag to True
            LOG.debug('POST /actions/ incoming action data has enabled field unset. '
                      'Defaulting enabled to True.')
            action.enabled = True
        else:
            action.enabled = bool(action.enabled)

        action_api = ActionAPI.to_model(action)
        LOG.debug('/actions/ POST verified ActionAPI object=%s', action_api)
        # TODO: POST operations should only add to DB.
        #       If an existing object conflicts then raise error.

        action_db = Action.add_or_update(action_api)
        LOG.debug('/actions/ POST saved ActionDB object=%s', action_db)
        action_api = ActionAPI.from_model(action_db)

        LOG.debug('POST /actions/ client_result=%s', action_api)
        return action_api

    @wsme_pecan.wsexpose(ActionAPI, body=ActionAPI, status_code=httplib.NOT_IMPLEMENTED)
    def put(self, action):
        """
            Update an action.

            Handles requests:
                POST /actions/1?_method=put
                PUT /actions/1
        """
        # TODO: Implement
        return {"dummy": "put"}

    @wsme_pecan.wsexpose(None, wstypes.text, status_code=httplib.NO_CONTENT)
    def delete(self, id):
        """
            Delete an action.

            Handles requests:
                POST /actions/1?_method=delete
                DELETE /actions/1
        """

        # TODO: Support delete by name
        LOG.info('DELETE /actions/ with id=%s', id)

        try:
            action_db = get_action_by_id(id)
        except StackStormDBObjectNotFoundError, e:
            LOG.error('DELETE /actions/ with id="%s": %s', id, e.message)
            abort(httplib.NOT_FOUND)

        LOG.debug('DELETE /actions/ lookup with id=%s found object: %s', id, action_db)

        try:
            Action.delete(action_db)
        except Exception, e:
            LOG.error('Database delete encountered exception during delete of id="%s". '
                      'Exception was %s', id, e)

        LOG.info('DELETE /actions/ with id="%s" completed', id)
        return None

    @staticmethod
    def __get_by_name(action_name):
        try:
            return [Action.get_by_name(action_name)]
        except ValueError as e:
            LOG.debug('Database lookup for name="%s" resulted in exception : %s.', action_name, e)
            return []

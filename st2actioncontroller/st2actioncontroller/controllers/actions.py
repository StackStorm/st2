import httplib
import jsonschema
from pecan import abort
from pecan.rest import RestController

from mongoengine import NotUniqueError

# TODO: Encapsulate mongoengine errors in our persistence layer. Exceptions
#       that bubble up to this layer should be core Python exceptions or
#       StackStorm defined exceptions.

from wsme import types as wstypes
import wsmeext.pecan as wsme_pecan

from st2common import log as logging
from st2common.exceptions.db import StackStormDBObjectNotFoundError
from st2common.models.base import jsexpose
from st2common.persistence.action import Action
from st2common.models.api.action import ActionAPI
from st2common.util.action_db import (get_action_by_id, get_action_by_name, get_runnertype_by_name)


LOG = logging.getLogger(__name__)


class ActionsController(RestController):
    """
        Implements the RESTful web endpoint that handles
        the lifecycle of Actions in the system.
    """

    @staticmethod
    def __get_by_id(id):
        try:
            return Action.get_by_id(id)
        except Exception as e:
            msg = 'Database lookup for id="%s" resulted in exception. %s' % (id, e.message)
            LOG.exception(msg)
            abort(httplib.NOT_FOUND, msg)

    @staticmethod
    def __get_by_name(name):
        try:
            action = Action.get_by_name(name)
            return [action]
        except Exception as e:
            LOG.debug('Database lookup for name="%s" resulted in exception : %s.', name, e)
            return []

    @jsexpose(str)
    def get_one(self, id):
        """
            List action by id.

            Handle:
                GET /actions/1
        """

        LOG.info('GET /actions/ with id=%s', id)
        action_db = ActionsController.__get_by_id(id)
        action_api = ActionAPI.from_model(action_db)
        LOG.debug('GET /actions/ with id=%s, client_result=%s', id, action_api)
        return action_api

    @jsexpose(str)
    def get_all(self, name=None):
        """
            List all actions.

            Handles requests:
                GET /actions/
        """
        LOG.info('GET all /actions/ and name=%s', str(name))
        action_dbs = Action.get_all() if name is None else ActionsController.__get_by_name(name)
        action_apis = [ActionAPI.from_model(action_db) for action_db in action_dbs]
        LOG.debug('GET all /actions/ client_result=%s', action_apis)
        return action_apis

    @staticmethod
    def _validate_action_parameters(action, runnertype_db):
        # check if action parameters conflict with those from the supplied runner_type.
        conflicts = [p for p in action.parameters.keys() if p in runnertype_db.runner_parameters]
        if len(conflicts) > 0:
            msg = 'Parameters %s conflict with those inherited from runner_type : %s' % \
                  (str(conflicts), action.runner_type)
            LOG.error(msg)
            abort(httplib.CONFLICT, msg)

    @jsexpose(body=ActionAPI, status_code=httplib.CREATED)
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

        # check if action parameters conflict with those from the supplied runner_type.
        try:
            runnertype_db = get_runnertype_by_name(action.runner_type)
        except StackStormDBObjectNotFoundError as e:
            msg = 'RunnerType %s is not found.' % action.runner_type
            LOG.exception('%s. Exception: %s', msg, e)
            abort(httplib.NOT_FOUND, msg)

        ActionsController._validate_action_parameters(action, runnertype_db)
        action_model = ActionAPI.to_model(action)
        LOG.debug('/actions/ POST verified ActionAPI object=%s', action)

        LOG.audit('Action about to be created in database. Action is: %s', action_model)
        try:
            action_db = Action.add_or_update(action_model)
        except NotUniqueError as e:
            # If an existing DB object conflicts with new object then raise error.
            LOG.exception('/actions/ POST unable to save ActionDB object "%s" due to uniqueness '
                          'conflict. %s', action_model, e)
            abort(httplib.CONFLICT, e.message)
        except Exception as e:
            LOG.exception('/actions/ POST unable to save ActionDB object "%s". %s',
                          action_model, e)
            abort(httplib.INTERNAL_SERVER_ERROR, e.message)

        LOG.debug('/actions/ POST saved ActionDB object=%s', action_db)

        LOG.audit('Action created in database. Action is: %s', action_db)
        action_api = ActionAPI.from_model(action_db)

        LOG.debug('POST /actions/ client_result=%s', action_api)
        return action_api

    @jsexpose(str, status_code=httplib.NO_CONTENT)
    def delete(self, id):
        """
            Delete an action.

            Handles requests:
                POST /actions/1?_method=delete
                DELETE /actions/1
        """

        LOG.info('DELETE /actions/ with id="%s"', id)
        action_db = ActionsController.__get_by_id(id)

        LOG.debug('DELETE /actions/ lookup with id=%s found object: %s', id, action_db)

        try:
            Action.delete(action_db)
        except Exception as e:
            LOG.error('Database delete encountered exception during delete of id="%s". '
                      'Exception was %s', id, e)

        LOG.audit('An Action was deleted from database. The Action was: %s', action_db)
        LOG.info('DELETE /actions/ with id="%s" completed', id)
        return None

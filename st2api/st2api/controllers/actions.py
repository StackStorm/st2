from mongoengine import ValidationError, NotUniqueError

from pecan import abort
import six

# TODO: Encapsulate mongoengine errors in our persistence layer. Exceptions
#       that bubble up to this layer should be core Python exceptions or
#       StackStorm defined exceptions.

from st2api.controllers import resource
from st2api.controllers.actionviews import ActionViewsController
from st2common import log as logging
from st2common.exceptions.apivalidation import ValueValidationException
from st2common.models.base import jsexpose
from st2common.persistence.action import Action
from st2common.models.api.action import ActionAPI
import st2common.validators.api.action as action_validator

http_client = six.moves.http_client

LOG = logging.getLogger(__name__)


class ActionsController(resource.ResourceController):
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

    @staticmethod
    def _get_by_id(action_id):
        try:
            return Action.get_by_id(action_id)
        except Exception as e:
            msg = 'Database lookup for id="%s" resulted in exception. %s' % (action_id, e)
            LOG.exception(msg)
            abort(http_client.NOT_FOUND, msg)

    @staticmethod
    def _validate_action_parameters(action, runnertype_db):
        # check if action parameters conflict with those from the supplied runner_type.
        conflicts = [p for p in action.parameters.keys() if p in runnertype_db.runner_parameters]
        if len(conflicts) > 0:
            msg = 'Parameters %s conflict with those inherited from runner_type : %s' % \
                  (str(conflicts), action.runner_type)
            LOG.error(msg)
            abort(http_client.CONFLICT, msg)

    @jsexpose()
    @resource.referenced
    def get_all(self, **kwargs):
        return super(ActionsController, self)._get_all(**kwargs)

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
            setattr(action, 'pack', 'default')

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
    def put(self, action_id, action):
        action_db = ActionsController._get_by_id(action_id)
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
    def delete(self, action_id):
        """
            Delete an action.

            Handles requests:
                POST /actions/1?_method=delete
                DELETE /actions/1
        """

        LOG.info('DELETE /actions/ with id="%s"', action_id)
        action_db = ActionsController._get_by_id(action_id)

        LOG.debug('DELETE /actions/ lookup with id=%s found object: %s', action_id, action_db)

        try:
            Action.delete(action_db)
        except Exception as e:
            LOG.error('Database delete encountered exception during delete of id="%s". '
                      'Exception was %s', action_id, e)
            abort(http_client.INTERNAL_SERVER_ERROR, str(e))
            return

        LOG.audit('Action deleted. Action=%s', action_db)
        LOG.info('DELETE /actions/ with id="%s" completed', action_id)
        return None

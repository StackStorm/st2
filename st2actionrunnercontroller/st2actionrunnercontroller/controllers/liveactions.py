import httplib
from pecan import (abort, expose)
from pecan.rest import RestController

from mongoengine import ValidationError

from wsme import types as wstypes
import wsmeext.pecan as wsme_pecan

from st2common import log as logging

from st2common.exceptions.db import StackStormDBObjectNotFoundError
from st2common.models.api.action import (ActionAPI, ActionExecutionAPI)
from st2common.models.api.actionrunner import (ActionTypeAPI, LiveActionAPI)
from st2common.persistence.action import ActionExecution
from st2common.persistence.actionrunner import LiveAction
from st2common.util.action_db import (get_actionexec_by_id, get_action_by_dict)
from st2common.util.actionrunner_db import (get_actiontype_by_name, get_liveaction_by_id)


LOG = logging.getLogger(__name__)


class LiveActionsController(RestController):
    """
        Implements the RESTful web endpoint that handles
        the lifecycle of ActionRunners in the system.
    """

#    def get_actionexecution_by_id(self, actionexecution_id):
#        """
#            Get ActionExecution by id.
#            On error, raise ST2ObjectNotFoundError.
#        """
#        # TODO: Maybe lookup should be done via HTTP interface. Handle via direct DB call
#        #       for now.
#        LOG.debug('Lookup for ActionExecution with id=%s', actionexecution_id)
#        try:
#            actionexecution_db = ActionExecution.get_by_id(actionexecution_id)
#        except (ValueError, ValidationError) as e:
#            LOG.error('Database lookup for actionexecution with id="%s" resulted in '
#                      'exception: %s', actionexecution_id, e)
#            raise StackStormDBObjectNotFoundError('Unable to find actionexecution with '
#                                                  'id="%s"' % actionexecution_id)
#
#        return actionexecution_db

    @wsme_pecan.wsexpose(LiveActionAPI, wstypes.text)
    def get_one(self, id):
        """
            List LiveAction by id.

            Handle:
                GET /liveactions/1
        """

        LOG.info('GET /liveactions/ with id=%s', id)

        liveaction_db = self._get_by_id(id)
        liveaction_api = LiveActionAPI.from_model(liveaction_db)

        LOG.debug('GET /liveactions/ with id=%s, client_result=%s', id, liveaction_api)
        return action_api
        

    @wsme_pecan.wsexpose([LiveActionAPI])
    def get_all(self):
        """
            List all liveactions.

            Handles requests:
                GET /liveactions/
        """

        LOG.info('GET all /liveactions/')

        liveaction_apis = [LiveActionAPI.from_model(liveaction_db)
                           for liveaction_db in LiveAction.get_all()]

        # TODO: unpack list in log message
        LOG.debug('GET all /liveactions/ client_result=%s', liveaction_apis)
        return liveaction_apis

    # @expose('json')
    # def post(self, **kwargs):
    @wsme_pecan.wsexpose(LiveActionAPI, body=LiveActionAPI, status_code=httplib.CREATED)
    def post(self, liveaction):
        """
            Create a new LiveAction.

            Handles requests:
                POST /liveactions/
        """
        LOG.info('POST /liveactions/ with liveaction data=%s', liveaction)

        # Validate incoming API object
        liveaction_api = LiveActionAPI.to_model(liveaction)
        LOG.debug('/liveactions/ POST verified LiveActionAPI object=%s',
                  liveaction_api)

        actionexecution_id = str(liveaction.actionexecution_id)

        ## To launch a LiveAction we need:
        #     1. ActionExecution object
        #     2. Action object
        #     3. ActionType object
        LOG.info('POST /liveactions/ received actionexecution_id: %s. '
                 'Attempting to obtain ActionExecution object from database.', actionexecution_id)
        try:
            db = get_actionexec_by_id(actionexecution_id)
            actionexecution_api = ActionExecutionAPI.from_model(db)
            db = None
        except StackStormDBObjectNotFoundError, e:
            LOG.error(e.message)
            # TODO: Is there a more appropriate status code?
            abort(httplib.BAD_REQUEST)

        ## Got ActionExecution object (1)
        LOG.info('POST /liveactions/ obtained ActionExecution object from database. '
                 'Object is %s', actionexecution_api)

        try:
            LOG.debug('actionexecution.action value: %s', actionexecution_api.action)
            db,d = get_action_by_dict(actionexecution_api.action)
            LOG.debug('got DB object: %s', db)
            action_api = ActionAPI.from_model(db)
            db = None
        except StackStormDBObjectNotFoundError, e:
            LOG.error(e.message)
            # TODO: Is there a more appropriate status code?
            abort(httplib.BAD_REQUEST)

        ## Got Action object (2)
        LOG.info('POST /liveactions/ obtained Action object from database. '
                 'Object is %s', action_api)

        try:
            db = get_actiontype_by_name(action_api.runner_type)
            actiontype_api = ActionTypeAPI.from_model(db)
            db = None
        except StackStormDBObjectNotFoundError, e:
            LOG.error(e.message)
            # TODO: Is there a more appropriate status code?
            abort(httplib.BAD_REQUEST)

        ## Got ActionType object (3)
        LOG.info('POST /liveactions/ obtained ActionType object from database. '
                 'Object is %s', actiontype_api)


        # Save LiveAction to DB
        liveaction_api.actionexecution_id = actionexecution_api.id
        liveaction_db = LiveAction.add_or_update(liveaction_api)
        LOG.info('POST /liveactions/ LiveAction object saved to DB. '
                 'Object is: %s', liveaction_db)
            
        # Launch action
        LOG.debug('Launching LiveAction command: ')
        print "Fe, Fi, Fo, Fum"

    ##################### Got to here.

        abort(httplib.NOT_IMPLEMENTED)

    @expose('json')
    def put(self, id, **kwargs):
        """
            Update not supported for LiveActions.

            Handles requests:
                POST /liveactions/1?_method=put
                PUT /liveactions/1
        """
        abort(httplib.METHOD_NOT_ALLOWED)

    @wsme_pecan.wsexpose(None, wstypes.text)
    def delete(self, id):
        """
            Delete a LiveAction.

            Handles requests:
                POST /liveactions/1?_method=delete
                DELETE /liveactions/1
        """

        abort(httplib.NOT_IMPLEMENTED)

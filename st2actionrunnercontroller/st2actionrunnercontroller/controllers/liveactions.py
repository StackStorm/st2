import httplib
from pecan import (abort, expose)
from pecan.rest import RestController

from mongoengine import ValidationError

from wsme import types as wstypes
import wsmeext.pecan as wsme_pecan

from st2common import log as logging

from st2common.exceptions.db import StackStormDBObjectNotFoundError
from st2common.models.api.actionrunner import LiveActionAPI
from st2common.persistence.action import ActionExecution
from st2common.persistence.actionrunner import LiveAction
from st2common.util.actionrunner_db import get_liveaction_by_id


LOG = logging.getLogger(__name__)


class LiveActionsController(RestController):
    """
        Implements the RESTful web endpoint that handles
        the lifecycle of ActionRunners in the system.
    """

    _liveaction_apis = {}

    """
    def __init__(self):
        api = LiveActionAPI()
        api.id = '12345'
        api.name = 'test/echo'
        api.description = 'A test/echo action'
        api.action_execution_id = 'some id'
        self._liveaction_apis['12345'] = api
        api = LiveActionAPI()
        api.id = '78901'
        api.name = 'test/hello'
        api.description = 'A test/hello action'
        api.action_execution_id = 'some other id'
        self._liveaction_apis['78901'] = api
    """

#    def _get_by_id(self, id):
#        """
#            Get LiveAction by id.
#
#            On error, raise ST2ObjectNotFoundError.
#        """
#        try:
#            liveaction = LiveAction.get_by_id(id)
#        except (ValueError, ValidationError) as e:
#            LOG.error('Database lookup for id="%s" resulted in exception: %s', id, e)
#            abort(httplib.NOT_FOUND)
#
#        return liveaction

    def get_actionexecution_by_id(self, actionexecution_id):
        """
            Get ActionExecution by id.
            On error, raise ST2ObjectNotFoundError.
        """
        # TODO: Maybe lookup should be done via HTTP interface. Handle via direct DB call
        #       for now.
        LOG.debug('Lookup for ActionExecution with id=%s', actionexecution_id)
        try:
            actionexecution_db = ActionExecution.get_by_id(actionexecution_id)
        except (ValueError, ValidationError) as e:
            LOG.error('Database lookup for actionexecution with id="%s" resulted in '
                      'exception: %s', actionexecution_id, e)
            raise StackStormDBObjectNotFoundError('Unable to find actionexecution with '
                                                  'id="%s"' % actionexecution_id)

        return actionexecution_db

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
        actionexecution_db = None

        LOG.info('POST /liveactions/ received action_execution_id: %s', actionexecution_id)
        LOG.info('here')
        LOG.info('POST /liveactions/ attempting to obtain action_execution from database.')
        try:
            actionexecution_db = self.get_actionexecution_by_id(actionexecution_id)

        except StackStormDBObjectNotFoundError, e:
            LOG.error(e.message)
            # TODO: Is there a more appropriate status code?
            abort(httplib.BAD_REQUEST)

        LOG.info('POST /liveactions/ obtained action execution object from database. '
                 'Object is %s', actionexecution_db)

        try:
            pass
        except StackStormDBObjectNotFoundError, e:
            LOG.error(e.message)
            # TODO: Is there a more appropriate status code?
            abort(httplib.BAD_REQUEST)
            

        LOG.debug('Got ActionExecution.... now launch action command.')

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

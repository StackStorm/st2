import httplib
from pecan import (abort, expose, request, response)
from pecan.rest import RestController
import uuid

from wsme import types as wstypes
import wsmeext.pecan as wsme_pecan

from st2common import log as logging

from st2common.exceptions.db import StackStormDBObjectNotFoundError
from st2common.models.api.actionrunner import LiveActionAPI
from st2common.persistence.action import ActionExecution
from st2common.persistence.actionrunner import LiveAction


LOG = logging.getLogger(__name__)


class LiveActionsController(RestController):
    """
        Implements the RESTful web endpoint that handles
        the lifecycle of ActionRunners in the system.
    """

    _liveaction_apis = {}

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

    def get_actionexecution_by_id(self, id):
        """
            Get ActionExecution by id.
            On error, raise ST2ObjectNotFoundError.
        """
        # TODO: Maybe lookup should be done via HTTP interface. Handle via direct DB call
        #       for now.
        try:
            actionexecution = ActionExecution.get_by_id(id)
        except (ValueError, ValidationError) as e:
            LOG.error('Database lookup for actionexecution with id="%s" resulted in exception: %s', id, e)
            raise StackStormDBObjectNotFoundError('Unable to find actionexecution with id="%s"', id)

        return actionexecution

    @wsme_pecan.wsexpose(LiveActionAPI, wstypes.text)
    def get_one(self, id):
        """
            List LiveAction by id.

            Handle:
                GET /liveactions/1
        """

        # TODO: test/handle object not found.
        return {'liveaction': id}

    @wsme_pecan.wsexpose([LiveActionAPI])
    def get_all(self):
        """
            List all liveactions.

            Handles requests:
                GET /liveactions/
        """

        LOG.info('GET all /liveactions/')

#        liveaction_apis = self._liveaction_apis

#        liveaction_api = LiveActionAPI()
#        liveaction_api.id = str(uuid.uuid4())
#        liveaction_api.action_name = u'test/echo'

#        self._liveaction_apis.append(self.create_liveaction('test/echo', {}, {}))

        # TODO: Implement list comprehension to transform the in-memory objects into API objects
#        liveaction_apis = [liveaction_api for (id, liveaction_api) in self._liveaction_apis.items()]
        liveaction_apis = self._liveaction_apis.values()

        for api in liveaction_apis:
            LOG.debug('    %s', str(api))
        
        LOG.debug('GET all /liveactions/ client_result=%s', self._liveaction_apis)
        return self._liveaction_apis

"""
    def create_liveaction(self, action_name, runner_parameters={}, action_parameters={}):
        # Note: action name, action runner parameters and action parameters are all
        # fields in the ActionExecutionDB object.
        liveaction_api = LiveActionAPI()
        liveaction_api.id = str(uuid.uuid4())
        liveaction_api.action_name = str.encode(action_name)
        liveaction_api.runner_parameters = runner_parameters
        liveaction_api.action_parameters = action_parameters

        return liveaction_api
"""
        

    #@wsme_pecan.wsexpose(LiveActionAPI, body=LiveActionAPI, status_code=httplib.CREATED)
    @expose('json')
    def post(self, **kwargs):
        """
            Create a new LiveAction.

            Handles requests:
                POST /liveactions/
        """
        LOG.info('POST /liveactions/ with liveaction data=%s', kwargs)

        actionexecution_id = str(kwargs['action_execution_id'])
        actionexecution_db = None

        LOG.info('POST /liveactions/ received action_execution_id: %s', actionexecution_id)
        LOG.info('POST /liveactions/ attempting to obtain action_execution from database.')
        try:
            actionexecution_db = self.get_actionexecution_by_id(actionexecution_id)

        except StackStormDBObjectNotFoundError, e:
            LOG.error(e.msg)
            # TODO: Is there a more appropriate status code?
            abort(httplib.BAD_REQUEST)

        LOG.info('POST /liveactions/ obtained action execution object from database. Object is %s', actionexecution_db)

        LOG.info('ae name %s', actionexecution_db.name)

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

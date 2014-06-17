import httplib
from pecan import (abort, expose, request, response)
from pecan.rest import RestController
import uuid

from wsme import types as wstypes
import wsmeext.pecan as wsme_pecan

from st2common import log as logging
from st2common.persistence.actionrunner import LiveAction
from st2common.models.api.actionrunner import LiveActionAPI


LOG = logging.getLogger(__name__)


class LiveActionsController(RestController):
    """
        Implements the RESTful web endpoint that handles
        the lifecycle of ActionRunners in the system.
    """

    _liveaction_apis = {}

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

        self._liveaction_apis.append(self.create_liveaction('test/echo', {}, {}))
        
        LOG.debug('GET all /liveactions/ client_result=%s', self._liveaction_apis)
        return self._liveaction_apis

    def create_liveaction(self, action_name, runner_parameters={}, action_parameters={}):
        liveaction_api = LiveActionAPI()
        liveaction_api.id = str(uuid.uuid4())
        liveaction_api.action_name = str.encode(action_name)
        liveaction_api.runner_parameters = runner_parameters
        liveaction_api.action_parameters = action_parameters

        return liveaction_api
        

    @wsme_pecan.wsexpose(LiveActionAPI, body=LiveActionAPI, status_code=httplib.CREATED)
    def post(self, liveaction_api):
        """
            Create a new LiveAction.

            Handles requests:
                POST /liveactions/
        """
        LOG.info('POST /liveactions/ with liveaction data=%s', liveaction_api)


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

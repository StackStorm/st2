import httplib
from pecan import (abort, expose, )
from pecan.rest import RestController

from wsme import types as wstypes
from wsmeext.pecan import wsexpose

from st2common.persistence.actionrunner import LiveAction
from st2common.models.api.actionrunner import LiveActionAPI


class LiveActionsController(RestController):
    """
        Implements the RESTful web endpoint that handles
        the lifecycle of ActionRunners in the system.
    """

    @wsexpose(LiveActionAPI, wstypes.text)
    def get_one(self, id):
        """
            List LiveAction by id.

            Handle:
                GET /liveactions/1
        """

        # TODO: test/handle object not found.
        return {'liveaction': id}

    # TODO: Update to wsexpose
    @expose('json')
    def get_all(self, **kwargs):
        """
            List all liveactions.

            Handles requests:
                GET /liveactions/
        """

        if not kwargs:
            pass
            # TODO: Implement
            abort(httplib.NOT_IMPLEMENTED)
        else:
            # TODO: implement id=foo and name=foo lookup to support query semantics.
            return {"dummy": "get_all", "kwargs": str(kwargs)}

    @wsexpose(LiveActionAPI, body=LiveActionAPI, status_code=httplib.CREATED)
    def post(self, live_action):
        """
            Create a new LiveAction.

            Handles requests:
                POST /liveactions/
        """

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

    @wsexpose(None, wstypes.text)
    def delete(self, id):
        """
            Delete a LiveAction.

            Handles requests:
                POST /liveactions/1?_method=delete
                DELETE /liveactions/1
        """

        abort(httplib.NOT_IMPLEMENTED)

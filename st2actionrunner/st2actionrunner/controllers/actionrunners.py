import httplib
from pecan import (abort, expose, )
from pecan.rest import RestController

from wsme import types as wstypes
from wsmeext.pecan import wsexpose

from st2common import log as logging
from st2common.persistence.action import LiveAction
from st2common.models.api.actionrunner import ActionRunnerAPI


LOG = logging.getLogger('st2actionrunner')


class ActionRunnersController(RestController):
    """
        Implements the RESTful web endpoint that handles
        the lifecycle of an ActionRunner in the system.
    """

    @wsexpose(ActionRunnerAPI, wstypes.text)
    def get_one(self, id):
        """
            List ActionRunners by id.

            Handle:
                GET /actionrunners/1
        """

        # TODO: test/handle object not found.
        return {'actionrunner': 'get %s' % id}

    @expose('json')
    def get_all(self):
        """
            List all ActionRunners.

            Handles requests:
                GET /actionrunners/
        """

        # TODO: Implement function
        # TODO: Implement if=foo and name=bar based lookup to support query semantics.
        return {"dummy": "get_all"}

    @wsexpose(ActionRunnerAPI, body=ActionRunnerAPI)
    def post(self, action_runner):
        """
            Create a new ActionRunner.

            Handles requests:
                POST /actionrunners/
        """

        return {'actionrunner': 'post %s' % action_runner}

    @expose('json')
    def put(self, id, **kwargs):
        """
            Update not supported for ActionRunners.

            Handles requests:
                POST /actionrunners/1?_method=put
                PUT /actionrunners/1
        """
        abort(httplib.METHOD_NOT_ALLOWED)

    @wsexpose(None, wstypes.text)
    def delete(self, id):
        """
            Delete an ActionRunner.

            Handles requests:
                POST /actionrunners/1?_method=delete
                DELETE /actionrunners/1
        """

        # TODO: Support delete by name

        return {'delete': 'by %s' % id}

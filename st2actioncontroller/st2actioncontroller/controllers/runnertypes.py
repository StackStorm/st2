import httplib
from pecan import abort
from pecan.rest import RestController

from wsme import types as wstypes
import wsmeext.pecan as wsme_pecan

from st2common import log as logging
from st2common.exceptions.db import StackStormDBObjectNotFoundError
from st2common.models.api.action import RunnerTypeAPI
from st2common.persistence.action import RunnerType
from st2common.util.action_db import get_runnertype_by_id


LOG = logging.getLogger(__name__)


class RunnerTypesController(RestController):
    """
        Implements the RESTful web endpoint that handles
        the lifecycle of an RunnerType in the system.
    """
    @wsme_pecan.wsexpose(RunnerTypeAPI, wstypes.text)
    def get_one(self, id):
        """
            List RunnerType objects by id.

            Handle:
                GET /runnertypes/1
        """

        LOG.info('GET /runnertypes/ with id=%s', id)

        try:
            runnertype_db = get_runnertype_by_id(id)
        except StackStormDBObjectNotFoundError as e:
            LOG.error('GET /runnertypes/ with id="%s": %s', id, e.message)
            abort(httplib.NOT_FOUND)
        runnertype_api = RunnerTypeAPI.from_model(runnertype_db)

        LOG.debug('GET /runnertypes/ with id=%s, client_result=%s', id, runnertype_api)
        return runnertype_api

    @wsme_pecan.wsexpose([RunnerTypeAPI])
    def get_all(self):
        """
            List all RunnerType objects.

            Handles requests:
                GET /runnertypes/
        """

        LOG.info('GET all /runnertypes/')

        runnertype_apis = [RunnerTypeAPI.from_model(runnertype_db)
                           for runnertype_db in RunnerType.get_all()]

        # TODO: Unpack list in log message
        LOG.debug('GET all /runnertypes/ client_result=%s', runnertype_apis)
        return runnertype_apis

    @wsme_pecan.wsexpose(RunnerTypeAPI, body=RunnerTypeAPI)
    def post(self, runnertype):
        """
            Update not supported for RunnerType.

            Create a new RunnerType object.

            Handles requests:
                POST /runnertypes/
        """

        abort(httplib.NOT_IMPLEMENTED)

    @wsme_pecan.wsexpose(RunnerTypeAPI, body=RunnerTypeAPI,
                         status_code=httplib.NOT_IMPLEMENTED)
    def put(self, action):
        """
            Update not supported for RunnerType.

            Handles requests:
                POST /runnertypes/1?_method=put
                PUT /runnertypes/1
        """

        abort(httplib.METHOD_NOT_ALLOWED)

    @wsme_pecan.wsexpose(None, status_code=httplib.NOT_IMPLEMENTED)
    def delete(self):
        """
            Delete an RunnerType.

            Handles requests:
                POST /runnertypes/1?_method=delete
                DELETE /runnertypes/1
        """

        # TODO: Support delete by name
        abort(httplib.NOT_IMPLEMENTED)

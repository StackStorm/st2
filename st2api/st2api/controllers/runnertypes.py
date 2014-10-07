from mongoengine import ValidationError
from pecan import abort
from pecan.rest import RestController
import six

from st2common import log as logging
from st2common.models.base import jsexpose
from st2common.models.api.action import RunnerTypeAPI
from st2common.persistence.action import RunnerType

http_client = six.moves.http_client

LOG = logging.getLogger(__name__)


class RunnerTypesController(RestController):
    """
        Implements the RESTful web endpoint that handles
        the lifecycle of an RunnerType in the system.
    """

    @staticmethod
    def __get_by_id(id):
        try:
            return RunnerType.get_by_id(id)
        except (ValueError, ValidationError) as e:
            msg = 'Database lookup for id="%s" resulted in exception. %s' % (id, e)
            LOG.exception(msg)
            abort(http_client.NOT_FOUND, msg)

    @staticmethod
    def __get_by_name(name):
        try:
            return [RunnerType.get_by_name(name)]
        except ValueError as e:
            LOG.debug('Database lookup for name="%s" resulted in exception : %s.', name, e)
            return []

    @jsexpose(str)
    def get_one(self, id):
        """
            List RunnerType objects by id.

            Handle:
                GET /runnertypes/1
        """
        LOG.info('GET /runnertypes/ with id=%s', id)
        runnertype_db = RunnerTypesController.__get_by_id(id)
        runnertype_api = RunnerTypeAPI.from_model(runnertype_db)
        LOG.debug('GET /runnertypes/ with id=%s, client_result=%s', id, runnertype_api)
        return runnertype_api

    @jsexpose(str)
    def get_all(self, **kw):
        """
            List all RunnerType objects.

            Handles requests:
                GET /runnertypes/
        """
        LOG.info('GET all /runnertypes/ with filters=%s', kw)
        runnertype_dbs = RunnerType.get_all(**kw)
        runnertype_apis = [RunnerTypeAPI.from_model(runnertype_db)
                           for runnertype_db in runnertype_dbs]
        LOG.debug('GET all /runnertypes/ client_result=%s', runnertype_apis)
        return runnertype_apis

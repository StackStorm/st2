import httplib
from pecan import expose, abort
from pecan.rest import RestController
from st2common import log as logging
import wsme.types
import wsmeext.pecan

from mirantis.resource import Resource

from st2reactor.container.base import get_sensor_container


LOG = logging.getLogger(__name__)


class SensorAPI(Resource):
    schema = wsme.types.text
    name = wsme.types.text
    artifact_url = wsme.types.text
    artifact_sha = wsme.types.text
    trigger_types = wsme.types.ArrayType(wsme.types.text)
    config_schema = wsme.types.text


class SensorController(RestController):
    """
        Implements the RESTful web endpoint that handles
        the custom sensors in the system.
    """
    @expose()
    def _lookup(self, primary_key, *remainder):
        hook = get_sensor_container().get_sensor_webhook(primary_key)
        if hook:
            return hook(), remainder
        else:
            abort(httplib.NOT_FOUND)

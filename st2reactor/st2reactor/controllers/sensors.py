from pecan import expose, abort
from pecan.rest import RestController
from st2common import log as logging

from st2reactor.container.base import get_sensor_container


LOG = logging.getLogger(__name__)


class SensorController(RestController):
    """
        Implements the RESTful web endpoint that handles
        the custom sensors in the system.
    """
    @expose()
    def _lookup(self, primary_key, *remainder):
        print('->', primary_key, remainder)
        hook = get_sensor_container().get_sensor_webhook(primary_key)
        if hook:
            return hook(), remainder
        else:
            abort(404)

import six
from pecan import abort
from pecan.rest import RestController
from mongoengine import ValidationError

from st2common import log as logging
from st2common.persistence.reactor import SensorType
from st2common.models.base import jsexpose
from st2common.models.api.reactor import SensorTypeAPI

http_client = six.moves.http_client

LOG = logging.getLogger(__name__)


class SensorTypeController(RestController):
    @jsexpose(str)
    def get_one(self, id):
        """
            Get sensortype by id.

            Handle:
                GET /sensortype/1
        """
        LOG.info('GET /sensortype/ with id=%s', id)

        try:
            sensor_type_db = SensorType.get_by_id(id)
        except (ValueError, ValidationError):
            LOG.exception('Database lookup for id="%s" resulted in exception.', id)
            abort(http_client.NOT_FOUND)
            return

        sensor_type_api = SensorTypeAPI.from_model(sensor_type_db)
        LOG.debug('GET /sensortype/ with id=%s, client_result=%s', id, sensor_type_api)
        return sensor_type_api

    @jsexpose(str)
    def get_all(self, **kw):
        """
            List all sensor types.

            Handles requests:
                GET /sensortypes/
        """
        LOG.info('GET all /sensortypes/ with filters=%s', kw)
        sensor_type_dbs = SensorType.get_all(**kw)
        sensor_type_apis = [SensorTypeAPI.from_model(sensor_type_db) for sensor_type_db
                            in sensor_type_dbs]
        return sensor_type_apis

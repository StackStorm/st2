import six
from st2common import log as logging
from st2common.persistence.reactor import SensorType
from st2common.models.api.reactor import SensorTypeAPI
from st2api.controllers.resource import ResourceController

http_client = six.moves.http_client

LOG = logging.getLogger(__name__)


class SensorTypeController(ResourceController):
    model = SensorTypeAPI
    access = SensorType
    supported_filters = {
        'name': 'name',
        'pack': 'content_pack'
    }

    options = {
        'sort': ['content_pack', 'name']
    }

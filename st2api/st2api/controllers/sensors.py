import six
from st2common import log as logging
from st2common.persistence.reactor import SensorType
from st2common.models.api.reactor import SensorTypeAPI
from st2api.controllers import resource

http_client = six.moves.http_client

LOG = logging.getLogger(__name__)


class SensorTypeController(resource.ContentPackResourceControler):
    model = SensorTypeAPI
    access = SensorType
    supported_filters = {
        'name': 'name',
        'pack': 'pack'
    }

    options = {
        'sort': ['pack', 'name']
    }

    include_reference = True

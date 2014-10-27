import six
from st2common import log as logging
from st2common.persistence.reactor import SensorType
from st2common.models.api.reactor import SensorTypeAPI
from st2common.models.base import jsexpose
from st2api.controllers import resource

http_client = six.moves.http_client

LOG = logging.getLogger(__name__)


class SensorTypeController(resource.ResourceController):
    model = SensorTypeAPI
    access = SensorType
    supported_filters = {
        'name': 'name',
        'pack': 'pack'
    }

    options = {
        'sort': ['pack', 'name']
    }

    @jsexpose()
    @resource.referenced
    def get_all(self, **kwargs):
        return super(SensorTypeController, self)._get_all(**kwargs)

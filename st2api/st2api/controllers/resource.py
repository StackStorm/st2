import copy

import six
import pecan
from six.moves import http_client

from st2common.models.base import jsexpose
from st2common import log as logging


LOG = logging.getLogger(__name__)


class ResourceManager(object):

    def __init__(self, model, access):
        self.model = model
        self.access = access

    def get_all(self, *args, **kwargs):
        instances = self.access.get_all(*args, **kwargs)
        resources = [self.model.from_model(instance) for instance in instances]
        return resources

    def get(self, *args, **kwargs):
        instance = self.access.get(*args, **kwargs)
        return self.model.from_model(instance) if instance else None


class QueryMixin(object):

    supported_filters = {
        'id': 'id',
        'name': 'name',
        'sort': 'order_by',
        'offset': 'offset',
        'limit': 'limit'
    }

    def __init__(self, manager, supported_filters):
        self.manager = manager
        self.supported_filters = copy.deepcopy(self.__class__.supported_filters)
        self.supported_filters.update(supported_filters)

    @jsexpose()
    def get_all(self, **kwargs):
        filters = {v: kwargs[k] for k, v in six.iteritems(self.supported_filters) if kwargs.get(k)}
        return self.manager.get_all(**filters)

    @jsexpose(str)
    def get_one(self, id):
        instance = self.manager.get(id=id)
        if not instance:
            msg = 'Unable to identify resource with id "%s".' % id
            pecan.abort(http_client.NOT_FOUND, msg)
        return instance

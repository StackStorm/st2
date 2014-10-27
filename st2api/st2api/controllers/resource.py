import abc
import copy

from mongoengine import ValidationError
import pecan
from pecan import rest
import six
from six.moves import http_client

from st2common.models.base import jsexpose
from st2common import log as logging
from st2common.models.system.common import InvalidResourceReferenceError
from st2common.models.system.common import ResourceReference


LOG = logging.getLogger(__name__)

RESERVED_QUERY_PARAMS = {
    'id': 'id',
    'name': 'name',
    'sort': 'order_by'
}


@six.add_metaclass(abc.ABCMeta)
class ResourceController(rest.RestController):
    model = abc.abstractproperty
    access = abc.abstractproperty
    supported_filters = abc.abstractproperty

    query_options = {   # Do not use options.
        'sort': []
    }
    max_limit = 100

    def __init__(self):
        self.supported_filters = copy.deepcopy(self.__class__.supported_filters)
        self.supported_filters.update(RESERVED_QUERY_PARAMS)

    @jsexpose()
    def get_all(self, **kwargs):
        return self._get_all(**kwargs)

    @jsexpose(str)
    def get_one(self, id):
        LOG.info('GET %s with id=%s', pecan.request.path, id)

        instance = None
        try:
            instance = self.access.get(id=id)
        except ValidationError:
            instance = None  # Someone supplied a mongo non-comformant id.

        if not instance:
            msg = 'Unable to identify resource with id "%s".' % id
            pecan.abort(http_client.NOT_FOUND, msg)

        result = self.model.from_model(instance)
        LOG.debug('GET %s with id=%s, client_result=%s', pecan.request.path, id, result)

        return result

    def _get_all(self, **kwargs):
        sort = kwargs.get('sort').split(',') if kwargs.get('sort') else []
        for i in range(len(sort)):
            sort.pop(i)
            direction = '-' if sort[i].startswith('-') else ''
            sort.insert(i, direction + self.supported_filters[sort[i]])
        kwargs['sort'] = sort if sort else copy.copy(self.query_options.get('sort'))

        # TODO: To protect us from DoS, we need to make max_limit mandatory
        offset = int(kwargs.pop('offset', 0))
        limit = kwargs.pop('limit', None)
        if limit and int(limit) > self.max_limit:
            limit = self.max_limit
        eop = offset + int(limit) if limit else None

        filters = {}

        for k, v in six.iteritems(self.supported_filters):
            if kwargs.get(k):
                filters['__'.join(v.split('.'))] = kwargs[k]

        LOG.info('GET all %s with filters=%s', pecan.request.path, filters)

        instances = self.access.query(**filters)

        if limit:
            pecan.response.headers['X-Limit'] = str(limit)
        pecan.response.headers['X-Total-Count'] = str(len(instances))

        return [self.model.from_model(instance) for instance in instances[offset:eop]]


def referenced(f):
    def decorate(*args, **kwargs):
        ref = kwargs.get('ref', None)

        if ref:
            try:
                ref_obj = ResourceReference.from_string_reference(ref=ref)
            except InvalidResourceReferenceError:
                # Invalid reference
                return []

            kwargs['name'] = ref_obj.name
            kwargs['pack'] = ref_obj.pack
            del kwargs['ref']

        return f(*args, **kwargs)

    return decorate

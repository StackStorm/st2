import json
import logging

from st2client.utils import httpclient


LOG = logging.getLogger(__name__)


class Resource(object):

    _plural = 'Resources'

    def __init__(self, *args, **kwargs):
        for k, v in kwargs.iteritems():
            setattr(self, k, v)

    def serialize(self):
        return dict((k, v)
                    for k, v in self.__dict__.iteritems()
                    if not k.startswith('_'))

    @classmethod
    def deserialize(cls, doc):
        if type(doc) is not dict:
            doc = json.loads(doc)
        return cls(**doc)


class ResourceManager(object):

    def __init__(self, resource, endpoint, read_only=False):
        self.endpoint = endpoint
        self.resource = resource
        self.read_only = read_only
        self.client = httpclient.HTTPClient(self.endpoint)

    def get_all(self):
        url = '/%s' % self.resource._plural.lower()
        LOG.info('GET %s/%s' % (self.endpoint, url))
        response = self.client.get(url)
        if response.status_code != 200:
            response.raise_for_status()
        return [self.resource.deserialize(item)
                for item in response.json()]

    def get_by_id(self, id):
        url = '/%s/%s' % (self.resource._plural.lower(), id)
        LOG.info('GET %s/%s' % (self.endpoint, url))
        response = self.client.get(url)
        if response.status_code == 404:
            return None
        if response.status_code != 200:
            response.raise_for_status()
        return self.resource.deserialize(response.json())

    def query(self, *args, **kwargs):
        if not kwargs:
            raise Exception('Search parameter is not provided.')
        url = '/%s/?' % self.resource._plural.lower()
        for k, v in kwargs.iteritems():
            url += '%s%s=%s' % (('&' if url[-1] != '?' else ''), k, v)
        LOG.info('GET %s/%s' % (self.endpoint, url))
        response = self.client.get(url)
        if response.status_code == 404:
            return []
        if response.status_code != 200:
            response.raise_for_status()
        items = response.json()
        instances = [self.resource.deserialize(item) for item in items]
        return instances

    def get_by_name(self, name):
        instances = self.query(name=name)
        if not instances:
            return None
        else:
            if len(instances) > 1:
                raise Exception('More than one %s named "%s" are found.' %
                                (self.resource.__name__.lower(), name))
            return instances[0]

    def create(self, instance):
        url = '/%s' % self.resource._plural.lower()
        LOG.info('POST %s/%s' % (self.endpoint, url))
        response = self.client.post(url, instance.serialize())
        if response.status_code != 200:
            response.raise_for_status()
        instance = self.resource.deserialize(response.json())
        return instance

    def update(self, instance):
        url = '/%s/%s' % (self.resource._plural.lower(), instance.id)
        LOG.info('PUT %s/%s' % (self.endpoint, url))
        response = self.client.put(url, instance.serialize())
        if response.status_code != 200:
            response.raise_for_status()
        instance = self.resource.deserialize(response.json())
        return instance

    def delete(self, instance):
        url = '/%s/%s' % (self.resource._plural.lower(), instance.id)
        LOG.info('DELETE %s/%s' % (self.endpoint, url))
        response = self.client.delete(url)
        if response.status_code not in (204, 404):
            response.raise_for_status()

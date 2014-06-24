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
        if response.status_code != 200:
            response.raise_for_status()
        return self.resource.deserialize(response.json())

    def get_by_name(self, name):
        url = '/%s/?name=%s' % (self.resource._plural.lower(), name)
        LOG.info('GET %s/%s' % (self.endpoint, url))
        response = self.client.get(url)
        if response.status_code != 200:
            response.raise_for_status()
        items = response.json()
        instance = (self.resource.deserialize(response.json()[0])
                    if len(items) == 1 else None)
        return instance

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

    def delete(self, id):
        url = '/%s/%s' % (self.resource._plural.lower(), id)
        LOG.info('DELETE %s/%s' % (self.endpoint, url))
        response = self.client.delete(url)
        if response.status_code != 204:
            response.raise_for_status()

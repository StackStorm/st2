import json
import logging

from st2client.utils import httpclient


LOG = logging.getLogger(__name__)


class Resource(object):

    # An alias to use for the resource if different than the class name.
    _alias = None

    # Display name of the resource. This may be different than its resource
    # name specifically when the resource name is composed of multiple words.
    _display_name = None

    # Plural form of the resource name. This will be used to build the
    # latter part of the REST URL.
    _plural = None

    # Plural form of the resource display name.
    _plural_display_name = None

    def __init__(self, *args, **kwargs):
        for k, v in kwargs.iteritems():
            setattr(self, k, v)

    @classmethod
    def get_alias(cls):
        return cls._alias if cls._alias else cls.__name__

    @classmethod
    def get_display_name(cls):
        return cls._display_name if cls._display_name else cls.__name__

    @classmethod
    def get_plural_name(cls):
        if not cls._plural:
            raise Exception('The %s class is missing class attributes '
                            'in its definition.' % cls.__name__)
        return cls._plural

    @classmethod
    def get_plural_display_name(cls):
        return (cls._plural_display_name
                if cls._plural_display_name
                else cls._plural)

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

    def get_all(self, *args, **kwargs):
        url = '/%s' % self.resource.get_plural_name().lower()
        limit = kwargs.get('limit', None)
        if limit and limit <= 0:
            limit = None
        if limit:
            url += '/?limit=%s' % limit
        LOG.info('GET %s/%s' % (self.endpoint, url))
        response = self.client.get(url)
        if response.status_code != 200:
            response.raise_for_status()
        return [self.resource.deserialize(item)
                for item in response.json()]

    def get_by_id(self, id):
        url = '/%s/%s' % (self.resource.get_plural_name().lower(), id)
        LOG.info('GET %s/%s' % (self.endpoint, url))
        response = self.client.get(url)
        if response.status_code == 404:
            return None
        if response.status_code != 200:
            response.raise_for_status()
        return self.resource.deserialize(response.json())

    def query(self, *args, **kwargs):
        if not kwargs:
            raise Exception('Query parameter is not provided.')
        if 'limit' in kwargs and kwargs.get('limit') <= 0:
            kwargs.pop('limit')
        url = '/%s/?' % self.resource.get_plural_name().lower()
        for k, v in kwargs.iteritems():
            url += '%s%s=%s' % (('&' if url[-1] != '?' else ''), k, v)
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
        url = '/%s' % self.resource.get_plural_name().lower()
        LOG.info('POST %s/%s' % (self.endpoint, url))
        response = self.client.post(url, instance.serialize())
        if response.status_code != 200:
            response.raise_for_status()
        instance = self.resource.deserialize(response.json())
        return instance

    def update(self, instance):
        url = '/%s/%s' % (self.resource.get_plural_name().lower(), instance.id)
        LOG.info('PUT %s/%s' % (self.endpoint, url))
        response = self.client.put(url, instance.serialize())
        if response.status_code != 200:
            response.raise_for_status()
        instance = self.resource.deserialize(response.json())
        return instance

    def delete(self, instance):
        url = '/%s/%s' % (self.resource.get_plural_name().lower(), instance.id)
        LOG.info('DELETE %s/%s' % (self.endpoint, url))
        response = self.client.delete(url)
        if response.status_code not in (204, 404):
            response.raise_for_status()

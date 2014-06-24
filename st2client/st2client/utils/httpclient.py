import json
import requests
import logging


LOG = logging.getLogger(__name__)


class HTTPClient(object):

    def __init__(self, root):
        self.root = root

    def get(self, url, **kwargs):
        return requests.get(self.root + url, **kwargs)

    def post(self, url, data, **kwargs):
        headers = kwargs.get('headers', {})
        content_type = headers.get('content-type', 'application/json')
        headers['content-type'] = content_type
        return requests.post(self.root + url,
                             json.dumps(data),
                             headers=headers)

    def put(self, url, data, **kwargs):
        return requests.put(self.root + url, data, **kwargs)

    def patch(self, url, data, **kwargs):
        return requests.patch(self.root + url, data, **kwargs)

    def delete(self, url, **kwargs):
        return requests.delete(self.root + url, **kwargs)

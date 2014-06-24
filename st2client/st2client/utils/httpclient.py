# -*- coding: utf-8 -*-
#
#    Licensed under the Apache License, Version 2.0 (the "License");
#    you may not use this file except in compliance with the License.
#    You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS,
#    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#    See the License for the specific language governing permissions and
#    limitations under the License.

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
